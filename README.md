# computer-use-fast

> An agent skill that makes GUI tasks on a Mac take one or two agent turns instead of a dozen: a shell command when
> one answers the question, otherwise a single `cu.py` call that opens the app, clicks by visible text, types,
> reads the screen and takes a screenshot.

[繁體中文說明](./README.zh-TW.md)

## Why

When an agent drives a Mac step by step, almost none of the time goes to the clicks. On a MacBook Air (M1),
"open System Settings → General → About and tell me the chip" took 108 s: the tools ran for 4.6 s, the model
turns between them took about 97 s. Every screenshot, every click and every "what next?" is another turn.

`cu.py` runs the whole sequence locally in one call, matching buttons by their accessibility text, so the
agent spends one turn instead of six.

| Task, end to end through an agent (Hermes, `gemini-3.8-flash`) | Step by step | With this skill |
|---|---|---|
| System Settings → General → About, read the chip, screenshot | 108 s | 28 s |
| Calculator: type `56*123=`, read the result, screenshot | 52 s | 25 s |

One run each, on one machine; your numbers will depend on your model's latency.

### Compared with a Jev-based skill

[jev-computer-use](https://github.com/kerpopule/hermes-jev-skills) speeds up the same problem from the other
end: a small model (TypeSafe Jev) picks each next action in about 0.3 s instead of the agent's main model.
Measured on the same machine, same agent, same task (System Settings → General → About, "what chip?"):

| | Time | Tool calls |
|---|---|---|
| Step by step, no skill | 108.6 s | 5 |
| jev-computer-use | 265.2 s | 13 |
| jev-computer-use with its `--plan` key set | 94.4 s | — (the runner failed twice; the agent finished by hand) |
| **this skill** | **27.8 s** | 2 |

Jev's choices were fast and accurate (confidence 0.98–0.99 on the right element); the time went to the turns
around them: the agent still wrote each command, read each result and re-tried when the runner stopped. One
`cu.py` call removes those turns instead. It also needs no API key. One run each; your numbers will differ.

## Requirements

| | |
|---|---|
| macOS | tested on macOS 27 (Apple Silicon) |
| Python | 3.9 or newer, no packages |
| [cua-driver](https://github.com/trycua/cua) | `CuaDriver.app` in `/Applications`, with Accessibility and Screen Recording granted (`cua-driver permissions grant`) |

`cu.py` starts `cua-driver mcp` itself. If the driver lives somewhere else, set `CUA_DRIVER_BIN`.

## Install

### Hermes Agent

```bash
hermes skills install Nanako0129/computer-use-fast/skills/computer-use-fast
```

Hermes tracks it from then on: `hermes skills check` reports when a new version is out and
`hermes skills update` installs it. Add `--category <folder>` to choose
which category folder it goes into.

### Claude Code

```bash
git clone https://github.com/Nanako0129/computer-use-fast ~/src/computer-use-fast
mkdir -p ~/.claude/skills
cp -R ~/src/computer-use-fast/skills/computer-use-fast ~/.claude/skills/
```

To update: `git -C ~/src/computer-use-fast pull`, then run the `cp -R` line again.

### Any other agent that reads `SKILL.md`

Copy `skills/computer-use-fast/` into that agent's skills folder. The skill calls its script as
`scripts/cu.py` next to `SKILL.md`, so keep the two together.

### Check that it works

Replace `<skill>` with the folder you installed to (for example `~/.claude/skills/computer-use-fast`).

```bash
python3 <skill>/scripts/test_cu.py     # no driver needed, prints "ok"
python3 <skill>/scripts/cu.py --app Calculator --open --type "1+1=" --read
```

The second command should open Calculator and print a line containing `2`.

### Chrome, Edge, Brave, Arc and Electron apps (optional)

Chromium browsers and Electron apps (Discord, VS Code …) show only their menu bar to accessibility clients until
one asks them to build the rest. `cu.py` asks through a 20-line helper, which macOS only lets run after you allow
it once:

```bash
mkdir -p ~/.local/share/computer-use-fast
swiftc -O <skill>/scripts/axenable.swift -o ~/.local/share/computer-use-fast/cu-axenable
~/.local/share/computer-use-fast/cu-axenable 1   # prints "not trusted: …" the first time
```

Then open **System Settings → Privacy & Security → Accessibility**, press **+**, press **⌘⇧G**, paste
`~/.local/share/computer-use-fast/cu-axenable` and make sure its switch is on. The binary lives outside the skill
folder on purpose: updating the skill must not replace the file you allowed. Rebuilding it does, so allow it again
after a rebuild. Without the helper, `cu.py` prints a `note` and Safari remains the browser to use.

## Using `cu.py` directly

```bash
cu.py --app "System Settings" --open --click General --click About --read Chip
cu.py --app Calculator --open --type "56*123=" --read --shot
cu.py --app Safari --url https://en.wikipedia.org/wiki/Rosetta_Stone --wait-for "Rosetta Stone" --click "Ptolemy V Epiphanes" --read Born
cu.py --app Safari --fill "Search Wikipedia=Hieroglyphs" --key return --wait-for "Egyptian hieroglyphs"
cu.py --app TextEdit --open --menu "File > New" --type "hello" --read hello
cu.py --app Finder --click Applications --wait-for Calculator --read Calculator
```

| Step | Does |
|---|---|
| `--app NAME` | English name, localized name (e.g. 計算機) or bundle id |
| `--open` | launch the app if needed and wait for its window |
| `--window TITLE` | act on the window whose title contains TITLE (default: the frontmost window with content) |
| `--url URL` | open a URL in the `--app` browser |
| `--click TEXT` | click the element whose visible text matches (exact, then prefix, then substring); `--double`, `--right` likewise |
| `--fill LABEL=TEXT` | set a text field found by its label, tooltip or placeholder, or the only field in the toolbar |
| `--type TEXT` | type into the focused field |
| `--key KEY` | `return`, `escape`, `tab`, or a chord like `cmd+n` |
| `--menu "A > B"` | invoke a menu-bar item by its path |
| `--scroll DIR[:N]` | `up` / `down` / `left` / `right`, N notches (default 5) |
| `--wait-for TEXT` | wait up to 15 s until TEXT is on screen |
| `--wait SEC` | plain pause |
| `--read [FILTER]` | print visible text; with a filter, each match and the line after it (`Chip \| Apple M1`) |
| `--shot` | save the window as PNG and print the path (`CU_SHOT_DIR`, else `~/.hermes/cache/images` if it exists, else the temp folder) |

Along the way it switches to a window that an action opened, looks in the app's other windows (dialogs, sheets)
when a `--click` target isn't in the current one, mouse-clicks rows that ignore an accessibility press (Finder's
sidebar), and fills web inputs by typing because pages ignore direct value writes.

Labels are in the system language: on a Traditional Chinese system it is `--click 一般`, not `--click General`.

Exit codes: `0` ok · `2` driver error · `3` target not found (the candidates are printed) · `4` `--wait-for`
timed out. Clicking something already selected prints `(no visible change)` and continues.

## Tested apps

Every app on one MacBook Air (macOS 27, Traditional Chinese), opened and read once with `--open --read`
(2026-10-01): **57 of 75** read fine, among them Safari, Chrome (with `cu-axenable`), Discord, VS Code,
Claude, Microsoft Word/Excel/PowerPoint, Keynote, Mail, Notes, Contacts, Calendar, Finder, System Settings,
Automator, Preview and Music. Seven were skipped on purpose (VPN clients, virtual machines, apps that turn
the camera on). The rest:

| Kind | Apps | What `cu.py` says |
|---|---|---|
| Menu-bar or background agents | Amphetamine, Maccy, ZeroTier, LogiPluginService … | "runs only as a menu-bar or background agent" |
| Running with every window closed | Spotify, Telegram, Freeform, Stickies | "running but has no window" |
| Flutter, drawn without accessibility text | RustDesk, Cloudflare WARP | use step-by-step computer use |
| Not windowed apps at all | Mission Control, Time Machine, Apps | — |

## Limits

- Apps without accessibility text (Flutter apps such as RustDesk, games, canvases) can't be matched by text.
  The skill tells the agent to fall back to its own computer-use tool for those.
- Very large trees are read shallowly: when a full walk passes the driver's 20 s budget (Music with a big
  library), `cu.py` retries at depth 10, which keeps the sidebar and toolbar.
- Admin prompts (an unlock button, a password dialog) stay with the person: the skill tells the agent to stop and
  say which button needs them. `cu.py` itself has no password handling.
- macOS only.

## License

MIT
