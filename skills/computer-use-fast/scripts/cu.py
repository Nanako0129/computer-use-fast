#!/usr/bin/env python3
"""cu — run a whole GUI sequence in ONE terminal call (no model round-trip per step).

    cu.py --app "System Settings" --open --click General --click About --read Chip
    cu.py --app Calculator --open --type "56*123=" --read --shot
    cu.py --app 計算機 --open --type "1+1=" --read          # localized app names work too
    cu.py --app Safari --key cmd+l --type "example.com" --key return

Steps: --app NAME, --open, --url URL, --click TEXT, --type TEXT, --key KEY (return, cmd+n …),
--wait SECONDS, --read [FILTER], --shot. Needs cua-driver (https://github.com/trycua/cua) with its
macOS permissions granted; set CUA_DRIVER_BIN if it is not in /Applications/CuaDriver.app.

Steps run in the order given. --click matches visible AX text locally (exact > prefix > substring).
Exit codes: 0 ok, 2 usage/driver error, 3 target not found (candidates printed), 4 click had no visible effect.
Pixels-only apps (Flutter, e.g. RustDesk: AX labels are empty) are out of scope: use computer_use there.
"""
import json, os, re, shutil, subprocess, sys, tempfile, time

DRIVER = (os.environ.get("CUA_DRIVER_BIN") or shutil.which("cua-driver")
          or "/Applications/CuaDriver.app/Contents/MacOS/cua-driver")
SKIP_ROLES = {"AXMenuItem", "AXMenuBarItem", "AXMenu", "AXMenuBar"}  # menu bar is in the tree but off-window


class Driver:
    def __init__(self):
        self.p = subprocess.Popen([DRIVER, "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True)
        self.n = 0
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "cu", "version": "1"}})
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"); self.p.stdin.flush()

    def _rpc(self, method, params):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params}) + "\n"); self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("cua-driver exited")
            r = json.loads(line)
            if r.get("id") == self.n:
                return r

    def call(self, tool, **args):
        r = self._rpc("tools/call", {"name": tool, "arguments": args})
        res = r.get("result") or {}
        if "error" in r:
            raise RuntimeError(f"{tool}: {r['error']}")
        sc = res.get("structuredContent")
        if sc is None:
            text = "".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
            try:
                sc = json.loads(text)
            except ValueError:
                sc = {"text": text}
        if res.get("isError"):
            text = "".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
            raise RuntimeError(f"{tool}: {text or json.dumps(sc, ensure_ascii=False)}"[:400])
        return sc


def norm(s):
    return "".join(str(s or "").split()).casefold()


class Session:
    def __init__(self, d):
        self.d, self.pid, self.wid, self.app = d, None, None, None

    def resolve_app(self, name, launch):
        def find(running=True):
            for a in self.d.call("list_apps")["apps"]:
                names = {norm(a.get("name")), norm(a.get("bundle_id")),
                         norm(os.path.basename(a.get("launch_path") or "").removesuffix(".app"))}
                if bool(a.get("running")) == running and norm(name) in names:
                    return a
        a = find()
        if not a or launch:
            # `open -a 計算機` fails (LaunchServices wants the bundle name), and list_apps names a not-running
            # app in English only. Spotlight's display name is localized, so it resolves either spelling.
            installed = a or find(running=False)
            if installed and installed.get("bundle_id"):
                cmd = ["open", "-b", installed["bundle_id"]]
            else:
                q = f'kMDItemDisplayName == "{name.replace(chr(34), "")}*" && kMDItemContentType == com.apple.application-bundle'
                hits = subprocess.run(["mdfind", q], capture_output=True, text=True).stdout.split("\n")
                cmd = ["open", hits[0]] if hits[0] else ["open", "-a", name]
            subprocess.run(cmd, check=False, capture_output=True)
            for _ in range(20):
                a = find()
                if a:
                    break
                time.sleep(0.5)
        if not a:
            raise LookupError(f"app not running and could not be opened: {name}")
        self.pid, self.app = a["pid"], a["name"]
        self.wait_window()

    def wait_window(self, timeout=10.0):
        end = time.time() + timeout
        while time.time() < end:
            wins = [w for w in self.d.call("list_windows")["windows"]
                    if w["pid"] == self.pid and w.get("layer") == 0 and w.get("is_on_screen") and w["bounds"]["height"] > 100]
            if wins:
                self.wid = max(wins, key=lambda w: w.get("z_index", 0))["window_id"]
                return
            time.sleep(0.4)
        raise LookupError(f"{self.app}: no on-screen window after {timeout:.0f}s")

    def snapshot(self):
        st = self.d.call("get_window_state", pid=self.pid, window_id=self.wid, include_screenshot=False)
        return [e for e in st.get("elements", []) if e.get("role") not in SKIP_ROLES and e.get("frame")]

    @staticmethod
    def signature(els):
        return tuple((e.get("role"), e.get("label"), e.get("value"), e.get("selected")) for e in els)

    def click(self, text):
        els = self.snapshot()
        want = norm(text)
        scored = []
        for e in els:
            lab = norm(e.get("label")) or norm(e.get("value"))
            if not lab or want not in lab:
                continue
            rank = 0 if lab == want else 1 if lab.startswith(want) else 2
            scored.append((rank, "AXPress" not in (e.get("actions") or []), len(lab), e))
        if not scored:
            labels = sorted({e.get("label") for e in els if e.get("label") and "AXPress" in (e.get("actions") or [])})
            raise LookupError(f"no element matching {text!r}; clickable: {labels[:40]}")
        scored.sort(key=lambda t: t[:3])
        target = scored[0][3]
        if "AXPress" not in (target.get("actions") or []):  # text inside a pressable container
            by_idx = {e["element_index"]: e for e in els}
            p = target
            while p.get("parent_index") in by_idx and "AXPress" not in (p.get("actions") or []):
                p = by_idx[p["parent_index"]]
            if "AXPress" in (p.get("actions") or []):
                target = p
        before = self.signature(els)
        self.d.call("click", element_token=target["element_token"], pid=self.pid, window_id=self.wid)
        for _ in range(8):  # up to ~3 s for the UI to react
            time.sleep(0.4)
            try:
                self.wait_window(timeout=2)
                if self.signature(self.snapshot()) != before:
                    return target.get("label")
            except LookupError:
                pass
        raise TimeoutError(f"clicked {target.get('label')!r} but the window did not change")

    def read(self, flt=None):
        md = self.d.call("get_window_state", pid=self.pid, window_id=self.wid, include_screenshot=False).get("tree_markdown", "")
        return texts_from_markdown(md, flt)


