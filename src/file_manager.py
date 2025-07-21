# file_manager.py
import os
import random
import time

def is_directory(path):
    """Checks if a given path is a directory."""
    try:
        return "stat" in dir(os) and os.stat(path)[0] & 0x4000
    except Exception:
        return False

def list_files(directory):
    """Lists files in a given directory, excluding subdirectories."""
    try:
        files = os.listdir(directory)
        return [f.split('.')[0] for f in files if not is_directory("{}/{}".format(directory, f))]
    except Exception as e:
        print(f"Error: Failed to list files in '{directory}'. Details: {e}")
        return []

def shuffle_files(file_list):
    """Shuffles a list of files randomly."""
    random.seed(time.time())
    n = len(file_list)
    for i in range(n - 1, 0, -1):
        j = random.randint(0, i)
        file_list[i], file_list[j] = file_list[j], file_list[i]
    return file_list

def get_image_path(directory, file_list, offset):
    """Gets the path to an image file based on current time and offset."""
    if not file_list:
        return None
    index = (int(time.time() // 120) + offset) % len(file_list)
    return "{}/{}.bin".format(directory, file_list[index])

def get_date_event_folder(date_mmdd):
    """Checks if an event folder exists for a given date."""
    event_folder = "/image/events/{}".format(date_mmdd)
    try:
        os.listdir(event_folder)
        return event_folder
    except Exception:
        return None

def get_date_event_images(date_mmdd):
    """Retrieves a list of event images for a specific date."""
    event_folder = get_date_event_folder(date_mmdd)
    if event_folder:
        return list_files(event_folder)
    return []