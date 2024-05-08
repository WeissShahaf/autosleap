from itertools import chain, combinations
from pathlib import Path, PureWindowsPath
import os
import sys
from utils import find_logo
from classes import SleapProcessor
from PySide2.QtCore import Qt,QThread, Signal
from PySide2.QtWidgets import QApplication, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox, QFileDialog, QWidget, QDesktopWidget, QCheckBox, QTextEdit, QGridLayout,QSizePolicy,QRadioButton
from PySide2.QtGui import QIcon, QPixmap, Qt, QPalette, QColor, QFont
from itertools import chain, combinations
import IPython
import json
import pandas as pd
import traceback
         
class InputBox(QWidget):    
    class SleapThread(QThread):
        signal = Signal(str)
    
        def __init__(self, sleap_processor):
            QThread.__init__(self)
            self.sleap_processor = sleap_processor
    
        def run(self):
            self.sleap_processor.run_sleap()
            self.signal.emit("Process completed successfully.")
               
    def __init__(self):
        """
        Initialize the GUI and load any previously saved configuration.
        """
        super().__init__()       

        # Initialize the parameters with default values
        self.file_path = Path()
        self.animal_type = []
        self.csv_path = Path("\\\\gpfs.corp.brain.mpg.de\\stem\\data\\project_hierarchy\\Sleap_projects\\sleap_model_paths.csv")
        self.optional_args = ''
        self.user_model_path = None  # New attribute for user selected model path
        self.model_prefix = ''
        self.chosen_model = Path()
        self.csv_layout =  QGridLayout()
        self.manual_layout =  QGridLayout()
       
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
        """
        Initialize the user interface elements of the GUI.
        """
        spacing=70
