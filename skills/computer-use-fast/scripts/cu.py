#!/usr/bin/env python3
"""cu — run a whole GUI sequence in ONE terminal call (no model round-trip per step).

    cu.py --app "System Settings" --open --click General --click About --read Chip
    cu.py --app Calculator --open --type "56*123=" --read --shot
    cu.py --app 計算機 --open --type "1+1=" --read          # localized app names work too
    cu.py --app Safari --open --url https://example.com --wait-for "Example Domain" --click "More information"
    cu.py --app TextEdit --open --menu "File > New" --type "hello" --read
    cu.py --app Notes --fill "Search=groceries" --key return --read

Steps (run in the order given):
  --app NAME          English name, localized name or bundle id; --open launches it if needed
  --window TITLE      act on the window whose title contains TITLE (default: frontmost window of the app)
  --url URL           open a URL (in the --app browser if one is set, else the default handler)
  --click TEXT        click the element whose visible text matches; --double TEXT / --right TEXT likewise
  --fill LABEL=TEXT   set a text field found by its label or placeholder
  --type TEXT         type into the focused field;  --key KEY: return, tab, escape, cmd+n …
  --menu "A > B > C"  invoke a menu-bar item by its path
  --scroll DIR[:N]    up / down / left / right, N notches (default 5)
  --wait-for TEXT     wait (up to 15 s) until TEXT is visible;  --wait SECONDS: plain pause
  --read [FILTER]     print visible text (first 150 lines); with FILTER, each match and the line after it
  --read-all          print all visible text, however long
  --drag "A > B"      drag the element showing text A onto the one showing text B
  --shot              save the window as PNG and print its path

Text matching is local (exact > prefix > substring) over the app's accessibility tree, menus excluded.
Exit codes: 0 ok, 2 usage/driver error, 3 target not found (candidates printed), 4 action had no visible effect.
Needs cua-driver (https://github.com/trycua/cua) with its permissions granted; CUA_DRIVER_BIN overrides
its path. Apps with no accessibility text (Flutter apps such as RustDesk, games) are out of scope.
"""
import json, os, re, shutil, subprocess, sys, tempfile, time

DRIVER = (os.environ.get("CUA_DRIVER_BIN") or shutil.which("cua-driver")
          or "/Applications/CuaDriver.app/Contents/MacOS/cua-driver")
SKIP_ROLES = {"AXMenuItem", "AXMenuBarItem", "AXMenu", "AXMenuBar"}  # menu bar is in the tree but off-window
FIELD_ROLES = {"AXTextField", "AXTextArea", "AXComboBox", "AXSearchField", "AXSecureTextField"}
# Web pages run to thousands of nodes; the driver's default (2 000 nodes, depth 25) cut a Wikipedia article
# off inside its table of contents. 10 000 / 60 read the whole Rosetta Stone article in 1.7 s.
WALK = {"max_elements": 10000, "max_depth": 60}
# --read output goes straight into the agent's context: a Wikipedia page in Safari came back as 2 165 lines.
READ_LIMIT = 150
# Chromium browsers and Electron apps expose their content only after an assistive client sets
# AXManualAccessibility; scripts/axenable.swift does that, built outside the skill folder so that updating the
# skill doesn't replace the binary the person granted Accessibility to.
AXENABLE = os.environ.get("CU_AXENABLE") or os.path.expanduser("~/.local/share/computer-use-fast/cu-axenable")
CHROMIUM = {"com.google.Chrome", "com.google.Chrome.beta", "com.google.Chrome.canary", "org.chromium.Chromium",
            "com.microsoft.edgemac", "com.brave.Browser", "company.thebrowser.Browser", "com.vivaldi.Vivaldi",
            "com.operasoftware.Opera"}


class Driver:
    def __init__(self):
        self.p = subprocess.Popen([DRIVER, "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True)
        self.n = 0
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "cu", "version": "2"}})
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
        if "error" in r:
            raise RuntimeError(f"{tool}: {r['error']}")
        res = r.get("result") or {}
        text = "".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
        if res.get("isError"):
            raise RuntimeError(f"{tool}: {text or res.get('structuredContent')}"[:400])
        sc = res.get("structuredContent")
        if sc is None:
            try:
                sc = json.loads(text)
            except ValueError:
                sc = {"text": text}
        return sc


