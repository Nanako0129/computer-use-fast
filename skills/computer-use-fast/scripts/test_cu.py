"""Driver-free checks for cu.py's pure parts. Run: python3 scripts/test_cu.py"""
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
import cu  # noqa: E402

# Shape of cua-driver's tree_markdown, trimmed from a real System Settings → About capture (2026-10-01).
MD = '''- AXWindow "關於"
  - AXStaticText = "M1, 2020"
    - AXStaticText = "M1, 2020"
  - AXStaticText = "晶片"
  - AXStaticText = "Apple M1"
    - AXStaticText = "Apple M1"
  - AXStaticText = "記憶體"
  - AXStaticText = "16 GB"
  - AXHeading (macOS)
  - [82] AXButton "系統報告⋯" [actions=[press]]
    - [266] AXMenuItem "macOS支援" [id=menuAction: actions=[cancel,press,pick]]
'''

texts = cu.texts_from_markdown(MD)
assert texts == ["關於", "M1, 2020", "晶片", "Apple M1", "記憶體", "16 GB", "macOS", "系統報告⋯"], texts
assert "macOS支援" not in texts                                    # menu bar items are dropped
assert cu.texts_from_markdown(MD, "晶片") == ["晶片", "Apple M1"]  # label comes back with its value
assert cu.texts_from_markdown(MD, "nothing") == []

assert cu.norm(" Apple  M1 ") == "applem1"
assert cu.parse(["--app", "Calculator", "--open", "--type", "1+1=", "--read"]) == [
    ("--app", "Calculator"), ("--open", None), ("--type", "1+1="), ("--read", None)]
assert cu.parse(["--read", "Chip", "--shot"]) == [("--read", "Chip"), ("--shot", None)]

# help="…" attributes are tooltips, not on-screen text
assert cu.texts_from_markdown('- [8] AXTextField "Search" [help="Search Wikipedia [x]" actions=[press]]') == ["Search"]

ELS = [
    {"element_index": 0, "role": "AXWindow", "label": "Settings", "frame": {}},
    {"element_index": 1, "role": "AXButton", "label": "General", "actions": ["AXPress"], "parent_index": 0, "frame": {}},
    {"element_index": 2, "role": "AXButton", "label": "General Info", "actions": ["AXPress"], "parent_index": 0, "frame": {}},
    {"element_index": 3, "role": "AXRow", "actions": ["AXPress"], "parent_index": 0, "frame": {}},
    {"element_index": 4, "role": "AXStaticText", "label": "About", "parent_index": 3, "frame": {}},
    {"element_index": 5, "role": "AXMenuItem", "label": "About", "actions": ["AXPress"], "parent_index": 0},
    {"element_index": 6, "role": "AXTextField", "help": "Search", "parent_index": 0, "frame": {}},
]
assert cu.best_match(ELS, "general")["element_index"] == 1          # exact beats prefix, case-insensitive
assert cu.best_match(ELS, "Gen")["element_index"] == 1               # shorter label wins among prefixes
assert cu.best_match(ELS, "About")["element_index"] == 3             # text inside a row resolves to the row; menu ignored
assert cu.best_match(ELS, "search", cu.FIELD_ROLES, None)["element_index"] == 6
assert cu.best_match(ELS, "missing") is None

print("ok")
