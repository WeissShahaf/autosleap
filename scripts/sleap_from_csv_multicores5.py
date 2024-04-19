#v4 only worked for mouse but not for cricket
import os
import subprocess
from pathlib import Path, PureWindowsPath
import pathlib
import pandas as pd
import multiprocessing
from multiprocessing import Pool

import psutil
import GPUtil
import IPython


def get_num_processes():
    # Define the number of processes based on RAM and VRAM

    ram = psutil.virtual_memory()  # Get RAM
    total_ram = ram.available / (1024**3)  # Convert bytes to GB

    # Get GPU VRAM
    gpus = GPUtil.getGPUs()
    total_vram = round(gpus[0].memoryFree) / (1024)  # Convert bytes to GB
    # Assuming one GPU, adjust if multiple GPUs

    # Define the number of processes based on RAM and VRAM
    GPU_GB_limit = 10  # Limit the GPU memory to 12GB
    # cricket model takes ~7GB VRAN to run on batch size = 4

    CPU_GB_limit = 4  # Limit the GPU memory to 12GB

    num_processes = min(
        round(total_ram / CPU_GB_limit), round(total_vram / GPU_GB_limit)
    )
    # case something went wrong:
    if num_processes <= 0:
        num_processes = 1

    return num_processes


def reset_gpu_memory():
    import tensorflow as tf

    tf.keras.backend.clear_session()


# Reset GPU memory
# reset_gpu_memory()


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

    def find_model_path_from_csv(self, model_type):
        """
        Finds the path to the Sleap model folder based on the model type.
        """
        csv_path = Path(
            r"\\gpfs.corp.brain.mpg.de\stem\data\project_hierarchy\Sleap_projects\sleap_model_paths.csv"
        )
     
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
        
      

        VRAM = model_paths_df.set_index("model type").to_dict()[
            "VRAM GB"
        ]
        
        
        opt_args = model_paths_df.set_index("model type").to_dict()[
            "optional arguments"
        ]
        model_path=model_paths.get(model_type)
        VRAM=VRAM.get(model_type)
        opt_args=opt_args.get(model_type)	
        out = []
        

        return model_path#, VRAM, opt_args

    def handle_subprocess(self, command):
        """
        Executes a shell command and handles the subprocess.
        """
        
        command_list = [part.replace("'", "") for part in command.split() if part not in ["'", '"']]
        print(command_list)
       
        result = subprocess.run(
            command_list,
            shell=True,
            check=False)

            # Save failed commands to a text file       
        # with open(self.failed_commands.path, "w") as ff:
        #  for command, result in self.failed_commands.results:
        #      ff.write(f"Command: {command}")
        #      ff.write(f"Return code: {result.returncode}")
        #      ff.write(f"stdout: {result.stdout.decode(''ISO-8859-1'')}")
        #      ff.write(f"stderr: {result.stderr.decode(ISO-8859-1')}")

           
        if not (result.returncode == 0):
          #  IPython.core.debugger.set_trace()
            print(f"Command failed with error code {result.returncode}")
            print(f"stdout: {result.stdout.decode('utf-8')}")
            print(f"stderr: {result.stderr.decode('utf-8')}")
        self.failed_commands.commands.append(command)
        self.failed_commands.results.append(result)
        # self.results.append(result)

    def process_video_file(
        self, video_file, input_folder, output_folder, model_type, model_path
    ):
        """
        Processes a single video file using Sleap.
        """
        input_path =Path.as_posix(Path.joinpath(input_folder,video_file))
        #output_folder=Path(output_folder)
        # input_path = (os.path.join(input_folder, video_file))    

        #(os.path.join(
        output_slp_path =Path.as_posix(Path.joinpath(
            output_folder, f"{video_file}.{model_type}.slp"
        ))
        output_h5_path =Path.as_posix(Path.joinpath(
            output_folder, f"{video_file}.{model_type}.h5"
        ))
        output_mp4_path =Path.as_posix(Path.joinpath(
            output_folder, f"{video_file}.{model_type}.mp4"
        ))
        
        
      
        #            f"sleap-track -m r'{model_path}' -o r'{output_slp_path}' r'{input_path}'"
        # Track poses
        track_command = (
            f"sleap-track -m {model_path} -o {output_slp_path} {input_path}"
        )
       
        print(f"infering: {track_command}")
        self.handle_subprocess(track_command)

      #  IPython.core.debugger.set_trace()  # debugging
        # Convert to h5 format
        # sleap-convert [-h] [-o OUTPUT] [--format FORMAT] [--video VIDEO]
        #output_slp_path=(pathlib.PurePath(output_slp_path))
        Path.is_file(output_slp_path)
        h5_command = f"sleap-convert -o {output_h5_path} --format analysis {output_slp_path}"
        print(f"Converting to h5: {h5_command}")
        self.handle_subprocess(h5_command)

        # Render video with poses
        render_command = (
            f"sleap-render -o {output_mp4_path} -f 50 {output_slp_path}"
        )
        print(f"Rendering video: {render_command}")
        self.handle_subprocess(render_command)

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
        """
       # IPython.core.debugger.set_trace()
        # Define the number of processes based on RAM and VRAM
        
        # pool = Pool()
       #if single video - process it
        if len(video_files)==1:#single file
               # IPython.core.debugger.set_trace()
                video_file=video_files[0]
                self.process_video_file(
                    video_file,
                    input_folder,
                    output_folder,
                    model_type,
                    model_path,
                )
        #if folder, go through  video files, in parrallel
        else:              
            #get optimal number of processes for the current PC at current timepoint
            num_processes = get_num_processes()
           
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


    def run_sleap(self, input_path, model_types: list = "mouse"):
        """
        Runs Sleap processing on video files.
        """
        suffix = "tracked"
        if Path.is_dir(input_path):
            input_folder = input_path
            output_folder = Path(os.path.join(input_folder, suffix))
            
            video_files = [
                f
                for f in os.listdir(input_folder)
                if f.endswith(".mp4") or f.endswith(".avi")
            ] 
        else:
            p = Path(input_path)
            video_files = [p.name] 
            input_folder = p.parent
            output_folder = Path(os.path.join(input_folder, suffix))
            
            
            self.failed_commands.path = os.path.join(
                output_folder, "failed_commands.txt"
            )
        output_folder.mkdir(exist_ok=True)
        
        for model_type in model_types:
            print(model_type)
            
            model_path = self.find_model_path_from_csv(model_type)
            self.process_batch(
                video_files,
                input_folder,
                output_folder,
                model_type,
                model_path,
            )


        # =============================================================================
        #             # Save failed commands to a text file
        #             self.failed_commands.path = os.path.join(
        #                 output_folder, "failed_commands.txt"
        #             )
        #             with open(self.failed_commands.path, "w") as ff:
        #                 ff.write("\n".join(str(self.failed_commands.results)))
        ## =============================================================================
       # print("Done!")


if __name__ == "__main__":
    sleap_processor = SleapProcessor()
 #s   input_path = Path(r"G:\scratch\afm16505\231215\231215_behaviour")
    input_path = Path(r"\\gpfs.corp.brain.mpg.de\stem\data\project_hierarchy\Sleap_projects\sharpened_vids\Afm16505_231213_0_sharp_short.mp4")
    model_types = ["cricket"]
    print(input_path, model_types)
 
    sleap_processor.run_sleap(input_path, model_types)
