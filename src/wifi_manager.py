# wifi_manager.py
import network
import socket
import ujson
import time
import machine
import gc
from display_utils import display_rotated_screen, draw_scaled_text
from display_manager import update_display_Restart
from config_manager import config_manager
from chime import Chime

def update_display_AP():
    def draw(canvas):
        ap_ssid = config_manager.get("ap_mode.ssid", "Pi_clock")
        ap_password = config_manager.get("ap_mode.password", "123456")
        draw_scaled_text(canvas, f"SSID: {ap_ssid}", 3, 20, 2, 0)
        draw_scaled_text(canvas, f"Password: {ap_password}", 3, 50, 2, 0)
        draw_scaled_text(canvas, "IP: 192.168.4.1", 3, 80, 2, 0)
    display_rotated_screen(draw, angle=90, partial_update=False)

def unquote(s):
    """簡易的 URL decode 函式（MicroPython 用）"""
    if not s:
        return s
    
    # 先處理 + 為空格
    s = s.replace('+', ' ')
    
    res = ""
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            try:
                hex_code = s[i+1:i+3]
                if len(hex_code) == 2:
                    char_code = int(hex_code, 16)
                    if 32 <= char_code <= 126:  # 只處理可顯示的 ASCII 字符
                        res += chr(char_code)
                    else:
                        res += s[i:i+3]  # 保留原始字符
                else:
                    res += s[i]
                i += 3
            except (ValueError, TypeError):
                res += s[i]
                i += 1
        else:
            res += s[i]
            i += 1
    return res

def parse_query_string(query_string):
    """解析 query string，避免使用正規表達式造成遞迴問題"""
    params = {}
    
    if not query_string:
        return params
    
    # 使用字串分割方式代替正規表達式
    pairs = query_string.split('&')
    
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)  # 只分割第一個 = 號
            params[key] = unquote(value)
        else:
            params[pair] = ''
    
    return params

def scan_networks():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    nets = sta.scan()
    networks = []
    for ssid_bytes, _, _, _, _, _ in nets:
        try:
            ssid = ssid_bytes.decode('utf-8')
            if ssid:
                networks.append(ssid)
        except UnicodeError:
            pass
    return sorted(list(set(networks)))

