import ujson
import os

CONFIG_FILE = 'config.json'

class ConfigManager:
    def __init__(self):
        self.config = self._load_config()

    def _load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return ujson.load(f)
        except (OSError, ValueError):
            # If config file doesn't exist or is invalid, return a default structure
            return {
                "ap_mode": {
                    "ssid": "Pi_clock",
                    "password": "123456"
                },
                "wifi": {
                    "ssid": "",
                    "password": ""
                },
                "weather": {
                    "api_key": "",
                    "location": "Taipei"
                },
                "user": {
                    "birthday": "0612",
                    "light_threshold": 56000,
                    "image_interval_min": 2
                },
                "chime": {
                    "enabled": True,
                    "interval": "hourly",
                    "pitch": 880,
                    "volume": 80
                }
            }

    def _save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            ujson.dump(self.config, f)

    def get(self, key, default=None):
        keys = key.split('.')
        val = self.config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key, value):
        keys = key.split('.')
        val = self.config
        for i, k in enumerate(keys):
            if i == len(keys) - 1:
                val[k] = value
            else:
                if k not in val or not isinstance(val[k], dict):
                    val[k] = {}
                val = val[k]
        self._save_config()

config_manager = ConfigManager()
