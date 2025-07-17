# weather.py
import time
import urequests
import network

def _make_request_with_retry(url, max_retries=3, delay=5):
    for attempt in range(max_retries):
        try:
            response = urequests.get(url)
            if response.status_code == 200:
                return response
            else:
                print(f"API request failed (attempt {attempt + 1}/{max_retries}), status code: {response.status_code}")
                response.close() # Close response if status code is not 200
        except Exception as e:
            print(f"API request exception (attempt {attempt + 1}/{max_retries}): {e}")
        time.sleep(delay)
    print(f"API request failed after {max_retries} attempts: {url}")
    return None

def fetch_current_weather(api_key, location):
    if not network.WLAN(network.STA_IF).isconnected():
        print("Not connected to the internet, skipping weather request.")
        return None
    url = "https://api.openweathermap.org/data/2.5/weather?q={},TW&appid={}&units=metric".format(location, api_key)
    response = _make_request_with_retry(url)
    if response:
        try:
            data = response.json()
            temp = data["main"]["temp"]
            condition = data["weather"][0]["main"]
            return temp, condition
        except (ValueError, AttributeError) as e:
            print(f"Failed to parse current weather data (invalid JSON or attribute error): {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while fetching current weather: {e}")
            return None
        finally:
            try:
                response.close()
            except Exception as e_close:
                print(f"Error closing response for current weather: {e_close}")
    return None
    return None

def fetch_weather_forecast(api_key, location):
    if not network.WLAN(network.STA_IF).isconnected():
        print("Not connected to the internet, skipping weather forecast request.")
        return []
    url = "https://api.openweathermap.org/data/2.5/forecast?q={0},TW&appid={1}&units=metric".format(location, api_key)
    response = _make_request_with_retry(url)
    if response:
        try:
            if response.status_code != 200:
                print(f"Weather forecast query failed, status code: {response.status_code}")
                return []
            data = response.json()
            forecast_list = data["list"]
            forecasts_by_date = {}
            for entry in forecast_list:
                dt = entry["dt"]
                local_time = time.localtime(dt + 8 * 3600)
                month_day = "{:02d}-{:02d}".format(local_time[1], local_time[2])
                temp = entry["main"]["temp"]
                weather = entry["weather"][0]["main"]
                rain_prob = entry.get("pop", 0)
                if month_day not in forecasts_by_date:
                    forecasts_by_date[month_day] = {"temps": [], "weathers": {}, "rain_probs": []}
                forecasts_by_date[month_day]["temps"].append(temp)
                forecasts_by_date[month_day]["rain_probs"].append(rain_prob)
                forecasts_by_date[month_day]["weathers"][weather] = forecasts_by_date[month_day]["weathers"].get(weather, 0) + 1
            result = []
            for date, info in forecasts_by_date.items():
                avg_temp = sum(info["temps"]) / len(info["temps"])
                most_common_weather = max(info["weathers"], key=info["weathers"].get)
                avg_rain_prob = sum(info["rain_probs"]) / len(info["rain_probs"]) * 100
                result.append((date, avg_temp, most_common_weather, avg_rain_prob))
            result.sort(key=lambda x: (int(x[0].split('-')[0]), int(x[0].split('-')[1])))
            return result
        except (ValueError, AttributeError) as e:
            print(f"Failed to parse weather forecast data (invalid JSON or attribute error): {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred while fetching weather forecast: {e}")
            return []
        finally:
            try:
                response.close()
            except Exception as e_close:
                print(f"Error closing response for weather forecast: {e_close}")
    return []