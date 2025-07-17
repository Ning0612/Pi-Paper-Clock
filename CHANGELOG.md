# Changelog

所有此專案的顯著變更將會記錄在此檔案。

格式遵循 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)，
且本專案遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

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
  - 移除 `chime.py` 中不再使用的 `test_chime` 函數.