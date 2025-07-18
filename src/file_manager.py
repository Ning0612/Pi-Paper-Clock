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
        print(f"Error listing files: {e}")
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

def get_date_event_folder(date_mmdd):
    """
    檢查是否存在指定日期的事件資料夾
    
    Args:
        date_mmdd (str): 日期格式 MMDD，例如 "0612"
    
    Returns:
        str: 事件資料夾路徑，如果存在的話；否則返回 None
    """
    event_folder = "/image/events/{}".format(date_mmdd)
    try:
        # 嘗試列出資料夾內容來檢查是否存在
        os.listdir(event_folder)
        return event_folder
    except Exception:
        return None

def get_date_event_images(date_mmdd):
    """
    獲取指定日期的事件圖片列表
    
    Args:
        date_mmdd (str): 日期格式 MMDD，例如 "0612"
    
    Returns:
        list: 圖片檔案名稱列表（不含副檔名），如果沒有則返回空列表
    """
    event_folder = get_date_event_folder(date_mmdd)
    if event_folder:
        return list_files(event_folder)
    return []