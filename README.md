# Pico Clock Weather Display - 基於 Pico W 與 E-Paper 的 IoT 時鐘

本專案是一個基於 Raspberry Pi Pico W 和 Waveshare 2.9 吋電子紙顯示器的 IoT 智慧時鐘。它不僅能顯示時間，還能連接網路獲取天氣資訊、輪播自訂圖片，並具備光線感應與觸控功能。

![Project Demo](https://example.com/your-project-image.gif)  <!-- 建議替換為您自己的專案展示圖片 -->

---

## ✨ 主要功能

- **即時天氣顯示**：自動從網路獲取並顯示指定地點的天氣狀況與溫度。
- **時間與日期顯示**：透過 NTP 協定自動同步網路時間，確保時間精準。
- **自訂圖片輪播**：可依設定的時間間隔，輪播 `src/image/custom` 資料夾中的圖片。
- **特殊事件圖片**：在特定日期（如生日）顯示專屬的慶祝圖片。
- **環境光感測**：在光線昏暗時自動關閉螢幕，節省電力並避免夜間光害。
- **觸控操作**：透過點擊電子紙螢幕進行互動（功能可自訂擴充，**支援長按觸發 Wi-Fi 重置與設備重啟**）。
- **定時響聲功能**：可設定整點或每半小時透過蜂鳴器發出提示音，音調與音量可調整。
- **AP 模式設定**：當無法連接 Wi-Fi 時，自動啟用 AP 模式，讓使用者透過手機或電腦連線至裝置，並透過網頁介面設定 Wi-Fi、天氣地點、定時響聲等參數，並可即時查看光感應器數值，**同時提供「測試響聲」按鈕，並優化了設定儲存流程，確保設定成功後能完整顯示儲存結果。**
- **穩定性與錯誤處理**：強化了網路連線、API 請求（包含重試機制）及圖片載入的錯誤處理，確保系統在異常情況下仍能穩定運行。

---

## 🛠️ 硬體需求

1.  **Raspberry Pi Pico W** - 內建 Wi-Fi 的主控制器。
2.  **[Waveshare 2.9inch Touch e-Paper HAT](https://www.waveshare.net/wiki/Pico-CapTouch-ePaper-2.9)** - 296x128 解析度，支援觸控的電子紙模組。
3.  **光敏電阻 (Photoresistor)** - 用於偵測環境亮度，連接至 Pico 的 ADC 引腳。
4.  **無源蜂鳴器 (Passive Buzzer)** - 連接至 Pico 的 Pin 20，用於定時響聲功能。
5.  **連接線與麵包板**
6.  **(選用) 3D 列印外殼**：`hardware/` 目錄中提供了 3D 外殼的 `.SLDPRT` 檔案，可自行列印使用。

---

## 🖼️ 圖片資源說明

本專案的所有圖片資源都存放在 `src/image/` 目錄下，並使用 `.bin` 格式。您可以替換或增加這些圖片來自訂您的時鐘。

- **`image/custom/`**
  - **用途**：存放使用者自訂的輪播圖片。
  - **格式**：建議為 `128x128` 像素的 1-bit 黑白圖片。
  - **說明**：您可以將自己喜歡的圖片（如動漫、風景、迷因等）轉換後放入此處，系統會定時輪播。

- **`image/events/birthday/`**
  - **用途**：當日期符合 `config.json` 中設定的生日時，會顯示此目錄下的圖片。
  - **說明**：您可以放入專屬的生日祝福圖片。

- **`image/login/`**
  - **用途**：在裝置啟動、嘗試連接 Wi-Fi 時顯示的過渡畫面。

- **`image/weather_icons/`**
  - **用途**：顯示天氣狀況的圖示。
  - **說明**：檔名必須對應 OpenWeatherMap API 回傳的天氣狀況。目前專案內建的圖示檔名如下：
    - `Clear.bin`
    - `Clouds.bin`
    - `Drizzle.bin`
    - `Dust.bin`
    - `Fog.bin`
    - `Haze.bin`
    - `Mist.bin`
    - `Rain.bin`
    - `Sand.bin`
    - `Smoke.bin`
    - `Snow.bin`
    - `Squall.bin`
    - `Thunderstorm.bin`
    - `Tornado.bin`

---

## 🚀 軟體安裝與設定

### 1. 安裝 MicroPython 韌體

- 前往 [MicroPython 官網](https://micropython.org/download/RPI_PICO_W/) 下載最新的 `.uf2` 韌體檔案。
- 按住 Raspberry Pi Pico W 上的 `BOOTSEL` 按鈕，同時將其連接到電腦。
- 電腦會將 Pico 識別為一個名為 `RPI-RP2` 的隨身碟。
- 將下載的 `.uf2` 韌體檔案拖曳至此隨身碟中，Pico 將自動更新並重新啟動。

### 2. 上傳專案檔案

本專案建議使用 `mpremote` 工具進行檔案上傳。

- **安裝 mpremote:**
  ```bash
  pip install mpremote
  ```

- **執行上傳腳本:**
  專案內已包含 `upload.py` 腳本，它會自動將 `src/` 目錄下的所有檔案和 `config.json` 上傳到 Pico。
  ```bash
  python upload.py
  ```

### 3. 進行裝置設定

設定裝置最方便的方式是使用 AP 模式。如果裝置無法連上 Wi-Fi，它會自動進入此模式。

#### a) 使用 AP 模式網頁介面 (建議方式)

- 當裝置無法連接到已設定的 Wi-Fi 時，會自動建立一個名為 `Pico-Clock-Setup` 的 Wi-Fi 熱點。
- 使用您的手機或電腦連接到此熱點。
- 打開瀏覽器，訪問 `http://192.168.4.1`。
- 在網頁介面中填寫您的 Wi-Fi 資訊、天氣地點、定時響聲等參數。
- 網頁會即時顯示光感應器數值，並每 3 秒自動更新。
- 提交後，裝置將儲存設定並自動重啟，嘗試連接新的 Wi-Fi。

#### b) 手動設定 (進階)

您也可以在電腦上預先建立設定檔再上傳。此方式適合需要自訂 AP 模式 SSID 或天氣 API 金鑰的開發者。

1.  將 `src/config.json.example` 複製一份並改名為 `src/config.json`。
2.  打開 `src/config.json` 並依據您的需求填寫。請參考下方「可調設定參數」章節。
3.  執行 `python upload.py`，腳本會將 `src` 目錄下的所有檔案（包含您的 `config.json`）上傳到裝置。

---

## 📊 可調設定參數

所有設定參數儲存在 `config.json` 中，並可透過 AP 模式網頁介面進行調整。支援巢狀結構，如 `chime.enabled`、`weather.location`。

| 參數名稱            | 說明                     | 類型   | 範例值        |
|---------------------|--------------------------|--------|---------------|
| `ap_mode_ssid`      | AP 模式 SSID              | 字串   | `"Pi_clock"` |
| `ap_mode_password`  | AP 模式密碼               | 字串   | `"123456"` |
| `wifi_ssid`         | Wi-Fi SSID              | 字串   | `"MyHomeWiFi"` |
| `wifi_password`     | Wi-Fi 密碼             | 字串   | `"password"` |
| `api_key`           | openweathermap API key  | 字串   | `""`     |
| `location`          | 天氣地點                 | 字串   | `"Taipei"`     |
| `birthday`          | 生日日期（MMDD）         | 字串   | `"0612"`       |
| `user.timezone_offset`| UTC 時間偏移量（小時）   | 數字   | `8`            |
| `user.light_threshold`| ADC 光感臨界值           | 整數   | `56000`        |
| `user.image_interval_min`| 圖片換圖間隔（分鐘）     | 整數   | `2`            |
| `chime.enabled`     | 啟用定時響聲             | 布林值 | `true`         |
| `chime.interval`    | 響聲間隔（整點／半小時）  | 字串   | `"hourly"`     |
| `chime.pitch`       | 音調（頻率，300 ~ 3k Hz） | 整數   | `80`           |
| `chime.volume`      | 音量（0~100）            | 整數   | `80`           |

---

## 🕹️ 使用說明

- **正常運作**：成功連上 Wi-Fi 後，裝置會自動顯示時間、天氣和輪播圖片。
- **觸控互動**：輕觸螢幕可以觸發預設的動作（例如：手動更換圖片）。
- **低光模式**：當環境光線低於 `light_threshold` 設定值時，螢幕會自動進入休眠狀態。

---

### 圖片轉換

- 本專案輪播的自訂圖片需要是 **1-bit 黑白** 的 `.bin` 格式檔案。
- **前置作業**：為了達到最好的顯示效果，建議您先將圖片進行 **去背處理**，並儲存為 **透明背景的 `.png` 檔案**。
- **轉換步驟**：
  1. 在您的電腦上執行 `python tools/image_to_bin.py`，這是一個圖形化介面的轉換工具。
  2. 點擊「選取圖片」並載入您處理好的 `.png` 圖檔。
  3. 設定「輸出寬度」為 `296`，「輸出高度」為 `128`。
  4. 點擊「更新預覽」查看轉換效果。
  5. 點擊「儲存 .bin 檔案」將結果儲存。
- 將轉換後的 `.bin` 檔案放入 `src/image/custom` 資料夾，並再次執行 `upload.py` 上傳即可。

### 專案結構

- `src/`: 主程式碼目錄。
  - `main.py`: 程式進入點，負責初始化與協調各模組。
  - `app_controller.py`: 應用程式主邏輯控制器。
  - `app_state.py`: 管理應用程式的狀態。
  - `chime.py`: 定時響聲功能模組。
  - `config_manager.py`: 設定檔讀寫管理，提供統一的設定存取介面。
  - `display_manager.py`: 顯示邏輯管理，負責畫面繪製與更新。
  - `display_utils.py`: 顯示相關的工具函數。
  - `file_manager.py`: 檔案操作相關工具。
  - `hardware_manager.py`: 硬體相關操作（如 ADC 讀取、蜂鳴器控制）。
  - `netutils.py`: 網路工具函數。
  - `weather.py`: 天氣資料獲取與處理。
  - `wifi_manager.py`: Wi-Fi 連線與 AP 模式管理，包含 Web 設定介面。
  - `epaper.py`: 電子紙驅動程式 (請勿修改)。
  - `image/`: 存放所有 `.bin` 圖片資源。
- `tools/`: 開發輔助工具。
- `hardware/`: 硬體相關的 CAD 檔案。
- `upload.py`: 用於部署檔案至 Pico 的腳本。

---

## 🧑‍💻 參考資料

本專案的部分程式碼參考了 Waveshare 官方提供的範例。

- **參考來源**：[Pico-CapTouch-ePaper-2.9 - Waveshare Wiki](https://www.waveshare.net/wiki/Pico-CapTouch-ePaper-2.9)