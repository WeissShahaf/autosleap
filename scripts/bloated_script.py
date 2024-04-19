#SLEAP_GUI
import os
import sys
import subprocess
from pathlib import Path, PureWindowsPath
import pathlib
import pandas as pd
import multiprocessing
from multiprocessing import Pool
import psutil
import GPUtil
import IPython
import argparse
#for GUI
from PySide2.QtWidgets import QApplication, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox, QFileDialog, QWidget, QDesktopWidget
from PySide2.QtGui import QIcon, QPixmap, Qt
from itertools import chain, combinations



def get_num_processes():
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

    CPU_GB_limit = 4  # Limit the GPU memory to 12GB

    num_processes = min(
        round(total_ram / CPU_GB_limit), round(total_vram / GPU_GB_limit)
    )
    # case something went wrong:
    if num_processes <= 0:
        num_processes = 1

    return num_processes


def reset_gpu_memory():
    """
    Reset GPU memory.
    """
    import tensorflow as tf
    tf.keras.backend.clear_session()


class FailedCommands:
    """
    A class to store failed commands and the path of where to save as a text file.
    """
    def __init__(self):
        self.path = []  # Path to save the text file
        self.commands = []  # List to store failed commands
        self.results = []
   # def get_file_path


class SleapProcessor:
    """
    A class to process videos using Sleap for pose estimation.
    """
    def __init__(self):
        self.failed_commands = (
            FailedCommands()
        )  # Initialize the failed commands tracker

    def find_model_path_from_csv(self, model_type,csv_path=None):
        """
        Finds the path to the Sleap model folder based on the model type.
        Args:
            model_type (str): The type of the model.
        Returns:
            model_path (str): The path to the model.
        """
        if csv_path is None:
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
       
        #IPython.core.debugger.set_trace()
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