def generate_html_page(networks):
    vals = {
        "wifi_ssid": config_manager.get("wifi.ssid", ""),
        "api_key": config_manager.get("weather.api_key", ""),
        "location": config_manager.get("weather.location", "Taipei"),
        "birthday": config_manager.get("user.birthday", "0101"),
        "image_interval_min": config_manager.get("user.image_interval_min", 2),
        "light_threshold": config_manager.get("user.light_threshold", 56000),
        "chime_enabled": "checked" if config_manager.get("chime.enabled", False) else "",
        "chime_interval_hourly": "selected" if config_manager.get("chime.interval") == "hourly" else "",
        "chime_interval_half": "selected" if config_manager.get("chime.interval") == "half_hourly" else "",
        "chime_pitch": config_manager.get("chime.pitch", 880),
        "chime_volume": config_manager.get("chime.volume", 80),
        "ap_ssid": config_manager.get("ap_mode.ssid", "Pi_clock"),
        "ap_password": config_manager.get("ap_mode.password", "123456"),
        "adc_value": machine.ADC(machine.Pin(26)).read_u16()
    }

    ssid_options = ""
    for ssid in networks:
        selected = "selected" if ssid == vals['wifi_ssid'] else ""
        ssid_options += f'<option value="{ssid}" {selected}>{ssid}</option>'

    html = """HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n
<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Pico Clock 設定</title>
<style>
body{margin:0;padding:1rem;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,Cantarell,'Open Sans','Helvetica Neue',sans-serif;background-color:#e0f7fa;color:#333;}
.container{max-width:600px;margin:auto;background-color:#fff;padding:1.5rem;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.1);}
h1{text-align:center;color:#00796b;margin-bottom:1.5rem;}
fieldset{border:1px solid #00bcd4;border-radius:6px;padding:1rem;margin-bottom:1rem;background-color:#e0f2f7;}
legend{font-weight:600;padding:0 .5rem;color:#00796b;}
label{display:block;font-weight:500;margin-bottom:.5rem;color:#004d40;}
input,select{width:100%;padding:0.75rem;box-sizing:border-box;border:1px solid #00bcd4;border-radius:6px;font-size:1rem;background-color:#f5f5f5;}
input[type='checkbox']{width:auto;margin-right:.5rem;}
.form-group{margin-bottom:1rem;}
.info{font-size:.9rem;color:#004d40;margin-top:.25rem;}
.submit-btn{width:100%;padding:1rem;font-size:1.1rem;font-weight:bold;color:#fff;background-color:#03dbfc;border:none;border-radius:6px;cursor:pointer;transition:background-color .2s;}
.submit-btn:hover{background-color:#02b8d4;}
.hidden{display:none;}
</style>
</head><body><div class="container">
<h1>Pico Clock 設定</h1>
<form action="/" method="get">

<fieldset><legend>Wi-Fi 連線</legend>
<div class="form-group"><label for="ssid">SSID:</label><select id="ssid" name="ssid">""" + ssid_options + """</select></div>
<div class="form-group"><label for="password">密碼:</label><input type="password" id="password" name="password"></div>
</fieldset>

<fieldset><legend>天氣與個人化</legend>
<div class="form-group"><label for="api_key">天氣 API Key:</label><input type="password" id="api_key" name="api_key" value=\"""" + vals['api_key'] + """\" readonly></div>
<div class="form-group"><label for="location">天氣地點:</label><input id="location" name="location" value=\"""" + vals['location'] + """\"></div>
<div class="form-group"><label for="birthday">生日 (MMDD):</label><input id="birthday" name="birthday" value=\"""" + vals['birthday'] + """\"></div>
</fieldset>

<fieldset><legend>系統設定</legend>
<div class="form-group"><label for="image_interval_min">圖片輪播間隔 (分鐘):</label><input type="number" id="image_interval_min" name="image_interval_min" value=\"""" + str(vals['image_interval_min']) + """\"></div>
<div class="form-group"><label for="light_threshold">光感臨界值 (ADC):</label><input type="number" id="light_threshold" name="light_threshold" value=\"""" + str(vals['light_threshold']) + """\"><p class="info">目前光感值: <span id="adc-value">""" + str(vals['adc_value']) + """</span> (建議取開燈時的值再稍微大一點)</p></div>
</fieldset>

<fieldset><legend>定時響聲</legend>
<div class="form-group" style="display:flex;align-items:center;"><input type="checkbox" id="chime_enabled" name="chime_enabled" value="true" """ + vals['chime_enabled'] + """><label for="chime_enabled" style="margin-bottom:0;">啟用定時響聲</label></div>
<div class="form-group"><label for="chime_interval">響聲間隔:</label><select id="chime_interval" name="chime_interval"><option value="hourly" """ + vals['chime_interval_hourly'] + """>每小時</option><option value="half_hourly" """ + vals['chime_interval_half'] + """>每半小時</option></select></div>
<div class="form-group"><label for="chime_pitch">音高 (Hz):</label><input type="number" id="chime_pitch" name="chime_pitch" value=\"""" + str(vals['chime_pitch']) + """\"></div>
<div class="form-group"><label for="chime_volume">音量 (0-100):</label><input type="number" id="chime_volume" name="chime_volume" value=\"""" + str(vals['chime_volume']) + """\"><button type="button" onclick="testChime()" style="width:100%;padding:0.75rem;font-size:1rem;font-weight:bold;color:#fff;background-color:#00bcd4;border:none;border-radius:6px;cursor:pointer;transition:background-color .2s;margin-top:0.5rem;">測試響聲</button></div>
</fieldset>

<fieldset><legend>AP 模式設定</legend>
<div class="form-group"><label for="ap_mode_ssid">AP 模式 SSID:</label><input id="ap_mode_ssid" name="ap_mode_ssid" value=\"""" + vals['ap_ssid'] + """\"></div>
<div class="form-group"><label for="ap_mode_password">AP 模式密碼:</label><input type="password" id="ap_mode_password" name="ap_mode_password" value=\"""" + vals['ap_password'] + """\"></div>
</fieldset>

<button type="submit" class="submit-btn">儲存設定並重啟</button>
</form></div>

<script>
let clickCount = 0;
let lastClickTime = 0;
const apiKeyInput = document.getElementById('api_key');

function updateAdc(){fetch('/adc').then(r=>r.json()).then(d=>{document.getElementById('adc-value').innerText=d.adc;}).catch(e=>console.error(e));}
function testChime(){const p=document.getElementById('chime_pitch').value;const v=document.getElementById('chime_volume').value;fetch('/test_chime?pitch='+p+'&volume='+v).catch(e=>console.error(e));}

apiKeyInput.addEventListener('click', () => { 
    const currentTime = Date.now();
    if (currentTime - lastClickTime < 3000) { 
        clickCount++;
        if (clickCount >= 7) { 
            apiKeyInput.readOnly = false;
            apiKeyInput.type = 'text';
            apiKeyInput.style.backgroundColor = '#fff';
            clickCount = 0; 
        }
    } else { 
        clickCount = 1;
    }
    lastClickTime = currentTime;
});

document.addEventListener('DOMContentLoaded',()=>{ 
setInterval(updateAdc,3000);
document.getElementById('chime_pitch').addEventListener('change',testChime);
document.getElementById('chime_volume').addEventListener('change',testChime);
});
</script></body></html>"""
    return html

