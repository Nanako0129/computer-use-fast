# 實測數據

以下全部在 2026-10-01、同一台機器上測量：MacBook Air（M1、2020、16 GB），macOS 27 繁體中文，cua-driver 0.28.2，
agent 是跑 `gemini-3.8-flash` 的 [Hermes](https://github.com/NousResearch/hermes-agent)。
**每個數字都只跑一次。** 你的數字會隨模型延遲而不同。

## 1. 透過 agent，從頭到尾

從 agent 收到請求到給出最後答案的時間，取自 Hermes 的 session 紀錄。

![透過 agent 從頭到尾的時間](../assets/speed.svg)

| 任務 | 之前 | 之後 | 加速 | 工具呼叫 |
|---|---|---|---|---|
| 系統設定 → 一般 → 關於，「什麼晶片？」 | 108.6 秒，一步一步的 computer use | **27.8 秒** | **3.9 倍** | 5 → 2 |
| 同一題改問記憶體，從 GitHub 安裝的版本 | — | **25.5 秒** | — | 4 |
| 計算機：輸入 56 × 123，截圖結果 | 52 秒，一步一步、但改用打字而非點按鍵 | **25.1 秒** | **2.1 倍** | 7 → 2 |
| 計算機，同一個請求，還沒做任何調整之前 | 239 秒（20 次模型呼叫） | **25.1 秒** | 9.5 倍 | — → 2 |

最後一列不是公平的比較，只是因為它是起點才列出：那次還有 95 秒卡在 `osascript`，而且對話累積到 16 萬 token。
第 1、3 列的「之前」，是 agent 用它自己的 computer use 工具，加上一組加速規則（能打字就不點、能讀文字就不截圖）。

### 時間花在哪裡

![時間花在哪裡](../assets/time-split.svg)

108.6 秒那次裡，六次工具呼叫本身只花了 4.6 秒，其餘都是 agent 在兩次呼叫之間思考。所以這個 skill 的做法
是減少回合數，而不是讓點擊變快。

### 與 jev-computer-use 的比較

[jev-computer-use](https://github.com/kerpopule/hermes-jev-skills) 用 [TypeSafe Jev](https://docs.typesafe.ai)
解同一個問題：一個小模型從輔助使用樹裡挑出下一個動作。同一台機器、同一個 agent、同一題系統設定：

| | 時間 | 工具呼叫 | 備註 |
|---|---|---|---|
| 一步一步 | 108.6 秒 | 5 | |
| jev-computer-use | 265.2 秒 | 13 | 規劃器沒有 key，每一步分開跑 |
| jev-computer-use，補上規劃器的 key | 94.4 秒 | — | runner 停了兩次（視窗還沒出現；點了沒反應），最後由 agent 手動完成 |
| **computer-use-fast** | **27.8 秒** | 2 | |

Jev 本身又快又準：每次決策 0.22–0.29 秒，選對元素的信心 0.98–0.99。花時間的是每一步前後 agent 的回合。

## 2. 單一 `cu.py` 呼叫，依任務

直接執行一次 `cu.py` 的實際時間（不經過 agent）。這些就是 agent 會下的指令。

| 任務 | 指令（節錄） | 時間 |
|---|---|---|
| 計算機：打字、讀結果 | `--app 計算機 --open --type "56*123=" --read` | 3.3–4.6 秒 |
| 文字編輯：從選單新增文件、打字、讀回 | `--menu "檔案 > 新增" --type … --read` | 3.8 秒 |
| 提醒事項：讀視窗 | `--app 提醒事項 --open --read` | 3.5 秒 |
| Finder：點兩次側邊欄、等檔案出現、讀取 | `--click 文件 --click 應用程式 --wait-for 計算機 --read` | 10.5 秒 |
| 系統設定：點兩下、讀晶片 | `--click 一般 --click 關於本機 --read 晶片` | 11.6–17.2 秒（較慢的幾次本來就停在該頁，點了沒變化會多等 3 秒） |
| Safari：開條目、點連結、讀欄位 | `--url … --wait-for … --click "Ptolemy V Epiphanes" --read Born` | 11.6 秒 |
| Safari：填搜尋框、送出、等結果 | `--fill "Search Wikipedia=Hieroglyphs" --key return --wait-for …` | 15.8 秒 |
| Chrome：開條目、點連結、讀欄位 | 同 Safari | 17.0 秒 |
| Chrome：填搜尋框、送出、等結果 | 同 Safari | 21.8 秒 |
| 活動監視器：篩選程序列表、讀取 | `--fill "搜尋=Finder" --read Finder` | 19.8 秒 |
| 音樂：讀視窗（媒體庫很大） | `--app 音樂 --open --read` | 32.4 秒 |

大視窗讀得比較慢：活動監視器和音樂有幾千列，音樂還會先撞到 driver 的 20 秒走訪上限，`cu.py` 才改讀淺層。

## 3. `cu.py` 本身的加速

測試過程中做的修正，每項都用同一道指令量過前後：

| 改了什麼 | 指令 | 之前 | 之後 |
|---|---|---|---|
| 判斷畫面有沒有變化時，只比對前 300 個元素，不整棵重讀 | Safari，點連結 | 7.7 秒 | 4.6 秒 |
| 輪詢時沿用目前的視窗，不每次重新挑選 | Finder，點側邊欄 | 7–9 秒 | 3.4–4.6 秒 |
| 原生欄位寫入值後直接採信，不再整棵重讀確認 | 活動監視器，填搜尋框 | 18.8 秒 | 10.4 秒 |
| 完整走訪逾時時，改用深度 10 重讀 | 音樂，讀取 | 20 秒後失敗 | 淺層走訪 2.6 秒 |
| 走訪上限調高到 10,000 個元素 | Safari，讀整篇維基條目 | 讀到目錄就被截斷 | 整篇 1.7 秒 |

## 4. 支援哪些 App

![74 個 App 有 58 個可以用](../assets/coverage.svg)

測試機上安裝的每個 App，都用 `--open --read` 開啟並讀取一次。74 個裡 58 個可以用，包含 Safari、Chrome、
Discord、VS Code、Claude、Word、Excel、PowerPoint、Keynote、郵件、備忘錄、聯絡人、行事曆、Finder、系統設定、
預覽程式、Automator、捷徑、天氣、音樂。另有 7 個刻意跳過：VPN（會切斷測試本身的連線）、虛擬機、會打開相機的 App。

| 不能用 | App | 原因 |
|---|---|---|
| 選單列或背景程式 | Adobe Lightroom Downloader、Amphetamine、Maccy、TokenBar、UniFi Endpoint、LogiPluginService、ZeroTier | 根本沒有視窗 |
| 在執行但視窗全關了 | Spotify、Telegram、無邊記、便條紙 | 重新打開視窗之前沒有東西可操作 |
| 不是視窗 App | 指揮中心、時光機、App | 沒有東西可操作 |
| Flutter | RustDesk | 自己繪製介面，沒有可讀的文字 |
| 開不起來 | News | 原因未查明 |

音樂在第一輪失敗（撞到 20 秒走訪上限），加上淺層重讀之後就能用了，已算在 58 個裡。

## 5. 會不會搶走你的畫面？

`cu.py` 透過 [cua-driver](https://github.com/trycua/cua) 操作 App，而 cua-driver **直接跑在你的 Mac 上**，
操作的是你真正的桌面，不是 CUA 的容器或虛擬機。所以要問的是：它會不會打擾到正在用這個桌面的人。

量測用的是 `scripts/watch_focus.py`，它**不經過** cua-driver：指令執行期間，每 50 毫秒直接從 macOS 的 CoreGraphics
讀取最前面的視窗屬於哪個 App、滑鼠在哪裡。它自己的對照組抓得到「切到 Safari 1 秒再切回來」，也抓得到「滑鼠移到
(600, 400) 再移回來」。每列開始時，前景是表中寫的那個 App。

| 指令 | 開始時的前景 | 前景 App 有沒有變（每 50 毫秒取樣） | 滑鼠 |
|---|---|---|---|
| 計算機，原本沒開：`--open --type "12*3=" --read` | Finder | 沒有 | 沒動過 |
| 計算機，已開啟：`--type "7*6=" --read` | Finder | 沒有 | 沒動過 |
| 系統設定，原本沒開：`--open --click … --click … --read 晶片` | Finder | 沒有 | 沒動過 |
| 系統設定，已開啟：`--click 外觀 --read` | Finder | 沒有 | 沒動過 |
| Safari：`--url … --wait-for … --click "Ptolemy V Epiphanes"` | Finder | 沒有 | 沒動過 |
| Safari：`--fill "Search Wikipedia=Hieroglyphs"` | Finder | 沒有 | 沒動過 |
| Finder 側邊欄（像素點擊） | Safari | 沒有 | 沒動過 |
| 文字編輯，原本沒開：`--open --read` | Finder | 沒有 | 沒動過 |
| 文字編輯，已開啟：`--read`（2 次） | Finder | 沒有 | 沒動過 |
| **文字編輯：`--menu "檔案 > 新增"`**（3 次） | Finder | **約 1.1 秒後文字編輯跳到前景，之後一直留在前面** | 沒動過 |
| **Finder：`--drag "檔案 > 資料夾"`**（檔案確實移進資料夾） | Safari | **Finder 到前景約 1.0 秒，再回到 Safari** | **移到放下的位置並停在那裡** |

會搶走畫面的有兩種。一是拖曳：cua-driver 在 macOS 上不允許背景拖曳，所以拖曳會把視窗帶到前面，並移動真正的滑鼠。二是「會開出新視窗的選單」：App 開新文件視窗時，macOS 會把它帶到前面。App 有多個視窗時打字會用
短暫的前景模式；那一輪量測的起始狀態不乾淨（上一步讓文字編輯留在前景），所以不下任何結論。

這張表的上一個版本是用 cua-driver 自己的 `active` 欄位量的，把選單那一列記成「沒變」；改用獨立取樣器後才發現不對。
`--open`、`--url` 改用 `open -g` 之前，開計算機、開系統設定、用 Safari 開網址都會把該 App 帶到前景。

## 6. 三個 agent、三個任務、各跑三次

![三個 agent 的比較](../assets/agents.svg)

`bench/agent_smoke.py` 給每個 agent 同一段英文提示、重設 App，再檢查答案。同一台 Mac（系統語言是繁體中文，所以提示裡的
英文標籤跟畫面對不上），每個 agent 都裝了這個 skill，工具全部放行。2026-10-01。**27 次全部答對。**

| 任務 | Claude Code（`claude-opus-5-5`） | Hermes（`gemini-3.8-flash`） | Grok CLI（`grok-4.7-build`） |
|---|---|---|---|
| 系統設定 → 一般 → 關於，讀晶片 | **29.3 秒**（31／29／27） | 37.0 秒（37／66／32） | 52.6 秒（42／53／60） |
| 計算機 56 × 123，讀顯示 | **14.3 秒**（14／19／14） | 24.9 秒（25／25／24） | 23.6 秒（24／19／29） |
| Safari：羅塞塔石碑 → 托勒密五世，出生日期 | **24.6 秒**（25／25／24） | 38.3 秒（50／38／38） | 75.8 秒（76／61／105） |

表中是中位數，括號裡是三次的數字。Claude Code 每個任務用了 4–5 輪。Hermes 的計算機和 Safari 是在下面那個系統設定修正之前
量的，那次修正不影響這兩條路徑。

先前幾輪看到了什麼、改了什麼：

- **系統設定**一開始 Hermes 要 75.2 秒、Grok 要 48.1 秒。讀取時漏掉了頁面上的按鈕（它們唯一的文字是 AX 描述），英文標籤
  也對不上中文畫面。`cu.py` 現在會讀描述，比對不到時改比對未翻譯的識別碼，中文系統上 `--click General --click About`
  也能用；Hermes 降到 37.0 秒。
- **Grok 跑 Safari** 一開始要 150.5 秒。它第一道 `cu.py` 指令在 14.2 秒就拿到答案，之後為了釐清參考資料裡的另一個日期，
  去讀了 `cu.py` 原始碼。SKILL.md 2.2.1 已經叫 agent 相信輸出。
- 透過 SSH 執行 Claude Code 會顯示「Not logged in」：它的登入憑證在登入鑰匙圈，SSH 工作階段讀不到。這次改用 launchd 在
  已登入的圖形工作階段裡執行。
- Grok 用 `--allow Bash` 時，`CU="…"; $CU …` 這種寫法和 `web_fetch` 會被擋，而非互動模式下工具被擋就直接結束；表中改用
  `--permission-mode bypassPermissions`，跟另外兩個一樣全部放行。

## 怎麼重現

```bash
# 單一 cu.py 呼叫
time python3 <skill>/scripts/cu.py --app "System Settings" --open --click 一般 --click 關於本機 --read 晶片
```

從頭到尾的數字：在裝和沒裝這個 skill 的情況下問 agent 同一個問題，再從它的紀錄讀出那一輪的時間
（Hermes：`~/.hermes/logs/agent.log` 裡 `response ready … time=` 那一行）。
