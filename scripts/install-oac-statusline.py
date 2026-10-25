#!/usr/bin/env python3
"""Install the OaC standard Claude Code statusline for this user (all repos).

Copies `oac-statusline.sh` to ~/.claude/ and points user settings at it, so
every repo on this machine gets the same line: folder, what you are working on,
model and context usage.

opscode-hq does not need this. Its checked-in .claude/settings.json already
points at the in-repo script, so cloning is enough. This is for every OTHER
repo, which falls back to user settings.

Idempotent. Safe to re-run after pulling a newer script.

    python3 code/scripts/install-oac-statusline.py
    python3 code/scripts/install-oac-statusline.py --check

See brand/standards/claude-code-statusline-standard.md.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "oac-statusline.sh"
CLAUDE_DIR = Path.home() / ".claude"
DEST = CLAUDE_DIR / "statusline-command.sh"
SETTINGS = CLAUDE_DIR / "settings.json"
WANT = f"bash {DEST}"


def main() -> int:
    check = "--check" in sys.argv

    if not SRC.is_file():
        print(f"error: {SRC} not found")
        return 1
    if not CLAUDE_DIR.is_dir():
        print(f"error: {CLAUDE_DIR} not found (is Claude Code installed?)")
        return 1

    src_text = SRC.read_text()
    in_sync = DEST.is_file() and DEST.read_text() == src_text

    settings = {}
    if SETTINGS.is_file():
        try:
            settings = json.loads(SETTINGS.read_text())
        except json.JSONDecodeError as e:
            print(f"error: {SETTINGS} is not valid JSON ({e}).")
            print("Fix it first: a malformed settings file disables ALL your settings.")
            return 1

    current = (settings.get("statusLine") or {}).get("command")
    wired = current == WANT

    if check:
        print(f"script in sync : {'yes' if in_sync else 'NO'}  ({DEST})")
        print(f"settings wired : {'yes' if wired else 'NO'}")
        if current and not wired:
            print(f"  currently    : {current}")
        return 0 if (in_sync and wired) else 1

    if in_sync:
        print(f"script already current: {DEST}")
    else:
        if DEST.is_file():
            backup = DEST.with_suffix(".sh.bak")
            shutil.copy2(DEST, backup)
            print(f"backed up existing -> {backup}")
        shutil.copy2(SRC, DEST)
        DEST.chmod(0o755)
        print(f"installed -> {DEST}")

    if wired:
        print("user settings already wired")
    else:
        if current:
            print(f"replacing existing statusLine: {current}")
        settings["statusLine"] = {"type": "command", "command": WANT}
        SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")
        print(f"wired -> {SETTINGS}")

    print("\nDone. Open /hooks once or restart a session to pick it up.")
    print("opscode-hq is unaffected: it uses its own in-repo copy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
