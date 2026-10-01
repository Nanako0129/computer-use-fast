# Command reference

```bash
python3 <skill>/scripts/cu.py STEP [STEP …]
```

Steps run in the order given, inside one process. It stops at the first step that fails and says why.

## Steps

| Step | What it does | Example |
|---|---|---|
| `--app NAME` | Pick the app: English name, localized name or bundle id | `--app Calculator`, `--app 計算機`, `--app com.apple.calculator` |
| `--open` | Launch it if it isn't running and wait for its window (anywhere in the line) | `--app Notes --open` |
| `--window TITLE` | Use the window whose title contains TITLE. Default: the frontmost window that has content | `--window "Downloads"` |
| `--url URL` | Open a web address in the `--app` browser | `--app Safari --url https://example.com` |
| `--click TEXT` | Click the element whose visible text matches | `--click "About"` |
| `--double TEXT` | Double-click it | `--double "report.pdf"` |
| `--right TEXT` | Right-click it | `--right "report.pdf"` |
| `--drag "A > B"` | Drag the element showing A onto the one showing B (moves the real pointer, see below) | `--drag "notes.txt > Archive"` |
| `--fill LABEL=TEXT` | Put TEXT in the field labelled LABEL (label, tooltip or placeholder) | `--fill "Search=groceries"` |
| `--type TEXT` | Type into whatever has focus | `--type "56*123="` |
| `--key KEY` | Press a key or a shortcut | `--key return`, `--key cmd+n` |
| `--menu "A > B"` | Choose a menu-bar item by its path | `--menu "File > New"` |
| `--scroll DIR[:N]` | Scroll `up`, `down`, `left` or `right`, N steps (default 5) | `--scroll down:10` |
| `--wait-for TEXT` | Wait up to 15 s until TEXT is on screen | `--wait-for "Results"` |
| `--wait SEC` | Wait a fixed time | `--wait 2` |
| `--read [FILTER]` | Print the visible text, at most 150 lines; with FILTER, only matching lines | `--read`, `--read Chip` |
| `--read-all` | Print every visible line, however many | `--read-all` |
| `--shot` | Save the window as PNG and print the path | `--shot` |

### How `--click` finds its target

1. Text is compared ignoring case and spaces: an **exact** match wins, then **starts with**, then **contains**.
   Shorter labels win ties. Menu-bar items are ignored.
2. If the matching text sits inside a clickable row or cell, the row is clicked.
3. If it isn't in the current window, the app's other windows are searched, so `--click Cancel` reaches a
   dialog or sheet.
4. Elements that ignore an accessibility "press" (Finder's sidebar rows) get a real mouse click at their centre.

Text is whatever the app shows in your system language: on a Traditional Chinese Mac, `--click 一般`.

### How `--read FILTER` pairs values

On screen a label and its value are neighbours (`Chip`, then `Apple M1`). With a filter, every matching line is
printed together with the line after it: `--read Chip` prints `Chip | Apple M1`.

### Things it handles on its own

- A window that an action opened (File → New, a preferences window) becomes the target.
- Web forms are filled by typing, because web pages ignore values set directly.
- When an app has several windows, keystrokes are delivered with the target window briefly in front.
- Popovers (a "sign in" bubble) are skipped when choosing the default window.
- A window too large to read in 20 s (Music with a big library) is read to depth 10.
- Chromium and Electron apps are asked to expose their content, if the helper from
  [setup step 4](setup.md#4-optional-chrome-edge-brave-arc-and-electron-apps) is installed.

## Background or foreground

`cu.py` drives apps through accessibility actions, so most steps leave the app you are using in front and the
pointer untouched. A few cases need the target window in front for a moment:

| Step | What you see |
|---|---|
| `--click`, `--fill`, `--type`, `--key`, `--read`, `--wait-for` in an open window | Nothing: your front app keeps focus |
| `--menu` for an item that opens a new window (File → New) | The app comes to the front with its new window |
| `--open`, `--url` | Nothing: apps and pages open behind your current app (`open -g`) |
| `--open` for an app whose first window only appears when it is activated (TextEdit) | The app comes to the front |
| `--click` on a row that needs a real mouse click (Finder's sidebar), when a background click is refused | The window comes forward for the click, then your app is put back in front |
| `--type` / `--key` while the app has several windows | The same brief switch, so the keys reach the right window |
| `--drag` | macOS has no background drag: the window comes forward for about a second and **the real pointer moves** to the drop point and stays there |

The measurements are in [benchmarks.md](benchmarks.md#5-does-it-take-over-the-screen). Check your own with
`python3 scripts/watch_focus.py -- python3 scripts/cu.py …`, which samples the front app and pointer every 50 ms
without going through cua-driver.

## Output

One line per step, then a total:

```
ok   --app 系統設定 pid=17858 window=1018  (2.7s)
ok   --click clicked '一般'  (5.0s)
ok   --click clicked '關於本機'  (4.1s)
[read 晶片] 晶片 | Apple M1
ok   --read 2 texts  (0.7s)
done in 12.4s
```

A click that changes nothing (the pane is already open) prints `(no visible change)` and continues. Use
`--wait-for` or `--read` to check an outcome.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Every step done |
| `2` | cua-driver missing or failing |
| `3` | Something wasn't found. The line lists what **is** there (`candidates: […]`), so pick a name from it and rerun |
| `4` | `--wait-for` gave up after 15 s |

## Environment variables

| Variable | Default |
|---|---|
| `CUA_DRIVER_BIN` | `cua-driver` on `PATH`, else `/Applications/CuaDriver.app/Contents/MacOS/cua-driver` |
| `CU_SHOT_DIR` | `~/.hermes/cache/images` if `~/.hermes` exists, else the system temp folder |
| `CU_AXENABLE` | `~/.local/share/computer-use-fast/cu-axenable` |