def texts_from_markdown(md, flt=None):
    """Visible text, in screen order. Plain text (e.g. "Chip" / "Apple M1") is not in `elements`, which holds
    indexed, actionable rows only; it is only in tree_markdown, as `AXStaticText = "…"` / `AXHeading (…)` lines.
    With a filter, each match comes back with the line after it, because a label and its value are adjacent."""
    texts = []
    for ln in md.splitlines():
        if "AXMenu" in ln:  # the menu bar is part of the tree but not of the window
            continue
        for t in re.findall(r'"([^"]+)"', ln) + re.findall(r"AXHeading \(([^)]+)\)", ln):
            t = t.strip()
            if t and t not in texts[-3:]:  # a container often repeats its child's text
                texts.append(t)
    if not flt:
        return list(dict.fromkeys(texts))
    out = []
    for i, t in enumerate(texts):
        if norm(flt) in norm(t):
            out += texts[i:i + 2]
    return list(dict.fromkeys(out))


def shot_dir():
    # cua-driver refuses an output path under a symlink (/tmp, /var), hence realpath.
    d = os.environ.get("CU_SHOT_DIR") or (os.path.expanduser("~/.hermes/cache/images")
                                          if os.path.isdir(os.path.expanduser("~/.hermes")) else tempfile.gettempdir())
    os.makedirs(d, exist_ok=True)
    return os.path.realpath(d)


def parse(argv):
    steps, i = [], 0
    flags = {"--open": 0, "--shot": 0, "--app": 1, "--url": 1, "--click": 1, "--type": 1, "--key": 1, "--wait": 1}
    while i < len(argv):
        a = argv[i]
        if a == "--read":
            nxt = argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith("--") else None
            steps.append(("--read", nxt)); i += 2 if nxt else 1
        elif a in flags:
            if flags[a] and i + 1 >= len(argv):
                sys.exit(f"cu: {a} needs a value")
            steps.append((a, argv[i + 1] if flags[a] else None)); i += 1 + flags[a]
        else:
            sys.exit(f"cu: unknown argument {a!r}\n{__doc__}")
    return steps


def main():
    if not sys.argv[1:] or sys.argv[1] in ("-h", "--help"):
        print(__doc__); return 0
    steps = parse(sys.argv[1:])
    launch = any(k in ("--open", "--url") for k, _ in steps)
    try:
        s = Session(Driver())
    except (OSError, RuntimeError) as e:
        print(f"FAIL cua-driver not usable ({DRIVER}): {e}. Install it or set CUA_DRIVER_BIN."); return 2
    kind = None
    t0 = time.time()
    try:
        for kind, val in steps:
            t = time.time()
            if kind == "--url":
                subprocess.run(["open", val], check=True, capture_output=True)
                note = val
            elif kind == "--app":
                s.resolve_app(val, launch); note = f"{s.app} pid={s.pid} window={s.wid}"
            elif kind == "--open":
                continue
            elif s.pid is None:
                raise LookupError(f"{kind} needs --app first")
            elif kind == "--click":
                note = f"clicked {s.click(val)!r}"
            elif kind == "--type":
                s.d.call("type_text", text=val, pid=s.pid, window_id=s.wid); note = f"typed {len(val)} chars"
            elif kind == "--key":
                *mods, key = val.split("+")
                if mods:
                    s.d.call("hotkey", keys=mods + [key], pid=s.pid, window_id=s.wid)
                else:
                    s.d.call("press_key", key=key, pid=s.pid, window_id=s.wid)
                note = f"key {val}"
            elif kind == "--wait":
                time.sleep(float(val)); note = f"waited {val}s"
            elif kind == "--read":
                time.sleep(0.3)
                texts = s.read(val)
                print(f"[read{' ' + val if val else ''}] " + " | ".join(texts) if texts else f"[read] nothing matching {val!r}")
                note = f"{len(texts)} texts"
            elif kind == "--shot":
                path = os.path.join(shot_dir(), f"cu_{int(time.time())}.png")
                s.d.call("get_window_state", pid=s.pid, window_id=s.wid, include_accessibility_tree=False, screenshot_out_file=path)
                note = f"screenshot {path}"
            print(f"ok   {kind} {note}  ({time.time() - t:.1f}s)")
    except LookupError as e:
        print(f"FAIL {kind} {e}"); return 3
    except TimeoutError as e:
        print(f"FAIL {kind} {e}"); return 4
    except Exception as e:  # driver/transport errors
        print(f"FAIL {kind} {type(e).__name__}: {e}"); return 2
    finally:
        s.d.p.terminate()
    print(f"done in {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
