import os
import IPython
import sys
import subprocess
from pathlib import Path
import pandas as pd
import multiprocessing
from multiprocessing import Pool
import psutil
import GPUtil
import tensorflow as tf
from pathlib import Path, PureWindowsPath



class FailedCommands:
    """
    A class to store failed commands and the path of where to save as a text file.
    """
    def __init__(self):
        self.path = []  # Path to save the text file
        self.commands = []  # List to store failed commands
        self.results = []

class SleapProcessor:
    """
    A class to process videos using Sleap for pose estimation.
    """
    def __init__(self):
        self.failed_commands = (
            FailedCommands()
        )  # Initialize the failed commands tracker
        self.paths_csv=[]
        self.num_processes=[]

    def get_num_processes(self):
        """
        Define the number of processes based on RAM and VRAM.
        Returns:
            num_processes (int): The number of processes to use.
        """
        ram = psutil.virtual_memory()  # Get RAM
        total_ram = ram.available / (1024**3)  # Convert bytes to GB

        # Get GPU VRAM
        gpus = GPUtil.getGPUs()
        total_vram = round(gpus[0].memoryFree) / (1024)  # Convert bytes to GB
        # Assuming one GPU, adjust if multiple GPUs

        # Define the number of processes based on RAM and VRAM
        GPU_GB_limit = 10  # Limit the GPU memory to 12GB
        # cricket model takes ~7GB VRAN to run on batch size = 4

        CPU_GB_limit = 5  # Limit the CPU memory to 12GB

        num_processes = min(
            round(total_ram / CPU_GB_limit), round(total_vram / GPU_GB_limit)
        )
        # case something went wrong:
        if num_processes <= 1:
            num_processes = 1
            
        self.num_processes=num_processes
        return num_processes


    def reset_gpu_memory():
        """
        Reset GPU memory.
        """
        tf.keras.backend.clear_session()


    def find_model_path_from_csv(self, model_type,csv_path=None):
        """
        Finds the path to the Sleap model folder based on the model type.
        Args:
            model_type (str): The type of the model.
        Returns:
            model_path (str): The path to the model.
        """
        #if csv_path is None:
         # csv_path = Path(
         #    r"\\gpfs.corp.brain.mpg.de\stem\data\project_hierarchy\Sleap_projects\sleap_model_paths.csv"
         # )
        if csv_path is None:
           csv_path = Path(self.paths_csv)
           
        model_paths_df = pd.read_csv(csv_path,engine="python",sep=',',encoding="cp437")
        model_paths_df["path to model folder"] = model_paths_df[
            "path to model folder"
        ]#.apply(os.path.normpath)
        model_paths = model_paths_df.set_index("model type").to_dict()[
            "path to model folder"
        ]

        current_path=model_paths.get(model_type)

        print(PureWindowsPath(current_path))
        return current_path

    def handle_subprocess(self, command):
        """
        Executes a shell command and handles the subprocess.
        Args:
            command (str): The command to be executed.
        """
        command_list = [part.replace("'", "") for part in command.split() if part not in ["'", '"']]
        print(command_list)
       
        result = subprocess.run(
            command_list,
            shell=True,
            check=True)

        if not (result.returncode == 0):
            print(f"Command failed with error code {result.returncode}")
            print(f"stdout: {result.stdout.decode('utf-8')}")
            print(f"stderr: {result.stderr.decode('utf-8')}")
        self.failed_commands.commands.append(command)
        self.failed_commands.results.append(result)

    def process_video_file(
        self, video_file, input_folder, output_folder, model_type, model_path
    ):
        """
        Processes a single video file using Sleap.
        Args:
            video_file (str): The video file to be processed.
            input_folder (str): The input folder path.
            output_folder (str): The output folder path.
            model_type (str): The type of the model.
            model_path (str): The path to the model.
        """
        
        input_path =Path.as_posix(Path.joinpath(input_folder,video_file))

        output_slp_path =Path.as_posix(Path.joinpath(
            output_folder, f"{video_file}.{model_type}.slp"
        ))
        output_h5_path =Path.as_posix(Path.joinpath(
            output_folder, f"{video_file}.{model_type}.h5"
        ))
        output_mp4_path =Path.as_posix(Path.joinpath(
            output_folder, f"{video_file}.{model_type}.mp4"
        ))
        model=Path.as_posix(Path(model_path))
        
        # Track poses
        track_command = (
            f"sleap-track -m {model} -o {output_slp_path} {input_path}"
        )
       
       # IPython.core.debugger.set_trace()
        print(f"infering: {track_command}")
        self.handle_subprocess(track_command)

        # Convert to h5 format
        if Path.is_file(Path(output_slp_path)):
         h5_command = f"sleap-convert -o {output_h5_path} --format analysis {output_slp_path}"
         print(f"Converting to h5: {h5_command}")
         self.handle_subprocess(h5_command)
        else:
            print(f"cannot convert video, file does not exist: {output_slp_path} ")

        # Render video with poses
        if  Path.is_file(Path(output_h5_path)):
         render_command = (
            f"sleap-render -o {output_mp4_path} -f 50 {output_slp_path}"
         )
         print(f"Rendering video: {render_command}")
         self.handle_subprocess(render_command)
        else:
            print(f"cannot render video, file does not exist: {output_slp_path} ")

        # Print paths of created files
        names = [output_slp_path, output_h5_path, output_mp4_path]
        nl = "\n"
        text = f"Tracked files created:\n{nl}{nl.join(names)}"
        print(text)

    def process_batch(
        self, video_files, input_folder, output_folder, model_type, model_path
    ):
        """
        Process a batch of video files concurrently.
        Args:
            video_files (list): The list of video files to be processed.
            input_folder (str): The input folder path.
            output_folder (str): The output folder path.
            model_type (str): The type of the model.
            model_path (str): The path to the model.
        """
        if len(video_files)==1:#single file
            video_file=video_files[0]
            self.process_video_file(
                video_file,
                input_folder,
                output_folder,
                model_type,
                model_path,
            )
        else:              
            
          #  IPython.core.debugger.set_trace()
            #get optimal number of processes for the current PC at current timepoint
            num_processes = self.get_num_processes()
            if num_processes > len(video_files):
               num_processes = len(video_files)
               
            print(f"# of processes: {num_processes}")
            # Create a multiprocessing Pool
            pool = Pool(processes=num_processes)
            for video_file in video_files:           
                pool.apply_async(
                    self.process_video_file,
                    args=(
                        video_file,
                        input_folder,
                        output_folder,
                        model_type,
                        model_path,
                    ),
                )
            pool.close()
            pool.join()

    def run_sleap(self, input_path, model_types: list = "mouse",csv_path=None):
        """
        Runs Sleap processing on video files.
        Args:
            input_path (str): The input path.
            model_types (list): The list of model types.
        """
        suffix = "tracked"
      

        P = Path(input_path)
      
        
        if Path.is_dir(Path(input_path)):
            input_folder = Path(input_path)
            output_folder = Path(os.path.join(input_folder, suffix))
            
            video_files = [
                f
                for f in os.listdir(input_folder)
                if f.endswith(".mp4") or f.endswith(".avi")
            ] 
        else:
          
            video_files = [P.name] 
            input_folder = P.parent
            output_folder = Path(os.path.join(input_folder, suffix))
           
            
        self.failed_commands.path = os.path.join(
                output_folder, "failed_commands.txt"
            )
        output_folder.mkdir(exist_ok=True)

        for model_type in model_types:
            print(model_type)
            if csv_path is None:
             model_path = self.find_model_path_from_csv(model_type)
            else:
             model_path = self.find_model_path_from_csv(model_type,csv_path)
             
             #run the files
            self.process_batch(
                video_files,
                input_folder,
                output_folder,
                model_type,
                model_path,
            )