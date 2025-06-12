import os
import sys
import subprocess
import pandas as pd
from multiprocessing import Pool, cpu_count
import psutil
import GPUtil
import tensorflow as tf
from pathlib import Path
import logging
import json
import tqdm

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
    worker_logger = logging.getLogger(f"worker_{os.getpid()}")
    worker_logger.setLevel(logging.INFO)
    if not worker_logger.handlers:
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
            command, shell=True, capture_output=True, text=True, check=False, encoding='utf-8'
        )
        if result.stdout:
            worker_logger.info("Command STDOUT: %s", result.stdout.strip())
        if result.stderr:
            worker_logger.error("Command STDERR: %s", result.stderr.strip())
        return f"STDOUT: {result.stdout.strip()}\nSTDERR: {result.stderr.strip()}"

    # 4. Define all paths and commands for SLEAP using .as_posix() for cross-platform compatibility.
    worker_logger.info("Worker started for video: %s", video_file)
    all_output = [f"--- Processing: {video_file} with model: {model_type} ---"]

    input_path = (input_folder / video_file).as_posix()
    output_slp_path = (output_folder / f"{Path(video_file).stem}.{model_type}.slp").as_posix()
    output_h5_path = (output_folder / f"{Path(video_file).stem}.{model_type}.h5").as_posix()
    output_mp4_path = (output_folder / f"{Path(video_file).stem}.{model_type}.mp4").as_posix()
    model = model_path.as_posix()

    # 5. Execute SLEAP commands sequentially.
    if Path(input_path).is_file():
        track_command = f'sleap-track -m "{model}" -o "{output_slp_path}" {optional_args} "{input_path}"'
        all_output.append(f"TRACK:\n{handle_subprocess_worker(track_command)}")
    else:
        msg = f"ERROR: Input video file not found, cannot track. Path: {input_path}"
        worker_logger.error(msg)
        all_output.append(msg)

    if Path(output_slp_path).is_file():
        h5_command = f'sleap-convert -o "{output_h5_path}" --format analysis "{output_slp_path}"'
        all_output.append(f"CONVERT:\n{handle_subprocess_worker(h5_command)}")
    else:
        msg = f"WARNING: SLP file not found, skipping conversion. Path: {output_slp_path}"
        worker_logger.warning(msg)
        all_output.append(msg)

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
        self.num_processes = 1
        self.log_file_path = Path("tracked/sleap_commands.log")
        script_dir = Path(sys.argv[0]).parent
        self.config_path = script_dir / "autosleap_config.json"

    def read_config(self):
        if self.config_path.exists() and os.path.getsize(self.config_path) > 0:
            with open(self.config_path, "r") as f:
                data = json.load(f)
            self.file_path = Path(data["file_path"])
            self.animal_type = data.get("animal_type", [])
            self.csv_path = Path(data["csv_path"])
            self.optional_args = data.get("optional_args", "")
            self.paths_csv = Path(data["csv_path"])
            self.log_file_path = Path(data.get("log_file_path", "tracked/sleap_commands.log"))
            self.chosen_model = Path(data["chosen_model"])
            self.model_prefix = data.get("model_prefix", "")
        else:
            print(f"Info: Configuration file not found at {self.config_path} or is empty.")

    def start_logger(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        # Avoid adding handlers multiple times
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        
        if self.log_file_path:
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(self.log_file_path, "a", encoding='utf-8')
            formatter = logging.Formatter(
                "%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        else:
            print("Warning: Log file path is not set.")

    def get_num_processes(self, GPU_GB_limit=None):
        try:
            ram = psutil.virtual_memory()
            total_ram_gb = ram.available / (1024**3)
            gpus = GPUtil.getGPUs()
            total_vram_gb = (gpus[0].memoryFree / 1024) if gpus else float('inf')
        except Exception as e:
            self.update_status_callback(f"Could not get system stats, defaulting to 1 process. Error: {e}")
            return 1

        GPU_GB_limit = GPU_GB_limit if GPU_GB_limit is not None else 12
        CPU_GB_limit = 5
        
        num_processes_ram = total_ram_gb // CPU_GB_limit
        num_processes_vram = total_vram_gb // GPU_GB_limit
        
        num_processes = int(min(num_processes_ram, num_processes_vram))
        if num_processes < 1:
            num_processes = 1
        
        self.num_processes = num_processes
        return num_processes

    def reset_gpu_memory(self):
        tf.keras.backend.clear_session()

    def find_model_path_from_csv(self, model_type, csv_path):
        if not Path(csv_path).is_file(): return None
        model_paths_df = pd.read_csv(csv_path)
        model_paths = model_paths_df.set_index("model type").to_dict()["path to model folder"]
        return model_paths.get(model_type.strip())

    def process_files(self, video_files, input_folder, output_folder, model_type, model_path):
        pool_args = [
            (
                video_file, str(input_folder), str(output_folder),
                model_type, str(model_path), self.optional_args,
                str(self.log_file_path),
            ) for video_file in video_files
        ]
        
        try:
         if len(video_files) == 1:
            self.update_status_callback("Processing single file...")
            result = _process_video_worker(pool_args[0])
            self.update_status_callback(result)
         else:
          results = []
          for arg in (pool_args):
             print(arg)
             result = _process_video_worker(arg)
             results.append(result)
             self.update_status_callback(result)
             self.update_status_callback("=" * 60)
        except Exception as e:
                self.update_status_callback(f"A multiprocessing error occurred: {e}. Check log for details.")
                self.logger.error(f"Multiprocessing error: {e}", exc_info=True)

    def run_sleap(self):
        suffix = "tracked"
        self.read_config() # Ensure latest config is loaded
        
        input_path = self.file_path
        P = Path(input_path)
        if P.is_dir():
            input_folder = P
            video_files = [f for f in os.listdir(input_folder) if f.lower().endswith((".mp4", ".avi"))]
        elif P.is_file():
            input_folder = P.parent
            video_files = [P.name]
        else:
            return f"Error: Input path is not a valid file or directory: {input_path}"
        
        output_folder = input_folder / suffix
        output_folder.mkdir(exist_ok=True)
        self.update_status_callback(f"Found {len(video_files)} video(s) to process.")
        
        # Determine model types and paths
        model_types_to_process = self.animal_type
        if Path(self.chosen_model).is_dir(): # Manual mode
            model_path = self.chosen_model
            model_type = self.model_prefix
            if not all([model_path, model_type]):
                 return "Error: In manual mode, both model path and prefix must be set."
            self.update_status_callback(f"--- Starting manual process for model: {model_type} ---")
            if not Path(model_path).exists():
                return f"ERROR: Manual model path not found: '{model_path}'"
            self.update_status_callback(f"Using model path: {model_path}")
            self.process_files(video_files, input_folder, output_folder, model_type, model_path)
        else: # CSV mode
            self.update_status_callback(f"--- Starting CSV process for models: {model_types_to_process} ---")
            for model_type in model_types_to_process:
                model_type = model_type.strip()
                model_path = self.find_model_path_from_csv(model_type, self.csv_path)
                if not model_path or not Path(model_path).exists():
                    self.update_status_callback(f"ERROR: Model path for '{model_type}' not found or is invalid. Skipping.")
                    continue
                self.update_status_callback(f"Processing with model '{model_type}' from path: {model_path}")
                self.process_files(video_files, input_folder, output_folder, model_type, Path(model_path))
        
        return "Finished running all files for all selected models."
