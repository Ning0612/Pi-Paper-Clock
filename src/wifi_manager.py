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

# Phase 3: CSRF 防護 - 全域 Token (啟動時生成)
# 使用時間戳 + ADC 噪音生成隨機 token (MicroPython 相容)
def _generate_csrf_token():
    """Generates a simple CSRF token using timestamp and ADC noise."""
    try:
        # 使用 ADC 讀取（電磁噪音）和時間戳生成隨機性
        adc = machine.ADC(machine.Pin(26))
        noise = adc.read_u16()
        timestamp = time.ticks_ms()
        # 組合生成 token (16進位字串)
        token_value = (timestamp * 31 + noise) & 0xFFFFFFFF
        return hex(token_value)[2:]  # 移除 '0x' 前綴
    except:
        # 降級方案：僅使用時間戳
        return hex(time.ticks_ms() & 0xFFFFFFFF)[2:]

CSRF_TOKEN = _generate_csrf_token()

def verify_csrf_token(params):
    """Verifies CSRF token from request parameters.

    Args:
        params: Dictionary of request parameters

    Returns:
        bool: True if token is valid, False otherwise
    """
    token = params.get("csrf_token", "")
    is_valid = token == CSRF_TOKEN
    if not is_valid:
        print(f"CSRF validation failed: expected={CSRF_TOKEN}, got={token}")
    return is_valid

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


def unquote(string):
    """Decodes URL-encoded strings (MicroPython compatible) with UTF-8 support."""
    if not string:
        return ""

    res = []
    i = 0
    n = len(string)

    while i < n:
        char = string[i]
        if char == '%' and i + 2 < n:
            try:
                hex_value = int(string[i+1:i+3], 16)
                res.append(hex_value)
                i += 3
            except ValueError:
                res.append(ord('%'))
                i += 1
        elif char == '+':
            res.append(ord(' '))
            i += 1
        else:
            res.append(ord(char))
            i += 1

    try:
        return bytes(res).decode('utf-8')
    except:
        return string

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

def html_escape(text):
    """Escapes HTML special characters to prevent XSS attacks.

    Args:
        text: String to escape (will be converted to string if not)

    Returns:
        Escaped string safe for HTML insertion

    Example:
        >>> html_escape('<script>alert("XSS")</script>')
        '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;'
    """
    if not isinstance(text, str):
        text = str(text)
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))

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

