# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 12:38:18 2025

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
#     def __init__(self, text_edit):
#         self.text_edit = text_edit

#     def write(self, text):
#         self.text_edit.append(text)

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
        self.csv_path = Path("\\\\gpfs.corp.brain.mpg.de\\stem\\data\\project_hierarchy\\Sleap_projects\\sleap_model_paths.csv")#.as_posix()
        self.optional_args = ''
        self.user_model_path = None  # New attribute for user selected model path
        self.model_prefix = ''
        self.chosen_model = Path()
        self.csv_layout =  QGridLayout()
        self.manual_layout =  QGridLayout()
        self.log_file_path=''
       
 
        # Initialize the configuration file path  

                
        # Check if the current operating system is Windows
        if platform.system() == 'Windows':
            # Change the home directory to the 'Users\Default' folder so all users can access the config file
            home_directory = Path(os.environ['USERPROFILE']).parent / 'Default'
        else:
            # Get the user's home directory path
            home_directory = Path.home()
        # Create the full path for the config file
        config_file_name='autosleap_config.json'
        self.config_path = home_directory / config_file_name
        
        
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
        #if  csv is not found, prompt user for another one
        self.getfile_csv()
        
        self.initUI()

    def getfile_csv(self):
        """
        Open a file dialog to select a CSV file containing model paths.
        """
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if fileName:
            self.csv_path = Path(fileName)
            self.model_path_CSV_le.setText(str(self.csv_path))
            self.update_csv_combos()
        
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
        Open a file dialog and update the file path text field with the selected file or directory.
        """
        if self.file_mode_checkbox.isChecked():
            # Folder mode
            directory = QFileDialog.getExistingDirectory(self, "Select Directory")
            if directory:
                self.file_path = Path(directory)
                self.le.setText(str(self.file_path))
        else:
            # File mode
            fileName, _ = QFileDialog.getOpenFileName(
                self,
                "Select Video File",
                "",
                "Video Files (*.avi *.mp4 *.mov);;All Files (*)"
            )
            if fileName:
                self.file_path = Path(fileName)
                self.le.setText(str(self.file_path))

    def getfile_csv(self):
        """
        Open a file dialog to select a CSV file containing model paths.
        """
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if fileName:
            self.csv_path = Path(fileName)
            self.model_path_CSV_le.setText(str(self.csv_path))
            self.update_csv_combos()
    
    def getfolder(self):
        """
        Open a folder dialog to select a model directory.
        """
        directory = QFileDialog.getExistingDirectory(self, "Select Model Directory")
        if directory:
            self.user_model_path = Path(directory)
            self.model_path_le.setText(str(self.user_model_path))
    
    def switch_mode(self, state):
        """
        Switch between file and folder selection modes.
        """
        if state:
            self.btn.clicked.disconnect()
            self.btn.clicked.connect(self.getfile_video)
        else:
            self.btn.clicked.disconnect()
            self.btn.clicked.connect(self.getfile_video)
        self.le.clear()
    
    def switch_csv_mode(self, state):
        """
        Switch to CSV-based model selection mode.
        """
        if state:
            self.manual_model_checkbox.setChecked(False)
            self.showLayout(self.csv_layout)
            self.hideLayout(self.manual_layout)
            self.update_combos(useCSV=True)
    
    def switch_model_mode(self, state):
        """
        Switch to manual model selection mode.
        """
        if state:
            self.use_csv_checkbox.setChecked(False)
            self.hideLayout(self.csv_layout)
            self.showLayout(self.manual_layout)
    
    def update_combos(self, useCSV=True):
        """
        Update the combo box with available model types.
        """
        self.cb.clear()
        if useCSV and self.csv_path.exists():
            try:
                df = pd.read_csv(self.csv_path)
                unique_types = df['animal_type'].unique()
                self.cb.addItems(unique_types)
            except Exception as e:
                print(f"Error reading CSV file: {e}")
        
    def update_csv_combos(self):
        """
        Update combo boxes based on the current CSV file.
        """
        self.update_combos(useCSV=True)
    
    def save_model_to_csv(self):
        """
        Save manually selected model information to the CSV file.
        """
        if not self.model_path_le.text() or not self.model_prefix_le.text():
            print("Please enter both model path and prefix")
            return
    
        new_row = {
            'animal_type': self.model_prefix_le.text(),
            'model_path': str(self.model_path_le.text())
        }
    
        try:
            df = pd.read_csv(self.csv_path) if self.csv_path.exists() else pd.DataFrame(columns=['animal_type', 'model_path'])
            df = df.append(new_row, ignore_index=True)
            df.to_csv(self.csv_path, index=False)
            print("Model successfully added to CSV file")
            self.update_csv_combos()
        except Exception as e:
            print(f"Error saving to CSV: {e}")