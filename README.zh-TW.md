# computer-use-fast

> 讓 agent 在 Mac 上操作 GUI 時，只用一兩個回合就做完，不用來回十幾趟。能用 shell 指令回答的就不開視窗；
> 要開的話，用一次 `cu.py` 呼叫把開 App、依文字點按鈕、打字、讀畫面、截圖全部做完。

[English](./README.md)

## 為什麼需要它

agent 一步一步操作 Mac 時，時間幾乎都不是花在點擊上。在 MacBook Air（M1）上請它「打開系統設定 → 一般 →
關於，告訴我晶片型號」，總共 108 秒：工具只跑了 4.6 秒，中間的模型回合花了大約 97 秒。每截一次圖、每點一下、
每想一次「接下來呢」，都是一個回合。

`cu.py` 在本機一次跑完整串動作，用輔助使用（AX）的文字找按鈕，agent 只要花一個回合，不用六個。

| 任務（透過 agent 從頭跑到尾；Hermes、`gemini-3.8-flash`） | 一步一步 | 用這個 skill |
|---|---|---|
| 系統設定 → 一般 → 關於，讀晶片型號、截圖 | 108 秒 | 28 秒 |
| 計算機：輸入 `56*123=`、讀結果、截圖 | 52 秒 | 25 秒 |

每題只跑一次、只在一台機器上量，實際數字會隨你用的模型延遲而不同。

## 需要什麼

