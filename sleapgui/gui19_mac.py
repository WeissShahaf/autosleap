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
from pathlib import Path
from PySide2.QtCore import QThread, Signal, Qt
from PySide2.QtGui import  QPixmap, QPalette, QColor, QTextCursor
from PySide2.QtWidgets import (QApplication, QLabel, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLineEdit, QComboBox, QFileDialog, 
                               QWidget, QCheckBox, QTextEdit, QGridLayout, QSizePolicy)

class OutputRedirector:
    def __init__(self, text_edit):
        self.text_edit = text_edit

    def write(self, text):
        self.text_edit.append(text)
        self.text_edit.moveCursor(QTextCursor.End)
        self.text_edit.ensureCursorVisible()

class SleapThread(QThread):
    signal = Signal(str)

    def __init__(self, sleap_processor):
        QThread.__init__(self)
        self.sleap_processor = sleap_processor

    def run(self):          
        output = self.sleap_processor.run_sleap()
        self.signal.emit(output)

class InputBox(QWidget):    
    def __init__(self):
        """
        Initialize the GUI and load any previously saved configuration.
        """
        super().__init__()        

        # Initialize the parameters with default values
        self.file_path = Path()
        self.animal_type = []
        # Platform-agnostic way to get the user's home directory.
        home_dir = Path.home()
        # Set a default, cross-platform-friendly path for the CSV.
        # This avoids hardcoding a Windows-specific network path.
        self.csv_path = str(home_dir / "sleap_model_paths.csv")
        self.optional_args = ''
        self.user_model_path = None
        self.model_prefix = ''
        self.chosen_model = Path()
        self.csv_layout =  QGridLayout()
        self.manual_layout =  QGridLayout()
        self.log_file_path=''
        
        # Initialize the configuration file path in the script's directory
        script_dir = Path(sys.argv[0]).parent
        config_file_name = 'autosleap_config.json'
        self.config_path = script_dir / config_file_name
        
        # Load config if it exists
        if self.config_path.exists() and os.path.getsize(self.config_path) > 0:
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)

                self.file_path = Path(data.get('file_path', ''))
                self.animal_type = data.get('animal_type', [])
                self.csv_path = Path(data.get('csv_path', self.csv_path))
                self.optional_args = data.get('optional_args', '')
                self.chosen_model = Path(data.get('chosen_model', ''))
                self.model_prefix = data.get('model_prefix', '')
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not load config file. Using defaults. Error: {e}")
        
        self.initUI()

    
    def initUI(self):
        """
        Initialize the user interface elements of the GUI.
        """
        spacing = 70
        layout = QVBoxLayout()
        layout.setSpacing(20)
            
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor('white'))
        self.setPalette(palette)

        # Add image at the top
        label = QLabel(self)
        try:
            logo_path = find_logo()
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaled(256, 256, Qt.KeepAspectRatio)
            label.setPixmap(pixmap)
        except FileNotFoundError:
            label.setText("Logo not found")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
                                
        self.setWindowTitle("Auto-sleap GUI")
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen.width() // 4, screen.height() // 4, screen.width() // 2, screen.height() // 2)
        self.center()

        # File/Folder Path layout
        layout.addWidget(QLabel("File/Folder Path:"))
        file_path_layout = QHBoxLayout()
        self.file_mode_checkbox = QCheckBox("Folder mode", self)
        self.file_mode_checkbox.stateChanged.connect(self.switch_mode)
        file_path_layout.addWidget(self.file_mode_checkbox)
        self.le = QLineEdit()
        file_path_layout.addWidget(self.le)
        self.btn = QPushButton("Browse")
        self.btn.clicked.connect(self.getfile_video)
        file_path_layout.addWidget(self.btn)
        layout.addLayout(file_path_layout)
        
        # Optional arguments layout
        arg_layout = QHBoxLayout()
        arg_layout.addWidget(QLabel("Optional sleap-track Arguments (e.g. --batch_size 50):"))
        self.optional_args_le = QLineEdit()
        arg_layout.addWidget(self.optional_args_le)
        layout.addLayout(arg_layout)
        
        layout.addSpacing(spacing)
        
        # Model selection layout
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
        # CSV Layout
        self.csv_layout = QGridLayout()
        self.csv_layout.addWidget(QLabel("CSV file with model paths:"), 0, 0, 1, 1)
        self.model_path_CSV_le = QLineEdit()
        self.model_path_CSV_le.setText(str(self.csv_path))
        self.csv_layout.addWidget(self.model_path_CSV_le, 0, 1, 1, 3)
        self.csvbtn_browse = QPushButton("Browse")
        self.csvbtn_browse.clicked.connect(self.getfile_csv)
        self.csv_layout.addWidget(self.csvbtn_browse, 0, 4, 1, 1)
        self.csv_layout.addWidget(QLabel("Model Types to infer:"), 1, 0, 1, 1)
        self.cb = QComboBox()
        self.update_combos(useCSV=True)
        self.cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.csv_layout.addWidget(self.cb, 1, 1, 1, 1)
        self.csvbtn_update = QPushButton("Update models from CSV")
        self.csvbtn_update.clicked.connect(self.update_csv_combos)
        self.csv_layout.addWidget(self.csvbtn_update, 1, 4, 1, 1)
        options_layout.addLayout(self.csv_layout)
        
        options_layout.addSpacing(spacing)

        # Manual Layout
        self.manual_layout = QGridLayout()
        self.manual_layout.addWidget(QLabel("Enter model path:"), 0, 0, 1, 1)
        self.model_path_le = QLineEdit()
        self.manual_layout.addWidget(self.model_path_le, 0, 1, 1, 2)
        self.btn_model = QPushButton("Browse for model")
        self.btn_model.clicked.connect(self.getfolder_model)
        self.manual_layout.addWidget(self.btn_model, 0, 3, 1, 1)
        self.manual_layout.addWidget(QLabel("Enter model prefix:"), 1, 0, 1, 1)
        self.model_prefix_le = QLineEdit()
        self.manual_layout.addWidget(self.model_prefix_le, 1, 1, 1, 2)
        self.btn_save_model = QPushButton("Save Model to CSV File")
        self.btn_save_model.clicked.connect(self.save_model_to_csv)
        self.manual_layout.addWidget(self.btn_save_model, 1, 3, 1, 1)
        options_layout.addLayout(self.manual_layout)
        
        layout.addLayout(options_layout)
        self.fill_from_config()
        layout.addSpacing(spacing)
        
        # Control Buttons Layout
        GUI_layout = QHBoxLayout()
        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(self.quitApp)
        GUI_layout.addWidget(self.quit_btn)
        self.reset_btn = QPushButton("Reset GUI")
        self.reset_btn.clicked.connect(self.reset)
        GUI_layout.addWidget(self.reset_btn)
        self.submit_btn = QPushButton("Run SLEAP")
        self.submit_btn.setStyleSheet("color: blue")
        self.submit_btn.clicked.connect(self.run_sleapGUI)
        GUI_layout.addWidget(self.submit_btn)
        layout.addLayout(GUI_layout)
        
        # Status message box
        self.status_message = QTextEdit("Status: waiting for user input")
        layout.addWidget(self.status_message)
        sys.stdout = OutputRedirector(self.status_message)
        
        self.showLayout(self.csv_layout)
        self.hideLayout(self.manual_layout)
        
        self.setLayout(layout)
        self.show()
        self.use_csv_checkbox.setChecked(True)

    def fill_from_config(self):
        if self.config_path.exists() and os.path.getsize(self.config_path) > 0:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            self.le.setText(data.get('file_path', ''))
            self.model_path_CSV_le.setText(data.get('csv_path', ''))
            self.optional_args_le.setText(data.get('optional_args', ''))
            self.model_prefix_le.setText(data.get('model_prefix', ''))
            animal_types_str = ', '.join(data.get('animal_type', []))
            self.cb.setCurrentText(animal_types_str)
            self.update_combos(useCSV=True) # Refresh combos
            self.cb.setCurrentText(animal_types_str) # Re-set current text

    def showLayout(self, layout):
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget is not None: widget.show()

    def hideLayout(self, layout):
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget is not None: widget.hide()

    def reset(self): self.fill_from_config()
    def center(self):
        frame = self.frameGeometry()
        center_point = QApplication.primaryScreen().availableGeometry().center()
        frame.moveCenter(center_point)
        self.move(frame.topLeft())

    def quitApp(self): self.close(); QApplication.quit()
    def getfile_video(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi);;All Files (*)")
        if fileName: self.le.setText(fileName)

    def getfile_csv(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Select CSV Model File", "", "CSV Files (*.csv);;All Files (*)")
        if fileName:
            self.model_path_CSV_le.setText(fileName)
            self.csv_path = Path(fileName)
            self.update_combos(useCSV=True)

    def update_csv_combos(self):
        self.csv_path = Path(self.model_path_CSV_le.text())
        self.update_combos(useCSV=True)

    def getfolder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")    
        if folder: self.le.setText(folder)

    def getfolder_model(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Model Folder")    
        if folder:
            self.model_path_le.setText(folder)
            self.switch_model_mode(state=Qt.Checked)

    def switch_mode(self, state):
        self.btn.clicked.disconnect()
        if state == Qt.Checked: self.btn.clicked.connect(self.getfolder)
        else: self.btn.clicked.connect(self.getfile_video)

    def switch_model_mode(self, state):
        if state == Qt.Checked:
            self.manual_model_checkbox.setChecked(True)
            self.use_csv_checkbox.setChecked(False)
            self.hideLayout(self.csv_layout)
            self.showLayout(self.manual_layout)
        else:
            self.manual_model_checkbox.setChecked(False)
            if not self.use_csv_checkbox.isChecked():
                self.use_csv_checkbox.setChecked(True)

    def switch_csv_mode(self, state):
        if state == Qt.Checked:
            self.use_csv_checkbox.setChecked(True)
            self.manual_model_checkbox.setChecked(False)
            self.showLayout(self.csv_layout)
            self.hideLayout(self.manual_layout)
            self.update_combos(useCSV=True)
        else:
            self.use_csv_checkbox.setChecked(False)
            if not self.manual_model_checkbox.isChecked():
                self.manual_model_checkbox.setChecked(True)

    def all_combinations(self, lst: list):
        return list(chain(*[combinations(lst, i + 1) for i, _ in enumerate(lst)]))

    def update_combos(self, useCSV=False):
        csvfile = Path(self.model_path_CSV_le.text()) if useCSV else self.csv_path
        if not csvfile.is_file():
            print(f"Warning: CSV file not found at {csvfile}. Cannot update model list.")
            return

        try:         
            df = pd.read_csv(csvfile)
            animals = df['model type'].unique().tolist()
            combos = self.all_combinations(animals)
            combo_set = {", ".join(map(str, combo)) for combo in combos}
            self.cb.clear()
            self.cb.addItems(sorted(list(combo_set)))
        except (pd.errors.EmptyDataError, FileNotFoundError, KeyError) as e:
            print(f"Could not update combos from {csvfile}. Is it a valid model CSV? Error: {e}")
            self.cb.clear()

    def save_model_to_csv(self):
        csv_path = Path(self.model_path_CSV_le.text())
        model_prefix = self.model_prefix_le.text()
        model_path_str = self.model_path_le.text()

        if not all([csv_path.parent.is_dir(), model_prefix, model_path_str]):
            print("Error: CSV path, model prefix, and model path must all be set.")
            return

        if not csv_path.exists():
            df = pd.DataFrame(columns=['model type', 'path to model folder'])
        else:
            df = pd.read_csv(csv_path)

        if model_prefix in df['model type'].values:
            print(f"Model '{model_prefix}' already exists. Not adding duplicate.")
            return

        # Use as_posix() to save the path with forward slashes for cross-platform compatibility.
        new_path = Path(model_path_str).as_posix()
        new_row = {'model type': model_prefix, 'path to model folder': new_path}
        new_row_df = pd.DataFrame([new_row])
        df = pd.concat([df, new_row_df], ignore_index=True)

        df.to_csv(csv_path, index=False)
        print(f"Model '{model_prefix}' saved to {csv_path}")
        self.update_combos(useCSV=True)

    def save_config(self):
        data = {
            'file_path': self.le.text(),
            'csv_path': self.model_path_CSV_le.text(),
            'optional_args': self.optional_args_le.text(),
            'animal_type': self.cb.currentText().split(', '),
            'chosen_model': str(self.chosen_model),
            'model_prefix': self.model_prefix_le.text(),
        }
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=4)
    
    def update_status_message(self, message):
        self.status_message.append(str(message))
        self.status_message.moveCursor(QTextCursor.End)
        self.status_message.ensureCursorVisible()

    def run_sleapGUI(self):
        self.update_status_message("RUNNING SLEAP...")
        try:          
            file_path = Path(self.le.text())    
            
            if self.manual_model_checkbox.isChecked():
                chosen_model = Path(self.model_path_le.text())
                animal_type = [self.model_prefix_le.text()]
                csv_path = "" # Not used in manual mode
            elif self.use_csv_checkbox.isChecked():
                csv_path = Path(self.model_path_CSV_le.text())
                chosen_model = csv_path
                animal_type = self.cb.currentText().split(', ')
            else:
                self.update_status_message("Error: No model selection mode (CSV or Manual) is checked.")
                return

            self.chosen_model = chosen_model
            
            sleap_processor = SleapProcessor(self.update_status_message)
            sleap_processor.paths_csv = csv_path
            sleap_processor.chosen_model = chosen_model
    
            directory = file_path.parent / 'tracked'        
            directory.mkdir(exist_ok=True)
            self.log_file_path = directory / 'sleap_commands.log'
            
            sleap_processor.log_file_path = self.log_file_path
            sleap_processor.start_logger()
            sleap_processor.logger.info(f'GUI Request: input={file_path}, models={animal_type}, csv={csv_path}')
    
            self.save_config()
    
            sleap_processor.config_path = self.config_path
            sleap_processor.read_config()
            
            self.thread = SleapThread(sleap_processor)
            self.thread.signal.connect(self.update_status_message)
            self.thread.finished.connect(lambda: self.submit_btn.setEnabled(True))
            self.submit_btn.setEnabled(False)
            self.thread.start()
    
        except Exception as e:
            tb = traceback.format_exc()
            message = f"An error occurred in GUI: {e}\n{tb}"
            self.update_status_message(message)    
            self.submit_btn.setEnabled(True)
                        
def manage_app():
    app = QApplication.instance()
    if app: app.quit()
    return QApplication(sys.argv)

if __name__ == '__main__':
    app = manage_app()  
    ex = InputBox()
    sys.exit(app.exec_())
