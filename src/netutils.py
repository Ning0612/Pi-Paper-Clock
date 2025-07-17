# netutils.py
import network
import time
import ntptime
import os
import machine
import ujson
from config_manager import config_manager

def connect_wifi(ssid, password, timeout=10):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(ssid, password)
        t = timeout
        while not wlan.isconnected() and t:
            time.sleep(1)
            t -= 1
    if wlan.isconnected():
        print("Wi-Fi connected, IP:", wlan.ifconfig()[0])
    else:
        print("Wi-Fi connection failed")
    return wlan

def sync_time():
    if not network.WLAN(network.STA_IF).isconnected():
        print("Not connected to the internet, skipping time synchronization.")
        return
    try:
        ntptime.settime()
        print("Time synchronized successfully")
    except Exception as e:
        print(f"Time synchronization failed: {e}")

def get_local_time(offset=8*3600+5):
    t = time.localtime()
    seconds = time.mktime(t) + offset
    return time.localtime(seconds)

def load_wifi_config():
    ssid = config_manager.get("wifi.ssid")
    password = config_manager.get("wifi.password")
    location = config_manager.get("weather.location")
    return ssid, password, location

def save_wifi_config(ssid, password, location):
    config_manager.set("wifi.ssid", ssid)
    config_manager.set("wifi.password", password)
    config_manager.set("weather.location", location)
    print("Wi-Fi settings saved")

def wifi_manager_connect():
    """根據 config.json 嘗試連線 Wi‑Fi，若有設定則返回 WLAN 物件，否則返回 None"""
    ssid, password, _ = load_wifi_config()
    if ssid and password:
        wlan = connect_wifi(ssid, password)
        if wlan and wlan.isconnected():
            return wlan
    return None