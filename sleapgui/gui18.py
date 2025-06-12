# -*- coding: utf-8 -*-
"""
Created on Thu Jun 12 10:41:23 2025

@author: su-weisss
"""

import os
import sys
import json
import platform     
import traceback
import pandas as pd
from utils import find_logo
from classes import SleapProcessor
from itertools import chain, combinations
from pathlib import Path#, PureWindowsPath
from PySide2.QtCore import QThread, Signal#,Qt,
from PySide2.QtGui import  QPixmap, Qt, QPalette, QColor,QTextCursor#, QFont,QIcon
from PySide2.QtWidgets import QApplication, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox, QFileDialog, QWidget, QCheckBox, QTextEdit, QGridLayout,QSizePolicy#,QRadioButton QDesktopWidget,

class OutputRedirector:
    def __init__(self, text_edit):
        self.text_edit = text_edit

    def write(self, text):
        self.text_edit.append(text)
        self.text_edit.moveCursor(QTextCursor.End)  # Move the cursor to the end of the text
        self.text_edit.ensureCursorVisible()  # Ensure the cursor is visible

# class OutputRedirector:
#      def __init__(self, text_edit):
#          self.text_edit = text_edit

#      def write(self, text):
#          self.text_edit.append(text)

class SleapThread(QThread):
    signal = Signal(str)

    def __init__(self, sleap_processor):
        QThread.__init__(self)
        self.sleap_processor = sleap_processor

    def run(self):          

            output = self.sleap_processor.run_sleap()
            self.signal.emit(output)
#            self.update_status_message(output)

class InputBox(QWidget):    

                                
    def __init__(self):
        """
        Initialize the GUI and load any previously saved configuration.
        """
        super().__init__()        

        # Initialize the parameters with default values
        self.file_path = Path()
        self.animal_type = []
        # 1. Modify self.csv_path to a string for cross-platform compatibility
        self.csv_path = str(Path("//gpfs.corp.brain.mpg.de/stem/data/project_hierarchy/Sleap_projects/sleap_model_paths.csv"))
        self.optional_args = ''
        self.user_model_path = None  # New attribute for user selected model path
        self.model_prefix = ''
        self.chosen_model = Path()
        self.csv_layout =  QGridLayout()
        self.manual_layout =  QGridLayout()
        self.log_file_path=''
        
    
        # Initialize the configuration file path  

                        
        # 2. Change home_directory to point to the script's running directory
        script_dir = Path(sys.argv[0]).parent
        config_file_name='autosleap_config.json'
        self.config_path = script_dir / config_file_name
        
        
