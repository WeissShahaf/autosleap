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



When you start the GUI,
It first looks for a config file in the environment folder: 'autosleap_config.json'
The config file stores parameters from the last run. And used to pre-fill input fields.

The first field to fill is the path to the data.
Here you have several options:
1)	First decide if you want to run on a specific video file or a whole folder. If the latter tick the box.
2)	You can manually enter the path (‘no “r” needed)
3)	Alternatively, browse for the video folder / file
4)	Enter any optional arguments for sleap-track

![vid](https://github.com/WeissShahaf/autosleap/assets/45653608/ab0da8f9-fbd8-4836-a828-b2644af91dbc)

The two methods are mutually exclusive and choosing one will deselect the other.
1)	From a csv file
2)	Manually enter model folder
   
![selection](https://github.com/WeissShahaf/autosleap/assets/45653608/2d17d145-34c6-49b5-ac60-fd32fb1b22a4)

1.	Get models path From a CSV file, and run any combination of models in the csv file:
 a.	Fill in path to csv file
 b.	Alternatively, browse for the csv file  
 c.	If using default settings, choose combination of models to infer from a dropdown menu
 d.	if model path was changed in a/b, update model combination and choose from menu

![csv](https://github.com/WeissShahaf/autosleap/assets/45653608/a76b5d87-3f0d-40b9-9795-c2a98447ed30)

2. Manually input a model’s path.
 a.	Enter a prefix for the model
 b.	Browse for model folder
 c.	Enter a prefix model
 d.	save the model prefix and path to the csv file

![manual](https://github.com/WeissShahaf/autosleap/assets/45653608/8011f738-9410-45eb-9746-324ee113fef3)

Now you can hit “Run” to run, refill the GUI using the config file by hitting “reset”, or exit by hitting “quit”. Note that any errors will appear in the bottom of the gui as a status text.

![run](https://github.com/WeissShahaf/autosleap/assets/45653608/cd20d4da-ac35-4464-bb5a-761919d428fd)

# Crashes / Trouble shooting:
A log file is created in the tracked subfolder. it sohuld contain information about any crashes.

 




   




