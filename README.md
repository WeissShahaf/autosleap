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


   -install sleap: 
   
   mamba create -y -n autosleap -c conda-forge -c nvidia -c sleap -c anaconda sleap=1.3.3

   -Activate autosleap: mamba activate autosleap
   
   #install pip dependencies:    pip install GPUtil IPython

   -Download the repository in the folder you want to put the repo:
   
   git clone https://github.com/WeissShahaf/autosleap
   
   cd autosleap

   

 

   
   

# checking sleap works:
run sleap-diagnostic

# run:
make sure you have access to the model_paths.csv file that you will use to get the models' paths. if using spyder access GPFS from spyder before trying to run.

cd into the cloned repository's "sleapgui" folder (e.g. D:\GitHub\autosleap\sleapgui)

run: python autosleap.py



# Using the GUI:
![GUI](https://github.com/WeissShahaf/autosleap/assets/45653608/f7dcad2b-8f25-4044-83c4-8f573014f8e0)
![image](https://github.com/WeissShahaf/autosleap/assets/45653608/79a4a966-3c98-4a8e-88ae-c50d43ab11c0)

When you start the GUI,
It first looks for a config file in the environment folder: 'autosleap_config.json'
The config file stores parameters from the last run. And used to pre-fill input fields.

The first field to fill is the path to the data.
Here you have several options:
1)	First decide if you want to run on a specific video file or a whole folder. If the latter tick the box.
2)	You can manually enter the path (‘no “r” needed)
3)	Alternatively, browse for the video folder / file
4)	Enter any optional arguments for sleap-track

 the GUI would close itself and the program would run in your commandline

# Crashes / Trouble shooting:
 a log file is created in the tracked subfolder. it sohuld contain information about any crashes.
  If you get a subprocess return result=1 /2 / -1 it means the command failed to execute. check the command for path or argument order violations
 




   




