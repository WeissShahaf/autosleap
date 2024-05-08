import os
import IPython
import sys
import subprocess
import pandas as pd
import multiprocessing
from multiprocessing import Pool
import psutil
import GPUtil
import tensorflow as tf
from pathlib import Path, PureWindowsPath
import logging
import configparser
import json

class SleapProcessor:
    """
    A class to process videos using Sleap for pose estimation.
    """
    def __init__(self):
        
        self.file_path = Path()
        self.animal_type = []
        self.csv_path = Path()
        self.optional_args = ''
        self.config_path=Path()
        self.chosen_model =Path ()     
      
        self.paths_csv=Path()
        self.num_processes=1
        
        self.log_file_path=Path(r'tracked/sleap_commands.log')
              
        env_dir = Path(sys.prefix)
        env_dir=env_dir.joinpath(env_dir, 'scripts')
        self.config_path = Path(env_dir, 'autosleap_config.json')  # Construct the path to the configuration file        
        
        
    def read_config(self):
     # If the configuration file exists and is not empty, fill in values from the configuration file
     if self.config_path.exists() and os.path.getsize(self.config_path) > 0:
        with open(self.config_path, 'r') as f:
            data = json.load(f)

        self.file_path = Path(data['file_path'])
        self.animal_type = data['animal_type']
        self.csv_path = Path(data['csv_path'])
        self.optional_args = data['optional_args']
        self.paths_csv = Path(data['csv_path'])
        self.log_file_path = Path(data.get('log_file_path', 'tracked/sleap_commands.log'))
        self.chosen_model = Path(data['chosen_model'])
        self.model_prefix = data['model_prefix']

    def start_logger(self):
    # Create a logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
        # Remove all handlers
        self.logger.handlers = []
    
        # Create the log file if it doesn't exist
        log_file_path=self.log_file_path
        log_file_path.touch(exist_ok=True)
    
        # Create a file handler        
        handler = logging.FileHandler(self.log_file_path,'a')
        handler.setLevel(logging.INFO)
    
        # Create a logging format with timestamps
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
    
        # Add the handler to the logger
        self.logger.addHandler(handler)

    # def start_logger(self):
        
    #     # Create a logger
    #     self.logger = logging.getLogger(__name__)
    #     self.logger.setLevel(logging.INFO)
        
        
    #     # Create the log file if it doesn't exist
    #     log_file_path=self.log_file_path
    #     log_file_path.touch(exist_ok=True)
        
    #     # Create a file handler        
    #     handler = logging.FileHandler(self.log_file_path,'a')
    #     handler.setLevel(logging.INFO)

        
    #     # Create a logging format with timestamps
    #     formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    #     handler.setFormatter(formatter)
        
    #     # Add the handler to the logger
    #     self.logger.addHandler(handler)

        

    def get_num_processes(self,GPU_GB_limit=None):
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
        if GPU_GB_limit is None:
         GPU_GB_limit = 12  # Limit the GPU memory to 12GB
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
    
    def convert(self, value, data_type):
     """
     Convert a value to a specified data type.
     Args:
        value: The value.
         data_type (str): The data type.
     Returns:
         The value converted to the specified data type.
     """
     if 'path' in data_type:
        return Path(value)
     elif data_type == 'str':
        return str(value)
     elif data_type == 'int':
        return int(value)
     elif data_type == 'float':
        return float(value)
     elif data_type == 'list':
        return list(value)
    # Add more elif statements here for other data types

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
           csv_path = self.paths_csv
       # IPython.core.debugger.set_trace()           
        model_paths_df = pd.read_csv(csv_path,engine="python",sep=',',encoding="cp437")
        model_paths_df["path to model folder"] = model_paths_df[
            "path to model folder"
        ]#.apply(os.path.normpath)
        model_paths = model_paths_df.set_index("model type").to_dict()[
            "path to model folder"
        ]

        current_path=model_paths.get(model_type)
       
        print(PureWindowsPath(current_path))
        
        import numpy as np
        GPUmem=model_paths_df.set_index("model type").to_dict()[
            "VRAM GB"
        ]
        
        reqVRAM=(GPUmem.get(model_type))
        if ~np.isnan(reqVRAM):
          reqVRAM=np.int8(reqVRAM)  
        
        
        return current_path

    def handle_subprocess(self, command):
        """
        Executes a shell command and handles the subprocess.
        Args:
            command (str): The command to be executed.
        """
        command_list = [part.replace("'", "") for part in command.split() if part not in ["'", '"']]
        print(command_list)
       
        # Log the command
        self.logger.info('Running command: %s', command_list)
        # Run the command using subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        # result = subprocess.run(
        #     command_list,
        #     shell=True,
        #     check=True)
        
        # Log the output
        self.logger.info('Command output: %s', result.stdout)

        # if not (result.returncode == 0):
        #     print(f"Command failed with error code {result.returncode}")
        #     print(f"stdout: {result.stdout.decode('utf-8')}")
        #     print(f"stderr: {result.stderr.decode('utf-8')}")
        # self.failed_commands.commands.append(command)
        # self.failed_commands.results.append(result)
    def process_video_file(self, video_file, input_folder, output_folder, model_type, model_path):
        """
        Processes a single video file using Sleap.
        Args:
            video_file (str): The video file to be processed.
            input_folder (str): The input folder path.
            output_folder (str): The output folder path.
            model_type (str): The type of the model.
            model_path (str): The path to the model.
        """
        
        # Log the parameters
        self.logger.info('Processing batch: video_file=%s, input_folder=%s, output_folder=%s, model_type=%s, model_path=%s',
                                 video_file, input_folder, output_folder, model_type, model_path)
    
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
         #if optional_args given use them
        if self.optional_args:        
         track_command = (
             f"sleap-track -m {model} -o {output_slp_path} {self.optional_args} {input_path}"
         )
        else:
         track_command = (
            f"sleap-track -m {model} -o {output_slp_path} {input_path}"
         )
       
        # Log the command
        self.logger.info('Running command: %s', track_command)
        self.handle_subprocess(track_command)
    
        # Convert to h5 format
        if Path.is_file(Path(output_slp_path)):
         h5_command = f"sleap-convert -o {output_h5_path} --format analysis {output_slp_path}"
         # Log the command
         self.logger.info('Running command: %s', h5_command)
         self.handle_subprocess(h5_command)
        else:
            self.logger.error(f"cannot convert video, file does not exist: {output_slp_path} ")
    
        # Render video with poses
        if  Path.is_file(Path(output_h5_path)):
         render_command = (
            f"sleap-render -o {output_mp4_path} -f 50 {output_slp_path}"
         )
         # Log the command
         self.logger.info('Running command: %s', render_command)
         self.handle_subprocess(render_command)
        else:
            self.logger.error(f"cannot render video, file does not exist: {output_slp_path} ")
    
        # Print paths of created files
        names = [output_slp_path, output_h5_path, output_mp4_path]
        nl = "\n"
        text = f"Tracked files created:\n{nl}{nl.join(names)}"
        # Log the output
        self.logger.info('Command output: %s', text)

    # def process_video_file(
    #     self, video_file, input_folder, output_folder, model_type, model_path
    # ):
    #     """
    #     Processes a single video file using Sleap.
    #     Args:
    #         video_file (str): The video file to be processed.
    #         input_folder (str): The input folder path.
    #         output_folder (str): The output folder path.
    #         model_type (str): The type of the model.
    #         model_path (str): The path to the model.
    #     """
        
    #     print(f"processing {video_file}")
    #     self.logger.info('Processing batch: video_file=%s, input_folder=%s, output_folder=%s, model_type=%s, model_path=%s',
    #                              video_file, input_folder, output_folder, model_type, model_path)

    #     input_path =Path.as_posix(Path.joinpath(input_folder,video_file))

    #     output_slp_path =Path.as_posix(Path.joinpath(
    #         output_folder, f"{video_file}.{model_type}.slp"
    #     ))
    #     output_h5_path =Path.as_posix(Path.joinpath(
    #         output_folder, f"{video_file}.{model_type}.h5"
    #     ))
    #     output_mp4_path =Path.as_posix(Path.joinpath(
    #         output_folder, f"{video_file}.{model_type}.mp4"
    #     ))
    #     model=Path.as_posix(Path(model_path))
    #     # Track poses
    #      #if optional_args given use them
    #     if self.optional_args:        
    #      track_command = (
    #          f"sleap-track -m {model} -o {output_slp_path} {self.optional_args} {input_path}"
    #      )
    #     else:
    #      track_command = (
    #         f"sleap-track -m {model} -o {output_slp_path} {input_path}"
    #      )
       
    #    # IPython.core.debugger.set_trace()
    #     print(f"infering: {track_command}")
    #     self.handle_subprocess(track_command)

    #     # Convert to h5 format
    #     if Path.is_file(Path(output_slp_path)):
    #      h5_command = f"sleap-convert -o {output_h5_path} --format analysis {output_slp_path}"
    #      print(f"Converting to h5: {h5_command}")
    #      self.handle_subprocess(h5_command)
    #     else:
    #         print(f"cannot convert video, file does not exist: {output_slp_path} ")

    #     # Render video with poses
    #     if  Path.is_file(Path(output_h5_path)):
    #      render_command = (
    #         f"sleap-render -o {output_mp4_path} -f 50 {output_slp_path}"
    #      )
    #      print(f"Rendering video: {render_command}")
    #      self.handle_subprocess(render_command)
    #     else:
    #         print(f"cannot render video, file does not exist: {output_slp_path} ")

    #     # Print paths of created files
    #     names = [output_slp_path, output_h5_path, output_mp4_path]
    #     nl = "\n"
    #     text = f"Tracked files created:\n{nl}{nl.join(names)}"
    #     print(text)
    
    def process_and_print(self, video_file, input_folder, output_folder, model_type, model_path):
        print(f"Processing: {video_file}")
        self.process_video_file(video_file, input_folder, output_folder, model_type, model_path)
        
    def worker(self,args):
       self.process_and_print(*args)
    def process_files(self, video_files, input_folder, output_folder, model_type, model_path):
                  
       
        
        if len(video_files) == 1:#single file
            self.process_video_file(video_files[0], input_folder, output_folder, model_type, model_path)
        else: #multiple files
            num_processes = self.get_num_processes()
            num_processes = min(4, len(video_files))  # Ensure num_processes does not exceed length of video_files
