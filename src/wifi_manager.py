# wifi_manager.py
import network
import socket
import ure
import ujson
import time
import machine
from display_utils import display_rotated_screen, draw_scaled_text, draw_image
from config_manager import config_manager

def update_display_AP():
    """
    AP 模式下顯示 SSID 與 Password 資訊
    """
    def draw(canvas):
        ap_ssid = config_manager.get("ap_mode.ssid", "Pico_Clock_AP")
        ap_password = config_manager.get("ap_mode.password", "password")
        draw_scaled_text(canvas, f"SSID: {ap_ssid}", 3, 20, 2, 0)
        draw_scaled_text(canvas, f"Password: {ap_password}", 3, 50, 2, 0)
        draw_scaled_text(canvas, "IP: 192.168.4.1", 3, 80, 2, 0)
    display_rotated_screen(draw, angle=90, partial_update=False)

def update_display_Restart():
    def draw(canvas):
        draw_scaled_text(canvas, "Reboot...", 3, 50, 4, 0)
    display_rotated_screen(draw, angle=90, partial_update=False)

def unquote(s):
    """簡易的 URL decode 函式（MicroPython 用）"""
    res = ""
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            try:
                res += chr(int(s[i+1:i+3], 16))
            except Exception:
                res += s[i]
            i += 3
        else:
            res += s[i]
            i += 1
    return res

def scan_networks():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    nets = sta.scan()  # 每個項目：(ssid, bssid, channel, RSSI, authmode, hidden)
    networks = []
    for net in nets:
        ssid = net[0]
        if isinstance(ssid, bytes):
            ssid = ssid.decode("utf-8")
        rssi = net[3]
        networks.append({"ssid": ssid, "rssi": rssi})
    networks.sort(key=lambda x: x["rssi"], reverse=True)
    return networks

def generate_html_page(networks):
    # 嘗試讀取預設天氣位置
    default_location = config_manager.get("weather.location", "")
    default_birthday = config_manager.get("user.birthday", "")
    default_image_interval = config_manager.get("user.image_interval_min", 5)
    default_light_threshold = config_manager.get("user.light_threshold", 56000)
    
    adc = machine.ADC(machine.Pin(26))
    adc_value = adc.read_u16()

    html = "HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n"
    html += """
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PicoW WiFi 設定</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 10px; margin: 0; background-color: #f4f4f4; }
    h1 { color: #333; text-align: center; }
    form { background: #fff; padding: 15px; margin-bottom: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    label { display: block; margin-bottom: 5px; font-weight: bold; }
    select, input[type="password"], input[type="text"], input[type="number"] { width: 100%; padding: 8px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
    input[type="submit"] { width: 100%; padding: 10px; background: #57c2e6; border: none; border-radius: 4px; color: #fff; font-size: 16px; }
    input[type="submit"]:hover { background: #0d5069; }
    .info { font-size: 12px; color: #606770; text-align: center; margin-top: 10px; }
  </style>
</head>
<body>
  <h1>選擇 WiFi 網路</h1>
  <form action="/" method="get">
    <label for="ssid">SSID:</label>
    <select name="ssid" id="ssid">
"""
    for net in networks:
        html += "<option value='{}'>{}</option>".format(net["ssid"], net["ssid"])
    html += """
    </select>
    <label for="password">密碼:</label>
    <input type="password" id="password" name="password" placeholder="請輸入密碼">
    <label for="location">Weather Location:</label>
    <input type="text" id="location" name="location" placeholder="請輸入天氣位置" value="{}">
    <label for="birthday">Birthday (MMDD):</label>
    <input type="text" id="birthday" name="birthday" value="{}">
    <label for="image_interval_min">Image Interval (minutes):</label>
    <input type="number" id="image_interval_min" name="image_interval_min" value="{}">
    <label for="light_threshold">Light Threshold (for screen off):</label>
    <input type="number" id="light_threshold" name="light_threshold" value="{}">
    <input type="submit" value="儲存設定">
  </form>
  <form action="/" method="get">
    <input type="hidden" name="action" value="refresh">
    <input type="submit" value="更新網路列表">
  </form>
  <p class="info">Current Light Sensor Value: <span id="adc-value">{}</span></p>
  <script>
    setInterval(() => {{
      fetch('/adc')
        .then(res => res.json())
        .then(data => {{
          document.getElementById('adc-value').textContent = data.adc;
        }});
    }}, 3000);
  </script>
</body>
</html>
""".format(default_location, default_birthday, default_image_interval, default_light_threshold, adc_value)
    return html

