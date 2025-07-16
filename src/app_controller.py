# app_controller.py
import time
import machine
from config_manager import config_manager
from netutils import sync_time, get_local_time
from weather import fetch_current_weather, fetch_weather_forecast
from display_manager import update_page_weather, update_page_time_image, update_page_birthday
from file_manager import get_image_path
from chime import Chime

class AppController:
    def __init__(self, state, hardware):
        self.state = state
        self.hw = hardware
        self.chime = Chime(20) if config_manager.get('chime.enabled') else None
        self.location = config_manager.get("weather.location", "Taipei")
        self.api_key = config_manager.get("weather.api_key")

    def handle_touch(self, touch_state):
        if touch_state and touch_state[0] == "Touch" and touch_state[1][0] > 168:
            if self.state.image_name_list:
                self.state.image_offset = (self.state.image_offset + 1) % len(self.state.image_name_list)
                print("Image changed, offset:", self.state.image_offset)

    def handle_buttons(self, button_states):
        if button_states == (0, 0, 0):
            config_manager.set("wifi.ssid", "")
            config_manager.set("wifi.password", "")
            print("Wi-Fi settings reset. Restarting...")
            time.sleep(3)
            machine.reset()

    def run_main_loop(self):
        adc_value = self.hw.get_adc_value()
        touch_state = self.hw.get_touch_state()
        t = get_local_time()

        if touch_state:
            self.state.last_touch_time = time.time()

        self.handle_buttons(self.hw.get_button_states())

        light_threshold = config_manager.get("user.light_threshold", 55000)
        time_since_touch = time.time() - self.state.last_touch_time if self.state.last_touch_time != -1 else 3601

        if adc_value <= light_threshold or time_since_touch < 3600:
            if t[4] != self.state.last_minute or touch_state is not None or self.state.is_first_run:
                self.handle_touch(touch_state)
                self._update_display(t)
                self._perform_chime(t)

                self.state.is_first_run = False
                self.state.partial_update = not self.state.partial_update
                self.state.last_minute = t[4]

            if t[2] != self.state.last_day:
                self.state.last_day = t[2]
                sync_time() # Resync time daily
        else:
            # Screen is off, reset flags for full update when it wakes up
            self.state.is_first_run = True
            self.state.partial_update = False

    def _update_display(self, t):
        image_directory = "/image/custom"
        self.state.display_image_path = get_image_path(image_directory, self.state.image_name_list, self.state.image_offset)

        # Fetch weather data periodically
        if t[4] % 3 == 0 or self.state.is_first_run:
            self.state.current_weather = fetch_current_weather(self.api_key, self.location)
        if t[4] % 30 == 0 or self.state.is_first_run:
            self.state.weather_forecast = fetch_weather_forecast(self.api_key, self.location)

        # Fallback if fetch failed
        if not self.state.current_weather:
            self.state.current_weather = fetch_current_weather(self.api_key, self.location)
        if not self.state.weather_forecast:
            self.state.weather_forecast = fetch_weather_forecast(self.api_key, self.location)

        # Page rendering logic
        if config_manager.get("user.birthday") == f"{t[1]:02d}{t[2]:02d}":
            update_page_birthday(self.state.partial_update)
        elif self.state.current_weather:
            update_page_weather(self.state.current_weather, self.state.weather_forecast, self.state.display_image_path, self.state.partial_update)
        else:
            update_page_time_image(self.state.display_image_path, self.state.partial_update)

    def _perform_chime(self, t):
        if self.chime and config_manager.get('chime.enabled'):
            is_hourly = config_manager.get('chime.interval') == 'hourly'
            is_half_hourly = config_manager.get('chime.interval') == 'half_hourly'

            if t[4] == 0 and (is_hourly or is_half_hourly):
                self.chime.do_chime(
                    pitch=config_manager.get('chime.pitch', 880),
                    volume=config_manager.get('chime.volume', 80)
                )
            if t[4] == 30 and is_half_hourly:
                self.chime.do_chime(
                    pitch=config_manager.get('chime.pitch', 880),
                    volume=config_manager.get('chime.volume', 80)
                )
