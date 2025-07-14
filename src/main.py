# main.py
import time, ujson, machine
from machine import ADC, Pin
from netutils import wifi_manager_connect, sync_time, get_local_time
from weather import fetch_current_weather, fetch_weather_forecast
from display_manager import update_page_weather, update_page_time_image, update_page_birthday, update_page_loading
from file_manager import list_files, shuffle_files, get_image_path
from wifi_manager import wifi_manager
from epaper import ICNT86, ICNT_Development, get_touch_state, EPD_2in9
from config_manager import config_manager

# 顯示載入畫面
update_page_loading(False)

# 全域變數
last_minute      = -1
last_day         = -1
last_touch       = -1
image_offset     = 0
current_weather  = None
weather_forecast = None
first_on         = True
partial_update   = False

# 取得圖片清單，並進行隨機洗牌處理
image_directory = "/image/custom"
image_name_list = list_files(image_directory)
image_name_list = shuffle_files(image_name_list)

# 初始圖片路徑
display_image_path = get_image_path(image_directory, image_name_list, image_offset)

# 嘗試透過 wifi_manager 模組取得 Wi‑Fi 連線
wlan = wifi_manager()
if wlan and wlan.isconnected():
    sync_time()

# 讀取天氣位置（若無則預設為 Taipei）
location = config_manager.get("weather.location", "Taipei")
api_key = config_manager.get("weather.api_key")

# 初始化 epaper 觸控模組（保持原觸控座標轉換部分不變）
tp = ICNT86()
icnt_dev = ICNT_Development()
icnt_old = ICNT_Development()
tp.ICNT_Init()

# 按鈕與 ADC 設定
button_1 = Pin(2, Pin.IN, Pin.PULL_UP)
button_2 = Pin(3, Pin.IN, Pin.PULL_UP)
button_3 = Pin(15, Pin.IN, Pin.PULL_UP)
adc = ADC(Pin(26))

def get_buttons():
    return button_1.value(), button_2.value(), button_3.value()

# 主迴圈僅保留主要邏輯
while True:
    adc_value = adc.read_u16()
    state = get_touch_state(tp, icnt_dev, icnt_old)
    t = get_local_time()
    
    if state:
        last_touch = time.time()
        
    if get_buttons() == (0, 0, 0):
            config_manager.set("wifi.ssid", "")
            config_manager.set("wifi.password", "")
            print("Wi‑Fi 設定已重設，系統重新啟動")
            time.sleep(3)
            machine.reset()
    
    if adc_value <= config_manager.get("user.light_threshold", 55000) or time.time() - last_touch < 3600:
        if t[4] != last_minute or state is not None or first_on:
            # 觸控事件：若觸控位置 x 座標大於 168，切換圖片
            if state and state[0] == "Touch" and state[1][0] > 168:
                image_offset = (image_offset + 1) % len(image_name_list)
                print("切換圖片，image_offset:", image_offset)
                
            display_image_path = get_image_path(image_directory, image_name_list, image_offset)
            
            if t[4] % 3 == 0 or first_on:
                current_weather = fetch_current_weather(api_key, location)
            if t[4] % 30 == 0 or first_on:
                weather_forecast = fetch_weather_forecast(api_key, location)
            if not current_weather:
                current_weather = fetch_current_weather(api_key, location)
            if not weather_forecast:
                weather_forecast = fetch_weather_forecast(api_key, location)
            
            if config_manager.get("user.birthday") == f"{t[1]:02d}{t[2]:02d}":
                update_page_birthday(partial_update)
            elif current_weather:
                update_page_weather(current_weather, weather_forecast, display_image_path, partial_update)
            else:
                update_page_time_image(display_image_path, partial_update)
            
            first_on = False
            partial_update = not partial_update
            last_minute = t[4]
        
        if t[2] != last_day or first_on:
            last_day = t[2]
            if wlan and wlan.isconnected():
                sync_time()
    else:
        first_on = True
        partial_update = False
    
    time.sleep(1)