# This is a work in progress!
# Automated sleap inference script / GUI

![half_logo](https://github.com/StempelLab/sleap_well/assets/101252955/c206e1bb-242e-4b02-a9a8-89c4b4c3b87d)


 The core script does the following:
 gets user input:
 input_path: a video file or folder containing video files
 csv_path: path to a csv file containing model paths
 model_type: a list of model types (must exit in csv_path file

 the script runs sleap sleap-track,sleap-convert,sleap-render commands on all files for all model types.
script includes autmated GPU and RAM managment and can run multiple video files in parallel.

# Installling
 Download the repository: 
in the folder you want to put the repo:
git clone https://github.com/StempelLab/sleap_well && cd sleap_well
install: (replace mamba for conda if the case)
mamba env create -f environment.yml -n autosleap
activate autosleap

# checking sleap works:
run sleap-diagnostic

# run:
make sure you have access to the model_paths.csv file that you will use to get the models' paths
run: python "sleap_Well\scripts\gui.py" (where sleap_Well is thae path to where you cloned the repository into



# Using the GUI:
![image](https://github.com/StempelLab/sleap_well/assets/101252955/abc5f1bb-f9c4-4824-896a-841b02f3bb0e)

1) Enter input folder or file,  by typing (no "PATH" or r'PATH' needed) or browsing
    if folder is chosen the program would run on all .avi or .mp4 files in the folder
   
3) Choose animal type to track from dropdown menu - single model or combination of models
4) Check path to CSV containing model paths is correct.
5) Hit "Submit"
6) the GUI would close itself and the program would run in your commandline

# Crashes / Trouble shooting:
 If you get a subprocess return result=1 /2 / -1 it means the command failed to execute. check the command for path or argument order violations
 




   




