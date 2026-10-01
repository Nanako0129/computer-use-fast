---
name: computer-use-fast
description: Do GUI tasks on a Mac in as few agent turns as possible. Try a shell command first, then run the whole click/type/read sequence in ONE terminal call with scripts/cu.py, and fall back to step-by-step computer use only for apps with no accessibility text. Load before any desktop or app task on macOS.
version: 2.1.0
author: Nanako Tsai
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [computer-use, performance, macos, cua-driver]
---

# GUI tasks on a Mac — fast path

**Why:** the tools are cheap, your own turns are not. Measured on a MacBook Air (M1, 2020), "System Settings →
General → About, what chip?" driven step by step: the tools took 4.6 s in total, the six model turns around them
took about 97 s. So the goal is **as few of your own turns as possible**.

Pick the first tier that works.

## Tier 1 — no GUI at all

If a command answers it, don't open a window.

| Asked for | Command |
|---|---|
| Chip, memory, model, serial | `system_profiler SPHardwareDataType` (or `sysctl -n machdep.cpu.brand_string`) |
| macOS version | `sw_vers` |
| Battery | `pmset -g batt` |
| Disk space | `df -h /` |
| Open an app, a file, a URL | `open -a "App"` · `open path` · `open https://…` |
| Open a System Settings pane | `open "x-apple.systempreferences:com.apple.systempreferences.GeneralSettings"` |

Only open the GUI when the person asked to *see* or *change* something on screen.

## Tier 2 — `cu.py`: the whole sequence in one terminal call

`scripts/cu.py` sits next to this file. Use its absolute path.

```bash
CU="python3 <this skill>/scripts/cu.py"
$CU --app "System Settings" --open --click General --click About --read Chip
$CU --app Calculator --open --type "56*123=" --read --shot
$CU --app Safari --url https://en.wikipedia.org/wiki/Rosetta_Stone --wait-for "Rosetta Stone" --click "Ptolemy V Epiphanes" --read Born
$CU --app Safari --fill "Search Wikipedia=Hieroglyphs" --key return --wait-for "Egyptian hieroglyphs"
$CU --app TextEdit --open --menu "File > New" --type "hello" --read hello
$CU --app Finder --click Applications --wait-for Calculator --read Calculator
```

Steps run in the order given:

| Step | Does |
|---|---|
| `--app NAME` | English name, localized name (e.g. 計算機) or bundle id |
| `--open` | launch the app if needed and wait for its window |
| `--window TITLE` | act on the app window whose title contains TITLE (default: the frontmost one with content) |
| `--url URL` | open a URL in the `--app` browser (Safari, Chrome …) |
| `--click TEXT` | click the element whose visible text matches (exact, then prefix, then substring); `--double`, `--right` likewise |
| `--fill LABEL=TEXT` | set a text field found by its label, tooltip or placeholder (or the only field in the toolbar) |
| `--type TEXT` | type into the focused field |
| `--key KEY` | `return`, `escape`, `tab`, or a chord like `cmd+n` |
| `--menu "A > B"` | invoke a menu-bar item by path, e.g. `"File > New"` (`"檔案 > 新增"` on a Chinese system) |
| `--scroll DIR[:N]` | `up`, `down`, `left`, `right`, N notches (default 5) |
| `--wait-for TEXT` | wait up to 15 s until TEXT is on screen (page loads, dialogs) |
| `--wait SEC` | plain pause |
| `--read [FILTER]` | print visible text; with a filter, each match **and the line after it** (label → value, e.g. `Chip | Apple M1`) |
| `--shot` | save the window as a PNG and print its path; send that file when asked for a screenshot |

What it handles for you, so you don't spend turns on it:

- **New windows.** After `--menu`, `--click`, `--key` or `--url`, a window that appeared (a new document, a
  preferences window) becomes the target.
- **Dialogs and sheets.** If `--click` can't find the text in the current window it looks in the app's other
  windows, so `--click Cancel` reaches a confirmation alert.
- **Rows that ignore a press** (Finder's sidebar) get a real mouse click at their centre.
- **Web pages.** Safari exposes the whole page; links, buttons and inputs match by their text. Web inputs are
  filled by typing, because pages ignore direct value writes.
- **Chrome, Edge, Brave, Arc and Electron apps** (Discord, VS Code …) show only their menus until asked;
  `cu.py` asks through `cu-axenable` (see the repository README). Without it you will see a `note` line and
  only menus: use Safari for web pages, or Tier 3.
- **Clicking what is already selected** reports `(no visible change)` and carries on; assert outcomes with
  `--wait-for` or `--read`, not with the click.

Labels are whatever the app shows in the system language: on a Traditional Chinese system it is `--click 一般`,
not `--click General`.

Exit codes: **0** ok. **3** target not found: the output lists the candidates; pick the right one and rerun,
don't take a screenshot to look for it. **4** `--wait-for` timed out. **2** driver error.

A first-run sheet (a privacy notice, "What's New") sits over an app until someone dismisses it. If it asks the
person to agree to something, don't click through it for them.

Measured on the same Mac: System Settings → General → About → read the chip in **12 s**, and Calculator type +
read + screenshot in **4 s**, each as one call. End to end through an agent, the two tasks went from 108 s and
52 s to 28 s and 25 s.

## Tier 3 — step-by-step computer use, only for pixel-only apps

Apps drawn without accessibility text (Flutter apps such as RustDesk, games, canvases) expose empty labels, so
text matching can't work. Use your computer-use tool there: one window capture, click by coordinate, one capture
to confirm. Type instead of clicking keys whenever the app takes keyboard input.

## Never

- **`osascript` / System Events.** It can block for a minute or more waiting on an Apple Event. To check whether
  an app runs, `pgrep -x Name`.
- **`screencapture` from a terminal** — without Screen Recording permission it fails. Use `--shot`.
- **Admin prompts** (an "unlock" button, a lock icon, an installer asking for the password): you don't have the
  password. Stop and tell the person exactly which button needs them.
- Describing a screenshot you did not actually receive.
