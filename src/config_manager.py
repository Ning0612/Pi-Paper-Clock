import ujson

CONFIG_FILE = 'config.json'

class ConfigManager:
    """Manages application configuration, loading from and saving to a JSON file."""
    def __init__(self):
        self.config = self._load_config()

    def _load_config(self):
        """Loads configuration from the CONFIG_FILE. Returns default config if file is not found or invalid."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                return ujson.load(f)
        except (OSError, ValueError):
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
                    "image_interval_min": 2,
                    "timezone_offset": 8
                },
                "chime": {
                    "enabled": True,
                    "interval": "hourly",
                    "pitch": 880,
                    "volume": 80
                }
            }

    def _save_config(self):
        """Saves the current configuration to the CONFIG_FILE."""
        with open(CONFIG_FILE, 'w') as f:
            ujson.dump(self.config, f)

    def get(self, key, default=None):
        """Retrieves a configuration value using a dot-separated key."""
        keys = key.split('.')
        val = self.config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key, value):
        """Sets a configuration value using a dot-separated key and saves the config."""
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
