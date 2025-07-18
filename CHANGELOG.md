# Changelog

所有此專案的顯著變更將會記錄在此檔案。

格式遵循 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)，
且本專案遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [1.3.0] - 2025-07-18

### 新增功能 (Added)
- **圖片管理增強**：
  - 新增日期特定事件圖片支援，可顯示與當前日期相關的圖片。
  - 觸控螢幕可循環切換圖片。
  - 載入頁面圖片現在會隨機顯示。

### 變更與重構 (Changed)
- **部署腳本優化 (`upload.py`)**：
  - 腳本已大幅重構，支援設備遞歸清理。
  - 上傳過程提供更詳細的進度報告（包含檔案大小）。
  - 改進目錄創建邏輯，避免重複的 `mkdir` 調用。
  - 移除 `get_device_space_info` 函數。
- **本地化與訊息統一**：
  - `src/app_controller.py` 和 `src/display_utils.py` 中的多處列印訊息和使用者介面字串已從中文改為英文。
- **工具改進 (`tools/image_to_bin.py`)**：
  - 轉換工具現在會保留原始檔案名稱作為預設儲存名稱。
- **版本控制忽略設定**：
  - `.gitignore` 已更新，忽略 `src/image` 目錄下的常見圖片格式 (`.jpg`, `.jpeg`, `.png`)。

## [1.2.0] - 2025-07-18

### 新增功能 (Added)
- **時區設定功能**：
  - 新增 `timezone_offset` 設定，允許使用者根據所在地區設定 UTC 時間偏移（-12 到 +14 小時）。
  - 可於 `config.json` 或 AP 模式設定頁面中進行設定。
  - 主畫面時間與天氣預報將根據此偏移量顯示正確的本地時間。

### 變更與重構 (Changed)
- **天氣模組記憶體優化**：
  - 重構 `weather.py` 中的天氣預報功能 (`fetch_weather_forecast`)，採用分段處理 JSON 資料的方式，大幅降低記憶體使用量，解決在記憶體有限的 Pico W 上可能發生的 `MemoryError`。
  - 增強 `_make_request_with_retry` 的錯誤處理，加入 `OSError` 和 `MemoryError` 的捕獲，並在請求前後手動觸發垃圾回收 (`gc.collect()`)。
- **設定檔結構調整**：
  - 在 `config.json` 中，將 `light_threshold` 和 `image_interval_min` 移至 `user` 物件下，使設定檔結構更清晰。
- **程式碼邏輯優化**：
  - `display_manager.py` 中的畫面更新函數現在直接接收時間物件，避免重複呼叫 `get_local_time()`。

## [1.1.0] - 2025-07-17

### 新增功能 (Added)
- **定時響聲功能**：
  - 新增 `chime.py` 模組，可透過無源蜂鳴器 (Pin 20) 實現整點或半點報時。
  - 可於 `config.json` 或 AP 模式設定頁面中啟用/停用、調整音調與音量。
- **AP 模式功能擴充**：
  - 設定頁面新增「定時響聲」相關選項。
  - 設定頁面會即時顯示當前光感應器的 ADC 數值，每 3 秒自動更新。
  - 新增 `/adc` API endpoint 供前端非同步取得感測器數值。
  - **新增「測試響聲」按鈕**：在 AP 模式設定頁面中，音量設定旁新增測試按鈕，可即時測試蜂鳴器響聲。

### 變更與重構 (Changed)
- **應用程式架構重構**：
  - 將原有的 `main.py` 核心邏輯拆分為多個獨立模組，包含 `app_controller.py`, `app_state.py`, `hardware_manager.py` 等，提高模組化與可維護性。
  - 遵循單一職責原則，各模組功能更專一。
- **統一設定管理**：
  - 引入 `config_manager.py` 模組，集中處理 `config.json` 的讀取與寫入，提供統一的設定存取介面。
  - `config.json` 擴充了響聲、生日、光感門檻等設定。
- **Web 設定介面優化**：
  - AP 模式的 HTML 頁面 (`wifi_manager.py`) 進行了重構，以支援更多設定選項與即時數據顯示。
  - **優化設定儲存流程**：調整 AP 模式下設定儲存流程，先解析並儲存設定，再回傳包含已儲存設定（敏感資料已遮蔽）的成功頁面，最後才重啟裝置。
  - **增加重啟延遲**：將設定儲存後的重啟延遲從 3 秒增加到 5 秒，確保客戶端能完整接收成功頁面。
- **按鈕行為優化**：
  - 在 `app_controller.py` 中實現按鈕長按偵測，長按可觸發 Wi-Fi 重置並重啟設備。
  - `hardware_manager.py` 中 `get_button_states` 方法調整，將按鈕原始值反轉，使 `1` 表示按下，`0` 表示未按下。
- **顯示函數重構**：
  - `update_display_Restart` 函數從 `wifi_manager.py` 移至 `display_manager.py`，統一顯示相關邏輯。
- **錯誤修正**：
  - 修正 `wifi_manager.py` 中 `success_page_template` 因 CSS 樣式中的 `{}` 未正確跳脫導致的 `KeyError: 'font-family'` 錯誤。
- **穩定性提升**：
  - 增強了 Wi-Fi 連線、天氣 API 請求及圖片載入時的錯誤處理機制，加入重試與 fallback 邏輯。
  - 移除 `chime.py` 中不再使用的 `test_chime` 函數。
  - **網路與檔案操作穩定性強化**：
    - 為天氣 API 請求 (於 `src/weather.py`) 實作了更穩健的重試機制，並改進了錯誤日誌，同時確保在無網路連線時跳過請求。
    - 在 NTP 時間同步 (於 `src/netutils.py`) 前增加網路連線檢查。
    - 改進了圖片載入 (於 `src/display_utils.py` 和 `src/file_manager.py`) 的錯誤處理，並將錯誤訊息翻譯為英文。
  - **`NoneType` 錯誤修正**：強化了 `urequests` 回應物件可能為 `None` 的錯誤處理邏輯，確保安全地關閉回應物件。
- **錯誤修正**：
  - 修正 `wifi_manager.py` 中 `success_page_template` 因 CSS 樣式中的 `{}` 未正確跳脫導致的 `KeyError: 'font-family'` 錯誤。
  - **訊息統一**：所有 `print` 訊息皆已轉換為英文。
- **內部邏輯調整**：
  - `src/app_controller.py` 中 `_perform_chime` 的呼叫順序調整。
  - `upload.py` 處理了 `UnicodeDecodeError` 並新增了顯示設備空間資訊的功能。