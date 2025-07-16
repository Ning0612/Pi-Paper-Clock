# main.py
import time
from wifi_manager import wifi_manager
from netutils import sync_time
from file_manager import list_files, shuffle_files
from display_manager import update_page_loading
from app_state import AppState
from hardware_manager import HardwareManager
from app_controller import AppController

def main():
    # 1. Initial Setup
    update_page_loading(False)
    
    # Initialize application state and hardware
    app_state = AppState()
    hardware = HardwareManager()

    # 2. Wi-Fi Connection
    wlan = wifi_manager() # This blocks until connected or configured
    if wlan and wlan.isconnected():
        sync_time()

    # 3. Prepare Image List
    image_directory = "/image/custom"
    app_state.image_name_list = list_files(image_directory)
    app_state.image_name_list = shuffle_files(app_state.image_name_list)

    # 4. Initialize Controller
    controller = AppController(app_state, hardware)

    # 5. Main Loop
    while True:
        controller.run_main_loop()
        time.sleep(1)

if __name__ == "__main__":
    main()
