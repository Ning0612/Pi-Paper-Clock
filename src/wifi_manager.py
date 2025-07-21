# wifi_manager.py
import network
import socket
import time
import machine
import gc
from display_manager import update_display_Restart, update_display_AP
from config_manager import config_manager
from chime import Chime

def unquote(s):
    """Decodes URL-encoded strings (MicroPython compatible)."""
    if not s:
        return s
    
    # Replace '+' with space
    s = s.replace('+', ' ')
    
    res = ""
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            try:
                hex_code = s[i+1:i+3]
                if len(hex_code) == 2:
                    char_code = int(hex_code, 16)
                    # Only process displayable ASCII characters
                    if 32 <= char_code <= 126:
                        res += chr(char_code)
                    else:
                        # Keep original characters if not displayable ASCII
                        res += s[i:i+3]
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
    """Parses a URL query string into a dictionary."""
    params = {}
    
    if not query_string:
        return params
    
    # Split pairs by '&'
    pairs = query_string.split('&')
    
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            params[key] = unquote(value)
        else:
            params[pair] = ''
    
    return params

def scan_networks():
    """Scans for available Wi-Fi networks."""
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
        "timezone_offset": config_manager.get("user.timezone_offset", 8),
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
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pico Clock 設定</title>
<style>
body{margin:0;padding:1rem;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f0f8ff;color:#333}
.container{max-width:600px;margin:auto;background:#fff;padding:1.5rem;border-radius:12px;box-shadow:0 4px 20px rgba(3,211,252,0.15)}
h1{text-align:center;color:#03d3fc;margin-bottom:1.5rem;font-size:2rem}
fieldset{border:2px solid #03d3fc;border-radius:8px;padding:1rem;margin-bottom:1rem;background:#f9fdff}
legend{font-weight:600;padding:0 .5rem;color:#03d3fc}
label{display:block;font-weight:500;margin-bottom:.5rem;color:#333}
input,select{width:100%;padding:0.75rem;box-sizing:border-box;border:1px solid #03d3fc;border-radius:6px;font-size:1rem;background:#fff}
input:focus,select:focus{border-color:#02b8d4;outline:none;box-shadow:0 0 0 2px rgba(3,211,252,0.2)}
input[type='checkbox']{width:auto;margin-right:.5rem;transform:scale(1.2);accent-color:#03d3fc}
.form-group{margin-bottom:1rem}
.info{font-size:.9rem;color:#666;margin-top:.25rem;padding:0.5rem;background:#e6f9ff;border-radius:4px}
.submit-btn{width:100%;padding:1rem;font-size:1.1rem;font-weight:bold;color:#fff;background:#03d3fc;border:none;border-radius:6px;cursor:pointer;transition:all .2s}
.submit-btn:hover{background:#02b8d4;transform:translateY(-1px)}
.test-btn{width:100%;padding:0.75rem;font-size:1rem;font-weight:bold;color:#fff;background:#ff9800;border:none;border-radius:6px;cursor:pointer;transition:all .2s;margin-top:0.5rem}
.test-btn:hover{background:#e68900}
.adc-value{font-weight:bold;color:#03d3fc}
</style>
</head>
<body>
<div class="container">
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
<div class="form-group"><label for="light_threshold">光感臨界值 (ADC):</label><input type="number" id="light_threshold" name="light_threshold" value=\"""" + str(vals['light_threshold']) + """\"><p class="info">目前光感值: <span class="adc-value" id="adc-value">""" + str(vals['adc_value']) + """</span> (建議取開燈時的值再稍微大一點)</p></div>
<div class="form-group"><label for="timezone_offset">時區偏移 (小時):</label><input type="number" id="timezone_offset" name="timezone_offset" value=\"""" + str(config_manager.get("user.timezone_offset", 8)) + """\"></div>
</fieldset>

<fieldset><legend>定時響聲</legend>
<div class="form-group" style="display:flex;align-items:center;"><input type="checkbox" id="chime_enabled" name="chime_enabled" value="true" """ + vals['chime_enabled'] + """><label for="chime_enabled" style="margin-bottom:0;">啟用定時響聲</label></div>
<div class="form-group"><label for="chime_interval">響聲間隔:</label><select id="chime_interval" name="chime_interval"><option value="hourly" """ + vals['chime_interval_hourly'] + """>每小時</option><option value="half_hourly" """ + vals['chime_interval_half'] + """>每半小時</option></select></div>
<div class="form-group"><label for="chime_pitch">音高 (Hz):</label><input type="number" id="chime_pitch" name="chime_pitch" value=\"""" + str(vals['chime_pitch']) + """\"></div>
<div class="form-group"><label for="chime_volume">音量 (0-100):</label><input type="number" id="chime_volume" name="chime_volume" value=\"""" + str(vals['chime_volume']) + """\"><button type="button" class="test-btn" onclick="testChime()">測試響聲</button></div>
</fieldset>

<fieldset><legend>AP 模式設定</legend>
<div class="form-group"><label for="ap_mode_ssid">AP 模式 SSID:</label><input id="ap_mode_ssid" name="ap_mode_ssid" value=\"""" + vals['ap_ssid'] + """\"></div>
<div class="form-group"><label for="ap_mode_password">AP 模式密碼:</label><input type="password" id="ap_mode_password" name="ap_mode_password" value=\"""" + vals['ap_password'] + """\"></div>
</fieldset>

<button type="submit" class="submit-btn">儲存設定並重啟</button>
</form>
</div>

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
</script>
</body>
</html>"""
    return html

def run_web_server():
    """Runs a simple web server to handle configuration requests."""
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    
    print(f"Web server listening on {addr}")
    
    start_time = time.time()
    timeout_duration = 600  # 10 minutes
    
    while True:
        try:
            # check if the total timeout has been reached
            if time.time() - start_time > timeout_duration:
                print("Info: AP mode timeout (10 minutes). Restarting system.")
                s.close()
                machine.reset()
            
            # set a short timeout for accepting connections
            s.settimeout(1.0)
            
            try:
                cl, addr = s.accept()
                print(f"Info: Client connected from {addr}")
            except OSError:
                continue
            
            # set a longer timeout for the client socket
            cl.settimeout(10.0)
            
            try:
                
                cl_file = cl.makefile("rwb", 0)
                request = ""
                
                # read the request line by line
                while True:
                    try:
                        line = cl_file.readline()
                        if not line or line == b"\r\n":
                            break
                        request += line.decode()
                    except OSError:
                        break
                
                print(f"Request received: {request[:100] + '...' if len(request) > 100 else request}")
                
                if "GET /favicon.ico" in request:
                    cl.send(b"HTTP/1.0 404 Not Found\r\n\r\n")
                    cl.close()
                    continue
                
                # handle ADC value request
                if "GET /adc" in request:
                    adc_value = machine.ADC(machine.Pin(26)).read_u16()
                    response = "HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n{\"adc\": " + str(adc_value) + "}"
                    cl.send(response.encode())
                    cl.close()
                    continue
                
                # handle chime request
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
                        print(f"Error: Failed to play chime. Details: {e}")
                        cl.send(b"HTTP/1.0 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nError playing chime")
                    cl.close()
                    continue
                
                # handle configuration form submission
                if "GET /?" in request and "ssid=" in request:
                    print("Info: Processing configuration form...")

                    try:
                        # Parse the query string from the request
                        if "?" in request:
                            query_start = request.find("?") + 1
                            query_end = request.find(" ", query_start)
                            if query_end == -1:
                                query_end = request.find("\r", query_start)
                            if query_end == -1:
                                query_end = len(request)

                            query_string = request[query_start:query_end]
                            print(f"Query string found: {query_string[:100] + '...' if len(query_string) > 100 else query_string}")

                            # parse query string into parameters
                            params = parse_query_string(query_string)
                            
                            config_manager.set("ap_mode.ssid", params.get("ap_mode_ssid", "Pi_clock"))
                            config_manager.set("ap_mode.password", params.get("ap_mode_password", "123456"))
                            config_manager.set("wifi.ssid", params.get("ssid", ""))
                            config_manager.set("wifi.password", params.get("password", ""))
                            config_manager.set("weather.api_key", params.get("api_key", ""))
                            config_manager.set("weather.location", params.get("location", "Taipei"))
                            config_manager.set("user.birthday", params.get("birthday", "0101"))

                            try:
                                config_manager.set("user.light_threshold", int(params.get("light_threshold", "56000")))
                            except (ValueError, TypeError):
                                config_manager.set("user.light_threshold", 56000)

                            try:
                                config_manager.set("user.image_interval_min", int(params.get("image_interval_min", "2")))
                            except (ValueError, TypeError):
                                config_manager.set("user.image_interval_min", 2)

                            try:
                                config_manager.set("user.timezone_offset", int(params.get("timezone_offset", "8")))
                            except (ValueError, TypeError):
                                config_manager.set("user.timezone_offset", 8)
                            
                            try:
                                config_manager.set("chime.pitch", int(params.get("chime_pitch", "880")))
                            except (ValueError, TypeError):
                                config_manager.set("chime.pitch", 880)

                            try:
                                config_manager.set("chime.volume", int(params.get("chime_volume", "80")))
                            except (ValueError, TypeError):
                                config_manager.set("chime.volume", 80)

                            print("Success: Configuration saved successfully!")

                            # Display success page with parameters
                            success_page = """HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>設定完成</title>
<style>
body{margin:0;padding:1rem;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f0f8ff;color:#333}
.container{max-width:600px;margin:auto;background:#fff;padding:1.5rem;border-radius:12px;box-shadow:0 4px 20px rgba(3,211,252,0.15)}
h1{text-align:center;color:#03d3fc;margin-bottom:1.5rem;font-size:2rem}
.success-msg{text-align:center;margin-bottom:1.5rem;color:#666;font-size:1.1rem}
.progress{width:100%;height:8px;background:#e0e0e0;border-radius:4px;margin:1.5rem 0;overflow:hidden}
.progress-bar{width:0%;height:100%;background:#03d3fc;border-radius:4px;animation:progress 5s ease-in-out forwards}
@keyframes progress{to{width:100%}}
fieldset{border:2px solid #03d3fc;border-radius:8px;padding:1rem;margin-bottom:1rem;background:#f9fdff}
legend{font-weight:600;padding:0 .5rem;color:#03d3fc}
.config-item{margin-bottom:0.8rem;display:flex;justify-content:space-between;align-items:center}
.config-item:last-child{margin-bottom:0}
.config-label{font-weight:500;color:#333}
.config-value{color:#03d3fc;font-weight:600}
.countdown{text-align:center;margin-top:1rem;color:#666;font-size:1.1rem}
</style>
</head>
<body>
<div class="container">
<h1>設定完成</h1>
<p class="success-msg">您的 Pico Clock 設定已成功儲存！系統將在 <span id="countdown">5</span> 秒後重新啟動。</p>
<div class="progress"><div class="progress-bar"></div></div>

<fieldset><legend>Wi-Fi 連線設定</legend>
<div class="config-item">
<span class="config-label">網路名稱:</span>
<span class="config-value">""" + config_manager.get("wifi.ssid") + """</span>
</div>
<div class="config-item">
<span class="config-label">密碼狀態:</span>
<span class="config-value">""" + ("已設定" if config_manager.get("wifi.password") else "未設定") + """</span>
</div>
</fieldset>

<fieldset><legend>天氣與個人化設定</legend>
<div class="config-item">
<span class="config-label">API Key:</span>
<span class="config-value">""" + ("已設定" if config_manager.get("weather.api_key") else "未設定") + """</span>
</div>
<div class="config-item">
<span class="config-label">天氣地點:</span>
<span class="config-value">""" + config_manager.get("weather.location") + """</span>
</div>
<div class="config-item">
<span class="config-label">生日設定:</span>
<span class="config-value">""" + config_manager.get("user.birthday") + """</span>
</div>
</fieldset>

<fieldset><legend>系統設定</legend>
<div class="config-item">
<span class="config-label">圖片輪播間隔:</span>
<span class="config-value">""" + str(config_manager.get("user.image_interval_min")) + """ 分鐘</span>
</div>
<div class="config-item">
<span class="config-label">光感臨界值:</span>
<span class="config-value">""" + str(config_manager.get("user.light_threshold")) + """</span>
</div>
<div class="config-item">
<span class="config-label">時區偏移:</span>
<span class="config-value">""" + str(config_manager.get("user.timezone_offset")) + """ 小時</span>
</div>
</fieldset>

<fieldset><legend>定時響聲設定</legend>
<div class="config-item">
<span class="config-label">響聲功能:</span>
<span class="config-value">""" + ("啟用" if config_manager.get("chime.enabled") else "停用") + """</span>
</div>
<div class="config-item">
<span class="config-label">響聲間隔:</span>
<span class="config-value">""" + ("每小時" if config_manager.get("chime.interval") == "hourly" else "每半小時") + """</span>
</div>
<div class="config-item">
<span class="config-label">音調頻率:</span>
<span class="config-value">""" + str(config_manager.get("chime.pitch")) + """ Hz</span>
</div>
<div class="config-item">
<span class="config-label">音量大小:</span>
<span class="config-value">""" + str(config_manager.get("chime.volume")) + """</span>
</div>
</fieldset>

<fieldset><legend>AP 模式設定</legend>
<div class="config-item">
<span class="config-label">AP 模式名稱:</span>
<span class="config-value">""" + config_manager.get("ap_mode.ssid") + """</span>
</div>
<div class="config-item">
<span class="config-label">AP 密碼狀態:</span>
<span class="config-value">""" + ("已設定" if config_manager.get("ap_mode.password") else "未設定") + """</span>
</div>
</fieldset>

<div class="countdown">系統正在重新啟動中...</div>
</div>

<script>
let timeLeft = 5;
const countdownElement = document.getElementById('countdown');
const timer = setInterval(() => {
timeLeft--;
countdownElement.textContent = timeLeft;
if (timeLeft <= 0) {
clearInterval(timer);
countdownElement.textContent = '重新啟動中...';
}
}, 1000);
</script>
</body>
</html>"""

                            try:
                                cl.send(success_page.encode())
                                cl.close()
                            except Exception as e:
                                print(f"Error: Failed to send response. Details: {e}")

                        else:
                            print("Warning: No query string found in the request.")

                    except Exception as e:
                        print(f"Error: An error occurred during configuration processing. Details: {str(e)}")
                        import sys
                        sys.print_exception(e)

                    # Restart the system after saving configuration and displaying restart message
                    try:
                        update_display_Restart()
                        print("Info: Restarting system in 5 seconds...")
                        time.sleep(5)
                        s.close()
                        machine.reset()
                    except Exception as e:
                        print(f"Error: An error occurred during system restart. Details: {e}")
                        machine.reset()
                
                else:
                    try:
                        networks = scan_networks()
                        page = generate_html_page(networks)
                        cl.send(page.encode())
                        cl.close()
                    except Exception as e:
                        print(f"Error: Failed to generate or send HTML page. Details: {e}")
                        try:
                            cl.close()
                        except:
                            pass
                    
            except Exception as e:
                print(f"Error: An error occurred while handling the client connection. Details: {e}")
                import sys
                sys.print_exception(e)
                try:
                    cl.close()
                except:
                    pass
                continue
                
        except Exception as e:
            print(f"Error: A server-level error occurred. Details: {e}")
            import sys
            sys.print_exception(e)
            continue
        finally:
            gc.collect()

def wifi_manager():
    """Main WiFi manager function that handles connection and configuration."""
    # Try to connect to saved WiFi
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    
    saved_ssid = config_manager.get("wifi.ssid", "")
    saved_password = config_manager.get("wifi.password", "")
    
    if saved_ssid and saved_password:
        print(f"Info: Attempting to connect to saved Wi-Fi network: {saved_ssid}")
        sta.connect(saved_ssid, saved_password)
        
        # Wait for connection (1 minutes timeout)
        timeout = 60
        while timeout > 0 and not sta.isconnected():
            time.sleep(1)
            timeout -= 1
            
        if sta.isconnected():
            print(f"Success: Connected to {saved_ssid}.")
            print(f"IP Address: {sta.ifconfig()[0]}")
            return sta
    
    # Connection failed, start AP mode for configuration
    print("Info: Wi-Fi connection failed or no configuration found. Starting AP mode.")
    
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    
    ap_ssid = config_manager.get("ap_mode.ssid", "Pi_clock")
    ap_password = config_manager.get("ap_mode.password", "123456")
    
    ap.config(ssid=ap_ssid, password=ap_password)
    ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
    
    update_display_AP(ap_ssid, ap_password, '192.168.4.1')
    
    print(f"Info: AP Mode enabled. SSID: {ap_ssid}, IP: 192.168.4.1")
    
    # Start the web server to handle configuration requests
    run_web_server()
    
    return None