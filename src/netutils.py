# netutils.py
import network
import time
import ntptime
from config_manager import config_manager

def connect_wifi(ssid, password, timeout=10):
    """Connects to a Wi-Fi network."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Attempting to connect to Wi-Fi network: {ssid}")
        wlan.connect(ssid, password)
        t = timeout
        while not wlan.isconnected() and t:
            time.sleep(1)
            t -= 1
    if wlan.isconnected():
        print(f"Wi-Fi connection successful. IP address: {wlan.ifconfig()[0]}")
    else:
        print("Error: Wi-Fi connection failed.")
    return wlan

def sync_time():
    """Synchronizes the system time using NTP."""
    if not network.WLAN(network.STA_IF).isconnected():
        print("Warning: No internet connection. Skipping time synchronization.")
        return
    try:
        ntptime.settime()
        print("Time synchronized successfully.")
    except Exception as e:
        print(f"Error: Time synchronization failed. Details: {e}")

def get_local_time(offset=8*3600):
    """Gets the current local time with a specified UTC offset."""
    t = time.localtime()
    seconds = time.mktime(t) + offset
    return time.localtime(seconds)
