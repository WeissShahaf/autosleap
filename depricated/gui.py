from PySide2.QtWidgets import QApplication, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox, QFileDialog, QWidget, QDesktopWidget, QCheckBox
from PySide2.QtGui import QIcon, QPixmap, Qt
from itertools import chain, combinations
from pathlib import Path
import os
import sys




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
        logo_path = os.path.join(env_dir,"lib\site-packages\autsleap\gui", "logo.jpg")  # Get the path of 'logo.jpg' in the conda environment directory
        pixmap = QPixmap(logo_path)
        pixmap = pixmap.scaled(512, 512, Qt.KeepAspectRatio)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)  # Center the pixmap object in the bo
        layout.addWidget(label)

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
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","All Files (*);;Python Files (*.py)", options=options)
        if fileName:
            self.le.setText(fileName)
            print(self.le.setText)

    def getfolder(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            self.le.setText(folder)

    def switch_mode(self, state):
        if state == Qt.Checked:
            self.btn.clicked.disconnect()
            self.btn.clicked.connect(self.getfolder)
        else:
            self.btn.clicked.disconnect()
            self.btn.clicked.connect(self.getfile)

    def run_sleapGUI(self):
        file_path = Path(self.le.text())
        animal_type = self.cb.currentText().split(',')
        csv_path = self.model_path_CSV_le.text()
        self.close()
        QApplication.processEvents()  # Process any pending events
        QApplication.quit()  # Destroy the QApplication
      #  sleap_processor = SleapProcessor()
#        sleap_processor.run_sleap(file_path, animal_type, csv_path)

    def close_qt_applications():
      app = QApplication.instance()
      if app is not None:
        app.quit()
        
if __name__ == '__main__':
            app = QApplication([])
            ex = InputBox()
            ex.show()
            app.exec_()                
            sys.exit(app.exec_())