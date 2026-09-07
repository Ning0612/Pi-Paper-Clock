# Pico Paper Clock 設定檔說明

## 📋 多設定檔架構

從 v2.0 開始，Pico Paper Clock 支援多設定檔功能，讓你可以在不同地點使用不同的設定。

---

## 🗂️ 設定檔結構

### 新版格式（v2.0+）

```json
{
  "schema_version": 4,
  "global": {
    "ap_mode": { ... },
    "discord_webhook_url": "...",
    "setup_complete": false,
    "lan_admin": { "username": "admin", "password": "" }
  },
  "profiles": [ ... ],
  "active_profile": "設定檔名稱",
  "last_connected_profile": "設定檔名稱"
}
```

`schema_version` 由裝置維護。啟動時會補齊 v4 必要欄位並將硬體相關數值限制在文件範圍；保存使用 `config.json.tmp`／`.bak` 交易，意外斷電後會自動復原。請勿手動降低版本號。

若 `config.json` 的 `schema_version` 大於目前韌體支援的版本（例如被較新版本寫入後降級韌體），裝置會進入唯讀相容模式：略過遷移與正規化，且拒絕任何保存操作，直到韌體升級或版本號還原為止。

### 舊版格式（v1.x）自動遷移

如果你使用的是舊版 config.json，系統會在首次啟動時自動轉換為新格式：
- 舊設定會被保留並轉換為名為「預設」的設定檔
- 所有設定值都會保留
- 原始檔案會被覆寫為新格式

---

## 📦 設定項目說明

### 1. Global 設定（全局設定，所有設定檔共用）

#### `global.ap_mode`
AP 模式（無法連接 WiFi 時的熱點模式）設定

| 欄位 | 類型 | 說明 | 預設值 |
|------|------|------|--------|
| `ssid` | String | AP 模式的 SSID（網路名稱） | `"Pi_Clock_AP"` |
| `password` | String | AP 模式的密碼（至少 8 個字元） | `"12345678"` |

#### 其他全域設定

| 欄位 | 用途 | 注意事項 |
|---|---|---|
| `global.discord_webhook_url` | 選用的 Discord 在席通知 webhook | 視為 secret；留空可停用通知 |
| `global.env_log.enabled` | 是否記錄溫濕度歷史（DHT22） | 預設 `true`；目前僅能透過 `config.json` 調整，Web UI 尚未提供切換開關 |
| `global.env_log.interval_min` | 溫濕度原始取樣間隔（分鐘） | 預設 `15`；目前僅能透過 `config.json` 調整，Web UI 尚未提供輸入欄位 |
| `global.setup_complete` | 是否已完成首次 Wi-Fi 設定；裝置也會依既有 profile 自動補正 | 一般不要手動修改 |
| `global.lan_admin.username` | WebUI session 固定登入帳號 | 固定為 `admin`；保留此欄位作舊設定相容性 |
| `global.lan_admin.password` | PBKDF2-HMAC-SHA256 密碼記錄，不是明文密碼 | 不要提交真實密碼或雜湊記錄 |

Web UI 對 secret 欄位只顯示「已設定」狀態；留白保存時會保留原值。裝置使用自訂登入頁與 server-side 單一 session，不使用 HTTP Basic Auth。LAN 設定與圖片 API 的認證細節請見 [`IMAGE_API.md`](IMAGE_API.md)。

---

### 2. Profiles 設定（設定檔陣列）

每個設定檔代表一個使用地點，包含該地點專屬的所有設定。

#### 設定檔結構

```json
{
  "name": "設定檔名稱",
  "wifi": { ... },
  "weather_latitude": 25.0330,
  "weather_longitude": 121.5654,
  "user": { ... },
  "chime": { ... }
}
```

#### `profile.name`
設定檔名稱（唯一識別）

| 類型 | 說明 | 範例 |
|------|------|------|
| String | 設定檔的顯示名稱，不可重複 | `"家裡"`, `"公司"`, `"咖啡廳"` |