def norm(s):
    return "".join(str(s or "").split()).casefold()


def texts_from_markdown(md, flt=None):
    """Visible text, in screen order. Plain text (e.g. "Chip" / "Apple M1") is not in `elements`, which holds
    indexed, actionable rows only; it is only in tree_markdown, as `AXStaticText = "…"` / `AXHeading (…)` lines.
    With a filter, each match comes back with the line after it, because a label and its value are adjacent."""
    texts = []
    for ln in md.splitlines():
        if "AXMenu" in ln:  # the menu bar is part of the tree but not of the window
            continue
        ln = re.sub(r'\[(?:id|help)="[^"]*"', "", ln)  # attribute values are not on-screen text
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


def best_match(els, text, roles=None, action="AXPress"):
    """The element `text` most likely names: exact > prefix > substring over label, value and help, preferring
    elements that can take `action`. Text sitting inside a pressable container resolves to the container."""
    want, scored = norm(text), []
    for e in els:
        if e.get("role") in SKIP_ROLES or (roles and e.get("role") not in roles):
            continue
        for rank_base, field in ((0, "label"), (0, "value"), (3, "help"), (3, "placeholder")):
            lab = norm(e.get(field))
            if lab and want in lab:
                rank = rank_base + (0 if lab == want else 1 if lab.startswith(want) else 2)
                scored.append((rank, action not in (e.get("actions") or []), len(lab), e["element_index"], e))
                break
    if not scored:
        return None
    scored.sort(key=lambda t: t[:4])
    target = scored[0][4]
    if action and action not in (target.get("actions") or []):
        by_idx = {e["element_index"]: e for e in els}
        p = target
        while p.get("parent_index") in by_idx and action not in (p.get("actions") or []):
            p = by_idx[p["parent_index"]]
        if action in (p.get("actions") or []):
            target = p
    return target


def owner_of_text(st, text):
    """Text that is not an indexed element of its own (a Finder sidebar row's `AXStaticText = "Applications"`
    is only a markdown line) belongs to the nearest indexed ancestor line above it; return that element."""
    by_idx = {e["element_index"]: e for e in st.get("elements", [])}
    stack, want = [], norm(text)
    for ln in st.get("tree_markdown", "").splitlines():
        if "AXMenu" in ln:
            continue
        indent = len(ln) - len(ln.lstrip())
        while stack and stack[-1][0] >= indent:
            stack.pop()
        m = re.match(r"\s*- \[(\d+)\]", ln)
        if m:
            stack.append((indent, int(m.group(1))))
            continue
        quoted = re.findall(r'"([^"]+)"', ln)
        if stack and any(want == norm(q) for q in quoted):
            return by_idx.get(stack[-1][1])
    return None


def shot_dir():
    # cua-driver refuses an output path under a symlink (/tmp, /var), hence realpath.
    d = os.environ.get("CU_SHOT_DIR") or (os.path.expanduser("~/.hermes/cache/images")
                                          if os.path.isdir(os.path.expanduser("~/.hermes")) else tempfile.gettempdir())
    os.makedirs(d, exist_ok=True)
    return os.path.realpath(d)


