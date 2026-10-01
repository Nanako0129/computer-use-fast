# 指令參考

```bash
python3 <skill>/scripts/cu.py 步驟 [步驟 …]
```

步驟依照給的順序，在同一個行程裡執行。任何一步失敗就停下來，並說明原因。

## 步驟

| 步驟 | 作用 | 範例 |
|---|---|---|
| `--app 名稱` | 指定 App：英文名、在地化名稱或 bundle id | `--app Calculator`、`--app 計算機`、`--app com.apple.calculator` |
| `--open` | 沒在執行就開啟，並等它的視窗出現（放在哪個位置都可以） | `--app 備忘錄 --open` |
| `--window 標題` | 操作標題含有該文字的視窗。預設：最前面、有內容的視窗 | `--window "下載項目"` |
| `--url 網址` | 用 `--app` 指定的瀏覽器打開網址 | `--app Safari --url https://example.com` |
| `--click 文字` | 點擊顯示文字相符的元素 | `--click "關於本機"` |
| `--double 文字` | 雙擊 | `--double "report.pdf"` |
| `--right 文字` | 按右鍵 | `--right "report.pdf"` |
| `--drag "A > B"` | 把顯示 A 的元素拖到顯示 B 的元素上（會移動真正的滑鼠，見下方） | `--drag "notes.txt > 封存"` |
| `--fill 標籤=文字` | 在標籤為「標籤」的欄位填入文字（依標籤、提示或預設文字） | `--fill "搜尋=採買"` |
| `--type 文字` | 在目前焦點的地方打字 | `--type "56*123="` |
| `--key 鍵` | 按鍵或快捷鍵 | `--key return`、`--key cmd+n` |
| `--menu "A > B"` | 依路徑選擇選單列項目 | `--menu "檔案 > 新增"` |
| `--scroll 方向[:N]` | 往 `up`、`down`、`left`、`right` 捲 N 格（預設 5） | `--scroll down:10` |
| `--wait-for 文字` | 最多等 15 秒，直到該文字出現在畫面上 | `--wait-for "搜尋結果"` |
| `--wait 秒數` | 固定等待 | `--wait 2` |
| `--read [篩選]` | 印出畫面上的文字，最多 150 行；加篩選時只印符合的 | `--read`、`--read 晶片` |
| `--read-all` | 不限行數，全部印出 | `--read-all` |
| `--shot` | 把視窗存成 PNG 並印出路徑 | `--shot` |

### `--click` 怎麼找目標

1. 比對時忽略大小寫和空白：**完全相同**優先，其次是**開頭相同**，最後是**包含**。同分時標籤較短的優先。
   選單列的項目不列入。
2. 符合的文字如果在可點擊的列或格子裡，就點那一列。
3. 目前視窗找不到時，會到這個 App 的其他視窗找，所以 `--click 取消` 點得到對話框或 sheet 裡的按鈕。
4. 不吃輔助使用「按下」動作的元素（例如 Finder 側邊欄的列），改用真正的滑鼠點擊它的中心。

文字就是 App 在你的系統語言下顯示的字：繁體中文的 Mac 要寫 `--click 一般`。畫面文字都比對不到時，`--click` 還會
比對每個元素未翻譯的輔助使用識別碼，所以 `--click About` 在系統設定裡一樣找得到「關於本機」（它的識別碼結尾是
`general.about`）。`--read 篩選` 沒有這個備援：純文字沒有識別碼，所以篩選要用畫面上的語言。

### `--read 篩選` 怎麼配對數值

畫面上標籤和數值是相鄰的兩行（先 `晶片`，再 `Apple M1`）。加上篩選時，每個符合的行會連同下一行一起印出：
`--read 晶片` 會印出 `晶片 | Apple M1`。

### 它會自動處理的事

- 動作開出的新視窗（檔案 → 新增、偏好設定視窗）會成為新的操作目標。
- 網頁表單用打字的方式填入，因為網頁不吃直接寫入的值。
- App 有好幾個視窗時，按鍵會先把目標視窗短暫帶到前景再送出。
- 挑預設視窗時會略過浮動提示（例如「登入」小泡泡）。
- 20 秒內讀不完的視窗（媒體庫很大的「音樂」）會改讀到深度 10。
- 如果裝了 [安裝第 4 步](setup.md) 的小工具，會請 Chromium 和
  Electron App 公開內容。

## 背景還是前景

`cu.py` 透過輔助使用的動作操作 App，所以大部分步驟都不會把你正在用的 App 擠到後面，也不碰滑鼠。少數情況需要
把目標視窗短暫帶到前面：

| 步驟 | 你會看到 |
|---|---|
| 在已開啟視窗裡的 `--click`、`--fill`、`--type`、`--key`、`--read`、`--wait-for` | 什麼都不會變，你的前景 App 保持焦點 |
| 會開出新視窗的 `--menu`（檔案 → 新增） | 該 App 會帶著新視窗跳到前面 |
| `--open`、`--url` | 什麼都不會變，App 和網頁在你目前的 App 後面開啟（`open -g`） |
| 對「要被帶到前景才會出現第一個視窗」的 App 用 `--open`（文字編輯） | 該 App 會跳到前面 |
| 對需要真正滑鼠點擊的列（Finder 側邊欄）用 `--click`，而背景點擊被拒絕時 | 視窗短暫到前面讓它點，點完再把你的 App 放回前面 |
| App 開了好幾個視窗時的 `--type`／`--key` | 同樣短暫切換一下，確保按鍵送進正確的視窗 |
| `--drag` | macOS 沒辦法在背景拖曳：視窗會到前面約 1 秒，而且**真正的滑鼠會移到放下的位置**並停在那裡 |

實測數據在 [benchmarks.md](benchmarks.md)。想自己驗證，可以用 `python3 scripts/watch_focus.py -- python3 scripts/cu.py …`，
它不經過 cua-driver，每 50 毫秒取樣一次前景 App 和滑鼠位置。

## 輸出

每個步驟一行，最後是總時間：

```
ok   --app 系統設定 pid=17858 window=1018  (2.7s)
ok   --click clicked '一般'  (5.0s)
ok   --click clicked '關於本機'  (4.1s)
[read 晶片] 晶片 | Apple M1
ok   --read 2 texts  (0.7s)
done in 12.4s
```

點了沒有任何變化（那一頁本來就開著）會印出 `(no visible change)` 並繼續。要確認結果，請用 `--wait-for`
或 `--read`。

## 結束代碼

| 代碼 | 意思 |
|---|---|
| `0` | 每一步都完成 |
| `2` | 找不到 cua-driver，或它出錯 |
| `3` | 找不到東西。同一行會列出**有哪些**（`candidates: […]`），從裡面挑對的名稱再跑一次 |
| `4` | `--wait-for` 等了 15 秒仍沒出現 |

## 環境變數

| 變數 | 預設 |
|---|---|
| `CUA_DRIVER_BIN` | `PATH` 上的 `cua-driver`，找不到就用 `/Applications/CuaDriver.app/Contents/MacOS/cua-driver` |
| `CU_SHOT_DIR` | 有 `~/.hermes` 就用 `~/.hermes/cache/images`，否則用系統暫存資料夾 |
| `CU_AXENABLE` | `~/.local/share/computer-use-fast/cu-axenable` |
