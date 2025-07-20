# weather.py
import time
import urequests
import network
import gc

def _make_request_with_retry(url, max_retries=3, delay=5):
    """發送 HTTP 請求，包含重試機制和錯誤處理"""
    for attempt in range(max_retries):
        try:
            # 增加超時設定避免連線掛起
            response = urequests.get(url, timeout=10)
            if response.status_code == 200:
                print(gc.mem_free(), "bytes free after request")
                return response
            else:
                print(f"API request failed (attempt {attempt + 1}/{max_retries}), status code: {response.status_code}")
                response.close()
        except OSError as e:
            if e.errno == 103:  # ECONNABORTED
                print(f"Connection aborted (attempt {attempt + 1}/{max_retries})")
            else:
                print(f"Network error (attempt {attempt + 1}/{max_retries}): {e}")
        except MemoryError:
            print(f"Memory allocation failed (attempt {attempt + 1}/{max_retries})")
            # 強制垃圾回收
            gc.collect()
        except Exception as e:
            print(f"API request exception (attempt {attempt + 1}/{max_retries}): {e}")
        
        # 等待後重試（除了最後一次嘗試）
        if attempt < max_retries - 1:
            time.sleep(delay)
    
    print(f"API request failed after {max_retries} attempts: {url}")
    return None

def fetch_current_weather(api_key, location):
    """獲取當前天氣資訊"""
    if not network.WLAN(network.STA_IF).isconnected():
        print("Not connected to the internet, skipping weather request.")
        return None
    print(f"Fetching current weather for {location}...")
    url = "https://api.openweathermap.org/data/2.5/weather?q={},TW&appid={}&units=metric".format(location, api_key)
    response = _make_request_with_retry(url)
    
    if response:
        try:
            data = response.json()
            temp = data["main"]["temp"]
            condition = data["weather"][0]["main"]
            # 立即清理記憶體
            del data
            gc.collect()

            return temp, condition
        except (ValueError, AttributeError) as e:
            print(f"Failed to parse current weather data (invalid JSON or attribute error): {e}")
            return None
        except MemoryError:
            print("Memory allocation failed during current weather processing")
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

def fetch_weather_forecast(api_key, location, days_limit=4, timezone_offset=8):
    if not network.WLAN(network.STA_IF).isconnected():
        print("Not connected to the internet, skipping weather forecast request.")
        return []

    print("Fetching weather forecast for {}...".format(location))
    url = "https://api.openweathermap.org/data/2.5/forecast?q={0},TW&appid={1}&units=metric&cnt=40".format(location, api_key)
    response = _make_request_with_retry(url)

    if not response:
        return []

    try:
        gc.collect()
        if response.status_code != 200:
            print("Weather forecast query failed, status code:", response.status_code)
            return []
        data = response.json()
        forecast_list = data.get("list", [])
        del data  # 立刻釋放主資料結構
        gc.collect()

        result = []
        processed_days = 0
        current_date = None
        temps_sum = 0
        temps_count = 0
        weather_counts = {}
        rain_sum = 0
        rain_count = 0

        for i in range(len(forecast_list)):
            if processed_days >= days_limit:
                break

            entry = forecast_list[i]
            dt = entry["dt"]
            local_time = time.localtime(dt + timezone_offset * 3600)
            month_day = "{:02d}-{:02d}".format(local_time[1], local_time[2])

            if current_date is None:
                current_date = month_day

            if month_day != current_date:
                # 儲存前一天
                if temps_count > 0:
                    avg_temp = temps_sum / temps_count
                    # 最常出現的天氣
                    most_common_weather = max(weather_counts, key=weather_counts.get)
                    avg_rain_prob = (rain_sum / rain_count) * 100 if rain_count > 0 else 0
                    result.append((current_date, avg_temp, most_common_weather, avg_rain_prob))
                    processed_days += 1

                # 重設
                current_date = month_day
                temps_sum = temps_count = rain_sum = rain_count = 0
                weather_counts = {}
                gc.collect()  # 只在換天時釋放

            # 累積數據
            temp = entry["main"]["temp"]
            weather = entry["weather"][0]["main"]
            rain_prob = entry.get("pop", 0)

            temps_sum += temp
            temps_count += 1
            weather_counts[weather] = weather_counts.get(weather, 0) + 1
            rain_sum += rain_prob
            rain_count += 1

            # 完全釋放已處理 entry
            forecast_list[i] = None

        # 最後一天
        if temps_count > 0 and processed_days <= days_limit:
            avg_temp = temps_sum / temps_count
            most_common_weather = max(weather_counts, key=weather_counts.get)
            avg_rain_prob = (rain_sum / rain_count) * 100 if rain_count > 0 else 0
            result.append((current_date, avg_temp, most_common_weather, avg_rain_prob))

        # 釋放主 list
        del forecast_list
        gc.collect()
        return result

    except (ValueError, AttributeError) as e:
        print("Failed to parse weather forecast data (invalid JSON or attribute error):", e)
        return []
    except MemoryError:
        print("Memory allocation failed during ultra minimal weather forecast processing")
        gc.collect()
        return []
    except Exception as e:
        print("An unexpected error occurred while fetching ultra minimal weather forecast:", e)
        return []
    finally:
        try:
            response.close()
        except Exception as e_close:
            print("Error closing response for ultra minimal weather forecast:", e_close)
