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

## Using `cu.py` directly

```bash
cu.py --app "System Settings" --open --click General --click About --read Chip
cu.py --app Calculator --open --type "56*123=" --read --shot
cu.py --app Safari --key cmd+l --type "example.com" --key return
```

| Step | Does |
|---|---|
| `--app NAME` | English name, localized name (e.g. 計算機) or bundle id |
| `--open` | launch the app if needed and wait for its window |
| `--url URL` | `open` a URL first |
| `--click TEXT` | click the element whose visible text matches (exact, then prefix, then substring); confirm the window changed |
| `--type TEXT` | type into the focused field |
| `--key KEY` | `return`, `escape`, `tab`, or a chord like `cmd+n` |
| `--wait SEC` | pause |
| `--read [FILTER]` | print visible text; with a filter, each match and the line after it (`Chip \| Apple M1`) |
| `--shot` | save the window as PNG and print the path (`CU_SHOT_DIR`, else `~/.hermes/cache/images` if it exists, else the temp folder) |

Labels are in the system language: on a Traditional Chinese system it is `--click 一般`, not `--click General`.

Exit codes: `0` ok · `2` driver error · `3` target not found (the clickable labels are printed) · `4` the click
changed nothing.

## Limits

- Apps without accessibility text (Flutter apps such as RustDesk, games, canvases) can't be matched by text.
  The skill tells the agent to fall back to its own computer-use tool for those.
- Admin prompts (an unlock button, a password dialog) stay with the person: the skill tells the agent to stop and
  say which button needs them. `cu.py` itself has no password handling.
- macOS only.

## License

MIT
