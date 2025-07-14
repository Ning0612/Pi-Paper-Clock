# weather.py
import time
import urequests

def fetch_current_weather(api_key, location):
    url = "https://api.openweathermap.org/data/2.5/weather?q={},TW&appid={}&units=metric".format(location, api_key)
    try:
        response = urequests.get(url)
        if response.status_code == 200:
            data = response.json()
            temp = data["main"]["temp"]
            condition = data["weather"][0]["main"]
            return temp, condition
        else:
            return None
    except Exception as e:
        print("天氣 API 錯誤:", e)
        return None
    finally:
        try:
            response.close()
        except:
            pass

def fetch_weather_forecast(api_key, location):
    url = "https://api.openweathermap.org/data/2.5/forecast?q={0},TW&appid={1}&units=metric".format(location, api_key)
    try:
        response = urequests.get(url)
        if response.status_code != 200:
            print("查詢天氣失敗，錯誤代碼:", response.status_code)
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
    except Exception as e:
        print("天氣 API 錯誤:", e)
        return None
    finally:
        try:
            response.close()
        except:
            pass