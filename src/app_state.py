# app_state.py

class AppState:
    def __init__(self):
        self.last_minute = -1
        self.last_day = -1
        self.last_touch_time = -1
        self.image_offset = 0
        self.current_weather = None
        self.weather_forecast = None
        self.is_first_run = True
        self.partial_update = False
        self.image_name_list = []
        self.display_image_path = ""
        # 新增：日期特定事件圖片相關狀態
        self.event_image_list = []
        self.event_image_offset = 0
        self.current_event_date = ""