# Compressed static HTML chunks for memory efficiency with improved UI/UX
HTML_HEADER = b"HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<!DOCTYPE html><html lang=\"zh-TW\"><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\"><title>Pi Clock</title><style>:root{--primary:#0288d1;--primary-dark:#0277bd;--primary-light:#4fc3f7;--danger:#d32f2f;--danger-dark:#c62828;--warning:#f57c00;--warning-dark:#e65100;--success:#388e3c;--bg:#f4f7f6;--card:#fff;--sidebar-bg:#fff;--text:#333;--text-light:#666;--border:#ddd;--shadow:rgba(2,136,209,0.15)}*{box-sizing:border-box}body{margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}.profile-selector{background:var(--sidebar-bg);border-bottom:2px solid var(--primary);padding:1rem}.profile-selector h2{color:var(--primary);font-size:1.2rem;margin:0 0 0.75rem 0}.profile-select-group{display:flex;gap:0.5rem;align-items:center;max-width:500px;margin:0 auto}.profile-select-group select{flex:1;padding:0.7rem;border:1px solid var(--primary);border-radius:6px;font-size:1rem;background:var(--card);color:var(--text);font-weight:500;cursor:pointer}.profile-select-group select:focus{border-color:var(--primary-dark);outline:none;box-shadow:0 0 0 2px rgba(2,136,209,0.2)}.profile-select-group .btn{flex:0 0 auto;width:auto;min-width:auto;margin:0;padding:0.4rem 0.6rem;font-size:0.85rem;line-height:1.2}.main-content{flex:1;padding:1rem;overflow-y:auto}.container{max-width:700px;margin:auto;background:var(--card);padding:1.25rem;border-radius:12px;box-shadow:0 4px 20px var(--shadow)}h1{text-align:center;color:var(--primary);margin-bottom:1.25rem;font-size:1.75rem}fieldset{border:2px solid var(--primary);border-radius:8px;padding:1rem;margin-bottom:1rem;background:#f9feff}legend{font-weight:600;padding:0 .5rem;color:var(--primary)}label{display:block;font-weight:500;margin-bottom:.4rem;color:var(--text);font-size:0.95rem}input,select{width:100%;padding:0.7rem;border:1px solid var(--border);border-radius:6px;font-size:1rem;background:var(--card);transition:border .2s}input:focus,select:focus{border-color:var(--primary);outline:none;box-shadow:0 0 0 2px rgba(2,136,209,0.2)}input[type='checkbox']{width:auto;margin-right:.5rem;transform:scale(1.2);accent-color:var(--primary)}.form-group{margin-bottom:1rem}.info{font-size:.85rem;color:var(--text-light);margin-top:.25rem;padding:0.5rem;background:#e3f2fd;border-radius:4px;border-left:3px solid var(--primary)}.btn{width:100%;padding:0.8rem;font-size:1rem;font-weight:bold;border:none;border-radius:6px;cursor:pointer;transition:all .2s;margin-top:0.5rem}.btn:disabled{opacity:0.6;cursor:not-allowed}.btn-primary{background:var(--primary);color:#fff}.btn-primary:hover:not(:disabled){background:var(--primary-dark);transform:translateY(-1px)}.btn-primary:active{transform:translateY(0)}.btn-danger{background:var(--danger);color:#fff}.btn-danger:hover:not(:disabled){background:var(--danger-dark)}.btn-warning{background:var(--warning);color:#fff}.btn-warning:hover:not(:disabled){background:var(--warning-dark)}.adc-value{font-weight:bold;color:var(--primary)}.button-group{display:flex;gap:0.5rem;margin-top:1rem;flex-wrap:wrap}.button-group .btn{flex:1;min-width:140px}.danger-zone{margin-top:2rem;border-color:var(--danger)!important;background:#fff5f5!important}.danger-zone legend{color:var(--danger)!important}@media (min-width:768px){.profile-selector{padding:1.5rem}.profile-selector h2{font-size:1.3rem;margin-bottom:1rem}.main-content{padding:1.5rem}.container{padding:1.5rem}h1{font-size:2rem}.button-group .btn{min-width:auto}}</style></head><body><div class=\"profile-selector\"><h2>設定檔管理</h2><div class=\"profile-select-group\">"

HTML_SIDEBAR_END = b"<button class=\"btn btn-primary\" onclick=\"createNewProfile()\" style=\"white-space:nowrap;\">➕ 新增</button></div></div><div class=\"main-content\"><div class=\"container\"><h1>設定檔編輯</h1><form id=\"profile-form\" action=\"/save_profile\" method=\"get\">"

