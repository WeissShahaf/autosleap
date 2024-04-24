



def find_logo():
    import os
    import sys
    from pathlib import Path
    env_dir = os.path.dirname(sys.executable)  # Get the directory of the current Python interpreter       
    current_directory = os.getcwd()
   
    logo_path = os.path.join(env_dir,"lib\site-packages\sleap\gui", "autosleap_logo.jpg")  # Get the path of 'logo.jpg' in the conda environment directory
    if  Path.is_file(Path(logo_path)):
     return logo_path
      
    logo_path = os.path.join(current_directory, "autosleap_logo.jpg")  # Get the path of 'logo.jpg' in the conda environment directory
    if  Path.is_file(Path(logo_path)):
     return logo_path
  
    logo_path=[];
    return logo_path
  

        
    

def get_num_processes():
    
    """
    Define the number of processes based on RAM and VRAM.
    Returns:
        num_processes (int): The number of processes to use.
    """
    import psutil
    import GPUtil
    ram = psutil.virtual_memory()  # Get RAM
    total_ram = ram.available / (1024**3)  # Convert bytes to GB

    # Get GPU VRAM
    gpus = GPUtil.getGPUs()
    total_vram = round(gpus[0].memoryFree) / (1024)  # Convert bytes to GB
    # Assuming one GPU, adjust if multiple GPUs

    # Define the number of processes based on RAM and VRAM
    GPU_GB_limit = 10  # Limit the GPU memory to 12GB
    # cricket model takes ~7GB VRAN to run on batch size = 4

    CPU_GB_limit = 4  # Limit the GPU memory to 12GB

    num_processes = min(
        round(total_ram / CPU_GB_limit), round(total_vram / GPU_GB_limit)
    )
    # case something went wrong:
    if num_processes <= 0:
        num_processes = 1

    return num_processes


def reset_gpu_memory():
    """
    Reset GPU memory.
    """
    import tensorflow as tf
    tf.keras.backend.clear_session()
    
    
