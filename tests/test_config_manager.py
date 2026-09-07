import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


class ConfigManagerMigrationTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.temp_dir = tempfile.TemporaryDirectory()
        os.chdir(self.temp_dir.name)
        self.original_ujson = sys.modules.get("ujson")
        sys.modules["ujson"] = json

        source = Path(__file__).resolve().parents[1] / "src" / "config_manager.py"
        spec = importlib.util.spec_from_file_location("config_manager_migration_target", source)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()
        if self.original_ujson is None:
            sys.modules.pop("ujson", None)
        else:
            sys.modules["ujson"] = self.original_ujson

    def _write_config(self, config):
        with open("config.json", "w") as config_file:
            json.dump(config, config_file)

    def test_v3_weather_fields_migrate_to_profile_coordinates(self):
        self._write_config({
            "schema_version": 3,
            "global": {
                "weather_api_key": "must not survive migration",
                "setup_complete": True,
            },
            "profiles": [
                {
                    "name": "宿舍",
                    "wifi": {"ssid": "dorm", "password": "secret"},
                    "weather_location": "Hsinchu",
                    "user": {},
                    "chime": {},
                },
                {
                    "name": "未知地點",
                    "wifi": {"ssid": "other", "password": "secret"},
                    "weather_location": "Somewhere",
                    "user": {},
                    "chime": {},
                },
            ],
            "active_profile": "宿舍",
            "last_connected_profile": "宿舍",
        })

        manager = self.module.ConfigManager()

        self.assertEqual(manager.config["schema_version"], 4)
        self.assertNotIn("weather_api_key", manager.config["global"])
        dorm = manager.get_profile("宿舍")
        self.assertEqual(dorm["weather_latitude"], 24.8138)
        self.assertEqual(dorm["weather_longitude"], 120.9675)
        self.assertNotIn("weather_location", dorm)
        fallback = manager.get_profile("未知地點")
        self.assertEqual(fallback["weather_latitude"], 25.033)
        self.assertEqual(fallback["weather_longitude"], 121.5654)
        self.assertEqual(fallback["legacy_weather_location"], "Somewhere")
        self.assertNotIn("weather_location", fallback)

        with open("config.json", "r") as config_file:
            saved = json.load(config_file)
        self.assertEqual(saved["schema_version"], 4)
        self.assertNotIn("weather_api_key", saved["global"])

    def test_weather_coordinates_reject_values_outside_earth(self):
        manager = self.module.ConfigManager()

        for profile_data, message in (
            ({"weather_latitude": 90.1, "weather_longitude": 121}, "latitude"),
            ({"weather_latitude": 25, "weather_longitude": -180.1}, "longitude"),
            ({"weather_latitude": "", "weather_longitude": 121}, "latitude"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    manager._validate_weather_coordinates(profile_data)

    def test_unknown_legacy_location_survives_profile_update_at_same_coordinates(self):
        self._write_config({
            "schema_version": 3,
            "profiles": [{
                "name": "Dorm",
                "wifi": {"ssid": "dorm", "password": "secret"},
                "weather_location": "Tokyo",
            }],
            "active_profile": "Dorm",
        })
        manager = self.module.ConfigManager()
        profile = json.loads(json.dumps(manager.get_profile("Dorm")))
        profile["user"]["image_interval_min"] = 5

        manager.apply_profile_update("Dorm", profile)

        self.assertEqual(manager.get_profile("Dorm")["legacy_weather_location"], "Tokyo")

    def test_save_failure_reloads_last_durable_config(self):
        manager = self.module.ConfigManager()
        manager._save_config()
        original_config = json.loads(json.dumps(manager.config))
        original_save = manager._save_config
        manager._save_config = lambda: (_ for _ in ()).throw(OSError("flash full"))
        try:
            with self.assertRaises(OSError):
                manager.set_global("example", "unsaved")
        finally:
            manager._save_config = original_save

        self.assertEqual(manager.config, original_config)

    def test_post_rename_sync_failure_restores_durable_file(self):
        manager = self.module.ConfigManager()
        manager._save_config()
        original_config = json.loads(json.dumps(manager.config))
        manager.config["global"]["temporary"] = "must not commit"

        original_sync = getattr(self.module.os, "sync", None)
        calls = []
        try:
            def sync_with_failure():
                calls.append(True)
                if len(calls) == 2:
                    raise OSError("sync failed")

            self.module.os.sync = sync_with_failure
            with self.assertRaises(OSError):
                manager._save_config_with_reload()
        finally:
            if original_sync is None:
                delattr(self.module.os, "sync")
            else:
                self.module.os.sync = original_sync

        with open("config.json", "r") as config_file:
            self.assertEqual(json.load(config_file), original_config)
        self.assertEqual(manager.config, original_config)

    def test_rejected_coordinate_does_not_pollute_live_profile(self):
        manager = self.module.ConfigManager()
        manager._save_config()
        original_profile = json.loads(json.dumps(manager.get_active_profile()))

        with self.assertRaisesRegex(ValueError, "latitude"):
            manager.set("weather.latitude", 91)

        self.assertEqual(manager.get_active_profile(), original_profile)

    def test_migration_preserves_valid_coordinate_when_the_other_is_missing(self):
        self._write_config({
            "schema_version": 3,
            "profiles": [{
                "name": "Partial",
                "wifi": {},
                "weather_latitude": 35.0,
                "weather_location": "Somewhere",
            }],
            "active_profile": "Partial",
        })

        manager = self.module.ConfigManager()
        profile = manager.get_profile("Partial")
        self.assertEqual(profile["weather_latitude"], 35.0)
        self.assertEqual(profile["weather_longitude"], 121.5654)
        self.assertEqual(profile["legacy_weather_location"], "Somewhere")


if __name__ == "__main__":
    unittest.main()
