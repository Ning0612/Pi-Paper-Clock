# app_controller.py
import time
import machine
from config_manager import config_manager
from netutils import sync_time, get_local_time
from weather import fetch_current_weather, fetch_weather_forecast
from display_manager import update_page_weather, update_page_time_image, update_page_birthday, update_display_Restart
from file_manager import get_image_path
from chime import Chime

class AppController:
    def __init__(self, state, hardware):
        self.state = state
        self.hw = hardware
        # 初始化 chime 物件，根據設定決定是否啟用
        self.chime = Chime(20) if config_manager.get('chime.enabled') else None
        self.location = config_manager.get("weather.location", "Taipei") # 從設定檔獲取天氣地點
        self.api_key = config_manager.get("weather.api_key") # 從設定檔獲取天氣 API 金鑰

        # 新增：用於按鈕長按判斷的屬性
        # 儲存每個按鈕的按下時間戳記
        self.button_press_timestamps = {}
        # 長按閾值，單位毫秒 (3 秒)
        self.long_press_threshold_ms = 5000

    def handle_touch(self, touch_state):
        # 如果有觸控事件且觸控位置在特定區域
        if touch_state and touch_state[0] == "Touch" and touch_state[1][0] > 168:
            # 如果圖片列表不為空
            if self.state.image_name_list:
                # 切換到下一張圖片
                self.state.image_offset = (self.state.image_offset + 1) % len(self.state.image_name_list)
                print("Image changed, offset:", self.state.image_offset)

    def handle_buttons(self, button_states):
        """
        處理按鈕狀態。當任意一個按鈕被長按 (超過 self.long_press_threshold_ms) 時，
        重置 Wi-Fi 設定並重新啟動裝置。

        Args:
            button_states (tuple): 包含多個按鈕狀態的元組，例如 (btn1_state, btn2_state, btn3_state)。
                                   其中 1 表示按下，0 表示未按下。
        """
        current_time_ms = time.ticks_ms() # 獲取當前時間 (毫秒)

        # 遍歷所有按鈕的狀態
        for i, state in enumerate(button_states):
            if state == 1: # 如果按鈕被按下 (假設按下為 1)
                if i not in self.button_press_timestamps:
                    # 如果這是按鈕第一次被按下，記錄下按下的時間
                    self.button_press_timestamps[i] = current_time_ms
                    # print(f"按鈕 {i+1} 被按下，開始計時...") # 除錯用
                else:
                    # 如果按鈕已經被按下，檢查是否達到長按閾值
                    press_duration = time.ticks_diff(current_time_ms, self.button_press_timestamps[i])

                    if press_duration >= self.long_press_threshold_ms:
                        print(f"按鈕 {i+1} 已長按 {self.long_press_threshold_ms / 1000} 秒，觸發 Wi-Fi 重置！")
                        self._reset_wifi_and_reboot()
                        # 注意：一旦觸發重置並重啟，後面的程式碼就不會執行了
                        return # 提前返回，避免處理其他按鈕或重複觸發
            else: # 如果按鈕沒有被按下 (狀態為 0)
                if i in self.button_press_timestamps:
                    # 如果按鈕曾被按下但現在放開了，則清除其計時
                    del self.button_press_timestamps[i]
                    # print(f"按鈕 {i+1} 已放開，計時重置。") # 除錯用

    def run_main_loop(self):
        adc_value = self.hw.get_adc_value() # 獲取 ADC 值 (光線感測器)
        touch_state = self.hw.get_touch_state() # 獲取觸控狀態
        t = get_local_time() # 獲取當前本地時間

        if touch_state: # 如果有觸控事件發生
            self.state.last_touch_time = time.time() # 更新最後觸控時間

        # 處理按鈕狀態，這裡會調用上面修改後的 handle_buttons
        self.handle_buttons(self.hw.get_button_states())

        light_threshold = config_manager.get("user.light_threshold", 55000) # 從設定檔獲取亮度閾值
        # 計算距離上次觸控的時間，如果沒有觸控過則設為一個大於 3600 秒的值
        time_since_touch = time.time() - self.state.last_touch_time if self.state.last_touch_time != -1 else 3601

        # 如果環境亮度低於閾值 (屏幕應關閉) 或距離上次觸控時間小於 3600 秒 (1 小時)
        if adc_value <= light_threshold or time_since_touch < 3600:
            # 如果分鐘發生變化，或有觸控，或首次運行
            if t[4] != self.state.last_minute or touch_state is not None or self.state.is_first_run:
                self.handle_touch(touch_state) # 處理觸控事件
                self._perform_chime(t) # 執行定時響聲
                self._update_display(t) # 更新顯示內容

                self.state.is_first_run = False # 標記為非首次運行
                self.state.partial_update = not self.state.partial_update # 切換部分更新標誌
                self.state.last_minute = t[4] # 更新上一次記錄的分鐘數

            # 如果日期發生變化
            if t[2] != self.state.last_day:
                self.state.last_day = t[2] # 更新上一次記錄的日期
                sync_time() # 每天重新同步時間
        else:
            # 螢幕關閉時，重置標誌以便喚醒時進行完整更新
            self.state.is_first_run = True
            self.state.partial_update = False

    def _update_display(self, t):
        image_directory = "/image/custom"
        # 獲取要顯示的圖片路徑
        self.state.display_image_path = get_image_path(image_directory, self.state.image_name_list, self.state.image_offset)

        # 定期獲取天氣資料
        if t[4] % 3 == 0 or self.state.is_first_run: # 每 3 分鐘或首次運行時獲取當前天氣
            self.state.current_weather = fetch_current_weather(self.api_key, self.location)
        if t[4] % 30 == 0 or self.state.is_first_run: # 每 30 分鐘或首次運行時獲取天氣預報
            self.state.weather_forecast = fetch_weather_forecast(self.api_key, self.location)

        # 如果天氣資料獲取失敗，嘗試再次獲取 (fallback 機制)
        if not self.state.current_weather:
            self.state.current_weather = fetch_current_weather(self.api_key, self.location)
        if not self.state.weather_forecast:
            self.state.weather_forecast = fetch_weather_forecast(self.api_key, self.location)

        # 頁面渲染邏輯
        # 如果是生日，顯示生日頁面
        if config_manager.get("user.birthday") == f"{t[1]:02d}{t[2]:02d}":
            update_page_birthday(self.state.partial_update)
        # 如果有當前天氣資料，顯示天氣頁面
        elif self.state.current_weather:
            update_page_weather(self.state.current_weather, self.state.weather_forecast, self.state.display_image_path, self.state.partial_update)
        # 否則，顯示時間和圖片頁面
        else:
            update_page_time_image(self.state.display_image_path, self.state.partial_update)

    def _perform_chime(self, t):
        # 如果蜂鳴器已啟用
        if self.chime and config_manager.get('chime.enabled'):
            is_hourly = config_manager.get('chime.interval') == 'hourly' # 判斷是否設定為整點響聲
            is_half_hourly = config_manager.get('chime.interval') == 'half_hourly' # 判斷是否設定為半小時響聲

            # 整點響聲邏輯
            if t[4] == 0 and (is_hourly or is_half_hourly):
                self.chime.do_chime(
                    pitch=config_manager.get('chime.pitch', 880), # 從設定檔獲取音調，預設 880 Hz
                    volume=config_manager.get('chime.volume', 80) # 從設定檔獲取音量，預設 80
                )
            # 半小時響聲邏輯 (僅當設定為 half_hourly 時)
            if t[4] == 30 and is_half_hourly:
                self.chime.do_chime(
                    pitch=config_manager.get('chime.pitch', 880),
                    volume=config_manager.get('chime.volume', 80)
                )

    def _reset_wifi_and_reboot(self):
        """
        執行 Wi-Fi 設定重置和裝置重啟的私有方法。
        """
        config_manager.set("wifi.ssid", "") # 清空 Wi-Fi SSID 設定
        config_manager.set("wifi.password", "") # 清空 Wi-Fi 密碼設定
        update_display_Restart()
        print("Wi-Fi 設定已重置。裝置正在重新啟動...")
        time.sleep(3) # 給予足夠時間顯示訊息
        machine.reset() # 重啟裝置