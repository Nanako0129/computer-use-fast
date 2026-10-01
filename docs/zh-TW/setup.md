# 安裝

四個步驟，最後兩步是選用但建議做。需要 macOS 和 Python 3.9 以上（不用裝任何套件）。

![一個 GUI 請求怎麼處理](../assets/how-it-works.svg)

## 1. 安裝 cua-driver

真正負責點擊和讀畫面的是 [cua-driver](https://github.com/trycua/cua)，`cu.py` 負責告訴它要做什麼。它直接跑在你的 Mac 上、
操作你真正的桌面，不是 CUA 的容器或虛擬機。
用官方安裝程式安裝，再授予它需要的權限：

```bash
/bin/bash -c "$(curl -fsSL https://cua.ai/driver/install.sh)"
cua-driver permissions grant
```

`permissions grant` 會跳出 macOS 的授權視窗：替 **CuaDriver** 打開 **輔助使用** 和 **螢幕錄製**。確認方式：

```bash
cua-driver permissions status
```

安裝程式會把 `cua-driver` 放在 `~/.local/bin`，`cu.py` 會從 `PATH` 找到它。如果放在別的地方，用
`CUA_DRIVER_BIN` 指定完整路徑。

## 2. 安裝 skill

### Hermes Agent

```bash
hermes skills install Nanako0129/computer-use-fast/skills/computer-use-fast
```

最後幾行會告訴你裝到哪裡（`Installed: …`），位置在 `~/.hermes/skills/` 底下。加上 `--category <資料夾>`
可以指定資料夾。之後 Hermes 會持續追蹤來源，更新只要一行指令（見下方）。

### Claude Code

```bash
git clone https://github.com/Nanako0129/computer-use-fast ~/src/computer-use-fast
mkdir -p ~/.claude/skills
cp -R ~/src/computer-use-fast/skills/computer-use-fast ~/.claude/skills/
```

### 其他 agent

把 `skills/computer-use-fast/` 資料夾複製到該 agent 的 skills 資料夾。agent 必須能執行終端機指令。
`SKILL.md` 和 `scripts/` 要放在一起：skill 會呼叫自己旁邊的 `scripts/cu.py`。

## 3. 確認裝好了

下面的 `<skill>` 是第 2 步裝好的資料夾（例如 `~/.claude/skills/computer-use-fast`）。

```bash
python3 <skill>/scripts/test_cu.py
python3 <skill>/scripts/cu.py --app Calculator --open --type "1+1=" --read
```

第一行會印出 `ok`（不需要 driver）。第二行會打開計算機，印出一行含有 `2` 的結果。
其他情況請看 [疑難排解](troubleshooting.md)。

## 4. 選用：Chrome、Edge、Brave、Arc 與 Electron App

Chromium 系瀏覽器和 Electron App（Discord、VS Code、Claude……）預設不把內容公開給輔助使用工具，
要有程式「要求」才會打開。沒做這一步的話，這些 App 只讀得到選單列；Safari 和所有原生 App 不受影響。

負責「要求」的是一支約 20 行的小工具。先編譯：

```bash
mkdir -p ~/.local/share/computer-use-fast
swiftc -O <skill>/scripts/axenable.swift -o ~/.local/share/computer-use-fast/cu-axenable
```

`swiftc` 隨 Xcode 或它的 Command Line Tools 安裝（`xcode-select --install`）。

接著授權，這一步只有你能做：

1. 打開 **系統設定 → 隱私權與安全性 → 輔助使用**。
2. 按 **＋**，再按 **⌘⇧G**，貼上 `~/.local/share/computer-use-fast/cu-axenable`，按 **打開**。
3. 要求密碼或 Touch ID 時照常確認，並確定它的開關是打開的。

為什麼放在 skill 資料夾外面：macOS 的授權綁在這個檔案本身。更新 skill 時不能把它換掉；重新編譯就會換掉，
所以重新編譯之後要再授權一次。

## 5. 建議：叫 agent 優先使用它

agent 會在它判斷相關時才載入 skill，而知道其他點擊方法的 agent，有時會改走別條路。在 agent 的常駐指示裡
加一行就能穩定下來：

| Agent | 寫在哪裡 |
|---|---|
| Hermes | `~/.hermes/SOUL.md` |
| Claude Code | `~/.claude/CLAUDE.md` 或專案的 `CLAUDE.md` |

```
For any task on a Mac app's screen, load the computer-use-fast skill first and follow it.
Never use osascript or System Events to control apps.
```

第二行很重要：在測試用的 Mac 上，用 `osascript` 透過 System Events 操作，一次卡了 76 秒，另一次 120 秒後逾時。

## 更新與移除

| | Hermes | Claude Code |
|---|---|---|
| 有沒有新版？ | `hermes skills check` | `git -C ~/src/computer-use-fast fetch && git -C ~/src/computer-use-fast status` |
| 更新 | `hermes skills update computer-use-fast` | `git -C ~/src/computer-use-fast pull`，再執行一次 `cp -R` |
| 移除 | `hermes skills uninstall computer-use-fast` | `rm -rf ~/.claude/skills/computer-use-fast` |

如果編譯過 Chrome 小工具：`rm -rf ~/.local/share/computer-use-fast`，再從輔助使用清單裡移除 `cu-axenable`。