#        self.config_path = Path(env_dir, 'autosleap_config.json')  

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
        self.model_path_CSV_le.setText(str(self.csv_path)) # Set initial text using the corrected self.csv_path
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
        self.btn_model.clicked.connect(lambda: self.switch_model_mode(state=Qt.Checked)) # Connect with a lambda to pass Qt.Checked
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
        
        self.status_message = QTextEdit("status: waiting for user input")
        layout.addWidget(self.status_message)

        # Redirect standard output to the QTextEdit
        sys.stdout = OutputRedirector(self.status_message)
      
        
        # self.status_message = QLabel("status: waiting for user input")
        # layout.addWidget(self.status_message)

      
        
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
        # Ensure self.csv_path is updated from the QLineEdit before calling update_combos
        self.csv_path = Path(self.model_path_CSV_le.text())
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
            # If manual is unchecked, ensure CSV is checked and update combos
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
            # If CSV is unchecked, ensure manual is checked
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
            csvfile = self.csv_path
        else:
            # If csvfile is explicitly provided and not None, convert it to Path
            if csvfile is not None:
                csvfile = Path(csvfile)
            else:
                # If no csvfile is provided and useCSV is False, try to get from QLineEdit
                csvfile = Path(self.model_path_CSV_le.text())


        try:
            if not csvfile.exists():
                self.getfile_csv()
                csvfile = self.csv_path
        except Exception as e:
            print(f"Please check 'destination is available: {csvfile}'. Error: {e}")
            useCSV=False
       # print(csvfile)          
        if useCSV and csvfile.exists(): # Added check for csvfile.exists() to prevent error            
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
        # Ensure self.csv_path is up-to-date with the QLineEdit value
        self.csv_path = Path(self.model_path_CSV_le.text())

        # Check if the CSV file exists
        if not self.csv_path.exists():
            # If it doesn't exist, open a file dialog for the user to choose where to save the CSV file and name it
            self.get_save_csv_file()
            # After get_save_csv_file, self.csv_path will be updated. If the user cancels, it won't be,
            # so we check again before proceeding.
            if not self.csv_path.exists(): # If user cancelled, exit
                print("CSV save cancelled by user.")
                return
        
        # If it does exist (or was just created), proceed with saving the model to the CSV file
        try:
            # Read the CSV file
            df = pd.read_csv(self.csv_path, engine="python", sep=',', encoding="cp437")

            # Get the current model prefix
            current_model_prefix = self.model_prefix_le.text()

            # Check if the current model prefix exists in the 'model type' column
            if current_model_prefix not in df['model type'].values:
                # If it doesn't exist, append a new row to the DataFrame
                new_row = {'model type': current_model_prefix, 'path to model folder': Path(self.model_path_le.text()).as_posix()}
                # Use pd.concat instead of append for newer pandas versions
                new_row_df = pd.DataFrame([new_row])
                df = pd.concat([df, new_row_df], ignore_index=True)

                # Write the DataFrame back to the CSV file
                df.to_csv(self.csv_path, index=False)
                print(f"Model '{current_model_prefix}' saved to {self.csv_path}")
            else:
                print(f"Model '{current_model_prefix}' already exists in {self.csv_path}. Not adding duplicate.")
            
            # After saving, update the comboboxes to reflect the new entry
            self.update_combos(useCSV=True)

        except Exception as e:
            print(f"Error saving model to CSV: {e}")


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
        # Check if 'message' is a string
        if isinstance(message, str):
          self.status_message.append(message)
          
        # Check if 'message' is a list
        elif isinstance(message, list):
          # Check if all items in the list are strings
            if all(isinstance(item, str) for item in message):
        
              message_str = '\n'.join(message)  # Join all items in the list into a single string separated by newlines
              self.status_message.append(message_str)  # Append the resulting string to the QTextEdit
        
        else:
          # Assuming message is a list of non-string items
          message_str = '\n'.join(str(item) for item in message)  # Convert each item to a string and join them
          self.status_message.append(message_str)

        # self.status_message.append(message)
        #self.status_message.setText(message)
        self.status_message.moveCursor(QTextCursor.End)  # Move the cursor to the end of the text
        self.status_message.ensureCursorVisible()  # Ensure the cursor is visible

    
    
    def run_sleapGUI(self):
        """
        Run the SLEAP pipeline with the current configuration.
        """
        message = "RUNNING SLEAP"
        #self.thread.signal.connect(self.update_status_message)
        self.update_status_message(message)  

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
            #leap_processor = SleapProcessor()
            sleap_processor = SleapProcessor(self.update_status_message)
    
            
            sleap_processor.paths_csv=csv_path
            sleap_processor.chosen_model = chosen_model
    
            # Set the output directory
            directory = Path(os.path.dirname(file_path)) / 'tracked'        
            directory.mkdir(exist_ok=True)

            # Construct the log file path
            log_file_path = Path(directory) / 'sleap_commands.log'
            self.log_file_path  = log_file_path
            
            sleap_processor.log_file_path= log_file_path
            sleap_processor.start_logger()
            sleap_processor.logger.info('Processing: input_folder=%s,  model_type=%s, csv_file=%s, logger_path=%s', file_path, animal_type, csv_path,log_file_path)            
    
            op_arg=self.optional_args_le.text()
                        
            
            
            #write to config file
            self.save_config(file_path=str(file_path), csv_path=str(csv_path), animal_type=animal_type,optional_args=op_arg)
    
            # run read from config file  
            sleap_processor.config_path = self.config_path
            sleap_processor.read_config()
            # Create a new thread and move the sleap_processor instance to it
            self.thread = SleapThread(sleap_processor)
            self.thread.signal.connect(self.update_status_message)
            self.thread.start()
    
        except Exception as e: #if there's an error, show it to the user            
            tb = traceback.format_exc()
            message =f"An error occurred: {str(e)}\n{tb}"
            #self.thread.signal.connect(self.update_status_message)
            self.update_status_message(message)    
            
            
                        
def manage_app():
        # Check if QApplication instance exists
        app = QApplication.instance()
    
        # If it exists, quit the application
        if app is not None:
            app.quit()
    
        # Create a new QApplication instance
        app = QApplication(sys.argv)
        return app

if __name__ == '__main__':
    # This block is crucial for multiprocessing to work correctly on some platforms (like Windows)
    # It prevents child processes from re-importing and re-executing the main script's code.
    app = manage_app()  
    ex = InputBox()
    ex.show()
    app.exec_()