HTML_FOOTER = """<div class="button-group"><button type="submit" class="btn btn-primary" id="save-btn">💾 儲存並重啟</button><button type="button" class="btn btn-danger" onclick="deleteProfile()">🗑️ 刪除設定檔</button></div><fieldset class="danger-zone"><legend>⚠️ 危險區域</legend><p style="font-size:0.9rem;color:#666;margin-bottom:1rem;">完全重置會刪除所有設定檔並恢復出廠設定，此操作無法復原！</p><button type="button" class="btn btn-danger" onclick="factoryReset()">🔥 完全重置系統</button></fieldset></form></div></div><script>
function getCsrfToken(){const el=document.querySelector('input[name="csrf_token"]');return el?el.value:'';}
function updateAdc(){fetch('/adc').then(r=>r.json()).then(d=>{const el=document.getElementById('adc-value');if(el)el.innerText=d.adc;}).catch(e=>console.error(e));}
function testChime(){const p=document.getElementById('chime_pitch');const v=document.getElementById('chime_volume');const t=getCsrfToken();if(p&&v)fetch('/test_chime?pitch='+p.value+'&volume='+v.value+'&csrf_token='+t).catch(e=>console.error(e));}
function loadProfile(n){window.location.href='/edit_profile?name='+encodeURIComponent(n);}
function createNewProfile(){const n=prompt('請輸入新設定檔名稱:');if(n&&n.trim()){const t=getCsrfToken();window.location.href='/new_profile?name='+encodeURIComponent(n.trim())+'&csrf_token='+t;}}
function deleteProfile(){const el=document.getElementById('profile_name');if(el){const n=el.value;const t=getCsrfToken();const escaped=n.replace(/'/g,"\\\\'");if(confirm('確定要刪除設定檔「'+escaped+'」嗎？此操作無法復原！')){window.location.href='/delete_profile?name='+encodeURIComponent(n)+'&csrf_token='+t;}}}
function factoryReset(){const t=prompt('⚠️ 警告：完全重置將刪除所有設定檔並恢復出廠設定！\\n\\n此操作無法復原！\\n\\n請輸入「RESET」確認執行：');if(t==='RESET'){if(confirm('最後確認：您確定要執行完全重置嗎？')){const csrf=getCsrfToken();window.location.href='/factory_reset?csrf_token='+csrf;}}else if(t!==null){alert('輸入錯誤，重置已取消。');}}
document.addEventListener('DOMContentLoaded',function(){
setInterval(updateAdc,3000);
const ps=document.getElementById('profile-select');
if(ps){ps.addEventListener('change',function(){loadProfile(this.value);});}
const p=document.getElementById('chime_pitch');
const v=document.getElementById('chime_volume');
if(p)p.addEventListener('change',testChime);
if(v)v.addEventListener('change',testChime);
let clickCount=0;
let lastClickTime=0;
const k=document.getElementById('api_key');
if(k){k.addEventListener('click',function(){const t=Date.now();if(t-lastClickTime<3000){clickCount++;if(clickCount>=7){k.readOnly=false;k.type='text';k.style.backgroundColor='#fff';clickCount=0;}}else{clickCount=1;}lastClickTime=t;});}
const form=document.getElementById('profile-form');
const saveBtn=document.getElementById('save-btn');
if(form&&saveBtn){form.addEventListener('submit',function(){saveBtn.disabled=true;saveBtn.innerHTML='⏳ 儲存中...';});}
});
</script></body></html>""".encode('utf-8')

# Compressed response pages for memory efficiency with countdown timers
HTML_SUCCESS_PAGE = b"HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\"><title>設定完成</title><style>body{font-family:sans-serif;text-align:center;padding:2rem;background:#e8f5e9;margin:0}h1{color:#388e3c;margin-bottom:1rem}p{font-size:1.1rem;color:#666;margin:0.5rem 0}.countdown{font-size:3rem;font-weight:bold;color:#388e3c;margin:1.5rem 0}.progress-bar{width:80%;max-width:300px;height:8px;background:#ddd;border-radius:4px;margin:1rem auto;overflow:hidden}.progress-fill{height:100%;background:#388e3c;width:100%;animation:countdown 5s linear forwards}@keyframes countdown{to{width:0}}</style></head><body><h1>✅ 設定已儲存</h1><p>系統正在重新啟動...</p><div class=\"countdown\" id=\"countdown\">5</div><div class=\"progress-bar\"><div class=\"progress-fill\"></div></div><p style=\"font-size:0.9rem;color:#999;\">請稍候，裝置重啟後會自動連接 WiFi</p><script>let t=5;const el=document.getElementById('countdown');setInterval(()=>{t--;if(t>=0)el.innerText=t;},1000);setTimeout(()=>{window.location.href='/'},5000);</script></body></html>"

