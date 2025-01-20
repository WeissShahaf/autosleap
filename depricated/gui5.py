
from itertools import chain, combinations
from pathlib import Path, PureWindowsPath
import os
import sys
from utils import find_logo
from classes import SleapProcessor
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QApplication, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox, QFileDialog, QWidget, QDesktopWidget, QCheckBox
from PySide2.QtGui import QIcon, QPixmap, Qt, QPalette, QColor
from itertools import chain, combinations
import IPython
import json
import pandas as pd

class InputBox(QWidget):
    def __init__(self):
        super().__init__()       

        # Initialize the parameters with default values
        self.file_path = Path()
        self.animal_type = []
        self.csv_path = Path()
        self.optional_args = ''
        self.user_model_path = None  # New attribute for user selected model path
        self.model_prefix = ''
        self.chosen_model = Path()

        # Construct the path to the configuration file
        env_dir = Path(sys.prefix)       
        env_dir=env_dir.joinpath(env_dir, 'scripts')
        # Initialize the configuration file path  
        self.config_path = Path(env_dir, 'autosleap_config.json')  

        # If the configuration file exists and is not empty, fill in values from the configuration file
        if self.config_path.exists() and os.path.getsize(self.config_path) > 0:
            with open(self.config_path, 'r') as f:
                data = json.load(f)

            self.file_path = Path(data['file_path'])
            self.animal_type = data['animal_type']
            self.csv_path = Path(data['csv_path'])
            self.optional_args = data['optional_args']
            self.chosen_model = Path(data['chosen_model'])
            self.model_prefix = data['model_prefix']
                                     

        self.initUI()

   
    def initUI(self):
        layout = QVBoxLayout()

        # Add image at the top
        label = QLabel(self)
        logo_path=find_logo()
        pixmap = QPixmap(logo_path)
        pixmap = pixmap.scaled(512, 512, Qt.KeepAspectRatio)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)  # Center the pixmap object in the bo
        layout.addWidget(label)


        self.setWindowTitle("Auto-sleap GUI")

        # Set window size to 1/4 of the screen and center it
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen.width() // 4, screen.height() // 4, screen.width() // 2, screen.height() // 2)
        self.center()

        # Modify file path input and browse button layout
        layout.addWidget(QLabel("File/Folder Path:"))
        file_path_layout = QHBoxLayout()
        self.le = QLineEdit()
        file_path_layout.addWidget(self.le)
        self.btn = QPushButton("Browse")
        self.btn.clicked.connect(self.getfile)  # default to file mode
        file_path_layout.addWidget(self.btn)
        self.file_mode_checkbox = QCheckBox("Folder mode", self)
        self.file_mode_checkbox.stateChanged.connect(self.switch_mode)
        file_path_layout.addWidget(self.file_mode_checkbox)
        layout.addLayout(file_path_layout)
        
        
        # Add a new checkbox for using CSV file for model paths
        self.use_csv_checkbox = QCheckBox("Use CSV file for model paths", self)
        self.use_csv_checkbox.stateChanged.connect(self.switch_csv_mode)
        layout.addWidget(self.use_csv_checkbox)
        
        #path box to models csv file
        layout.addWidget(QLabel("CSV file containing model Paths:"))
        self.model_path_CSV_le = QLineEdit()
        self.model_path_CSV_le.setText("\\\\gpfs.corp.brain.mpg.de\\stem\\data\\project_hierarchy\\Sleap_projects\\sleap_model_paths.csv")
        layout.addWidget(self.model_path_CSV_le)

        #drop down menu of model combinations
        layout.addWidget(QLabel("Model Types to infer:"))
        self.cb = QComboBox()
        self.update_combos()
       ###
        layout.addWidget(self.cb)
        


        # Add a new checkbox for manual model selection
        self.manual_model_checkbox = QCheckBox("Manual model selection", self)
        self.manual_model_checkbox.stateChanged.connect(self.switch_model_mode)
        layout.addWidget(self.manual_model_checkbox)
        
        
        
        
        # Add a new QLineEdit for model path
        layout.addWidget(QLabel("Manually enter model prefix:"))
        self.model_prefix_le = QLineEdit()
        layout.addWidget(self.model_prefix_le)
        
        
        
        # Add a new QLineEdit for model path
        layout.addWidget(QLabel("Manually enter model path:"))
        self.model_path_le = QLineEdit()
        layout.addWidget(self.model_path_le)
        
        # Add a new browse button for model selection
        self.btn_model = QPushButton("Browse for model")
        self.btn_model.clicked.connect(self.getfolder)
        self.btn_model.clicked.connect(self.switch_model_mode(state=True))        
        layout.addWidget(self.btn_model)

         # Add a new button for saving model to CSV file
        self.btn_save_model = QPushButton("Save Model to CSV File")
        self.btn_save_model.clicked.connect(self.save_model_to_csv)
        layout.addWidget(self.btn_save_model)
        
        # Add a QLineEdit for optional_args
        layout.addWidget(QLabel("Optional Args:"))
        self.optional_args_le = QLineEdit()
        layout.addWidget(self.optional_args_le)
        
       
        #get previous data to prefill if config file exists
        if self.config_path.exists() and os.path.getsize(self.config_path) > 0:
            with open(self.config_path, 'r') as f:
                data = json.load(f)

            self.le.setText(data['file_path'])
            self.model_path_CSV_le.setText(data['csv_path'])
            self.optional_args_le.setText(data['optional_args'])
            self.cb.setCurrentText(', '.join(data['animal_type']))
            self.model_prefix_le.setText(data['model_prefix'])
            



        self.submit_btn = QPushButton("Submit")
        self.submit_btn.clicked.connect(self.run_sleapGUI)
        layout.addWidget(self.submit_btn)
        
        self.reset_btn = QPushButton("reset")
        self.reset_btn.clicked.connect(self.reset)
        layout.addWidget(self.reset_btn)


        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(self.quitApp)
        layout.addWidget(self.quit_btn)
        
        self.status_message = QLabel("")
        layout.addWidget(self.status_message)
        
        #set the layout to display
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor('white'))  # Change 'red' to your desired color
        self.setPalette(palette)
        self.show()
        self.setLayout(layout)
        
    def reset(self):
        self.initUI()
        
        
    def center(self):
        frame = self.frameGeometry()
        center_point = QApplication.primaryScreen().availableGeometry().center()
        frame.moveCenter(center_point)
        self.move(frame.topLeft())

    def quitApp(self):
        self.close()
        QApplication.quit()
       

    def getfile(self):
       fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "All Files (*);;csv Files (*.csv);;MP4 Files (*.mp4);;avi Files (*.avi)")
       if fileName:
           self.le.setText(fileName)

    def getfolder(self):
       folder = QFileDialog.getExistingDirectory(self, "Select Directory")
       if folder:
           self.model_path_le.setText(folder)
           
    def switch_mode(self, state):
        if state == Qt.Checked:
            self.btn.clicked.disconnect()
            self.btn.clicked.connect(self.getfolder)
        else:
            self.btn.clicked.disconnect()
            self.btn.clicked.connect(self.getfile)

    def switch_model_mode(self, state):
       if state == Qt.Checked:
           self.use_csv_checkbox.setChecked(False)
           self.model_path_CSV_le.setDisabled(True)
           self.btn_model.setDisabled(False)
           self.model_prefix_le.setDisabled(False)
           
       else:
           self.use_csv_checkbox.setChecked(True)
           self.model_path_le.setDisabled(False)
           self.btn_model.setDisabled(True)
           self.model_path_CSV_le.setDisabled(False)
           self.model_prefix_le.setDisabled(True)
           self.update_combos(useCSV=True)
           

           

    def switch_csv_mode(self, state):
       if state == Qt.Checked:
           self.manual_model_checkbox.setChecked(False)
           self.use_csv_checkbox.setChecked(True)
           self.model_path_le.setDisabled(True)
           self.btn_model.setDisabled(True)
           self.model_path_CSV_le.setDisabled(False)
           self.model_prefix_le.setDisabled(True)
           self.update_combos(useCSV=True)
           
       else:
           self.manual_model_checkbox.setChecked(True)
           self.use_csv_checkbox.setChecked(False)
           self.model_path_le.setDisabled(False)
           self.btn_model.setDisabled(False)
           self.model_path_CSV_le.setDisabled(True)
           self.model_prefix_le.setDisabled(False)

    def all_combinations(self,lst:list):
         return list(chain(*[combinations(lst, i + 1) for i, _ in enumerate(lst)]))

    def update_combos(self,animals = ["mouse", "cricket", "pups"],useCSV = False):        
        if useCSV==True:
         df = pd.read_csv(self.csv_path,engine="python",sep=',',encoding="cp437")
         model_types = df['model type'].tolist()
         animals = model_types
        
        combos = self.all_combinations(animals)        
        
        for combo in combos:
            self.cb.addItem(", ".join(combo))

    def save_model_to_csv(self):
        # Read the CSV file
        df = pd.read_csv(self.csv_path,engine="python",sep=',',encoding="cp437")

        # Get the current model prefix
        current_model_prefix = self.model_prefix_le.text()

        # Check if the current model prefix exists in the 'model type' column
        if current_model_prefix not in df['model type'].values:
            # If it doesn't exist, append a new row to the DataFrame
            new_row = {'model type': current_model_prefix, 'path to model folder': str(Path(self.model_path_le.text()))}
            df = df.append(new_row, ignore_index=True)

            # Write the DataFrame back to the CSV file
            df.to_csv(self.csv_path, index=False)
            
    def run_sleapGUI(self):
        self.status_message.setText("Running SLEAP...")
      
        file_path = Path(self.le.text())        
        

        csv_path = Path(self.model_path_CSV_le.text())
        manual_model_path = Path(self.model_path_le.text())
        if self.manual_model_checkbox.isChecked():
            chosen_model = Path(manual_model_path)
            animal_type = [self.model_prefix_le.text()]
        elif self.use_csv_checkbox.isChecked():
            chosen_model=csv_path
            animal_type = self.cb.currentText().split(',')
        
        
        self.chosen_model= chosen_model


        #close the GUI window
