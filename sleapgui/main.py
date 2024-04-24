import argparse
from PySide2.QtWidgets import QApplication
import sys
import os
from classes import SleapProcessor
from gui2 import InputBox
env_dir = os.path.dirname(sys.executable)  # Get the directory of the current Python interpreter       
sys.path.append(env_dir)


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