HTML_RESET_PAGE = b"HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\"><title>完全重置</title><style>body{font-family:sans-serif;text-align:center;padding:2rem;background:#ffebee;margin:0}h1{color:#d32f2f;margin-bottom:1rem}p{font-size:1.1rem;color:#666;margin:0.5rem 0}.countdown{font-size:3rem;font-weight:bold;color:#d32f2f;margin:1.5rem 0}.progress-bar{width:80%;max-width:300px;height:8px;background:#ddd;border-radius:4px;margin:1rem auto;overflow:hidden}.progress-fill{height:100%;background:#d32f2f;width:100%;animation:countdown 5s linear forwards}@keyframes countdown{to{width:0}}</style></head><body><h1>🔥 完全重置完成</h1><p>所有設定檔已刪除，系統已恢復出廠設定</p><div class=\"countdown\" id=\"countdown\">5</div><div class=\"progress-bar\"><div class=\"progress-fill\"></div></div><p style=\"font-size:0.9rem;color:#999;\">系統即將重新啟動...</p><script>let t=5;const el=document.getElementById('countdown');setInterval(()=>{t--;if(t>=0)el.innerText=t;},1000);setTimeout(()=>{window.location.href='/'},5000);</script></body></html>"

HTML_ERROR_PAGE_PREFIX = b"HTTP/1.0 400 Bad Request\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<html><head><meta charset=\"utf-8\"><title>錯誤</title></head><body><h1>儲存失敗</h1><p>"
HTML_ERROR_PAGE_SUFFIX = b"</p><a href=\"/\">返回</a></body></html>"

HTML_RESET_ERROR_PREFIX = b"HTTP/1.0 500 Internal Server Error\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<html><head><meta charset=\"utf-8\"><title>錯誤</title></head><body><h1>重置失敗</h1><p>"
HTML_RESET_ERROR_SUFFIX = b"</p><a href=\"/\">返回</a></body></html>"

def send_chunk(cl, data):
    """
    可靠地分段傳送資料，並加入微小延遲以防止緩衝區溢位。
    解決頁面載入不全或傳送失敗的問題。
    """
    total_sent = 0
    while total_sent < len(data):
        try:
            sent = cl.send(data[total_sent:])
            if sent == 0:
                raise OSError("Socket connection broken")
            total_sent += sent
            # 關鍵：每次傳送後暫停 10ms，讓 Pico W 的網路堆疊有時間清空緩衝區
            time.sleep(0.01)
        except OSError as e:
            print(f"Error sending chunk: {e}")
            break

