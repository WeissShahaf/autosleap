import psutil
import GPUtil
import tensorflow as tf

def get_num_processes():
    """
    Define the number of processes based on RAM and VRAM.
    Returns:
        num_processes (int): The number of processes to use.
    """
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
   
    tf.keras.backend.clear_session()