def run_web_server():
    """
    運行 Web 服務器處理配置請求，包含 10 分鐘超時機制
    """
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    
    print("Web server listening on", addr)
    
    start_time = time.time()
    timeout_duration = 600  # 10 minutes
    
    while True:
        try:
            # 檢查是否超過 10 分鐘
            if time.time() - start_time > timeout_duration:
                print("AP mode timeout (10 minutes), restarting...")
                s.close()
                machine.reset()
            
            # 設定 socket 接受連線的超時為 1 秒，避免無限期等待
            s.settimeout(1.0)
            
            try:
                cl, addr = s.accept()
                print("Client connected from", addr)
            except OSError:
                # 超時，繼續迴圈檢查總體超時
                continue
            
            # 重設超時給客戶端連線處理
            cl.settimeout(10.0)
            
            try:
                # 使用 makefile 穩定處理請求
                cl_file = cl.makefile("rwb", 0)
                request = ""
                
                # 讀取完整的 HTTP 請求
                while True:
                    try:
                        line = cl_file.readline()
                        if not line or line == b"\r\n":
                            break
                        request += line.decode()
                    except OSError:
                        break
                
                print("Request:", request[:100] + "..." if len(request) > 100 else request)
                
                # 忽略 favicon 請求
                if "GET /favicon.ico" in request:
                    cl.send(b"HTTP/1.0 404 Not Found\r\n\r\n")
                    cl.close()
                    continue
                
                # 處理 ADC 請求
                if "GET /adc" in request:
                    adc_value = machine.ADC(machine.Pin(26)).read_u16()
                    response = "HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n{\"adc\": " + str(adc_value) + "}"
                    cl.send(response.encode())
                    cl.close()
                    continue
                
                # 處理測試響聲請求
                if "GET /test_chime" in request:
                    query_start = request.find("?") + 1
                    query_end = request.find(" ", query_start)
                    query_string = request[query_start:query_end]
                    params = parse_query_string(query_string)
                    
                    pitch = int(params.get("pitch", "880"))
                    volume = int(params.get("volume", "80"))
                    
                    try:
                        chime_obj = Chime()
                        chime_obj.do_chime(pitch=pitch, volume=volume)
                        chime_obj.deinit()
                        cl.send(b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nChime test successful")
                    except Exception as e:
                        print("Error playing chime:", e)
                        cl.send(b"HTTP/1.0 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nError playing chime")
                    cl.close()
                    continue
                
                # 處理配置表單提交
                # 處理配置表單提交
                if "GET /?" in request and "ssid=" in request:
                    print("Processing configuration form...")

                    try:
                        # 提取 query string
                        if "?" in request:
                            query_start = request.find("?") + 1
                            query_end = request.find(" ", query_start)
                            if query_end == -1:
                                query_end = request.find("\r", query_start)
                            if query_end == -1:
                                query_end = len(request)

                            query_string = request[query_start:query_end]
                            print("Query string:", query_string[:100] + "..." if len(query_string) > 100 else query_string)

                            # 使用新的解析函數
                            params = parse_query_string(query_string)
                            print("Parsed parameters:", len(params), "items")

                            # 安全地取得參數值
                            new_ssid = params.get("ssid", "")
                            new_password = params.get("password", "")
                            new_location = params.get("location", "Taipei")
                            new_api_key = params.get("api_key", "")
                            new_birthday = params.get("birthday", "0101")

                            print("SSID:", new_ssid)
                            print("Password length:", len(new_password))
                            print("Location:", new_location)

                            # 構建配置
                            config_data = {
                                "ap_mode": {
                                    "ssid": params.get("ap_mode_ssid", "Pi_clock"),
                                    "password": params.get("ap_mode_password", "123456")
                                },
                                "wifi": {
                                    "ssid": new_ssid,
                                    "password": new_password
                                },
                                "weather": {
                                    "api_key": new_api_key,
                                    "location": new_location
                                },
                                "user": {
                                    "birthday": new_birthday,
                                    "light_threshold": 56000,
                                    "image_interval_min": 2
                                },
                                "chime": {
                                    "enabled": "chime_enabled" in params,
                                    "interval": params.get("chime_interval", "hourly"),
                                    "pitch": 880,
                                    "volume": 80
                                }
                            }

                            # 處理數值參數，加入異常處理
                            try:
                                config_data["user"]["light_threshold"] = int(params.get("light_threshold", "56000"))
                            except (ValueError, TypeError):
                                config_data["user"]["light_threshold"] = 56000

                            try:
                                config_data["user"]["image_interval_min"] = int(params.get("image_interval_min", "2"))
                            except (ValueError, TypeError):
                                config_data["user"]["image_interval_min"] = 2

                            try:
                                config_data["chime"]["pitch"] = int(params.get("chime_pitch", "880"))
                            except (ValueError, TypeError):
                                config_data["chime"]["pitch"] = 880

                            try:
                                config_data["chime"]["volume"] = int(params.get("chime_volume", "80"))
                            except (ValueError, TypeError):
                                config_data["chime"]["volume"] = 80

                            # 保存配置
                            print("Saving configuration...")
                            with open("config.json", "w") as f:
                                ujson.dump(config_data, f)
                            print("Configuration saved successfully!")

                            # Prepare data for success page, masking sensitive info
                            display_config = {
                                "wifi_ssid": config_data["wifi"]["ssid"],
                                "location": config_data["weather"]["location"],
                                "birthday": config_data["user"]["birthday"],
                                "light_threshold": config_data["user"]["light_threshold"],
                                "image_interval_min": config_data["user"]["image_interval_min"],
                                "chime_enabled": "是" if config_data["chime"]["enabled"] else "否",
                                "chime_interval": "每小時" if config_data["chime"]["interval"] == "hourly" else "每半小時",
                                "chime_pitch": config_data["chime"]["pitch"],
                                "chime_volume": config_data["chime"]["volume"],
                                "ap_mode_ssid": config_data["ap_mode"]["ssid"]
                            }

                            success_page_template = """HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n
<html>
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>設定進行中</title>
  <style>
    body {{ font-family: Arial, sans-serif; padding: 20px; margin: 0; background-color: #f4f4f4; text-align: center; }}
    .container {{ background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: inline-block; margin-top: 50px; max-width: 400px; }}
    h1 {{ color: #00796b; margin-bottom: 20px; }}
    p {{ color: #666; font-size: 16px; line-height: 1.5; }}
    .progress {{ width: 100%; height: 4px; background-color: #e0e0e0; border-radius: 2px; margin: 20px 0; overflow: hidden; }}
    .progress-bar {{ width: 100%; height: 100%; background-color: #00796b; border-radius: 2px; animation: progress 5s ease-in-out forwards; }}
    @keyframes progress {{ to {{ width: 100%; }} }}
    .config-details {{ text-align: left; margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px; }}
    .config-details p {{ margin: 5px 0; }}
    .config-details strong {{ color: #004d40; }}
  </style>
</head>
<body>
  <div class=\"container\">
    <h1>Pico Clock 設定完成</h1>
    <p>設定已成功儲存，系統將在 5 秒後重新啟動。</p>
    <div class=\"progress\"><div class=\"progress-bar\"></div></div>
    <div class=\"config-details\">
      <h2>已儲存的設定:</h2>
      <p><strong>Wi-Fi SSID:</strong> {wifi_ssid}</p>
      <p><strong>天氣地點:</strong> {location}</p>
      <p><strong>生日:</strong> {birthday}</p>
      <p><strong>光感臨界值:</strong> {light_threshold}</p>
      <p><strong>圖片輪播間隔:</strong> {image_interval_min} 分鐘</p>
      <p><strong>定時響聲啟用:</strong> {chime_enabled}</p>
      <p><strong>響聲間隔:</strong> {chime_interval}</p>
      <p><strong>音高:</strong> {chime_pitch} Hz</p>
      <p><strong>音量:</strong> {chime_volume}</p>
      <p><strong>AP 模式 SSID:</strong> {ap_mode_ssid}</p>
    </div>
    <p>請稍候...</p>
  </div>
</body>
</html>
"""
                            success_page = success_page_template.format(**display_config)

                            try:
                                cl.send(success_page.encode())
                                cl.close()
                            except Exception as e:
                                print("Error sending response:", e)

                        else:
                            print("No query string found in request")

                    except Exception as e:
                        print("Error in configuration processing:", str(e))
                        import sys
                        sys.print_exception(e)

                    # 顯示重啟訊息並重啟
                    try:
                        update_display_Restart()
                        print("Restarting in 5 seconds...")
                        time.sleep(5)
                        s.close()
                        machine.reset()
                    except Exception as e:
                        print("Error during restart:", e)
                        machine.reset()
                
                # 顯示主配置頁面
                else:
                    try:
                        networks = scan_networks()
                        page = generate_html_page(networks)
                        cl.send(page.encode())
                        cl.close()
                    except Exception as e:
                        print("Error generating page:", e)
                        try:
                            cl.close()
                        except:
                            pass
                    
            except Exception as e:
                print("Error handling client:", e)
                import sys
                sys.print_exception(e)
                try:
                    cl.close()
                except:
                    pass
                continue
                
        except Exception as e:
            print("Server error:", e)
            import sys
            sys.print_exception(e)
            continue
        finally:
            gc.collect()

def wifi_manager():
    """
    Main WiFi manager function that handles connection and configuration
    Returns WLAN object if successful, None otherwise
    """
    
    # Try to connect to saved WiFi
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    
    saved_ssid = config_manager.get("wifi.ssid", "")
    saved_password = config_manager.get("wifi.password", "")
    
    if saved_ssid and saved_password:
        print("Connecting to", saved_ssid, "...")
        sta.connect(saved_ssid, saved_password)
        
        # Wait for connection (10 minutes timeout)
        timeout = 600
        while timeout > 0 and not sta.isconnected():
            time.sleep(1)
            timeout -= 1
            
        if sta.isconnected():
            print("Connected to", saved_ssid)
            print("IP:", sta.ifconfig()[0])
            return sta
    
    # Connection failed, start AP mode for configuration
    print("Starting AP mode for configuration...")
    
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    
    ap_ssid = config_manager.get("ap_mode.ssid", "Pi_clock")
    ap_password = config_manager.get("ap_mode.password", "123456")
    
    ap.config(ssid=ap_ssid, password=ap_password)
    ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
    
    update_display_AP()
    
    print("AP Mode: SSID=" + ap_ssid + ", IP=192.168.4.1")
    
    # 啟動 Web 服務器，包含 10 分鐘超時機制
    run_web_server()
    
    return None