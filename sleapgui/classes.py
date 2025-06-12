import os
import sys
import subprocess
import pandas as pd
from multiprocessing import Pool, cpu_count
import psutil
import GPUtil
import tensorflow as tf
from pathlib import Path, PureWindowsPath
import logging
import json

# =====================================================================================
# Top-level Worker Function for Multiprocessing
# =====================================================================================
# This function is defined at the top level of the module so that it can be
# "pickled" and sent to child processes by the multiprocessing.Pool.
def _process_video_worker(args):
    """
    Worker function that processes a single video file. It runs in a separate process.

    Args:
        args (tuple): A tuple containing all necessary parameters to process one video.
    """
    # 1. Unpack arguments. Paths are passed as strings for robust pickling.
    (
        video_file,
        input_folder_str,
        output_folder_str,
        model_type,
        model_path_str,
        optional_args,
        log_file_path_str,
    ) = args

    # 2. Reconstruct Path objects within the worker process.
    input_folder = Path(input_folder_str)
    output_folder = Path(output_folder_str)
    model_path = Path(model_path_str)
    log_file_path = Path(log_file_path_str)

    # 3. Set up a logger for this specific worker process.
    # This allows each process to write to the central log file.
    worker_logger = logging.getLogger(f"worker_{os.getpid()}")
    worker_logger.setLevel(logging.INFO)
    if not worker_logger.handlers:
        # FileHandler in append mode ('a') is generally safe for multiple processes.
        handler = logging.FileHandler(log_file_path, "a")
        formatter = logging.Formatter(
            "%(asctime)s - %(processName)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        worker_logger.addHandler(handler)

    def handle_subprocess_worker(command):
        """A simple subprocess handler for the worker."""
        worker_logger.info("Running command: %s", command)
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=False
        )
        if result.stdout:
            worker_logger.info("Command STDOUT: %s", result.stdout.strip())
        if result.stderr:
            worker_logger.error("Command STDERR: %s", result.stderr.strip())
        return f"STDOUT: {result.stdout.strip()}\nSTDERR: {result.stderr.strip()}"

    # 4. Define all paths and commands for SLEAP.
    worker_logger.info("Worker started for video: %s", video_file)
    all_output = [f"--- Processing: {video_file} with model: {model_type} ---"]

    input_path = Path.as_posix(input_folder / video_file)
    output_slp_path = Path.as_posix(output_folder / f"{video_file}.{model_type}.slp")
    output_h5_path = Path.as_posix(output_folder / f"{video_file}.{model_type}.h5")
    output_mp4_path = Path.as_posix(output_folder / f"{video_file}.{model_type}.mp4")
    model = Path.as_posix(model_path)

    # 5. Execute SLEAP commands sequentially.
    # Step A: Track poses with sleap-track
    if Path(input_path).is_file():
        if optional_args:
            track_command = f'sleap-track -m "{model}" -o "{output_slp_path}" {optional_args} "{input_path}"'
        else:
            track_command = f'sleap-track -m "{model}" -o "{output_slp_path}" "{input_path}"'
        all_output.append(f"TRACK:\n{handle_subprocess_worker(track_command)}")
    else:
        msg = f"ERROR: Input video file not found, cannot track. Path: {input_path}"
        worker_logger.error(msg)
        all_output.append(msg)

    # Step B: Convert to H5 format
    if Path(output_slp_path).is_file():
        h5_command = f'sleap-convert -o "{output_h5_path}" --format analysis "{output_slp_path}"'
        all_output.append(f"CONVERT:\n{handle_subprocess_worker(h5_command)}")
    else:
        msg = f"WARNING: SLP file not found, skipping conversion. Path: {output_slp_path}"
        worker_logger.warning(msg)
        all_output.append(msg)

    # Step C: Render tracked video
    if Path(output_slp_path).is_file():
        render_command = f'sleap-render -o "{output_mp4_path}" -f 50 "{output_slp_path}"'
        all_output.append(f"RENDER:\n{handle_subprocess_worker(render_command)}")
    else:
        msg = f"WARNING: SLP file not found, skipping render. Path: {output_slp_path}"
        worker_logger.warning(msg)
        all_output.append(msg)

    # 6. Prepare and return the final status string for this worker.
    nl = "\n"
    names = [output_slp_path, output_h5_path, output_mp4_path]
    final_status = f"Finished processing for {video_file}.\nCreated files:\n{nl.join(names)}"
    all_output.append(final_status)
    worker_logger.info("Worker finished for video: %s", video_file)

    return "\n\n".join(all_output)


