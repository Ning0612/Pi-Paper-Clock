# wifi_manager.py
import network
import socket
import time
import machine
import gc
import ujson
from display_manager import update_display_Restart, update_display_AP
from config_manager import config_manager
from chime import Chime
from hardware_manager import HardwareManager

def reset_wifi_and_reboot():
    """Sets force AP mode flag and reboots to enter configuration mode."""
    print("Long press detected. Entering AP mode for configuration...")

    # Set force AP mode flag
    config_manager.set_global("force_ap_mode", True)

    # Display restart message
    update_display_Restart()
    print("Entering AP mode. System will restart...")
    time.sleep(2)
    machine.reset()

def factory_reset():
    """Performs a complete factory reset - deletes all profiles and restores defaults."""
    print("FACTORY RESET: Deleting all configurations and restoring defaults...")

    # Delete config file completely
    try:
        import os
        os.remove('config.json')
        print("Config file deleted.")
    except:
        pass

    # Reinitialize config manager with defaults
    config_manager.config = config_manager._get_default_config()
    config_manager._save_config()

    print("Factory reset complete. Default configuration restored.")
    return True


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
    """Scans for available Wi-Fi networks and returns with signal strength."""
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    nets = sta.scan()
    networks = []
    for ssid_bytes, bssid, channel, rssi, authmode, hidden in nets:
        try:
            ssid = ssid_bytes.decode('utf-8')
            if ssid:
                networks.append({
                    'ssid': ssid,
                    'rssi': rssi  # Signal strength (higher is better, usually negative values)
                })
        except UnicodeError:
            pass

    # Remove duplicates and keep the one with strongest signal
    unique_networks = {}
    for net in networks:
        ssid = net['ssid']
        if ssid not in unique_networks or net['rssi'] > unique_networks[ssid]['rssi']:
            unique_networks[ssid] = net

    return list(unique_networks.values())