#### `profile.wifi`
WiFi 連線設定

| 欄位 | 類型 | 說明 |
|------|------|------|
| `ssid` | String | WiFi 網路名稱（SSID） |
| `password` | String | WiFi 密碼 |

**重要：** 系統會根據 WiFi SSID 自動識別並切換設定檔

#### `profile.weather_latitude` / `profile.weather_longitude`
天氣查詢位置的緯度與經度。每個 profile 可使用不同座標；裝置會將座標直接傳給 Open-Meteo，並使用該 profile 的固定 `timezone_offset` 產生預報日期。

| 欄位 | 類型 | 範圍 | 範例 |
|------|------|------|------|
| `weather_latitude` | Number | `-90` ~ `90` | `25.0330` |
| `weather_longitude` | Number | `-180` ~ `180` | `121.5654` |

Open-Meteo 提供目前天氣與 5 天每日預報，不需要 API Key。WMO 天氣代碼會對應到裝置既有的天氣圖示；若網路或 API 暫時不可用，裝置沿用快取有效期限與日期／時間／圖片頁面的 fallback 行為。

從舊版城市名稱遷移時，裝置只會離線對應內建的少數既有範例城市。無法對應的舊值會暫存於 `legacy_weather_location` 作為人工恢復提示，並先使用台北預設座標；此欄位不會被韌體拿來查詢天氣，請在設定頁填入正確座標後即可移除它。

#### `profile.user`
使用者個人化設定

| 欄位 | 類型 | 說明 | 預設值 | 範圍 |
|------|------|------|--------|------|
| `birthday` | String | 生日（MMDD 格式） | `"0101"` | `"0101"` ~ `"1231"` |
| `light_threshold` | Number | 光感臨界值（ADC 數值） | `56000` | `0` ~ `65535` |
| `presence_leave_timeout_sec` | Number | 光感持續多久才判定離開書桌（秒） | `180` | `60` ~ `3600` |
| `presence_return_timeout_sec` | Number | 光感持續多久才恢復在席（秒） | `10` | `0` ~ `60` |
| `image_interval_min` | Number | 圖片輪播間隔（分鐘） | `2` | `1` ~ `60` |
| `timezone_offset` | Number | 時區偏移（小時） | `8` | `-12` ~ `14` |

**光感臨界值說明：**
- 數值越低 = 越容易觸發螢幕休眠
- 建議在目標環境開燈時查看網頁中的「目前光感值」
- 設定為該值稍微大一點即可

**離開書桌判定說明：**
- 光感低於或等於臨界值時立即判定在桌前
- 光感高於臨界值必須連續達到 `presence_leave_timeout_sec` 秒，才會判定離開書桌
- 回到臨界值以內必須連續達到 `presence_return_timeout_sec` 秒，才會恢復在桌前狀態
- `presence_return_timeout_sec` 設為 `0` 時，回到臨界值以內會立即恢復在席
- 只要處於離開書桌狀態、且韌體本次尚未對電子紙下過清屏睡眠指令，就會執行一次全白刷新並送入睡眠，直到偵測到返回在席才恢復正常時間／圖片更新。判準是**狀態**而非轉換的瞬間，因此在暗處重新開機（開機畫面已經畫上面板、但從頭就是離席狀態、沒有「剛剛離開」這個轉換）也會照樣清屏睡眠
- 離席期間收到的圖片預覽請求會被丟棄而不繪製：韌體已對面板下過睡眠指令且環境無光，畫上去也看不見，只會把面板重新叫醒。API 仍會照常回傳 `preview_queued: true`，但該次預覽不會顯示

#### `profile.chime`
定時響聲設定

| 欄位 | 類型 | 說明 | 預設值 | 選項/範圍 |
|------|------|------|--------|-----------|
| `enabled` | Boolean | 是否啟用定時響聲 | `true` | `true` / `false` |
| `interval` | String | 響聲間隔 | `"hourly"` | `"hourly"` / `"half_hourly"` |
| `pitch` | Number | 音高（Hz） | `880` | `100` ~ `5000` |
| `volume` | Number | 音量（百分比） | `80` | `0` ~ `100` |