#        self.close()
#        QApplication.processEvents()  # Process any pending events
#        QApplication.quit()  # Destroy the QApplication
        sleap_processor = SleapProcessor()      
        sleap_processor.paths_csv=csv_path
        sleap_processor.chosen_model = chosen_model

        # Set the output directory
        directory = Path(os.path.dirname(file_path)) / 'tracked'      
        directory.mkdir(exist_ok=True)

        # Construct the log file path
        log_file_path = Path(directory) / 'sleap_commands.log'
        sleap_processor.log_file_path= log_file_path
        sleap_processor.start_logger()
        sleap_processor.logger.info('Processing: input_folder=%s,  model_type=%s, csv_file=%s', file_path, animal_type, csv_path)        

        op_arg=self.optional_args_le.text()
           
        self.save_config()

        # run sleap pipeline 
        sleap_processor.config_path = self.config_path
        sleap_processor.read_config()

        sleap_processor.run_sleap()
        self.status_message.setText("Process completed successfully.")

    def save_config(self):
        # Save the user input parameters to the configuration file
        data = {
            'file_path': str(self.le.text()),
            'csv_path': str(self.model_path_CSV_le.text()),
            'optional_args': self.optional_args_le.text(),
            'animal_type': self.cb.currentText().split(','),
            'chosen_model': str(self.chosen_model),
            'model_prefix': self.model_prefix_le.text(),
        }

        with open(self.config_path, 'w') as f:
            json.dump(data, f)

if __name__ == '__main__':
    app = QApplication([])
    ex = InputBox()
    ex.show()
    app.exec_()
