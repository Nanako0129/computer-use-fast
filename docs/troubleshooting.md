# Troubleshooting

| You see | Cause | Do this |
|---|---|---|
| `FAIL cua-driver not usable (…)` | The driver isn't installed or isn't on `PATH` | [Setup step 1](setup.md#1-install-cua-driver), or set `CUA_DRIVER_BIN` |
| `FAIL --app … app not found or could not be opened` | The name doesn't match an installed app | Use the name shown in Finder, the English name, or the bundle id |
| `FAIL --app … runs only as a menu-bar or background agent` | The app has no windows at all (Amphetamine, Maccy …) | Nothing to drive; use its menu-bar icon yourself |
| `FAIL --app … is running but has no window` | Every window of the app is closed (Spotify, Telegram …) | Reopen a window from its Dock icon or menu, then run again |
| `note … shows only its menus to accessibility clients` | A Chromium or Electron app without the helper | [Setup step 4](setup.md#4-optional-chrome-edge-brave-arc-and-electron-apps) |
| `note not trusted: allow … cu-axenable …` | The helper isn't allowed yet, or was rebuilt | Allow it under Privacy & Security → Accessibility |
| `FAIL --click no element matching '…'; candidates: […]` | The text differs from what is on screen (often another language) | Pick the right name from `candidates` and rerun |
| `FAIL --fill no text field matching '…'` | No field with that label, and more than one unlabelled field | Click the field with `--click`, then `--type` |
| `FAIL --wait-for '…' did not appear within 15s` | The page or dialog didn't show it (yet) | Check the spelling against `--read`, or add `--wait` before it |
| `clicked '…' (no visible change)` | It was already selected, or the click had no effect | Fine if it was already selected; otherwise check with `--read` |
| A "What's New" or privacy sheet covers the app | First launch | Dismiss it yourself if it asks you to agree to something |
| The agent still takes screenshot after screenshot | It didn't load the skill | [Setup step 5](setup.md#5-recommended-tell-the-agent-to-use-it) |
| Apps open and the agent waits a long time | `osascript` / System Events hung | Add the "never use osascript" line from setup step 5 |

## Apps it can't drive

Apps that draw their own interface without readable text (Flutter apps such as RustDesk, games, drawing
canvases) give `cu.py` nothing to match. The skill sends the agent back to its own computer-use tool there:
screenshot, click by coordinate, screenshot to confirm. It works, only slower.

## Things that stay with you

Password prompts, Touch ID, anything under Privacy & Security, and "agree to continue" sheets. The skill tells
the agent to stop and say which button needs you.