class Session:
    def __init__(self, d):
        self.d, self.pid, self.wid, self.app, self.bundle, self.window_title = d, None, None, None, None, None

    # ---- targeting ---------------------------------------------------------------------------------------
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
                cmd = ["open", "-g", "-b", installed["bundle_id"]]
            else:
                # Exact name first: "音樂*" alone matched 音樂辨識 (MusicRecognitionMac) before 音樂 (Music).
                hit = ""
                for pattern in (f"{name}.app", f"{name}*"):
                    q = f'kMDItemDisplayName == "{pattern.replace(chr(34), "")}" && kMDItemContentType == com.apple.application-bundle'
                    hit = subprocess.run(["mdfind", q], capture_output=True, text=True).stdout.split("\n")[0]
                    if hit:
                        break
                cmd = ["open", "-g", hit] if hit else ["open", "-g", "-a", name]
            # -g: launch without bringing the app forward, so the person's front app keeps focus.
            subprocess.run(cmd, check=False, capture_output=True)
            for _ in range(20):
                a = find()
                if a:
                    break
                time.sleep(0.5)
        if not a:
            agent = subprocess.run(["pgrep", "-if", f"/{name}.app/"], capture_output=True).returncode == 0
            raise LookupError(f"{name} runs only as a menu-bar or background agent: it has no windows to drive"
                              if agent else f"app not found or could not be opened: {name}")
        self.pid, self.app, self.bundle = a["pid"], a["name"], a.get("bundle_id")
        try:
            self.wait_window(timeout=10 if not launch else 6)
        except LookupError:
            if not launch:
                raise
            # Some apps create their first window only when brought forward (TextEdit shows its open panel on
            # activation, nothing when launched with -g). Finishing the task beats keeping focus here.
            subprocess.run(["open", "-b", self.bundle] if self.bundle else ["open", "-a", name], capture_output=True)
            self.wait_window()
        path = a.get("launch_path") or ""
        if self.bundle in CHROMIUM or os.path.isdir(os.path.join(path, "Contents/Frameworks/Electron Framework.framework")):
            self.expose_chromium()

    def expose_chromium(self):
        if "AXWebArea" in self.state(query="AXWebArea").get("tree_markdown", ""):
            return
        if not os.path.exists(AXENABLE):
            print(f"note {self.app} shows only its menus to accessibility clients; build scripts/axenable.swift "
                  f"to {AXENABLE} and allow it under Privacy & Security > Accessibility to read its pages")
            return
        r = subprocess.run([AXENABLE, str(self.pid)], capture_output=True, text=True)
        if "not trusted" in r.stdout:
            print(f"note {r.stdout.strip()}")
            return
        # Chrome answers both attribute writes with an error (-25205 / -25208) and still switches its
        # accessibility on (chrome://accessibility then reports VoiceOver as active), so judge by the tree.
        for _ in range(10):  # Chromium builds the tree asynchronously
            time.sleep(0.5)
            if "AXWebArea" in self.state(query="AXWebArea").get("tree_markdown", ""):
                return
        print(f"note {self.app} still exposes no web content ({r.stdout.strip()})")

    def wait_window(self, timeout=10.0):
        end = time.time() + timeout
        while time.time() < end:
            wins = [w for w in self.d.call("list_windows")["windows"]
                    if w["pid"] == self.pid and w.get("layer") == 0 and w.get("is_on_screen") and w["bounds"]["height"] > 100]
            if self.window_title:
                wins = [w for w in wins if norm(self.window_title) in norm(w.get("title"))] or wins
            if wins:
                self.wid = self.pick_window(wins)
                self.bounds = next(w["bounds"] for w in wins if w["window_id"] == self.wid)
                return
            time.sleep(0.4)
        raise LookupError(f"{self.app} is running but has no window: a menu-bar app, or its window was closed "
                          f"(reopen it from the app's menu or Dock); nothing here for cu.py to drive")

    def pick_window(self, wins):
        """The frontmost window (highest z_index) that has content of its own. Finder keeps tabs as separate
        windows and left two empty shells, holding only the menu bar, above the tab in view; those are skipped.
        Picking by "most content" instead chose an arbitrary one of three blank TextEdit documents."""
        wins = sorted(wins, key=lambda w: -(w.get("z_index") or 0))
        # Popovers float above the window they belong to (Chrome's "sign in to Google" bubble, 362x148 over a
        # 1680x1019 window, had the highest z_index). Dialogs are small too, but --click reaches them anyway
        # through find_elsewhere, so the default target is a full-size window.
        area = lambda w: w["bounds"]["width"] * w["bounds"]["height"]
        big = max(area(w) for w in wins)
        wins = [w for w in wins if area(w) >= big / 4]
        if len(wins) == 1:
            return wins[0]["window_id"]
        for w in wins[:4]:
            st = self.d.call("get_window_state", pid=self.pid, window_id=w["window_id"], include_screenshot=False,
                             max_elements=60, max_depth=6)
            if sum(1 for e in st.get("elements", []) if e.get("frame") and e.get("role") not in SKIP_ROLES) >= 2:
                return w["window_id"]
        return wins[0]["window_id"]

    # ---- observation -------------------------------------------------------------------------------------
    def state(self, query=None):
        args = dict(WALK, pid=self.pid, window_id=self.wid, include_screenshot=False)
        if query:
            args["query"] = query
        try:
            return self.d.call("get_window_state", **args)
        except RuntimeError as e:
            if "not a live window" in str(e) or "window_id_not_found" in str(e):
                # The window was replaced under us (Finder reopening a folder): pick the current one, retry.
                self.wait_window()
                args["window_id"] = self.wid
                return self.d.call("get_window_state", **args)
            if "timed out" not in str(e):
                raise
            # Music ran the driver's 20 s walk budget out; depth is what costs (1 500 / 25 still timed out,
            # 400 / 15 took 17 s, 200 / 10 took 2.6 s) and the shallow part (sidebar, toolbar) is what is needed.
            args.update(max_elements=200, max_depth=10)
            return self.d.call("get_window_state", **args)

    def elements(self, query=None):
        self.last = self.state(query).get("elements", [])  # kept so callers can walk a hit's ancestors
        return [e for e in self.last if e.get("frame") or e.get("role") == "AXWindow"]

    def in_web_page(self, el):
        by_idx = {e["element_index"]: e for e in self.last}
        while el is not None:
            if el.get("role") == "AXWebArea":
                return True
            el = by_idx.get(el.get("parent_index"))
        return False

    def signature(self):
        # The first 300 nodes are enough to see a page or pane change (window title, sidebar selection, top of
        # the content) and cost a fraction of a full walk: a full walk of a Wikipedia article is ~1.5 s.
        st = self.d.call("get_window_state", pid=self.pid, window_id=self.wid, include_screenshot=False,
                         max_elements=300, max_depth=20)
        return tuple((e.get("role"), e.get("label"), e.get("value"), e.get("selected")) for e in st.get("elements", []))

    def find(self, text, roles=None, action="AXPress"):
        # Ask the driver to project the tree onto `text` first (ancestors kept, indices unchanged): far less to
        # ship than a 4 000-node web page. Fall back to the whole tree for matches the projection misses.
        st = self.state(query=text)
        els = [e for e in st.get("elements", []) if e.get("frame") or e.get("role") == "AXWindow"]
        target = best_match(els, text, roles, action) or owner_of_text(st, text) or self.find_elsewhere(text, roles, action)
        if target is None:
            els = self.elements()
            pool = [e for e in els if (roles and e.get("role") in roles) or (not roles and action in (e.get("actions") or []))]
            labels = sorted({e.get("label") or e.get("help") for e in pool
                             if (e.get("label") or e.get("help")) and not str(e.get("label")).startswith("_NS:")})
            raise LookupError(f"no element matching {text!r}; candidates: {labels[:40]}")
        return target

    def act(self, tool, **args):
        """A window-addressed action. If the window went away underneath us (a sheet closed, File > New replaced
        an open panel), re-pick the window and try once more."""
        try:
            return self.d.call(tool, pid=self.pid, window_id=self.wid, **args)
        except RuntimeError as e:
            if "same_pid_keyboard_ambiguity" in str(e):
                # Two windows of one app (an open panel next to a new document): background key events can't
                # be proven to reach ours, so briefly bring it forward.
                return self.d.call(tool, pid=self.pid, window_id=self.wid, delivery_mode="foreground", **args)
            if not any(k in str(e) for k in ("off_space_or_ax_unresolved", "window_id_not_found", "not among")):
                raise
            time.sleep(0.5)
            self.wait_window()
            return self.d.call(tool, pid=self.pid, window_id=self.wid, **args)

    def window_ids(self):
        return {w["window_id"] for w in self.d.call("list_windows")["windows"]
                if w["pid"] == self.pid and w.get("layer") == 0 and w.get("is_on_screen") and w["bounds"]["height"] > 100}

    def adopt_new_window(self, before, seconds=2.0):
        """After an action that can open a window (File > New, a Preferences click, cmd+n), switch to the window
        that appeared. Without this, typing went to the new document while reading looked at the old one."""
        end = time.time() + seconds
        while time.time() < end:
            new = self.window_ids() - before
            if new:
                time.sleep(0.3)  # let it finish drawing
                wins = [w for w in self.d.call("list_windows")["windows"] if w["window_id"] in new]
                if wins:
                    self.wid = self.pick_window(wins)
                    self.bounds = next(w["bounds"] for w in wins if w["window_id"] == self.wid)
                    self.scale = None
                    return True
            time.sleep(0.25)
        return False

    def keep_window(self):
        """Stay on the current window while it exists; re-pick only when it closed (a sheet or dialog went away,
        a navigation replaced it). Re-picking probes every stacked window, which is what made polling slow."""
        if not any(w["window_id"] == self.wid and w.get("is_on_screen") for w in self.d.call("list_windows")["windows"]):
            self.wait_window(timeout=2)

    def find_elsewhere(self, text, roles, action):
        """Not in this window: look in the app's other windows, then switch to the one that has it. A quit
        confirmation alert sat on top of TextEdit's documents with a LOWER z_index than one of them, so stacking
        order alone can't find dialogs; their names (提示, Alert …) are localized, so they can't be named either."""
        wins = [w for w in self.d.call("list_windows")["windows"]
                if w["pid"] == self.pid and w["window_id"] != self.wid and w.get("layer") == 0 and w.get("is_on_screen")
                and w["bounds"]["height"] > 60]
        for w in sorted(wins, key=lambda w: w["bounds"]["width"] * w["bounds"]["height"]):  # dialogs are small
            st = self.d.call("get_window_state", pid=self.pid, window_id=w["window_id"], include_screenshot=False,
                             query=text, **WALK)
            els = [e for e in st.get("elements", []) if e.get("frame")]
            hit = best_match(els, text, roles, action) or owner_of_text(st, text)
            if hit:
                self.wid, self.bounds, self.scale = w["window_id"], w["bounds"], None
                return hit
        return None

    def changed_since(self, before, seconds=3.0):
        end = time.time() + seconds
        while time.time() < end:
            time.sleep(0.3)
            try:
                self.keep_window()
                if self.signature() != before:
                    return True
            except LookupError:
                pass
        return False

    # ---- actions -----------------------------------------------------------------------------------------
    def press(self, text, tool="click"):
        before = self.signature()
        target = self.find(text)  # must be the last snapshot before acting: a newer one makes its token stale
        if "AXPress" in (target.get("actions") or []) or not target.get("frame"):
            self.d.call(tool, element_token=target["element_token"], pid=self.pid, window_id=self.wid)
        else:
            # Rows and cells (Finder's sidebar) ignore an accessibility press and only react to a real mouse
            # click, so click the centre of the element's frame instead.
            try:
                x, y = self.to_pixels(target["frame"])
                self.d.call(tool, x=x, y=y, pid=self.pid, window_id=self.wid)
            except RuntimeError as e:
                if "off_space_or_ax_unresolved" not in str(e):
                    raise
                # The driver won't post a background pixel click into this window (Finder after Time Machine
                # had covered the screen); a foreground click brings the window forward for the click.
                x, y = self.to_pixels(target["frame"])
                self.d.call(tool, x=x, y=y, pid=self.pid, window_id=self.wid, delivery_mode="foreground")
        label = target.get("label") or target.get("help") or target.get("role")
        # Clicking what is already selected (the pane that is already open) legitimately changes nothing, so this
        # is reported, not fatal; --wait-for or --read is how a sequence asserts the outcome it needs.
        return label if self.changed_since(before) else f"{label} (no visible change)"

    def drag(self, spec):
        src, sep, dst = spec.partition(">")
        if not sep:
            raise LookupError('--drag needs "FROM > TO"')
        a = self.find(src.strip(), action=None)
        b = self.find(dst.strip(), action=None)
        (x1, y1), (x2, y2) = self.to_pixels(a["frame"]), self.to_pixels(b["frame"])
        before = self.signature()
        # cua-driver refuses background drags on macOS ("Background drag is unavailable"): a drag-and-drop has to
        # go through the window server, so the window comes forward for the gesture.
        self.act("drag", from_x=x1, from_y=y1, to_x=x2, to_y=y2, duration_ms=600, steps=24, delivery_mode="foreground")
        label = f"{a.get('label') or a.get('role')} -> {b.get('label') or b.get('role')}"
        return label if self.changed_since(before) else f"{label} (no visible change)"

    def fill(self, spec):
        label, sep, value = spec.partition("=")
        if not sep:
            raise LookupError("--fill needs LABEL=TEXT")
        field = self.find_field(label)
        tok = dict(element_token=field["element_token"], pid=self.pid, window_id=self.wid)
        if not self.in_web_page(field):
            try:  # native fields take an AXValue write directly
                self.d.call("set_value", value=value, **tok)
                return field.get("label") or field.get("help")
            except RuntimeError:
                pass
        # Web inputs ignore AXValue writes (the page never sees an input event), so focus, select all, type.
        self.d.call("click", **tok)
        self.act("hotkey", keys=["cmd", "a"])
        self.act("type_text", text=value)
        return field.get("label") or field.get("help")

    def to_pixels(self, frame):
        """Screen points (AX frames) -> pixels of this window's screenshot, which is what x/y clicks take."""
        if not getattr(self, "scale", None):
            st = self.d.call("get_window_state", pid=self.pid, window_id=self.wid, include_accessibility_tree=False)
            # Not screenshot_scale: the PNG is also downscaled to the driver's max_image_dimension (1568), so a
            # 942-pt Finder window came back 1467 px wide (1.56), while screenshot_scale said 2.0.
            self.scale = st["screenshot_width"] / self.bounds["width"]
        return ((frame["x"] + frame["w"] / 2 - self.bounds["x"]) * self.scale,
                (frame["y"] + frame["h"] / 2 - self.bounds["y"]) * self.scale)

    def find_field(self, label, reveal_tried=False):
        """A text field by its label, tooltip or placeholder. Many native fields carry no text at all (Activity
        Monitor's search box is labelled `_NS:147`), so when nothing matches fall back to the only field in the
        toolbar, then to the only field in the window."""
        hit = best_match(self.elements(query=label), label, FIELD_ROLES, None)
        if hit:
            return hit
        # Some search fields only exist after their button is pressed (App Store's sidebar 搜尋/Search).
        button = best_match(self.elements(query=label), label, None, "AXPress") if not reveal_tried else None
        # Exact or prefix only: a substring match once pressed a long privacy-notice button that merely
        # mentioned 搜尋 in its description.
        name = norm(button.get("label") or button.get("help")) if button else ""
        if button and button.get("role") not in FIELD_ROLES and name.startswith(norm(label)):
            self.d.call("click", element_token=button["element_token"], pid=self.pid, window_id=self.wid)
            time.sleep(1.0)
            return self.find_field(label, reveal_tried=True)
        # The projection matches markdown lines, so querying a role name returns just those fields + ancestors.
        # One query per snapshot, and return from that snapshot: a later get_window_state makes its tokens stale.
        fields = []
        for q in ("AXTe", "AXSearchField"):  # "AXTe" covers AXTextField and AXTextArea
            els = self.elements(query=q)
            # AXTextArea is left out of the guess: a lone text area is as often read-only prose as an input.
            fields = [e for e in els if e.get("role") in FIELD_ROLES - {"AXTextArea"}]
            toolbars = {e["element_index"] for e in els if e.get("role") == "AXToolbar"}
            for pool in ([f for f in fields if f.get("parent_index") in toolbars], fields):
                if len(pool) == 1:
                    return pool[0]
            if fields:
                break
        raise LookupError(f"no text field matching {label!r}; fields: "
                          f"{[f.get('label') or f.get('help') or f.get('value') for f in fields][:20]}")

    def wait_for(self, text, seconds=15.0):
        end = time.time() + seconds
        while time.time() < end:
            try:
                self.keep_window()
                if texts_from_markdown(self.state(query=text).get("tree_markdown", ""), text):
                    return
            except LookupError:
                pass
            time.sleep(0.5)
        raise TimeoutError(f"{text!r} did not appear within {seconds:.0f}s")

    def read(self, flt=None):
        return texts_from_markdown(self.state().get("tree_markdown", ""), flt)


