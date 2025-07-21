# app_controller.py
import time
import machine
from config_manager import config_manager
from netutils import sync_time, get_local_time
from weather import fetch_current_weather, fetch_weather_forecast
from display_manager import update_page_weather, update_page_time_image, update_page_birthday, update_display_Restart
from file_manager import get_image_path, get_date_event_images, shuffle_files
from chime import Chime

class AppController:
    """Manages the application's main logic, including hardware interaction, display updates, and data fetching."""
    def __init__(self, state, hardware):
        """Initializes the AppController.

        Args:
            state: The application's state object.
            hardware: The hardware manager object.
        """
        self.state = state
        self.hw = hardware
        self.chime = Chime(20) if config_manager.get('chime.enabled') else None
        self.location = config_manager.get("weather.location", "Taipei")
        self.api_key = config_manager.get("weather.api_key")
        self.time_zone_offset = config_manager.get("user.timezone_offset", 8)

        self.button_press_timestamps = {}
        self.long_press_threshold_ms = 5000

    def handle_touch(self, touch_state):
        # Handle touch events and switch images
        if touch_state and touch_state[0] == "Touch" and touch_state[1][0] > 168:
            if self.state.event_image_list:
                self.state.event_image_offset = (self.state.event_image_offset + 1) % len(self.state.event_image_list)
                print(f"Event image changed, offset: {self.state.event_image_offset}")
            elif self.state.image_name_list:
                self.state.image_offset = (self.state.image_offset + 1) % len(self.state.image_name_list)
                print(f"Image changed, offset: {self.state.image_offset}")

    def handle_buttons(self, button_states):
        """Handles button states, checking for long presses to reset Wi-Fi and reboot."""
        current_time_ms = time.ticks_ms()

        for i, state in enumerate(button_states):
            if state == 1:
                if i not in self.button_press_timestamps:
                    self.button_press_timestamps[i] = current_time_ms
                else:
                    press_duration = time.ticks_diff(current_time_ms, self.button_press_timestamps[i])

                    if press_duration >= self.long_press_threshold_ms:
                        print(f"Button {i+1} long pressed for {press_duration} ms, resetting Wi-Fi and rebooting...")
                        self._reset_wifi_and_reboot()
                        return
            else:
                if i in self.button_press_timestamps:
                    del self.button_press_timestamps[i]

    def run_main_loop(self):
        """Executes the main application loop, handling sensor readings, time updates, and display logic."""
        adc_value = self.hw.get_adc_value()
        touch_state = self.hw.get_touch_state()
        t = get_local_time(offset=self.time_zone_offset*3600)

        if touch_state:
            self.state.last_touch_time = time.time()

        self.handle_buttons(self.hw.get_button_states())

        light_threshold = config_manager.get("user.light_threshold", 55000)
        time_since_touch = time.time() - self.state.last_touch_time if self.state.last_touch_time != -1 else 3601

        # If ambient light is below threshold (screen should be off) or time since last touch is less than 1 hour
        if adc_value <= light_threshold or time_since_touch < 3600:         
            # If date has changed
            if t[2] != self.state.last_day:
                self.state.last_day = t[2]
                self.state.weather_forecast = None
                self.state.current_weather = None
                sync_time()

            # If minute has changed, or touch occurred, or first run
            if t[4] != self.state.last_minute or touch_state is not None or self.state.is_first_run:
                self.handle_touch(touch_state)
                self._perform_chime(t)
                self._update_weather()
                self._update_display(t)

                self.state.is_first_run = False
                self.state.partial_update = not self.state.partial_update
                self.state.last_minute = t[4]
        else:
            # Reset flags when screen is off to ensure full update on wake-up
            self.state.is_first_run = True
            self.state.partial_update = False

    def _update_display(self, t):
        """Updates the display content based on current state and time.

        Args:
            t (tuple): Current time tuple.
        """
        image_directory = "/image/custom"
        self.state.display_image_path = get_image_path(image_directory, self.state.image_name_list, self.state.image_offset)

        # Check for date-specific events
        current_date = f"{t[1]:02d}{t[2]:02d}"
        if current_date != self.state.current_event_date:
            self.state.current_event_date = current_date
            self.state.event_image_list = get_date_event_images(current_date)
            if self.state.event_image_list:
                self.state.event_image_list = shuffle_files(self.state.event_image_list)
                self.state.event_image_offset = 0
                print(f"Date event found for {current_date}, loaded {len(self.state.event_image_list)} images.")

        # Page rendering logic
        if config_manager.get("user.birthday") == current_date:
            update_page_birthday(self.state.partial_update, t)
        elif self.state.current_weather and self.state.weather_forecast:
            update_page_weather(self.state.current_weather, self.state.weather_forecast, self.state.display_image_path, self.state.partial_update, t)
        else:
            update_page_time_image(self.state.display_image_path, self.state.partial_update, t)

    def _perform_chime(self, t):
        """Plays chime sound based on configured interval."""
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

    def _update_weather(self):
        """Fetches and updates current weather and forecast data if needed."""
        if time.ticks_diff(time.ticks_ms(), self.state.current_weather_last_updated) > 3 * 60 * 1000 or self.state.is_first_run or not self.state.current_weather:
            current_weather = fetch_current_weather(self.api_key, self.location)
            if current_weather:
                self.state.current_weather = current_weather
                self.state.current_weather_last_updated = time.ticks_ms()
        
        if time.ticks_diff(time.ticks_ms(), self.state.weather_forecast_last_updated) > 30 * 60 * 1000 or self.state.is_first_run or not self.state.weather_forecast:
            weather_forecast = fetch_weather_forecast(self.api_key, self.location, days_limit=4, timezone_offset=self.time_zone_offset)
            if weather_forecast:
                self.state.weather_forecast = weather_forecast
                self.state.weather_forecast_last_updated = time.ticks_ms()

        # Clear current weather data if older than 30 minutes
        if time.ticks_diff(time.ticks_ms(), self.state.current_weather_last_updated) > 30 * 60 * 1000:
            self.state.current_weather = None

        # Clear weather forecast data if older than 4 hours
        if time.ticks_diff(time.ticks_ms(), self.state.weather_forecast_last_updated) > 4 * 60 * 60 * 1000 :
            self.state.weather_forecast = None

    def _reset_wifi_and_reboot(self):
        """Resets Wi-Fi configuration and reboots the device."""
        config_manager.set("wifi.ssid", "")
        config_manager.set("wifi.password", "")
        update_display_Restart()
        print("Wi-Fi Configuration reset. Rebooting device...")
        time.sleep(3)
        machine.reset()