**響聲間隔：**
- `"hourly"`: 每小時整點響一次
- `"half_hourly"`: 每半小時響一次（整點 + 30 分）

---

### 3. 其他設定

#### `active_profile`
目前活動的設定檔名稱

| 類型 | 說明 |
|------|------|
| String | 系統目前使用的設定檔名稱，會自動更新 |

#### `last_connected_profile`
最後成功連接的設定檔名稱

| 類型 | 說明 |
|------|------|
| String 或 null | 記錄最後一次成功連接 WiFi 的設定檔，用於優先連接 |

---

## 🚀 使用方式

### 方法 1：透過網頁介面管理（推薦）

1. 長按時鐘上的任一按鈕約 3 秒
2. 系統會重啟並進入 AP Mode
3. 連接到 WiFi：`Pi_Clock_AP`（或你設定的 AP SSID）
4. 開啟瀏覽器，前往 `192.168.4.1`
5. 首次進入先設定固定管理帳號 `admin` 的至少 8 字元密碼；之後以 session 登入 WebUI
6. 在網頁介面中管理設定檔：
   - 新增設定檔
   - 編輯設定檔
   - 刪除設定檔
   - 切換活動設定檔

管理介面目前使用 HTTP。即使 session cookie 不再於每次 request 傳送密碼，同網段主動攻擊者仍可能攔截並重放 cookie 或 CSRF token；請只在可信任的 AP/LAN 使用。

### 方法 2：手動編輯 config.json

1. 停止時鐘程式
2. 使用 `mpremote` 或其他工具編輯 `config.json`
3. 參考 `config.json.example` 格式
4. 重啟時鐘

---

## 🔄 自動切換設定檔

系統會在啟動時：

1. **掃描可用的 WiFi 網路**
2. **匹配已知設定檔** - 根據 WiFi SSID 尋找對應的設定檔
3. **智能連接順序**：
   - 優先嘗試上次成功連接的設定檔
   - 其他設定檔按信號強度排序嘗試
4. **自動切換** - 連接成功後，自動設定對應的設定檔為活動設定檔

### 範例場景

假設你有三個設定檔：「家裡」、「公司」、「咖啡廳」

**在家中：**
```
掃描到 "Home_WiFi"（家裡的 SSID）
  ↓
連接成功
  ↓
自動切換到「家裡」設定檔
  ↓
使用家裡的光感臨界值、響聲設定等
```

**帶到公司：**
```
掃描到 "Office_WiFi"（公司的 SSID）和其他網路
  ↓
上次成功是「家裡」，但這裡沒有 "Home_WiFi"
  ↓
找到「公司」設定檔（匹配 Office_WiFi）
  ↓
連接成功
  ↓
自動切換到「公司」設定檔
  ↓
使用公司的設定（關閉響聲、延長圖片間隔等）
```

---

## ⚙️ 完全重置

如果系統出現問題需要恢復出廠設定：

1. 長按按鈕進入 AP Mode
2. 連接到 AP 並開啟網頁介面
3. 滾動到最下方「⚠️ 危險區域」
4. 點擊「🔥 完全重置系統」
5. 輸入 `RESET` 確認
6. 再次確認
7. 系統會刪除所有設定檔並恢復預設設定

**注意：** 完全重置會清空所有設定檔，此操作無法復原！

---

## 📝 範例設定檔

參考 `config.json.example` 檔案，其中包含三個範例設定檔：

- **家裡**：啟用響聲，正常圖片間隔
- **公司**：關閉響聲，延長圖片間隔
- **咖啡廳**：啟用響聲，較低光感臨界值（環境較暗）

---

## 🔧 進階設定

### 自訂 AP Mode 設定

在網頁介面的「全局設定」區域可以修改：
- AP 模式的 SSID
- AP 模式的密碼