#            if num_processes > len(video_files): num_processes = len(video_files)
            print(f"# of parallel processes: {num_processes}")
 
            from multiprocessing.pool import ThreadPool
            with ThreadPool(processes=num_processes) as pool:
                pool.starmap(
                    self.process_and_print,
                    [(video_file, input_folder, output_folder, model_type, model_path) for video_file in video_files]
                        )
            
            # with Pool(processes=num_processes) as pool:
            #     [pool.apply_async(self.worker, (video_file, input_folder, output_folder, model_type, model_path)) for video_file in video_files]
                # get the results when they are ready
                #results = [result.get() for result in results]
            #     pool.starmap(
            #     self.process_and_print,
            #     [(video_file, input_folder, output_folder, model_type, model_path) for video_file in video_files]
            # )
            # #    pool.starmap(
            # #     self.process_and_print,
            # #     [(video_file, input_folder, output_folder, model_type, model_path) for video_file in video_files]
            # # )
                
           
    
                                       
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
       # IPython.core.debugger.set_trace()   
        self.process_files(video_files, input_folder, output_folder, model_type, model_path)
         

            # #get optimal number of processes for the current PC at current timepoint
            # num_processes = self.get_num_processes()
            # if num_processes > len(video_files):
            #    num_processes = len(video_files)
               
            # print(f"# of processes: {num_processes}")
            # # Create a multiprocessing Pool
            # pool = Pool(processes=num_processes)
            # for video_file in video_files:           
            #     # Log the parameters
              
            #     pool.apply_async(
            #         self.process_video_file,
            #         args=(
            #             video_file,
            #             input_folder,
            #             output_folder,
            #             model_type,
            #             model_path,
            #         ),
            #     )
            # pool.close()
            # pool.join()

    def run_sleap(self):
        """
        Runs Sleap processing on video files.
        Args:
            input_path (str): The input path.
            model_types (list): The list of model types.
        """
        #  prevously def run_sleap(self, input_path, model_types: list = "mouse",csv_path=None):
            #   called      sleap_processor.run_sleap((file_path, animal_type, csv_path))
            
        suffix = "tracked"
        input_path = self.file_path
        csv_path = self.csv_path
        chosen_model = self.chosen_model
        model_prefix = self.model_prefix
        model_types = self.animal_type
        
        if Path.is_dir(chosen_model):
            model_types = model_prefix
            csv_path = chosen_model
    
      
        # if model_types isn't a list make it one
        if not isinstance(model_types, list):
            model_types = [model_types]
            
        print(model_types)

        
        P = Path(input_path)
      
#        IPython.core.debugger.set_trace()           
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
           
            
        
        output_folder.mkdir(exist_ok=True)
        
        
        #if manual model path was used, skip model_type iterations
        print(video_files)
        for model_type in model_types:
            print(model_type)
            if Path.is_dir(csv_path):
             model_path = csv_path
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
    # # Get exception info
    # exc_type, exc_value, exc_traceback = sys.exc_info()
    # if exc_type is not None:
    #     print(f"An error occurred: {exc_value}")