def connect_wifi(ssid, password):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(ssid, password)
    timeout = 20
    while not sta.isconnected() and timeout:
        time.sleep(1)
        timeout -= 1
    if sta.isconnected():
        print("WiFi connected, IP:", sta.ifconfig()[0])
        return sta
    else:
        print("WiFi connection failed.")
        return None

def start_ap_mode():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap_ssid = config_manager.get("ap_mode.ssid", "Pico_Clock_AP")
    ap_password = config_manager.get("ap_mode.password", "password")
    ap.config(essid=ap_ssid, password=ap_password)
    print("AP mode started, SSID:", ap.config("essid"))
    return ap

def run_web_server():
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Web server listening on", addr)
    while True:
        cl, addr = s.accept()
        print("Client connected from", addr)
        cl_file = cl.makefile("rwb", 0)
        request = ""
        while True:
            line = cl_file.readline()
            if not line or line == b"\r\n":
                break
            request += line.decode()
        print("Request:", request)

        if request.startswith("GET /adc"):
            adc = machine.ADC(machine.Pin(26))
            adc_value = adc.read_u16()
            response = ujson.dumps({'adc': adc_value})
            cl.send("HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            cl.send(response)
            cl.close()
            continue

        # 忽略 favicon 請求
        if request.startswith("GET /favicon.ico"):
            cl.send("HTTP/1.0 404 Not Found\r\n\r\n")
            cl.close()
            continue
        if "action=refresh" in request:
            nets = scan_networks()
            page = generate_html_page(nets)
            cl.send(page)
            cl.close()
            continue

        match = ure.search(r"\?(ssid=[^ ]+)", request)
        if match:
            query_string = match.group(1)
            match_params = ure.search(r"ssid=([^&]+)&password=([^&]+)&location=([^&]+)&birthday=([^&]+)&image_interval_min=([^&]+)&light_threshold=([^&]+)", query_string)
            if match_params:
                new_ssid = unquote(match_params.group(1))
                new_password = unquote(match_params.group(2))
                new_location = unquote(match_params.group(3))
                new_birthday = unquote(match_params.group(4))
                new_image_interval = int(unquote(match_params.group(5)))
                new_light_threshold = int(unquote(match_params.group(6)))

                config_manager.set("wifi.ssid", new_ssid)
                config_manager.set("wifi.password", new_password)
                config_manager.set("weather.location", new_location)
                config_manager.set("user.birthday", new_birthday)
                config_manager.set("user.image_interval_min", new_image_interval)
                config_manager.set("user.light_threshold", new_light_threshold)
                
                update_display_Restart()
                response = ("""HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>設定成功</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 10px; margin: 0; background-color: #f4f4f4; text-align: center; }
    .container { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: inline-block; margin-top: 50px; }
    h1 { color: #333; margin-bottom: 10px; }
    p { color: #666; font-size: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>設定已儲存</h1>
    <p>Pico Pi Clock 將重新啟動。</p>
  </div>
</body>
</html>
""")
                cl.send(response)
                cl.close()
                s.close()
                time.sleep(5)
                machine.reset()
                raise SystemExit
        else:
            nets = scan_networks()
            page = generate_html_page(nets)
            cl.send(page)
            cl.close()
    print("Web server terminated. Please reboot Pico manually.")
    while True:
        time.sleep(1)

def wifi_manager():
    ssid = config_manager.get("wifi.ssid")
    password = config_manager.get("wifi.password")

    if ssid and password:
        wlan = connect_wifi(ssid, password)
        if wlan and wlan.isconnected():
            return wlan
    # 若無有效設定，則進入 AP 模式並啟動 Web 伺服器
    update_display_AP()
    start_ap_mode()
    run_web_server()  # 此函式會阻塞，直到使用者設定完畢並重啟 Pico

def main():
    wlan = wifi_manager()
    if wlan:
        print("WiFi 已連線。")
    else:
        print("WiFi Manager 模式啟動中，請透過網頁設定 WiFi。")

if __name__ == "__main__":
    main()