| | |
|---|---|
| macOS | 在 macOS 27（Apple Silicon）上測過 |
| Python | 3.9 以上，不用裝任何套件 |
| [cua-driver](https://github.com/trycua/cua) | `CuaDriver.app` 放在 `/Applications`，並已授權「輔助使用」與「螢幕錄製」（`cua-driver permissions grant`） |

`cu.py` 會自己啟動 `cua-driver mcp`。driver 不在預設位置的話，用 `CUA_DRIVER_BIN` 指定路徑。

## 安裝

### Hermes Agent

```bash
hermes skills install Nanako0129/computer-use-fast/skills/computer-use-fast
```

裝好之後 Hermes 會持續追蹤：有新版時 `hermes skills check` 會提示，`hermes skills update` 就會更新。
想指定放在哪個分類資料夾，加上 `--category <資料夾>`。

### Claude Code

```bash
git clone https://github.com/Nanako0129/computer-use-fast ~/src/computer-use-fast
mkdir -p ~/.claude/skills
cp -R ~/src/computer-use-fast/skills/computer-use-fast ~/.claude/skills/
```

之後要更新：`git -C ~/src/computer-use-fast pull`，再執行一次 `cp -R` 那一行。

### 其他會讀 `SKILL.md` 的 agent

把 `skills/computer-use-fast/` 複製到那個 agent 的 skills 資料夾。skill 會用 `SKILL.md` 旁邊的
`scripts/cu.py`，兩者要放在一起。

### 確認裝好了

把 `<skill>` 換成你安裝的資料夾（例如 `~/.claude/skills/computer-use-fast`）。

```bash
python3 <skill>/scripts/test_cu.py     # 不需要 driver，印出 "ok"
python3 <skill>/scripts/cu.py --app Calculator --open --type "1+1=" --read
```

第二行應該會打開計算機，印出一行含有 `2` 的結果。

### Chrome、Edge、Brave、Arc 與 Electron App（選用）

Chromium 系的瀏覽器和 Electron App（Discord、VS Code……）預設只把選單列提供給輔助使用程式，要有程式「要求」，
它們才會建出其餘的內容。`cu.py` 透過一支約 20 行的小工具來要求，而 macOS 規定這支工具要你授權一次才能執行：

```bash
mkdir -p ~/.local/share/computer-use-fast
swiftc -O <skill>/scripts/axenable.swift -o ~/.local/share/computer-use-fast/cu-axenable
~/.local/share/computer-use-fast/cu-axenable 1   # 第一次會印出 "not trusted: …"
```

接著打開 **系統設定 → 隱私權與安全性 → 輔助使用**，按 **＋**，按 **⌘⇧G** 貼上
`~/.local/share/computer-use-fast/cu-axenable`，確認它的開關是打開的。這個檔案刻意放在 skill 資料夾外面：
更新 skill 時不能把你授權過的檔案換掉。重新編譯就會換掉，所以重新編譯後要再授權一次。沒有這支工具時，
`cu.py` 會印出一行 `note`，網頁請改用 Safari。

## 直接使用 `cu.py`

```bash
cu.py --app "System Settings" --open --click 一般 --click 關於本機 --read 晶片
cu.py --app 計算機 --open --type "56*123=" --read --shot
cu.py --app Safari --url https://en.wikipedia.org/wiki/Rosetta_Stone --wait-for "Rosetta Stone" --click "Ptolemy V Epiphanes" --read Born
cu.py --app Safari --fill "Search Wikipedia=Hieroglyphs" --key return --wait-for "Egyptian hieroglyphs"
cu.py --app 文字編輯 --open --menu "檔案 > 新增" --type "你好" --read 你好
cu.py --app Finder --click 應用程式 --wait-for 計算機 --read 計算機
```

| 步驟 | 作用 |
|---|---|
| `--app 名稱` | 英文名、在地化名稱（例如 計算機）或 bundle id |
| `--open` | 需要時開啟 App，並等它的視窗出現 |
| `--window 標題` | 操作標題含有該文字的視窗（預設：最前面、有內容的視窗） |
| `--url URL` | 用 `--app` 指定的瀏覽器打開網址 |
| `--click 文字` | 點擊顯示文字相符的元素（完全相符 → 開頭相符 → 包含）；`--double`、`--right` 同理 |
| `--fill 標籤=文字` | 依標籤、提示文字或預設文字找到輸入框並填入；找不到時用工具列上唯一的輸入框 |
| `--type 文字` | 在目前焦點的欄位打字 |
| `--key 鍵` | `return`、`escape`、`tab`，或 `cmd+n` 這類組合鍵 |
| `--menu "A > B"` | 依路徑觸發選單列項目 |
| `--scroll 方向[:N]` | `up`／`down`／`left`／`right`，捲 N 格（預設 5） |
| `--wait-for 文字` | 最多等 15 秒，直到該文字出現在畫面上 |
| `--wait 秒數` | 單純暫停 |
| `--read [篩選]` | 印出畫面上的文字；加篩選時，回傳符合的那行和下一行（`晶片 \| Apple M1`） |
| `--shot` | 把視窗存成 PNG 並印出路徑（`CU_SHOT_DIR`；沒設定時，有 `~/.hermes` 就存到 `~/.hermes/cache/images`，否則存到暫存資料夾） |

執行過程中它還會：動作開出新視窗時自動切過去；`--click` 在目前視窗找不到目標時，到同一個 App 的其他視窗
（對話框、sheet）裡找；側邊欄這類不吃「按下」的列，改用真正的滑鼠點擊；網頁輸入框用打字填入，因為網頁不吃
直接寫入的值。

按鈕文字跟著系統語言：繁體中文系統要寫 `--click 一般`，不是 `--click General`。

結束代碼：`0` 成功 · `2` driver 錯誤 · `3` 找不到目標（會列出候選）· `4` `--wait-for` 逾時。點到本來就選取
的項目會印出 `(no visible change)` 並繼續。

## 實測過的 App

在一台 MacBook Air（macOS 27、繁體中文）上，把每個 App 都用 `--open --read` 開啟並讀取一次（2026-10-01）：
**75 個裡有 57 個讀取正常**，包含 Safari、Chrome（搭配 `cu-axenable`）、Discord、VS Code、Claude、
Microsoft Word／Excel／PowerPoint、Keynote、郵件、備忘錄、聯絡人、行事曆、Finder、系統設定、Automator、
預覽程式、音樂。另有 7 個刻意跳過（VPN、虛擬機、一開就會打開相機的 App）。其餘的：

| 類型 | App | `cu.py` 的回應 |
|---|---|---|
| 選單列或背景程式 | Amphetamine、Maccy、ZeroTier、LogiPluginService…… | 「runs only as a menu-bar or background agent」 |
| 在執行但視窗全關了 | Spotify、Telegram、無邊記、便條紙 | 「running but has no window」 |
| Flutter，沒有 AX 文字 | RustDesk、Cloudflare WARP | 改用一步一步的 computer use |
| 本來就不是視窗 App | 指揮中心、時光機、App | — |

## 限制

- 沒有 AX 文字的 App（RustDesk 這類 Flutter App、遊戲、畫布）沒辦法用文字比對。skill 會叫 agent 改用它自己的
  computer use 工具。
- 樹太大時只讀淺層：完整走訪超過 driver 的 20 秒上限時（媒體庫很大的「音樂」），`cu.py` 會改用深度 10 重試，
  側邊欄和工具列還讀得到。
- 管理員權限的對話框（解鎖按鈕、輸入密碼）要由人處理：skill 會叫 agent 停下來，說清楚哪個按鈕需要你。
  `cu.py` 本身不處理密碼。
- 只支援 macOS。

## 授權

MIT
