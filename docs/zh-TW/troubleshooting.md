# 疑難排解

| 你看到 | 原因 | 怎麼做 |
|---|---|---|
| `FAIL cua-driver not usable (…)` | driver 沒裝，或不在 `PATH` 上 | 做 [安裝第 1 步](setup.md)，或設定 `CUA_DRIVER_BIN` |
| `FAIL --app … app not found or could not be opened` | 名稱對不上任何已安裝的 App | 改用 Finder 裡顯示的名稱、英文名或 bundle id |
| `FAIL --app … runs only as a menu-bar or background agent` | 這個 App 完全沒有視窗（Amphetamine、Maccy……） | 沒有東西可操作，請自己用它的選單列圖示 |
| `FAIL --app … is running but has no window` | App 的視窗全部關掉了（Spotify、Telegram……） | 從 Dock 圖示或選單重新打開視窗，再跑一次 |
| `note … shows only its menus to accessibility clients` | Chromium 或 Electron App，還沒裝小工具 | 做 [安裝第 4 步](setup.md) |
| `note not trusted: allow … cu-axenable …` | 小工具還沒授權，或重新編譯過 | 到「隱私權與安全性 → 輔助使用」允許它 |
| `FAIL --click no element matching '…'; candidates: […]` | 文字跟畫面上的不同（常見是語言不同） | 從 `candidates` 挑對的名稱再跑一次 |
| `FAIL --fill no text field matching '…'` | 沒有這個標籤的欄位，而且沒有標籤的欄位不只一個 | 先用 `--click` 點那個欄位，再用 `--type` |
| `FAIL --wait-for '…' did not appear within 15s` | 頁面或對話框還沒出現那段文字 | 用 `--read` 對一下拼字，或在前面加 `--wait` |
| `clicked '…' (no visible change)` | 本來就選取了，或點了沒反應 | 本來就選取的話沒問題；否則用 `--read` 確認 |
| 「新功能」或隱私說明蓋住了 App | 第一次開啟 | 如果它要你同意什麼，請自己處理 |
| agent 還是一直截圖 | 它沒載入這個 skill | 做 [安裝第 5 步](setup.md) |
| App 開了之後 agent 等很久 | `osascript`／System Events 卡住 | 加上安裝第 5 步裡「never use osascript」那一行 |

## 操作不了的 App

自己繪製介面、沒有可讀文字的 App（RustDesk 這類 Flutter App、遊戲、繪圖畫布），`cu.py` 沒有東西可以比對。
skill 會叫 agent 改用它自己的 computer use 工具：截圖、依座標點擊、再截圖確認。做得到，只是比較慢。

## 一定要由你處理的事

密碼、Touch ID、「隱私權與安全性」裡的任何設定，以及「同意後繼續」的畫面。skill 會叫 agent 停下來，
說清楚哪個按鈕需要你。