修改後下次進入 AP Mode 會使用新的設定。

---

## ❓ 常見問題

### Q: 舊版 config.json 會被刪除嗎？
A: 會被自動轉換為新格式並覆寫。已知範例城市會轉成座標；無法離線對應的舊地點會保存在 `legacy_weather_location`，並先使用台北預設座標，避免靜默遺失資料。

### Q: 可以有多個設定檔使用同一個 WiFi SSID 嗎？
A: 不建議。系統會根據 SSID 識別設定檔，如果有重複會使用第一個匹配的。

### Q: AP Mode 超時後會發生什麼？
A: 系統會切換到最後一次連接的設定檔並重啟時鐘。

### Q: 可以手動切換設定檔嗎？
A: 可以透過網頁介面編輯任一設定檔並儲存，該設定檔會自動成為活動設定檔。

### Q: 刪除設定檔有限制嗎？
A: 系統至少需要保留一個設定檔，無法刪除最後一個。

### Q: Discord 通知突然不再送出了，怎麼查？
A: 先看裝置上的 `discord_diag.log`（可用 `mpremote connect COM<n> cat :discord_diag.log` 讀取），每行格式為 `日期,時間,事件,可用記憶體,細節`：

- `fail,...,lowmem,n=<次數>,largest=<最大連續區塊>`：heap 碎片化，連續記憶體不足以完成 TLS handshake。這是已知限制，pending 通知不會遺失。實測穩態下最大連續區塊只有約 10 KiB（門檻 20 KiB），送出幾乎只發生在重開機後的低記憶體啟動窗口，因此裝置會在連續失敗達門檻後自動重開機取回連續記憶體。**門檻依當下在席狀態而定**：離席（面板已清屏睡眠）時 2 次，約 2 分鐘；在席、或開機後第一次在席判定出來之前，則為 10 次、約 10 分鐘——重開機在你面前發生時要付出等待開機畫面的代價，離席時則幾乎無感。**保底重啟需同時滿足下列條件，任一不成立就不會重啟，這是刻意的 fail-safe 而非故障**：仍有 pending 通知、pending 已成功寫入 flash、開機已滿 5 分鐘、距上次自動重啟已滿 2 小時、且重啟時間戳能寫入 `discord_autoreset.log`。條件齊備時通常在該筆記錄後數分鐘內會看到 `autoreset` 與隨後送達的通知；若遲遲沒有，先依上述條件逐項確認，不要直接判定功能失效。
- `fail,...,http<狀態碼>`：webhook 本身的問題（例如 `http404` 代表 webhook 已被刪除、`http429` 代表被限流），請檢查 `global.discord_webhook_url`。**這類失敗不會觸發自動重啟**，需要你手動處理。
- `fail,...,offline` / `fail,...,nowebhook`：分別代表當下沒有網路連線、以及尚未設定 webhook；同樣不會觸發自動重啟。
- `recovered,...,after=<次數>`：先前失敗後已恢復送出。
- `autoreset,...,failures=<次數>,<away|present>`：曾觸發保底自動重啟。末欄是觸發當下的在席狀態，也就是套用了哪一個門檻（`away`＝2 次、`present`＝10 次）；沒有它就無法判斷失敗次數是否合乎預期。**這類重啟之後不會再送「已上線」通知**（若 IP 未變）——那次重啟唯一能用的 TLS 窗口要留給積壓的在席通知，不是拿來重報一個你已經知道的位址。IP 真的變了、或你自己斷電重開，則照常送出。

注意 `/api/v1/device` 回報的 `heap_free` 充足**不代表** Discord 送得出去，關鍵指標是最大連續區塊。

---

## 📚 相關資源

- [Open-Meteo API 文件](https://open-meteo.com/en/docs)
- [MicroPython 文件](https://docs.micropython.org/)
- [專案 GitHub](https://github.com/Ning0612/pico-paper-clock)

---

**版本：** 4.0（schema v4）
**更新日期：** 2026-07-17
