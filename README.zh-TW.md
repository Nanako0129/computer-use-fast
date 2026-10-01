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

## 直接使用 `cu.py`

```bash
cu.py --app "System Settings" --open --click 一般 --click 關於本機 --read 晶片
cu.py --app 計算機 --open --type "56*123=" --read --shot
cu.py --app Safari --key cmd+l --type "example.com" --key return
```

| 步驟 | 作用 |
|---|---|
| `--app 名稱` | 英文名、在地化名稱（例如 計算機）或 bundle id |
| `--open` | 需要時開啟 App，並等它的視窗出現 |
| `--url URL` | 先用 `open` 打開網址 |
| `--click 文字` | 點擊顯示文字相符的元素（完全相符 → 開頭相符 → 包含），並確認視窗有變化 |
| `--type 文字` | 在目前焦點的欄位打字 |
| `--key 鍵` | `return`、`escape`、`tab`，或 `cmd+n` 這類組合鍵 |
| `--wait 秒數` | 暫停 |
| `--read [篩選]` | 印出畫面上的文字；加篩選時，回傳符合的那行和下一行（`晶片 \| Apple M1`） |
| `--shot` | 把視窗存成 PNG 並印出路徑（`CU_SHOT_DIR`；沒設定時，有 `~/.hermes` 就存到 `~/.hermes/cache/images`，否則存到暫存資料夾） |

按鈕文字跟著系統語言：繁體中文系統要寫 `--click 一般`，不是 `--click General`。

結束代碼：`0` 成功 · `2` driver 錯誤 · `3` 找不到目標（會列出可以點的文字）· `4` 點了但畫面沒變化。

## 限制

- 沒有 AX 文字的 App（RustDesk 這類 Flutter App、遊戲、畫布）沒辦法用文字比對。skill 會叫 agent 改用它自己的
  computer use 工具。
- 管理員權限的對話框（解鎖按鈕、輸入密碼）要由人處理：skill 會叫 agent 停下來，說清楚哪個按鈕需要你。
  `cu.py` 本身不處理密碼。
- 只支援 macOS。

## 授權

MIT