def generate_html_page(networks, current_profile=None):
    """Generates the configuration HTML page with multi-profile support."""

    # Get all profiles
    profiles = []
    for profile_name in config_manager.list_profiles():
        profile = config_manager.get_profile(profile_name)
        if profile:
            profiles.append(profile)

    # Current active profile
    if not current_profile:
        current_profile = config_manager.get_active_profile()

    # Global settings
    global_vals = {
        "api_key": config_manager.get_global("weather_api_key", ""),
        "ap_ssid": config_manager.get("ap_mode.ssid", "Pi_Clock_AP"),
        "ap_password": config_manager.get("ap_mode.password", "12345678"),
        "adc_value": machine.ADC(machine.Pin(26)).read_u16()
    }

    # Current profile settings (for editing)
    profile_vals = {
        "profile_name": current_profile.get("name", "") if current_profile else "",
        "wifi_ssid": current_profile.get("wifi", {}).get("ssid", "") if current_profile else "",
        "location": current_profile.get("weather_location", "Taipei") if current_profile else "Taipei",
        "birthday": current_profile.get("user", {}).get("birthday", "0101") if current_profile else "0101",
        "image_interval_min": current_profile.get("user", {}).get("image_interval_min", 2) if current_profile else 2,
        "light_threshold": current_profile.get("user", {}).get("light_threshold", 56000) if current_profile else 56000,
        "timezone_offset": current_profile.get("user", {}).get("timezone_offset", 8) if current_profile else 8,
        "chime_enabled": "checked" if (current_profile and current_profile.get("chime", {}).get("enabled", False)) else "",
        "chime_interval_hourly": "selected" if (current_profile and current_profile.get("chime", {}).get("interval") == "hourly") else "",
        "chime_interval_half": "selected" if (current_profile and current_profile.get("chime", {}).get("interval") == "half_hourly") else "",
        "chime_pitch": current_profile.get("chime", {}).get("pitch", 880) if current_profile else 880,
        "chime_volume": current_profile.get("chime", {}).get("volume", 80) if current_profile else 80,
    }

    # Generate SSID options
    ssid_options = ""
    for net in networks:
        ssid = net['ssid'] if isinstance(net, dict) else net
        selected = "selected" if ssid == profile_vals['wifi_ssid'] else ""
        ssid_options += f'<option value="{ssid}" {selected}>{ssid}</option>'

    # Generate profile list for sidebar
    profile_list_html = ""
    active_profile_name = config_manager.get_active_profile_name()
    for profile in profiles:
        active_badge = " 🔵" if profile["name"] == active_profile_name else ""
        profile_list_html += f'<div class="profile-item" onclick="loadProfile(\'{profile["name"]}\')">{profile["name"]}{active_badge}</div>'

    html = """HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n
<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pi Clock 多設定檔管理</title>
<style>
body{margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f0f8ff;color:#333;display:flex;min-height:100vh}
.sidebar{width:250px;background:#fff;border-right:2px solid #03d3fc;padding:1rem;overflow-y:auto}
.sidebar h2{color:#03d3fc;font-size:1.3rem;margin:0 0 1rem 0}
.profile-item{padding:0.75rem;margin:0.5rem 0;background:#f9fdff;border:1px solid #03d3fc;border-radius:6px;cursor:pointer;transition:all .2s}
.profile-item:hover{background:#e6f9ff;transform:translateX(3px)}
.add-profile-btn{width:100%;padding:0.75rem;background:#03d3fc;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:bold;margin-top:1rem}
.add-profile-btn:hover{background:#02b8d4}
.main-content{flex:1;padding:1.5rem;overflow-y:auto}
.container{max-width:700px;margin:auto;background:#fff;padding:1.5rem;border-radius:12px;box-shadow:0 4px 20px rgba(3,211,252,0.15)}
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
.delete-btn{width:100%;padding:0.75rem;font-size:1rem;font-weight:bold;color:#fff;background:#ff4444;border:none;border-radius:6px;cursor:pointer;transition:all .2s;margin-top:0.5rem}
.delete-btn:hover{background:#cc0000}
.test-btn{width:100%;padding:0.75rem;font-size:1rem;font-weight:bold;color:#fff;background:#ff9800;border:none;border-radius:6px;cursor:pointer;transition:all .2s;margin-top:0.5rem}
.test-btn:hover{background:#e68900}
.adc-value{font-weight:bold;color:#03d3fc}
.button-group{display:flex;gap:0.5rem;margin-top:1rem}
.button-group button{flex:1}
@media (max-width: 768px){
body{flex-direction:column}
.sidebar{width:100%;border-right:none;border-bottom:2px solid #03d3fc}
}
</style>
</head>
<body>
<div class="sidebar">
<h2>設定檔列表</h2>
<div id="profile-list">""" + profile_list_html + """</div>
<button class="add-profile-btn" onclick="createNewProfile()">➕ 新增設定檔</button>
</div>

<div class="main-content">
<div class="container">
<h1>設定檔編輯</h1>
<form id="profile-form" action="/save_profile" method="get">

<input type="hidden" id="original_profile_name" name="original_profile_name" value=\"""" + profile_vals['profile_name'] + """\">

<fieldset><legend>設定檔資訊</legend>
<div class="form-group"><label for="profile_name">設定檔名稱:</label><input id="profile_name" name="profile_name" value=\"""" + profile_vals['profile_name'] + """\" required></div>
</fieldset>

<fieldset><legend>Wi-Fi 連線</legend>
<div class="form-group"><label for="ssid">SSID:</label><select id="ssid" name="ssid">""" + ssid_options + """</select></div>
<div class="form-group"><label for="password">密碼:</label><input type="password" id="password" name="password"></div>
</fieldset>

<fieldset><legend>天氣與個人化</legend>
<div class="form-group"><label for="location">天氣地點:</label><input id="location" name="location" value=\"""" + profile_vals['location'] + """\"></div>
<div class="form-group"><label for="birthday">生日 (MMDD):</label><input id="birthday" name="birthday" value=\"""" + profile_vals['birthday'] + """\"></div>
</fieldset>

<fieldset><legend>系統設定</legend>
<div class="form-group"><label for="image_interval_min">圖片輪播間隔 (分鐘):</label><input type="number" id="image_interval_min" name="image_interval_min" value=\"""" + str(profile_vals['image_interval_min']) + """\"></div>
<div class="form-group"><label for="light_threshold">光感臨界值 (ADC):</label><input type="number" id="light_threshold" name="light_threshold" value=\"""" + str(profile_vals['light_threshold']) + """\"><p class="info">目前光感值: <span class="adc-value" id="adc-value">""" + str(global_vals['adc_value']) + """</span></p></div>
<div class="form-group"><label for="timezone_offset">時區偏移 (小時):</label><input type="number" id="timezone_offset" name="timezone_offset" value=\"""" + str(profile_vals['timezone_offset']) + """\"></div>
</fieldset>

<fieldset><legend>定時響聲</legend>
<div class="form-group" style="display:flex;align-items:center;"><input type="checkbox" id="chime_enabled" name="chime_enabled" value="true" """ + profile_vals['chime_enabled'] + """><label for="chime_enabled" style="margin-bottom:0;">啟用定時響聲</label></div>
<div class="form-group"><label for="chime_interval">響聲間隔:</label><select id="chime_interval" name="chime_interval"><option value="hourly" """ + profile_vals['chime_interval_hourly'] + """>每小時</option><option value="half_hourly" """ + profile_vals['chime_interval_half'] + """>每半小時</option></select></div>
<div class="form-group"><label for="chime_pitch">音高 (Hz):</label><input type="number" id="chime_pitch" name="chime_pitch" value=\"""" + str(profile_vals['chime_pitch']) + """\"></div>
<div class="form-group"><label for="chime_volume">音量 (0-100):</label><input type="number" id="chime_volume" name="chime_volume" value=\"""" + str(profile_vals['chime_volume']) + """\"><button type="button" class="test-btn" onclick="testChime()">測試響聲</button></div>
</fieldset>

<fieldset><legend>全局設定 (所有設定檔共用)</legend>
<div class="form-group"><label for="api_key">天氣 API Key:</label><input type="password" id="api_key" name="api_key" value=\"""" + global_vals['api_key'] + """\" readonly></div>
<div class="form-group"><label for="ap_mode_ssid">AP 模式 SSID:</label><input id="ap_mode_ssid" name="ap_mode_ssid" value=\"""" + global_vals['ap_ssid'] + """\"></div>
<div class="form-group"><label for="ap_mode_password">AP 模式密碼:</label><input type="password" id="ap_mode_password" name="ap_mode_password" value=\"""" + global_vals['ap_password'] + """\"></div>
</fieldset>

<div class="button-group">
<button type="submit" class="submit-btn">💾 儲存並重啟</button>
<button type="button" class="delete-btn" onclick="deleteProfile()">🗑️ 刪除設定檔</button>
</div>

<fieldset style="margin-top:2rem;border-color:#ff4444;background:#fff5f5;"><legend style="color:#ff4444;">⚠️ 危險區域</legend>
<p style="font-size:0.9rem;color:#666;margin-bottom:1rem;">完全重置會刪除所有設定檔並恢復出廠設定，此操作無法復原！</p>
<button type="button" class="delete-btn" onclick="factoryReset()" style="background:#ff0000;">🔥 完全重置系統</button>
</fieldset>

</form>
</div>
</div>

<script>
let clickCount = 0;
let lastClickTime = 0;
const apiKeyInput = document.getElementById('api_key');

function updateAdc(){fetch('/adc').then(r=>r.json()).then(d=>{document.getElementById('adc-value').innerText=d.adc;}).catch(e=>console.error(e));}
function testChime(){const p=document.getElementById('chime_pitch').value;const v=document.getElementById('chime_volume').value;fetch('/test_chime?pitch='+p+'&volume='+v).catch(e=>console.error(e));}

function loadProfile(profileName){
    window.location.href = '/edit_profile?name=' + encodeURIComponent(profileName);
}

function createNewProfile(){
    const newName = prompt('請輸入新設定檔名稱:');
    if(newName && newName.trim()){
        window.location.href = '/new_profile?name=' + encodeURIComponent(newName.trim());
    }
}

function deleteProfile(){
    const profileName = document.getElementById('profile_name').value;
    if(confirm('確定要刪除設定檔「' + profileName + '」嗎？此操作無法復原！')){
        window.location.href = '/delete_profile?name=' + encodeURIComponent(profileName);
    }
}

function factoryReset(){
    const confirmText = prompt('⚠️ 警告：完全重置將刪除所有設定檔並恢復出廠設定！\\n\\n此操作無法復原！\\n\\n請輸入「RESET」確認執行：');
    if(confirmText === 'RESET'){
        if(confirm('最後確認：您確定要執行完全重置嗎？')){
            window.location.href = '/factory_reset';
        }
    } else if(confirmText !== null) {
        alert('輸入錯誤，重置已取消。');
    }
}

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
    """Runs a simple web server to handle configuration requests with multi-profile support."""
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)

    print(f"Web server listening on {addr}")

    # Initialize hardware manager for unified button handling
    hardware = HardwareManager()

    def reset_callback(button_index):
        """Callback function for button long press reset."""
        print(f"Button {button_index+1} long pressed in AP mode. Resetting WiFi and AP settings...")
        s.close()
        reset_wifi_and_reboot()

    start_time = time.time()
    last_activity_time = time.time()
    timeout_duration = 600  # 10 minutes base timeout
    activity_extension = 300  # 5 minutes extension per activity

    while True:
        try:
            # Check for button long press
            if hardware.handle_button_long_press(reset_callback):
                return

            # Check timeout
            current_time = time.time()
            time_since_start = current_time - start_time
            time_since_activity = current_time - last_activity_time

            effective_timeout = timeout_duration
            if time_since_activity < activity_extension:
                effective_timeout = timeout_duration + activity_extension

            if time_since_start > effective_timeout:
                print(f"Info: AP mode timeout ({effective_timeout/60:.1f} minutes). Using last connected profile and restarting.")
                s.close()
                # Set active profile to last connected if available
                last_profile = config_manager.get_last_connected_profile_name()
                if last_profile:
                    try:
                        config_manager.set_active_profile(last_profile)
                        print(f"Info: Switched to last connected profile: {last_profile}")
                    except:
                        pass
                machine.reset()

            s.settimeout(1.0)

            try:
                cl, addr = s.accept()
                last_activity_time = time.time()
                print(f"Info: Client connected from {addr}.")
            except OSError:
                continue

            cl.settimeout(10.0)

            try:
                cl_file = cl.makefile("rwb", 0)
                request = ""

                while True:
                    try:
                        line = cl_file.readline()
                        if not line or line == b"\r\n":
                            break
                        request += line.decode()
                    except OSError:
                        break

                print(f"Request: {request[:100] + '...' if len(request) > 100 else request}")

                # Handle favicon
                if "GET /favicon.ico" in request:
                    cl.send(b"HTTP/1.0 404 Not Found\r\n\r\n")
                    cl.close()
                    continue

                # Handle ADC value request
                if "GET /adc" in request:
                    adc_value = machine.ADC(machine.Pin(26)).read_u16()
                    response = "HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n{\"adc\": " + str(adc_value) + "}"
                    cl.send(response.encode())
                    cl.close()
                    continue

                # Handle chime test
                if "GET /test_chime" in request:
                    last_activity_time = time.time()
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
                        cl.send(b"HTTP/1.0 200 OK\r\n\r\nOK")
                    except Exception as e:
                        print(f"Error: Chime test failed. {e}")
                        cl.send(b"HTTP/1.0 500 Internal Server Error\r\n\r\nError")
                    cl.close()
                    continue

                # Handle edit profile request
                if "GET /edit_profile?" in request:
                    query_start = request.find("?") + 1
                    query_end = request.find(" ", query_start)
                    query_string = request[query_start:query_end]
                    params = parse_query_string(query_string)
                    profile_name = params.get("name", "")

                    profile = config_manager.get_profile(profile_name)
                    if profile:
                        networks = scan_networks()
                        page = generate_html_page(networks, profile)
                        cl.send(page.encode())
                    else:
                        cl.send(b"HTTP/1.0 404 Not Found\r\n\r\nProfile not found")
                    cl.close()
                    continue

                # Handle new profile request
                if "GET /new_profile?" in request:
                    query_start = request.find("?") + 1
                    query_end = request.find(" ", query_start)
                    query_string = request[query_start:query_end]
                    params = parse_query_string(query_string)
                    new_name = params.get("name", "")

                    if new_name:
                        # Create new profile based on last connected or active profile
                        base_profile = config_manager.get_active_profile()
                        new_profile = {
                            "name": new_name,
                            "wifi": {"ssid": "", "password": ""},
                            "weather_location": base_profile.get("weather_location", "Taipei") if base_profile else "Taipei",
                            "user": base_profile.get("user", {
                                "birthday": "0101",
                                "light_threshold": 56000,
                                "image_interval_min": 2,
                                "timezone_offset": 8
                            }) if base_profile else {
                                "birthday": "0101",
                                "light_threshold": 56000,
                                "image_interval_min": 2,
                                "timezone_offset": 8
                            },
                            "chime": base_profile.get("chime", {
                                "enabled": True,
                                "interval": "hourly",
                                "pitch": 880,
                                "volume": 80
                            }) if base_profile else {
                                "enabled": True,
                                "interval": "hourly",
                                "pitch": 880,
                                "volume": 80
                            }
                        }

                        try:
                            config_manager.add_profile(new_profile)
                            # Redirect to edit this new profile
                            redirect = "HTTP/1.0 302 Found\r\nLocation: /edit_profile?name=" + new_name + "\r\n\r\n"
                            cl.send(redirect.encode())
                        except ValueError as e:
                            cl.send(b"HTTP/1.0 400 Bad Request\r\n\r\nProfile name already exists")
                    else:
                        cl.send(b"HTTP/1.0 400 Bad Request\r\n\r\nInvalid profile name")
                    cl.close()
                    continue

                # Handle delete profile request
                if "GET /delete_profile?" in request:
                    query_start = request.find("?") + 1
                    query_end = request.find(" ", query_start)
                    query_string = request[query_start:query_end]
                    params = parse_query_string(query_string)
                    profile_name = params.get("name", "")

                    try:
                        config_manager.delete_profile(profile_name)
                        # Redirect to home
                        redirect = "HTTP/1.0 302 Found\r\nLocation: /\r\n\r\n"
                        cl.send(redirect.encode())
                    except ValueError as e:
                        cl.send(("HTTP/1.0 400 Bad Request\r\n\r\n" + str(e)).encode())
                    cl.close()
                    continue

                # Handle factory reset request
                if "GET /factory_reset" in request:
                    last_activity_time = time.time()
                    print("WARNING: Factory reset requested!")

                    try:
                        # Perform factory reset
                        factory_reset()

                        # Send success page
                        reset_page = """HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n