def send_html_page(cl, networks, current_profile=None):
    """Sends configuration HTML page using chunked sending with improved stability and UI."""

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
    api_key = config_manager.get_global("weather_api_key", "")
    ap_ssid = config_manager.get("ap_mode.ssid", "Pi_Clock_AP")
    ap_password = config_manager.get("ap_mode.password", "12345678")
    adc_value = machine.ADC(machine.Pin(26)).read_u16()

    # Current profile settings
    profile_name = current_profile.get("name", "") if current_profile else ""
    wifi_ssid = current_profile.get("wifi", {}).get("ssid", "") if current_profile else ""
    location = current_profile.get("weather_location", "Taipei") if current_profile else "Taipei"
    birthday = current_profile.get("user", {}).get("birthday", "0101") if current_profile else "0101"
    image_interval = current_profile.get("user", {}).get("image_interval_min", 2) if current_profile else 2
    light_threshold = current_profile.get("user", {}).get("light_threshold", 56000) if current_profile else 56000
    timezone = current_profile.get("user", {}).get("timezone_offset", 8) if current_profile else 8
    chime_enabled = "checked" if (current_profile and current_profile.get("chime", {}).get("enabled", False)) else ""
    chime_interval = current_profile.get("chime", {}).get("interval", "hourly") if current_profile else "hourly"
    chime_pitch = current_profile.get("chime", {}).get("pitch", 880) if current_profile else 880
    chime_volume = current_profile.get("chime", {}).get("volume", 80) if current_profile else 80

    # 1. Send header and CSS (使用 send_chunk)
    send_chunk(cl, HTML_HEADER)

    # 2. Send profile selector (UI 改良：手機版下拉選單)
    active_profile_name = config_manager.get_active_profile_name()

    # 使用 <select> 下拉選單取代橫向捲動的 <div> 列表（事件綁定在 JavaScript 中）
    send_chunk(cl, '<select id="profile-select">'.encode('utf-8'))

    send_chunk(cl, '<option value="" disabled>-- 切換設定檔 --</option>'.encode('utf-8'))

    for p in profiles:
        # selected 指向正在編輯的設定檔
        selected = "selected" if p["name"] == profile_name else ""

        # 顯示設定檔名稱，加上狀態標籤
        option_text = p["name"]
        if p["name"] == active_profile_name and p["name"] == profile_name:
            # 既是啟用的又是正在編輯的
            option_text += " ●"
        elif p["name"] == active_profile_name:
            # 僅是啟用的
            option_text += " (啟用)"
        elif p["name"] == profile_name:
            # 僅是正在編輯的
            option_text += " ●"

        send_chunk(cl, f'<option value="{html_escape(p["name"])}" {selected}>{html_escape(option_text)}</option>'.encode('utf-8'))

    send_chunk(cl, b'</select>')

    # 3. Send sidebar end and form start (包含新增按鈕)
    send_chunk(cl, HTML_SIDEBAR_END)

    # 4. Send form fields (全部改用 send_chunk)
    # Phase 3: CSRF Token (隱藏欄位)
    send_chunk(cl, f'<input type="hidden" name="csrf_token" value="{CSRF_TOKEN}">'.encode('utf-8'))
    send_chunk(cl, f'<input type="hidden" id="original_profile_name" name="original_profile_name" value="{html_escape(profile_name)}">'.encode('utf-8'))
    send_chunk(cl, f'<fieldset><legend>設定檔資訊</legend><div class="form-group"><label for="profile_name">設定檔名稱:</label><input id="profile_name" name="profile_name" value="{html_escape(profile_name)}" required></div></fieldset>'.encode('utf-8'))

    # WiFi section
    send_chunk(cl, '<fieldset><legend>Wi-Fi 連線</legend><div class="form-group"><label for="ssid">SSID:</label><select id="ssid" name="ssid">'.encode('utf-8'))
    for net in networks:
        ssid = net['ssid'] if isinstance(net, dict) else net
        sel = "selected" if ssid == wifi_ssid else ""
        send_chunk(cl, f'<option value="{html_escape(ssid)}" {sel}>{html_escape(ssid)}</option>'.encode('utf-8'))
    # 密碼欄位不顯示已儲存密碼（安全性改進）
    send_chunk(cl, '</select></div><div class="form-group"><label for="password">密碼:</label><input type="password" id="password" name="password" placeholder="已設定（留空表示不修改）"></div></fieldset>'.encode('utf-8'))

    # Weather section
    send_chunk(cl, f'<fieldset><legend>天氣與個人化</legend><div class="form-group"><label for="location">天氣地點:</label><input id="location" name="location" value="{html_escape(location)}"></div><div class="form-group"><label for="birthday">生日 (MMDD):</label><input id="birthday" name="birthday" value="{html_escape(birthday)}"></div></fieldset>'.encode('utf-8'))

    # System settings
    send_chunk(cl, f'<fieldset><legend>系統設定</legend><div class="form-group"><label for="image_interval_min">圖片輪播間隔 (分鐘):</label><input type="number" id="image_interval_min" name="image_interval_min" value="{html_escape(str(image_interval))}"></div><div class="form-group"><label for="light_threshold">光感臨界值 (ADC):</label><input type="number" id="light_threshold" name="light_threshold" value="{html_escape(str(light_threshold))}"><p class="info">目前光感值: <span class="adc-value" id="adc-value">{html_escape(str(adc_value))}</span></p></div><div class="form-group"><label for="timezone_offset">時區偏移 (小時):</label><input type="number" id="timezone_offset" name="timezone_offset" value="{html_escape(str(timezone))}"></div></fieldset>'.encode('utf-8'))

    # Chime settings
    hourly_sel = "selected" if chime_interval == "hourly" else ""
    half_sel = "selected" if chime_interval == "half_hourly" else ""
    send_chunk(cl, f'<fieldset><legend>定時響聲</legend><div class="form-group" style="display:flex;align-items:center;"><input type="checkbox" id="chime_enabled" name="chime_enabled" value="true" {chime_enabled}><label for="chime_enabled" style="margin-bottom:0;">啟用定時響聲</label></div><div class="form-group"><label for="chime_interval">響聲間隔:</label><select id="chime_interval" name="chime_interval"><option value="hourly" {hourly_sel}>每小時</option><option value="half_hourly" {half_sel}>每半小時</option></select></div><div class="form-group"><label for="chime_pitch">音高 (Hz):</label><input type="number" id="chime_pitch" name="chime_pitch" value="{html_escape(str(chime_pitch))}"></div><div class="form-group"><label for="chime_volume">音量 (0-100):</label><input type="number" id="chime_volume" name="chime_volume" value="{html_escape(str(chime_volume))}"><button type="button" class="btn btn-warning" onclick="testChime()">🔊 測試響聲</button></div></fieldset>'.encode('utf-8'))

    # Global settings (Phase 2: 敏感資訊保護 - 不顯示已儲存密碼)
    # API Key 顯示遮罩或留空
    api_key_display = f"{api_key[:7]}...{api_key[-4:]}" if api_key and len(api_key) > 11 else ("已設定" if api_key else "")
    send_chunk(cl, f'<fieldset><legend>全局設定 (所有設定檔共用)</legend><div class="form-group"><label for="api_key">天氣 API Key:</label><input type="text" id="api_key" name="api_key" value="{html_escape(api_key_display)}" placeholder="留空表示不修改" readonly></div><div class="form-group"><label for="ap_mode_ssid">AP 模式 SSID:</label><input id="ap_mode_ssid" name="ap_mode_ssid" value="{html_escape(ap_ssid)}"></div><div class="form-group"><label for="ap_mode_password">AP 模式密碼:</label><input type="password" id="ap_mode_password" name="ap_mode_password" placeholder="已設定（留空表示不修改）"></div></fieldset>'.encode('utf-8'))

    # Send footer with JavaScript
    send_chunk(cl, HTML_FOOTER)

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
                max_request_size = 2048  # 2KB limit to prevent memory exhaustion

                while True:
                    try:
                        line = cl_file.readline()
                        if not line or line == b"\r\n":
                            break
                        # Check request size limit
                        if len(request) + len(line) > max_request_size:
                            print("Warning: Request too large, rejecting.")
                            cl.send(b"HTTP/1.0 413 Request Entity Too Large\r\n\r\n")
                            cl.close()
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

                    # Phase 3: CSRF 防護
                    if not verify_csrf_token(params):
                        print("Error: CSRF token validation failed for test_chime")
                        cl.send(b"HTTP/1.1 403 Forbidden\r\n\r\nCSRF token invalid")
                        cl.close()
                        continue

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
                        send_html_page(cl, networks, profile)
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

                    # Phase 3: CSRF 防護（Gemini 審查建議補強）
                    if not verify_csrf_token(params):
                        print("Error: CSRF token validation failed for new_profile")
                        cl.send(b"HTTP/1.1 403 Forbidden\r\nContent-Type: text/html; charset=utf-8\r\n\r\n")
                        cl.send(b"<h1>403 Forbidden</h1><p>CSRF token invalid.</p>")
                        cl.close()
                        continue

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

                    # Phase 3: CSRF 防護
                    if not verify_csrf_token(params):
                        print("Error: CSRF token validation failed for delete_profile")
                        cl.send(b"HTTP/1.1 403 Forbidden\r\nContent-Type: text/html; charset=utf-8\r\n\r\n")
                        cl.send(b"<h1>403 Forbidden</h1><p>CSRF token invalid.</p>")
                        cl.close()
                        continue

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

                    # Phase 3: CSRF 防護 (factory reset 需要 token)
                    # 解析 query string (如果有)
                    params = {}
                    if "?" in request:
                        query_start = request.find("?") + 1
                        query_end = request.find(" ", query_start)
                        query_string = request[query_start:query_end]
                        params = parse_query_string(query_string)

                    if not verify_csrf_token(params):
                        print("Error: CSRF token validation failed for factory_reset")
                        cl.send(b"HTTP/1.1 403 Forbidden\r\nContent-Type: text/html; charset=utf-8\r\n\r\n")
                        cl.send(b"<h1>403 Forbidden</h1><p>CSRF token invalid. Cannot perform factory reset.</p>")
                        cl.close()
                        continue

                    try:
                        # Perform factory reset
                        factory_reset()

                        # Send success page (compressed constant)
                        cl.send(HTML_RESET_PAGE)
                        cl.close()

                        # Restart system
                        update_display_Restart()
                        print("Factory reset complete. Restarting in 5 seconds...")
                        time.sleep(5)
                        s.close()
                        machine.reset()

                    except Exception as e:
                        print(f"Error: Factory reset failed. {e}")
                        # Send error page using chunked sending
                        cl.send(HTML_RESET_ERROR_PREFIX)
                        cl.send(str(e).encode('utf-8'))
                        cl.send(HTML_RESET_ERROR_SUFFIX)
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

                    # Phase 3: CSRF 防護
                    if not verify_csrf_token(params):
                        print("Error: CSRF token validation failed for save_profile")
                        cl.send(b"HTTP/1.1 403 Forbidden\r\nContent-Type: text/html; charset=utf-8\r\n\r\n")
                        cl.send(b"<h1>403 Forbidden</h1><p>CSRF token invalid. Please reload the page.</p>")
                        cl.close()
                        continue

                    try:
                        original_name = params.get("original_profile_name", "")
                        new_name = params.get("profile_name", "")

                        # 取得原始設定檔資料（用於保留密碼）
                        original_profile = config_manager.get_profile(original_name)

                        # Phase 2 安全改進：空密碼不覆蓋已儲存密碼
                        wifi_password = params.get("password", "")
                        if not wifi_password and original_profile:
                            # 保留原密碼
                            wifi_password = original_profile.get("wifi", {}).get("password", "")

                        # Build profile data
                        profile_data = {
                            "name": new_name,
                            "wifi": {
                                "ssid": params.get("ssid", ""),
                                "password": wifi_password
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

                        # Phase 2 安全改進：僅在有值時更新全局設定
                        api_key_input = params.get("api_key", "")
                        # 忽略遮罩值和空值
                        if api_key_input and not api_key_input.startswith("已設定") and "..." not in api_key_input:
                            config_manager.set_global("weather_api_key", api_key_input)

                        # AP SSID 總是更新
                        config_manager.set_global("ap_mode.ssid", params.get("ap_mode_ssid", "Pi_Clock_AP"))

                        # AP 密碼僅在有輸入時更新
                        ap_password_input = params.get("ap_mode_password", "")
                        if ap_password_input:
                            config_manager.set_global("ap_mode.password", ap_password_input)

                        # Set as active profile and update last connected
                        # This ensures the device will prioritize this profile on next restart
                        config_manager.set_active_profile(new_name)
                        config_manager.set_last_connected_profile(new_name)

                        print(f"Success: Profile '{new_name}' saved and activated.")

                        # Send success page (compressed constant)
                        cl.send(HTML_SUCCESS_PAGE)
                        cl.close()

                        update_display_Restart()
                        print("Info: Restarting in 5 seconds...")
                        time.sleep(5)
                        s.close()
                        machine.reset()

                    except Exception as e:
                        print(f"Error: Failed to save profile. {e}")
                        # Send error page using chunked sending
                        cl.send(HTML_ERROR_PAGE_PREFIX)
                        cl.send(str(e).encode('utf-8'))
                        cl.send(HTML_ERROR_PAGE_SUFFIX)
                        cl.close()
                        continue

                # Default: show main page
                try:
                    networks = scan_networks()
                    send_html_page(cl, networks)
                    cl.close()
                except Exception as e:
                    print(f"Error: Failed to send page. {e}")
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
