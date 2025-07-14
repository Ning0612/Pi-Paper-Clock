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
        print("Wi‑Fi 連線中…")
        wlan.connect(ssid, password)
        t = timeout
        while not wlan.isconnected() and t:
            time.sleep(1)
            t -= 1
    if wlan.isconnected():
        print("Wi‑Fi 連線成功，IP:", wlan.ifconfig()[0])
    else:
        print("Wi‑Fi 連線失敗")
    return wlan

def sync_time():
    try:
        ntptime.settime()
        print("時間同步成功")
    except Exception as e:
        print("時間同步失敗:", e)

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
    print("Wi‑Fi 設定已儲存")

def wifi_manager_connect():
    """根據 config.json 嘗試連線 Wi‑Fi，若有設定則返回 WLAN 物件，否則返回 None"""
    ssid, password, _ = load_wifi_config()
    if ssid and password:
        wlan = connect_wifi(ssid, password)
        if wlan and wlan.isconnected():
            return wlan
    return None