#        grid_layout = QGridLayout()
        layout = QVBoxLayout()
        layout.setSpacing(20)
          
        #set the layout to display
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor('white'))  # Change 'red' to your desired color
        self.setPalette(palette)

        # Add image at the top
        label = QLabel(self)
        logo_path=find_logo()
        pixmap = QPixmap(logo_path)
        pixmap = pixmap.scaled(256, 256, Qt.KeepAspectRatio)
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
        self.file_mode_checkbox = QCheckBox("Folder mode", self)
        self.file_mode_checkbox.stateChanged.connect(self.switch_mode)
        file_path_layout.addWidget(self.file_mode_checkbox)
        
        self.le = QLineEdit()
        file_path_layout.addWidget(self.le)
        
        self.btn = QPushButton("Browse")
        self.btn.clicked.connect(self.getfile_video)  # default to file mode
        file_path_layout.addWidget(self.btn)
        layout.addLayout(file_path_layout)
        
        
        arg_layout =  QHBoxLayout()
        # Add a QLineEdit for optional_args
        arg_layout.addWidget(QLabel("Optional sleap-track Arguments (e.g. --batch_size 50 ):  "))
        self.optional_args_le = QLineEdit()
        arg_layout.addWidget(self.optional_args_le)
        layout.addLayout(arg_layout)
        
        layout.addSpacing(spacing)
        
        layout.addWidget(QLabel("Model selection:")) 
        radiobuttons_layout = QHBoxLayout()
        self.use_csv_checkbox = QCheckBox("From CSV file", self)
        self.use_csv_checkbox.stateChanged.connect(self.switch_csv_mode)
        radiobuttons_layout.addWidget(self.use_csv_checkbox)
        
        self.manual_model_checkbox = QCheckBox("Manual selection", self)
        self.manual_model_checkbox.stateChanged.connect(self.switch_model_mode)
        radiobuttons_layout.addWidget(self.manual_model_checkbox)
        
        
        layout.addLayout(radiobuttons_layout)
        layout.addSpacing(spacing)
        
        
        
        options_layout = QHBoxLayout()
        self.csv_layout =  QGridLayout()
        
        self.csv_layout.addWidget(QLabel("CSV file containing model Paths:"),0,0,1,1)
        self.model_path_CSV_le = QLineEdit()
        self.model_path_CSV_le.setText("\\\\gpfs.corp.brain.mpg.de\\stem\\data\\project_hierarchy\\Sleap_projects\\sleap_model_paths.csv")
        self.csv_layout.addWidget(self.model_path_CSV_le,0,1,1,3)
        
        
        self.csv_layout.addWidget(QLabel("Model Types to infer:"),1,0,1,1)
        self.cb = QComboBox()
        self.update_combos(useCSV=True)
        self.cb.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        self.csv_layout.addWidget(self.cb,1,1,1,1)
        

        self.csvbtn = QPushButton("Browse")
        self.csvbtn.clicked.connect(self.getfile_csv)  # default to file mode
        self.csv_layout.addWidget(self.csvbtn,0,4,1,1)
        
        
        
        self.csvbtn = QPushButton("Update models list from CSV file")
        self.csvbtn.clicked.connect(self.update_csv_combos)  # default to file mode
        self.csv_layout.addWidget(self.csvbtn,1,4,1,1)
        
      
        

        options_layout.addLayout(self.csv_layout)
        options_layout.addSpacing(spacing)
        
        self.manual_layout =  QGridLayout()
        # Add a new QLineEdit for model path
        self.manual_layout.addWidget(QLabel("Enter model path:"),0,0,1,1)
        self.model_path_le = QLineEdit()
        self. manual_layout.addWidget(self.model_path_le,0,1,1,2)
        
        # Add a new browse button for model selection
        self.btn_model = QPushButton("Browse for model")
        self.btn_model.clicked.connect(self.getfolder)
        self.btn_model.clicked.connect(self.switch_model_mode(state=True))        
        self.manual_layout.addWidget(self.btn_model,0,3,1,1)


        # Add a new QLineEdit for model path
        self.manual_layout.addWidget(QLabel("Enter model prefix:"),1,0,1,1)
        self.model_prefix_le = QLineEdit()
        self.manual_layout.addWidget(self.model_prefix_le,1,1,1,2)
        
         # Add a new button for saving model to CSV file
        self.btn_save_model = QPushButton("Save Model to CSV File")
        self.btn_save_model.clicked.connect(self.save_model_to_csv)
        self.manual_layout.addWidget(self.btn_save_model,1,3,1,1)

        
        options_layout.addLayout(self.manual_layout)
        
        layout.addLayout(options_layout)
        
        self.fill_from_config()
            


        layout.addSpacing(spacing)
        
        GUI_layout = QHBoxLayout()

        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(self.quitApp)
        GUI_layout.addWidget(self.quit_btn)
        
        
       
        self.reset_btn = QPushButton("reset GUI")
        self.reset_btn.clicked.connect(self.reset)
        GUI_layout.addWidget(self.reset_btn)
        
        self.submit_btn = QPushButton("Run SLEAP")
        self.submit_btn.setStyleSheet("color: blue")

        self.submit_btn.clicked.connect(self.run_sleapGUI)
        GUI_layout.addWidget(self.submit_btn)

        layout.addLayout(GUI_layout)
      
        
        self.status_message = QLabel("status: waiting for user input")
        layout.addWidget(self.status_message)

      
        
        self.showLayout(self.csv_layout)
        self.hideLayout(self.manual_layout)
        
        self.show()
        self.setLayout(layout)
        
    def fill_from_config(self):
    #get previous data to prefill if config file exists
     if self.config_path.exists() and os.path.getsize(self.config_path) > 0:
        with open(self.config_path, 'r') as f:
            data = json.load(f)

        self.le.setText(data['file_path'])
        self.model_path_CSV_le.setText(data['csv_path'])
        self.optional_args_le.setText(data['optional_args'])
        self.cb.setCurrentText(', '.join(data['animal_type']))
        self.model_prefix_le.setText(data['model_prefix'])
    
    def onRadioButtonToggled(self):
     if self.radioButton1.isChecked():
         self.showLayout(self.csv_layout)
         self.hideLayout(self.manual_layout)
     else:
         self.hideLayout(self.csv_layout)
         self.showLayout(self.manual_layout)

    def showLayout(self, layout):
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget is not None:
                widget.show()

    def hideLayout(self, layout):
     for i in range(layout.count()):
         widget = layout.itemAt(i).widget()
         if widget is not None:
             widget.hide()

    def reset(self):
        """
        Reset the GUI to its initial state.
        """
        self.fill_from_config()

    def center(self):
        """
        Center the GUI window on the screen.
        """
        frame = self.frameGeometry()
        center_point = QApplication.primaryScreen().availableGeometry().center()
        frame.moveCenter(center_point)
        self.move(frame.topLeft())

    def quitApp(self):
        """
        Close the GUI and quit the application.
        """
        self.close()
        QApplication.quit()

    def getfile_video(self):
        """
        Open a file dialog and update the file path text field with the selected file.
        """
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "All Files (*);;csv Files (*.csv);;MP4 Files (*.mp4);;avi Files (*.avi)")
        if fileName:
            self.le.setText(fileName)

    def getfile_csv(self):
        """
        Open a file dialog and update the file path text field with the selected file.
        """
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "All Files (*);;csv Files (*.csv);;MP4 Files (*.mp4);;avi Files (*.avi)")
        if fileName:
            self.model_path_CSV_le.setText(fileName)
            self.csv_path=Path(fileName)
            self.update_combos(useCSV=True)

    def update_csv_combos(self):
        self.csv_path==Path(self.model_path_CSV_le.text())
        self.update_combos(useCSV=True)

    def getfolder(self):
        """
        Open a folder dialog and update the model path text field with the selected folder.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")     
        if folder:
            self.model_path_le.setText(folder)
            self.le.setText(folder)

    def switch_mode(self, state):
        """
        Switch between file and folder mode for the file path input.
        """
        if state == Qt.Checked:
            self.btn.clicked.disconnect()
            self.btn.clicked.connect(self.getfolder)
        else:
            self.btn.clicked.disconnect()
            self.btn.clicked.connect(self.getfile_video)

    def switch_model_mode(self, state):
        """
        Switch between manual and CSV mode for the model selection.
        """
        if state == Qt.Checked:
            self.use_csv_checkbox.setChecked(False)
            self.hideLayout(self.csv_layout)
            self.showLayout(self.manual_layout)
        else:
            self.use_csv_checkbox.setChecked(True)
            self.update_combos(useCSV=True)
            self.showLayout(self.csv_layout)
            self.hideLayout(self.manual_layout)

    def switch_csv_mode(self, state):
        """
        Switch between CSV and manual mode for the model selection.
        """
        if state == Qt.Checked:
            self.manual_model_checkbox.setChecked(False)
            self.use_csv_checkbox.setChecked(True)
            self.showLayout(self.csv_layout)
            self.hideLayout(self.manual_layout)
            self.update_combos(useCSV=True)
        else:
            self.manual_model_checkbox.setChecked(True)
            self.use_csv_checkbox.setChecked(False)
            self.hideLayout(self.csv_layout)
            self.showLayout(self.manual_layout)

    def all_combinations(self,lst:list):
        """
        Generate all combinations of a list.
        """
        return list(chain(*[combinations(lst, i + 1) for i, _ in enumerate(lst)]))

    def update_combos(self, useCSV=False,csvfile=None):
        """
        Update the model types dropdown based on the available models.
        """
        if useCSV:
            csvfile= self.csv_path
        else:
            csvfile=Path(csvfile)
       # print(csvfile)         

        df = pd.read_csv(csvfile, engine="python", sep=',', encoding="cp437")
        animals = df['model type'].tolist()

        combos = self.all_combinations(animals)

        #  Use a set to store the combinations
        combo_set = set()

        for combo in combos:
            # Convert the combination to a string
            combo_str = ", ".join(combo)

            # Add the combination to the set
            combo_set.add(combo_str)

            # Clear the dropdown menu
            self.cb.clear()

        # Add the combinations in the set to the dropdown menu
        for combo_str in combo_set:
            self.cb.addItem(combo_str)

    def save_model_to_csv(self):
        """
        Save the current model to the CSV file.
        """
        # Check if the CSV file exists
        if not os.path.exists(self.csv_path):
            # If it doesn't exist, open a file dialog for the user to choose where to save the CSV file and name it
            self.get_save_csv_file()
        else:
            # If it does exist, proceed with saving the model to the CSV file
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

    def get_save_csv_file(self):
        """
        Open a file dialog for the user to choose where to save the CSV file and name it.
        """
        fileName, _ = QFileDialog.getSaveFileName(self, "QFileDialog.getSaveFileName()", "", "CSV Files (*.csv)")
        if fileName:
            self.csv_path = Path(fileName)


    def save_config(self, file_path=None, csv_path=None, optional_args=None, animal_type=None, chosen_model=None, model_prefix=None):
         """
         Save the current configuration to the configuration file.
         Or override with user inputs
         """     
         #format data for config file
         data = {
             'file_path': file_path if file_path is not None else str(self.le.text()),
             'csv_path': csv_path if csv_path is not None else str(self.model_path_CSV_le.text()),
             'optional_args': optional_args if optional_args is not None else self.optional_args_le.text(),
             'animal_type': animal_type if animal_type is not None else self.cb.currentText().split(','),
             'chosen_model': chosen_model if chosen_model is not None else str(self.chosen_model),
             'model_prefix': model_prefix if model_prefix is not None else self.model_prefix_le.text(),
         }
         #write config file
         with open(self.config_path, 'w') as f:
                  json.dump(data, f)
    
    def update_status_message(self, message):
        self.status_message.setText(message)
        
   
    
    def run_sleapGUI(self):
        """
        Run the SLEAP pipeline with the current configuration.
        """
        
        noErrors=True
        try:        
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
#            sleap_processor = SleapProcessor(self.update_status_message)
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
               
            #IPython.core.debugger.set_trace()           
            #write to config file
            self.save_config(file_path=str(file_path), csv_path=str(csv_path), animal_type=animal_type,optional_args=op_arg)
    
            # run read from config file 
            sleap_processor.config_path = self.config_path
            sleap_processor.read_config()
            # run sleap pipeline             
            
            self.thread = self.SleapThread(sleap_processor)
            message="Running SLEAP"
            self.thread.signal.connect(self.update_status_message)
            self.thread.start()           
            
        #    self.status_message.setText("Running SLEAP")
               
    
        except Exception as e: #if there's an error, show it to the user
            noErrors = False
            tb = traceback.format_exc()
            message =f"An error occurred: {str(e)}\n{tb}"
            #self.thread.signal.connect(self.update_status_message)
            self.status_message.setText(message)         
        
        if noErrors: 
            message = f"Succescully finished processing"
            self.thread.signal.connect(self.update_status_message)
            
                    
def manage_app():
        # Check if QApplication instance exists
        app = QApplication.instance()
    
        # If it exists, quit the application
        if app is not None:
            app.quit()
    
        # Create a new QApplication instance
        app = QApplication(sys.argv)
        return app

# Usage:
   
     

if __name__ == '__main__':
    app = manage_app()  
    ex = InputBox()
    ex.show()
    app.exec_()

                       