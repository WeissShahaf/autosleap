import argparse
from PySide2.QtWidgets import QApplication
import sys
from classes import SleapProcessor
from gui18_possix import InputBox, manage_app
from pathlib import Path
from utils import ascii_logo

def main():
    """
    Main function to run the AutoSLEAP application.
    It can be started in either GUI or command-line mode.
    """
    # This check is crucial for multiprocessing to work correctly, especially on Windows.
    # It prevents child processes from re-importing and re-executing the main script's code.
    if len(sys.argv) > 1 and sys.argv[1].startswith('-c'):
        # This is a workaround for PyInstaller's multiprocessing issue on Windows
        # where it relaunches the executable. We do nothing and exit if it's a child process.
        return

    ascii_logo()
    parser = argparse.ArgumentParser(description='Run AutoSLEAP for automated video tracking.')
    parser.add_argument('--runtype', type=str, default='gui', choices=['cmd', 'gui'], 
                        help='Specify run type: "gui" to launch the graphical interface, "cmd" for command-line mode.')
    parser.add_argument('--input_path', type=str, default=None, 
                        help='(cmd mode) Path to the video file or folder of videos.')
    parser.add_argument('--model_type', type=str, default=None, 
                        help='(cmd mode) Specify a single model type from the CSV file.')
    parser.add_argument('--csv_path', type=str, default=None, 
                        help='(cmd mode) Path to the CSV file containing model paths.')
    args = parser.parse_args()

    if args.runtype == 'cmd':
        # --- Command Line Mode ---
        print("Running in command-line mode...")
        if not all([args.input_path, args.model_type, args.csv_path]):
            print("Error: For command-line mode, you must specify --input_path, --model_type, and --csv_path.")
            sys.exit(1)

        def cmd_callback(message):
            print(message)

        sleap_processor = SleapProcessor(update_status_callback=cmd_callback)
        
        # Manually set the properties that would be set by the GUI/config
        sleap_processor.file_path = Path(args.input_path)
        sleap_processor.animal_type = [args.model_type]
        sleap_processor.csv_path = Path(args.csv_path)
        # Use the CSV path as the "chosen model" for the logic in run_sleap
        sleap_processor.chosen_model = Path(args.csv_path)
        
        # Start logging for the command line run
        log_dir = Path(args.input_path).parent / 'tracked'
        log_dir.mkdir(exist_ok=True)
        sleap_processor.log_file_path = log_dir / 'sleap_commands_cmd.log'
        sleap_processor.start_logger()

        result = sleap_processor.run_sleap()
        print(result)

    elif args.runtype == 'gui':
        # --- GUI Mode ---
        try:
            app = manage_app()
            window = InputBox()
            sys.exit(app.exec_())
        except Exception as e:
            print(f"An error occurred while running the GUI: {e}")

if __name__ == "__main__":
    # The main entry point for the application.
    main()
