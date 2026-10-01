![computer-use-fast](docs/assets/cover.svg)

# computer-use-fast

> 讓你的 AI agent 用 Mac 用得快。請它開 App、一路點下去、打字、讀畫面或傳截圖，大約 25 秒就完成，
> 不用再等 50 到 100 秒。

[English](./README.md)

## 亮點

- **GUI 任務快 2 到 4 倍，都是實測。** 同一個 agent、同一台 Mac：系統設定 → 關於從 108.6 秒降到 27.8 秒，
  計算機加截圖從 52 秒降到 25.1 秒。[所有測量 →](docs/zh-TW/benchmarks.md)
- **一個任務一道指令，不是每點一下就一個回合。** 一步一步操作時，大約 90% 的時間是 agent 在兩次點擊之間
  思考。`cu.py` 用一次呼叫就把開 App、依畫面文字點按鈕、打字、選選單、填欄位、等待、讀畫面、截圖全做完，
  這些回合就省掉了。
- **大多數 App 都能用。** 在一台 Mac 上測了 74 個 App，58 個可以用，包含 Safari、Chrome、Discord、VS Code、
  Word、Excel、Keynote、郵件、備忘錄、Finder、系統設定。不能用的 App 會講清楚原因。
- **不挑系統語言，不需要 API key。** 中文 App 名稱和按鈕文字都能用（計算機、一般），全部在你的 Mac 上執行。
- **支援 Hermes、Claude Code，以及任何會讀 `SKILL.md` 的 agent。** Hermes 一行指令就能安裝和更新。

![透過 agent 從頭到尾的時間](docs/assets/speed.svg)

## 快速開始

```bash
# 1. 負責點擊的 driver，以及它需要的兩項 macOS 權限
/bin/bash -c "$(curl -fsSL https://cua.ai/driver/install.sh)"
cua-driver permissions grant

# 2. 安裝 skill（Hermes）
hermes skills install Nanako0129/computer-use-fast/skills/computer-use-fast
```

Claude Code 和其他 agent、Chrome 與 Electron App、確認安裝成功、更新：
**[docs/zh-TW/setup.md](docs/zh-TW/setup.md)**

## 怎麼用

照平常的方式跟 agent 說就好：

> 打開系統設定，告訴我這台 Mac 是什麼晶片。
> 打開計算機，算 56 × 123，截圖給我。
> 用 Safari 在維基百科搜尋「hieroglyphs」，告訴我寫了什麼。

agent 在背後只會跑一行，例如：

```bash
cu.py --app "System Settings" --open --click 一般 --click 關於本機 --read 晶片
```

## 文件

| | |
|---|---|
| [安裝](docs/zh-TW/setup.md) | 安裝、權限、Chrome／Electron 小工具、讓 agent 優先使用、更新、移除 |
| [指令參考](docs/zh-TW/reference.md) | 每個步驟、比對方式、輸出、結束代碼、環境變數 |
| [實測數據](docs/zh-TW/benchmarks.md) | 所有測量：從頭到尾、單一指令、每項修正的前後、與 Jev 的比較、App 相容性 |
| [疑難排解](docs/zh-TW/troubleshooting.md) | `cu.py` 會印出的每種訊息，以及該怎麼處理 |

## 授權

MIT
