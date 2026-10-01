---
name: computer-use-fast
description: Do GUI tasks on a Mac in as few agent turns as possible. Try a shell command first, then run the whole click/type/read sequence in ONE terminal call with scripts/cu.py, and fall back to step-by-step computer use only for apps with no accessibility text. Load before any desktop or app task on macOS.
version: 2.0.0
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
python3 <this skill>/scripts/cu.py --app "System Settings" --open --click General --click About --read Chip
python3 <this skill>/scripts/cu.py --app Calculator --open --type "56*123=" --read --shot
python3 <this skill>/scripts/cu.py --app Safari --key cmd+l --type "example.com" --key return
```

Steps run in the order given:

| Step | Does |
|---|---|
| `--app NAME` | English name, localized name (e.g. 計算機) or bundle id |
| `--open` | launch the app if needed and wait for its window |
| `--url URL` | `open` a URL first (combine with `--app` for the app it opens) |
| `--click TEXT` | click the element whose visible text matches (exact, then prefix, then substring), then confirm the window changed |
| `--type TEXT` | type into the focused field |
| `--key KEY` | `return`, `escape`, `tab`, or a chord like `cmd+n` |
| `--wait SEC` | pause |
| `--read [FILTER]` | print visible text; with a filter, each match **and the line after it** (label → value, e.g. `Chip | Apple M1`) |
| `--shot` | save the window as a PNG and print its path; send that file when asked for a screenshot |

Labels are whatever the app shows in the system language: on a Traditional Chinese system it is `--click 一般`,
not `--click General`.

Exit codes: **0** ok. **3** target not found: the output lists the clickable labels; pick the right one and rerun,
don't take a screenshot to look for it. **4** the click had no visible effect. **2** driver error.

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