class InputBox(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def all_combinations(self,lst:list):
        return list(chain(*[combinations(lst, i + 1) for i, _ in enumerate(lst)]))
   
    def initUI(self):
        layout = QVBoxLayout()

        # Add image at the top
        label = QLabel(self)
        env_dir = os.path.dirname(sys.executable)  # Get the directory of the current Python interpreter       
        logo_path = os.path.join(env_dir,"lib\site-packages\sleap\gui", "autosleap_logo.jpg")  # Get the path of 'logo.jpg' in the conda environment directory
        pixmap = QPixmap(logo_path)
        pixmap = pixmap.scaled(512, 512, Qt.KeepAspectRatio)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)  # Center the pixmap object in the bo
        layout.addWidget(label)
        
        # Modify file path input and browse button layout
        layout.addWidget(QLabel("File Path:"))
        file_path_layout = QHBoxLayout()
        self.le = QLineEdit()
        file_path_layout.addWidget(self.le)
        self.btn = QPushButton("Browse")
        self.btn.clicked.connect(self.getfile)
        file_path_layout.addWidget(self.btn)
        layout.addLayout(file_path_layout)

        # # Modify file path input and browse button layout
        # layout.addWidget(QLabel("File Path:"))
        # file_path_layout = QHBoxLayout()
        # self.le = QLineEdit()
        # file_path_layout.addWidget(self.le)
        # self.btn = QPushButton("Browse")
        # self.btn.clicked.connect(self.getfile)
        # file_path_layout.addWidget(self.btn)
        # layout.addLayout(file_path_layout)

        layout.addWidget(QLabel("Animal Type:"))
        animals = ["mouse", "cricket", "pups"]
        combos = self.all_combinations(animals)        
        self.cb = QComboBox()
        for combo in combos:
          self.cb.addItem(", ".join(combo))
        layout.addWidget(self.cb)

        layout.addWidget(QLabel("CSV file containing model Paths:"))
        self.model_path_CSV_le = QLineEdit()
        self.model_path_CSV_le.setText("\\\\gpfs.corp.brain.mpg.de\\stem\\data\\project_hierarchy\\Sleap_projects\\sleap_model_paths.csv")
        layout.addWidget(self.model_path_CSV_le)

        self.submit_btn = QPushButton("Submit")
        self.submit_btn.clicked.connect(self.run_sleapGUI)
        layout.addWidget(self.submit_btn)

        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(self.quitApp)
        layout.addWidget(self.quit_btn)
        
        self.setLayout(layout)
        self.setWindowTitle("PySide2 File Dialog")

        # Set window size to 1/4 of the screen and center it
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen.width() // 4, screen.height() // 4, screen.width() // 2, screen.height() // 2)
        self.center()

    def center(self):
        frame = self.frameGeometry()
        center_point = QApplication.primaryScreen().availableGeometry().center()
        frame.moveCenter(center_point)
        self.move(frame.topLeft())
        
    def quitApp(self):
        QApplication.quit()
        
    def getfile(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', '\\\\gpfs.corp.brain.mpg.de\\stem\\data\\project_hierarch')  # Set the default path
        self.le.setText(fname[0])


    # def getfile(self):
    #     fname = QFileDialog.getOpenFileName(self, 'Open file', '/')
    #     self.le.setText(fname[0])

    def run_sleapGUI(self):
        file_path = Path(self.le.text())
        animal_type = self.cb.currentText().split(',')
        csv_path = self.model_path_CSV_le.text()
        self.close()
        QApplication.processEvents()  # Process any pending events
        QApplication.quit()  # Destroy the QApplication
        sleap_processor = SleapProcessor()
        sleap_processor.run_sleap(file_path, animal_type, csv_path)

    def close_qt_applications():
      app = QApplication.instance()
      if app is not None:
        app.quit()




def main():
    parser = argparse.ArgumentParser(description='Run SLEAP_GUI.')
    parser.add_argument('--runtype', type=str, default='gui', help='Specify run type: cmd or gui')
    parser.add_argument('--input_path', type=str, default=None, help='Specify input path')
    parser.add_argument('--model_type', type=str, default='mouse', help='Specify model type')
    parser.add_argument('--csv_path', type=str, default=None, help='Specify CSV path')
    args = parser.parse_args()

    if args.runtype == 'cmd':
        # Command line mode
        sleap_processor = SleapProcessor()
        sleap_processor.run_sleap(args.input_path, args.model_type, args.csv_path)
    elif args.runtype == 'gui':
        # GUI mode
        try:
            app = QApplication(sys.argv)
            window = InputBox()
            window.show()
            sys.exit(app.exec_())
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # Destroy the QApplication singleton
            app = QApplication.instance()
            if app is not None:
                app.quit()

if __name__ == "__main__":
    main()



# class InputBox(QWidget):
#     def __init__(self):
#         super().__init__()
#         self.initUI()
        

#     def all_combinations(self,lst:list):
#       return list(chain(*[combinations(lst, i + 1) for i, _ in enumerate(lst)]))
     
#     def initUI(self):
#         layout = QVBoxLayout()

#         # Add image at the top
#         label = QLabel(self)
#         pixmap = QPixmap('https://github.com/StempelLab/sleap_well/blob/main/docs/half_logo.jpg')  # GUI logo
#         if pixmap.isNull():
#             print("Failed to load image!")
#         else:
#             print("Image loaded successfully!")
#         pixmap = pixmap.scaled(512, 512, Qt.KeepAspectRatio)
#         label.setPixmap(pixmap)
#         layout.addWidget(label)

#         # Modify file path input and browse button layout
#         layout.addWidget(QLabel("File Path:"))
#         file_path_layout = QHBoxLayout()
#         self.le = QLineEdit()
#         file_path_layout.addWidget(self.le)
#         self.btn = QPushButton("Browse")
#         self.btn.clicked.connect(self.getfile)
#         file_path_layout.addWidget(self.btn)
#         layout.addLayout(file_path_layout)

#         layout.addWidget(QLabel("Animal Type:"))
        
#         animals = ["mouse", "cricket", "pups"]
#         combos = self.all_combinations(animals)        
#         self.cb = QComboBox()
#         for combo in combos:
#           self.cb.addItem(", ".join(combo))
#         layout.addWidget(self.cb)

       

#         layout.addWidget(QLabel("CSV file containing model Paths:"))
#         self.model_path_CSV_le = QLineEdit()
#         self.model_path_CSV_le.setText("\\\\gpfs.corp.brain.mpg.de\\stem\\data\\project_hierarchy\\Sleap_projects\\sleap_model_paths.csv")
#         layout.addWidget(self.model_path_CSV_le)

#         self.submit_btn = QPushButton("Submit")
#         self.submit_btn.clicked.connect(self.run_sleapGUI)
#         layout.addWidget(self.submit_btn)

#         self.quit_btn = QPushButton("Quit")
#         self.quit_btn.clicked.connect(self.quitApp)
#         layout.addWidget(self.quit_btn)
        
#         self.setLayout(layout)
#         self.setWindowTitle("PySide2 File Dialog")

#         # Set window size to 1/4 of the screen and center it
#         screen = QDesktopWidget().screenGeometry()
#         self.setGeometry(screen.width() // 4, screen.height() // 4, screen.width() // 2, screen.height() // 2)
#         self.center()

#     def center(self):
#         frame = self.frameGeometry()
#         center_point = QDesktopWidget().availableGeometry().center()
#         frame.moveCenter(center_point)
#         self.move(frame.topLeft())
        
#     def quitApp(self):
#         QApplication.quit()

#     def getfile(self):
#         fname = QFileDialog.getOpenFileName(self, 'Open file', '/')
#         self.le.setText(fname[0])

#     def run_sleapGUI(self):
#         file_path = Path(self.le.text())
#         animal_type = self.cb.currentText().split(',')
#         csv_path = self.model_path_CSV_le.text()
#         self.close()
#         QApplication.processEvents()  # Process any pending events
#         QApplication.quit()  # Destroy the QApplication
#         sleap_processor = SleapProcessor()
#         sleap_processor.run_sleap(file_path, animal_type, csv_path)

#     def close_qt_applications():
#       app = QApplication.instance()
#       if app is not None:
#         app.quit()

           


def main():
    parser = argparse.ArgumentParser(description='Run SLEAP_GUI.')
    parser.add_argument('--runtype', type=str, default='gui', help='Specify run type: cmd or gui')
    parser.add_argument('--input_path', type=str, default=None, help='Specify input path')
    parser.add_argument('--model_type', type=str, default='mouse', help='Specify model type')
    parser.add_argument('--csv_path', type=str, default=None, help='Specify CSV path')
    args = parser.parse_args()

    if args.runtype == 'cmd':
        # Command line mode
        sleap_processor = SleapProcessor()
        sleap_processor.run_sleap(args.input_path, args.model_type, args.csv_path)
    elif args.runtype == 'gui':
        # GUI mode
        try:
            app = QApplication(sys.argv)
            window = InputBox()
            window.show()
            sys.exit(app.exec_())
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # Destroy the QApplication singleton
            app = QApplication.instance()
            if app is not None:
                app.quit()

if __name__ == "__main__":
    main()