class SleapProcessor:
    """
    A class to process videos using Sleap for pose estimation.
    """

    def __init__(self, update_status_callback):
        self.update_status_callback = update_status_callback
        self.file_path = Path()
        self.animal_type = []
        self.csv_path = Path()
        self.optional_args = ""
        self.config_path = Path()
        self.chosen_model = Path()
        self.paths_csv = Path()
        self.num_processes = 2
        self.log_file_path = Path("tracked/sleap_commands.log")
        env_dir = Path(sys.prefix)
        self.config_path = env_dir / "autosleap_config.json"

    def read_config(self):
        if self.config_path.exists() and os.path.getsize(self.config_path) > 0:
            with open(self.config_path, "r") as f:
                data = json.load(f)
            self.file_path = Path(data["file_path"])
            self.animal_type = data["animal_type"]
            self.csv_path = Path(data["csv_path"])
            self.optional_args = data["optional_args"]
            self.paths_csv = Path(data["csv_path"])
            self.log_file_path = Path(data.get("log_file_path", "tracked/sleap_commands.log"))
            self.chosen_model = Path(data["chosen_model"])
            self.model_prefix = data["model_prefix"]
        else:
            raise FileNotFoundError("Configuration file not found or is empty.")

    def start_logger(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.handlers = []
        if self.log_file_path:
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_file_path.touch(exist_ok=True)
            handler = logging.FileHandler(self.log_file_path, "a")
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                "%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        else:
            raise ValueError("Log file path is not set.")

    def get_num_processes(self, GPU_GB_limit=None):
        try:
            ram = psutil.virtual_memory()
            total_ram = ram.available / (1024**3)
            gpus = GPUtil.getGPUs()
            total_vram = round(gpus[0].memoryFree) / 1024 if gpus else float('inf')
        except Exception as e:
            self.update_status_callback(f"Could not get system stats, defaulting to 1 process. Error: {e}")
            return 1

        if GPU_GB_limit is None:
            GPU_GB_limit = 12
        CPU_GB_limit = 5
        num_processes = min(
            round(total_ram / CPU_GB_limit), round(total_vram / GPU_GB_limit)
        )
        if num_processes < 1:
            num_processes = 1
        self.num_processes = num_processes
        return num_processes

    def reset_gpu_memory(self):
        tf.keras.backend.clear_session()

    def find_model_path_from_csv(self, model_type, csv_path=None):
        if csv_path is None:
            csv_path = self.paths_csv
        model_paths_df = pd.read_csv(
            csv_path, engine="python", sep=",", encoding="cp437"
        )
        model_paths_df["path to model folder"] = model_paths_df["path to model folder"]
        model_paths = model_paths_df.set_index("model type").to_dict()[
            "path to model folder"
        ]
        current_path = model_paths.get(model_type)
        return current_path

    def process_files(self, video_files, input_folder, output_folder, model_type, model_path):
        """
        Manages the processing of video files, using multiprocessing for batches.
        """
        # Prepare arguments for the worker function. Pass paths as strings.
        pool_args = [
            (
                video_file,
                str(input_folder),
                str(output_folder),
                model_type,
                str(model_path),
                self.optional_args,
                str(self.log_file_path),
            )
            for video_file in video_files
        ]

        # Case 1: A single file is being processed.
        # Run it directly in the current process without creating a pool.
        if len(video_files) == 1:
            self.update_status_callback("Processing single file...")
            result = _process_video_worker(pool_args[0])
            self.update_status_callback(result)
        else:
            num_processes = self.get_num_processes()
            max_cores = cpu_count()
            if num_processes > max_cores:
                num_processes = max_cores / 2
            if num_processes > len(video_files):
                num_processes = len(video_files)
        
            self.update_status_callback(f"Starting processing pool with {num_processes} parallel process(es)...")
        
            try:
                with Pool(processes=num_processes) as pool:
                    results = pool.map(_process_video_worker, pool_args)
                
                self.update_status_callback("\n--- All parallel processes finished. Results: ---")
                for result in results:
                    self.update_status_callback(result)
                    self.update_status_callback("=" * 60)
            except Exception as e:
                error_message = f"A multiprocessing error occurred: {e}"
                self.update_status_callback(error_message)
                self.logger.error(error_message, exc_info=True)
        
                # Fallback to serial processing
                self.update_status_callback("Switching to serial processing...")
                results = []
                for arg in pool_args:
                    result = _process_video_worker(arg)
                    results.append(result)
                    self.update_status_callback(result)
                    self.update_status_callback("=" * 60)
        # if len(video_files) == 1:
        #     self.update_status_callback("Processing single file...")
        #     result = _process_video_worker(pool_args[0])
        #     self.update_status_callback(result)
        # # Case 2: Multiple files are being processed.
        # # Use a multiprocessing Pool for parallel execution.
        # else:
        #     num_processes = self.get_num_processes()
        #     # As a fail-safe, don't use more processes than available CPU cores.
        #     max_cores = cpu_count()
        #     if num_processes > max_cores:
        #         num_processes = max_cores/2
        #     if num_processes > len(video_files):
        #         num_processes = len(video_files)
            
        #     self.update_status_callback(f"Starting processing pool with {num_processes} parallel process(es)...")

        #     try:
        #         with Pool(processes=2) as pool:
        #             # map() distributes the arguments in pool_args to the worker function.
        #             results = pool.map(_process_video_worker, pool_args)
                
        #         # After all workers are done, report their collected results to the GUI.
        #         self.update_status_callback("\n--- All parallel processes finished. Results: ---")
        #         for result in results:
        #             self.update_status_callback(result)
        #             self.update_status_callback("=" * 60)
        #     except Exception as e:
        #         error_message = f"A multiprocessing error occurred: {e}"
        #         self.update_status_callback(error_message)
        #         self.logger.error(error_message, exc_info=True)

    def run_sleap(self):
        suffix = "tracked"
        input_path = self.file_path
        csv_path = self.csv_path
        chosen_model = self.chosen_model
        model_prefix = self.model_prefix
        model_types = self.animal_type

        if Path.is_dir(chosen_model):
            model_types = model_prefix
            csv_path = chosen_model

        if not isinstance(model_types, list):
            model_types = [model_types]

        self.update_status_callback(f"Models to be processed: {model_types}")

        P = Path(input_path)
        if P.is_dir():
            input_folder = P
            video_files = [
                f
                for f in os.listdir(input_folder)
                if f.endswith((".mp4", ".avi"))
            ]
        else:
            input_folder = P.parent
            video_files = [P.name]
        
        output_folder = input_folder / suffix
        output_folder.mkdir(exist_ok=True)
        
        self.update_status_callback(f"Found {len(video_files)} video(s) to process.")

        for model_type in model_types:
            self.update_status_callback(f"--- Starting process for model: {model_type} ---")
            if Path(csv_path).is_dir():
                model_path = csv_path
            else:
                model_path = self.find_model_path_from_csv(model_type, csv_path)

            if not model_path or not Path(model_path).exists():
                self.update_status_callback(f"ERROR: Model path not found for '{model_type}'. Skipping.")
                continue

            self.update_status_callback(f"Using model path: {model_path}")
            
            self.process_files(
                video_files, input_folder, output_folder, model_type, model_path
            )
        
        # FIXED: Moved the return statement outside the loop.
        return "Finished running all files for all selected models."
