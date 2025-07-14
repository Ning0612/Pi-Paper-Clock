# file_manager.py
import os
import random
import time

def is_directory(path):
    try:
        return "stat" in dir(os) and os.stat(path)[0] & 0x4000
    except Exception:
        return False

def list_files(directory):
    try:
        files = os.listdir(directory)
        # 回傳不含副檔名的檔名
        return [f.split('.')[0] for f in files if not is_directory("{}/{}".format(directory, f))]
    except Exception as e:
        print("列出檔案錯誤:", e)
        return []

def shuffle_files(file_list):
    random.seed(time.time())
    n = len(file_list)
    for i in range(n - 1, 0, -1):
        j = random.randint(0, i)
        file_list[i], file_list[j] = file_list[j], file_list[i]
    return file_list

def get_image_path(directory, file_list, offset):
    if not file_list:
        return None
    index = (int(time.time() // 120) + offset) % len(file_list)
    return "{}/{}.bin".format(directory, file_list[index])