def parse(argv):
    steps, i = [], 0
    flags = {"--open": 0, "--shot": 0, "--app": 1, "--window": 1, "--url": 1, "--click": 1, "--double": 1,
             "--right": 1, "--fill": 1, "--type": 1, "--key": 1, "--menu": 1, "--scroll": 1, "--wait": 1,
             "--wait-for": 1, "--drag": 1, "--read-all": 0}
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


def run_step(s, kind, val):
    if kind in ("--menu", "--click", "--double", "--key", "--url") and s.pid:
        before = s.window_ids()
        note = _run_step(s, kind, val)
        if s.adopt_new_window(before, seconds=2.0 if kind in ("--menu", "--key", "--url") else 0.8):
            note += f"  → new window {s.wid}"
        return note
    return _run_step(s, kind, val)


def _run_step(s, kind, val):
    if kind == "--url":
        if s.bundle:
            subprocess.run(["open", "-g", "-b", s.bundle, val], check=True, capture_output=True)
            s.wait_window()
        else:
            subprocess.run(["open", "-g", val], check=True, capture_output=True)
        return val
    if kind == "--window":
        s.window_title = val
        if s.pid:
            s.wait_window()
        return f"window {s.wid}"
    if s.pid is None:
        raise LookupError(f"{kind} needs --app first")
    if kind == "--click":
        return f"clicked {s.press(val)!r}"
    if kind == "--double":
        return f"double-clicked {s.press(val, 'double_click')!r}"
    if kind == "--right":
        target = s.find(val)
        s.d.call("right_click", element_token=target["element_token"], pid=s.pid, window_id=s.wid)
        return f"right-clicked {target.get('label')!r}"
    if kind == "--fill":
        return f"filled {s.fill(val)!r}"
    if kind == "--drag":
        return f"dragged {s.drag(val)}"
    if kind == "--type":
        s.act("type_text", text=val); return f"typed {len(val)} chars"
    if kind == "--key":
        *mods, key = val.split("+")
        if mods:
            s.act("hotkey", keys=mods + [key])
        else:
            s.act("press_key", key=key)
        return f"key {val}"
    if kind == "--menu":
        path = [p.strip() for p in re.split(r"\s*>\s*", val) if p.strip()]
        s.act("invoke_menu", path=path)
        return f"menu {' > '.join(path)}"
    if kind == "--scroll":
        direction, _, n = val.partition(":")
        s.act("scroll", direction=direction, amount=int(n or 5))
        return f"scrolled {direction} {n or 5}"
    if kind == "--wait":
        time.sleep(float(val)); return f"waited {val}s"
    if kind == "--wait-for":
        s.wait_for(val); return f"saw {val!r}"
    if kind in ("--read", "--read-all"):
        time.sleep(0.3)
        texts = s.read(val)
        shown = texts if kind == "--read-all" else texts[:READ_LIMIT]
        print(f"[read{' ' + val if val else ''}] " + " | ".join(shown) if texts else f"[read] nothing matching {val!r}")
        if len(shown) < len(texts):
            print(f"[read] {len(texts) - len(shown)} more lines not shown: narrow with --read TEXT, or use --read-all")
        return f"{len(texts)} texts"
    if kind == "--shot":
        path = os.path.join(shot_dir(), f"cu_{int(time.time() * 1000)}.png")
        s.act("get_window_state", include_accessibility_tree=False, screenshot_out_file=path)
        return f"screenshot {path}"
    raise LookupError(f"unhandled step {kind}")


def main():
    if not sys.argv[1:] or sys.argv[1] in ("-h", "--help"):
        print(__doc__); return 0
    steps = parse(sys.argv[1:])
    launch = any(k in ("--open", "--url") for k, _ in steps)
    try:
        s = Session(Driver())
    except (OSError, RuntimeError) as e:
        print(f"FAIL cua-driver not usable ({DRIVER}): {e}. Install it or set CUA_DRIVER_BIN."); return 2
    t0, kind = time.time(), None
    try:
        for kind, val in steps:
            t = time.time()
            if kind == "--open":
                continue
            if kind == "--app":
                s.resolve_app(val, launch); note = f"{s.app} pid={s.pid} window={s.wid}"
            else:
                note = run_step(s, kind, val)
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
