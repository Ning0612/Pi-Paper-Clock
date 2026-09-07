import gzip
import unittest
from pathlib import Path


class SettingsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.source = (root / "tools" / "html_src" / "settings.html").read_text(encoding="utf-8")
        cls.asset = gzip.decompress((root / "src" / "html" / "settings.bin").read_bytes()).decode("utf-8")

    def test_presence_timeout_fields_are_loaded_and_submitted(self):
        for content in (self.source, self.asset):
            self.assertIn('name="presence_leave_timeout_sec"', content)
            self.assertIn('name="presence_return_timeout_sec"', content)
            self.assertIn("離開書桌判定時間（秒）", content)
            self.assertIn("恢復在席判定時間（秒）", content)
            self.assertIn("setValue('presenceLeaveTimeout',u.presence_leave_timeout_sec)", content)
            self.assertIn("setValue('presenceReturnTimeout',u.presence_return_timeout_sec)", content)

    def test_weather_coordinates_replace_city_and_openweather_fields(self):
        for content in (self.source, self.asset):
            self.assertIn('name="weather_latitude"', content)
            self.assertIn('name="weather_longitude"', content)
            self.assertNotIn("OpenWeather API Key", content)
            self.assertNotIn("weather_location", content)

    def test_map_picker_is_lazy_and_keeps_manual_coordinate_fallback(self):
        for content in (self.source, self.asset):
            self.assertIn("unpkg.com/leaflet@1.9.4/dist/leaflet.js", content)
            self.assertIn("tile.openstreetmap.org/{z}/{x}/{y}.png", content)
            self.assertIn("keepBuffer:0", content)
            self.assertIn("locationMarker.on('dragend'", content)
            self.assertIn("locationMap.on('click'", content)
            self.assertIn("地圖無法載入", content)
            self.assertNotIn('<script src="https://unpkg.com/leaflet', content)

    def test_settings_load_does_not_scan_wifi_until_requested(self):
        for content in (self.source, self.asset):
            load_start = content.index("async function load(){")
            load_end = content.index("}catch(error){", load_start)
            load_function = content[load_start:load_end]
            self.assertNotIn("loadNetworks(", load_function)
            self.assertIn("currentSsid=p.wifi&&p.wifi.ssid||''", load_function)
            self.assertIn("option.value=currentSsid", load_function)
            self.assertIn("ssid.append(option)", load_function)
            self.assertIn(
                "document.getElementById('scanNetworks').onclick=function(){loadNetworks(",
                content,
            )


if __name__ == "__main__":
    unittest.main()