<html><head><meta charset="utf-8"><title>完全重置</title>
<style>body{font-family:sans-serif;text-align:center;padding:2rem;background:#fff0f0}
h1{color:#ff0000}p{font-size:1.2rem;color:#666}</style></head>
<body><h1>🔥 完全重置完成</h1><p>所有設定檔已刪除，系統已恢復出廠設定。</p>
<p>系統將在 5 秒後重新啟動...</p>
<script>setTimeout(()=>{window.location.href='/'},5000)</script></body></html>"""

                        cl.send(reset_page.encode())
                        cl.close()

                        # Restart system
                        update_display_Restart()
                        print("Factory reset complete. Restarting in 5 seconds...")
                        time.sleep(5)
                        s.close()
                        machine.reset()

                    except Exception as e:
                        print(f"Error: Factory reset failed. {e}")
                        error_page = """HTTP/1.0 500 Internal Server Error\r\nContent-Type: text/html; charset=utf-8\r\n\r\n
<html><head><meta charset="utf-8"><title>錯誤</title></head>
<body><h1>重置失敗</h1><p>""" + str(e) + """</p><a href="/">返回</a></body></html>"""
                        cl.send(error_page.encode())
                        cl.close()
                        continue

                # Handle save profile request
                if "GET /save_profile?" in request:
                    last_activity_time = time.time()
                    print("Info: Saving profile...")

                    query_start = request.find("?") + 1
                    query_end = request.find(" ", query_start)
                    query_string = request[query_start:query_end]
                    params = parse_query_string(query_string)

                    try:
                        original_name = params.get("original_profile_name", "")
                        new_name = params.get("profile_name", "")

                        # Build profile data
                        profile_data = {
                            "name": new_name,
                            "wifi": {
                                "ssid": params.get("ssid", ""),
                                "password": params.get("password", "")
                            },
                            "weather_location": params.get("location", "Taipei"),
                            "user": {
                                "birthday": params.get("birthday", "0101"),
                                "light_threshold": int(params.get("light_threshold", "56000")),
                                "image_interval_min": int(params.get("image_interval_min", "2")),
                                "timezone_offset": int(params.get("timezone_offset", "8"))
                            },
                            "chime": {
                                "enabled": params.get("chime_enabled") == "true",
                                "interval": params.get("chime_interval", "hourly"),
                                "pitch": int(params.get("chime_pitch", "880")),
                                "volume": int(params.get("chime_volume", "80"))
                            }
                        }

                        # Update profile
                        config_manager.update_profile(original_name, profile_data)

                        # Update global settings
                        config_manager.set_global("weather_api_key", params.get("api_key", ""))
                        config_manager.set_global("ap_mode.ssid", params.get("ap_mode_ssid", "Pi_Clock_AP"))
                        config_manager.set_global("ap_mode.password", params.get("ap_mode_password", "12345678"))

                        # Set as active profile and update last connected
                        # This ensures the device will prioritize this profile on next restart
                        config_manager.set_active_profile(new_name)
                        config_manager.set_last_connected_profile(new_name)

                        print(f"Success: Profile '{new_name}' saved and activated.")

                        # Send success page and restart
                        success_page = """HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n
<html><head><meta charset="utf-8"><title>設定完成</title>
<style>body{font-family:sans-serif;text-align:center;padding:2rem;background:#f0f8ff}
h1{color:#03d3fc}p{font-size:1.2rem;color:#666}</style></head>
<body><h1>✅ 設定已儲存</h1><p>系統將在 5 秒後重新啟動...</p>
<script>setTimeout(()=>{window.location.href='/'},5000)</script></body></html>"""

                        cl.send(success_page.encode())
                        cl.close()

                        update_display_Restart()
                        print("Info: Restarting in 5 seconds...")
                        time.sleep(5)
                        s.close()
                        machine.reset()

                    except Exception as e:
                        print(f"Error: Failed to save profile. {e}")
                        error_page = """HTTP/1.0 400 Bad Request\r\nContent-Type: text/html; charset=utf-8\r\n\r\n
<html><head><meta charset="utf-8"><title>錯誤</title></head>
<body><h1>儲存失敗</h1><p>""" + str(e) + """</p><a href="/">返回</a></body></html>"""
                        cl.send(error_page.encode())
                        cl.close()
                        continue

                # Default: show main page
                try:
                    networks = scan_networks()
                    page = generate_html_page(networks)
                    cl.send(page.encode())
                    cl.close()
                except Exception as e:
                    print(f"Error: Failed to generate page. {e}")
                    try:
                        cl.close()
                    except:
                        pass

            except Exception as e:
                print(f"Error: Client handling error. {e}")
                try:
                    cl.close()
                except:
                    pass
                continue

        except Exception as e:
            print(f"Error: Server error. {e}")
            continue
        finally:
            gc.collect()

def wifi_manager():
    """
    Main WiFi manager with multi-profile support and intelligent connection logic.
    Scans networks, matches with known profiles, tries to connect by priority.
    """
    # Check if force AP mode is enabled
    if config_manager.get_global("force_ap_mode", False):
        print("Info: Force AP mode detected. Entering AP mode directly...")
        # Clear the flag
        config_manager.set_global("force_ap_mode", False)
        # Jump directly to AP mode (skip WiFi connection attempts)
        # Set sta inactive and go to AP mode section
        sta = network.WLAN(network.STA_IF)
        sta.active(False)
        # Skip to AP mode
        ap = network.WLAN(network.AP_IF)
        ap.active(True)

        ap_ssid = config_manager.get("ap_mode.ssid", "Pi_Clock_AP")
        ap_password = config_manager.get("ap_mode.password", "12345678")

        ap.config(ssid=ap_ssid, password=ap_password)
        ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))

        update_display_AP(ap_ssid, ap_password, '192.168.4.1')

        print(f"Info: AP Mode enabled (forced). SSID: {ap_ssid}, IP: 192.168.4.1")

        # Start web server
        run_web_server()

        return None

    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    print("Info: Scanning for available networks...")
    available_networks = scan_networks()  # Returns list of {ssid, rssi}

    if not available_networks:
        print("Warning: No networks found in scan.")
    else:
        print(f"Info: Found {len(available_networks)} networks.")

    # Find matching profiles
    matching_profiles = []
    for net in available_networks:
        ssid = net['ssid']
        profile = config_manager.find_profile_by_ssid(ssid)
        if profile:
            matching_profiles.append({
                'profile': profile,
                'rssi': net['rssi']
            })

    if not matching_profiles:
        print("Info: No known networks found. Entering AP mode.")
    else:
        print(f"Info: Found {len(matching_profiles)} known network(s).")

        # Sort by priority:
        # 1. Last connected profile first
        # 2. Then by signal strength (rssi, higher is better)
        last_connected = config_manager.get_last_connected_profile_name()

        # Separate last connected from others
        priority_profile = None
        other_profiles = []

        for match in matching_profiles:
            if match['profile']['name'] == last_connected:
                priority_profile = match
            else:
                other_profiles.append(match)

        # Sort others by signal strength
        other_profiles.sort(key=lambda x: x['rssi'], reverse=True)

        # Build final connection order
        connection_order = []
        if priority_profile:
            connection_order.append(priority_profile)
        connection_order.extend(other_profiles)

        # Try to connect in order
        for match in connection_order:
            profile = match['profile']
            ssid = profile['wifi']['ssid']
            password = profile['wifi']['password']
            rssi = match['rssi']

            print(f"Info: Trying to connect to '{ssid}' (signal: {rssi} dBm, profile: '{profile['name']}')...")

            sta.connect(ssid, password)

            timeout = 30
            while timeout > 0 and not sta.isconnected():
                time.sleep(1)
                timeout -= 1

            if sta.isconnected():
                print(f"Success: Connected to '{ssid}'.")
                print(f"IP Address: {sta.ifconfig()[0]}")

                # Set this profile as active and last connected
                config_manager.set_active_profile(profile['name'])
                config_manager.set_last_connected_profile(profile['name'])

                print(f"Info: Active profile set to '{profile['name']}'.")
                return sta
            else:
                print(f"Warning: Failed to connect to '{ssid}'.")

    # Connection failed, start AP mode
    print("Info: Starting AP mode for configuration.")

    ap = network.WLAN(network.AP_IF)
    ap.active(True)

    ap_ssid = config_manager.get("ap_mode.ssid", "Pi_Clock_AP")
    ap_password = config_manager.get("ap_mode.password", "12345678")

    ap.config(ssid=ap_ssid, password=ap_password)
    ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))

    update_display_AP(ap_ssid, ap_password, '192.168.4.1')

    print(f"Info: AP Mode enabled. SSID: {ap_ssid}, IP: 192.168.4.1")

    # Start web server
    run_web_server()

    return None
