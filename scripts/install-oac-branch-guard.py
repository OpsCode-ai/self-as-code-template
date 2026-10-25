#!/usr/bin/env python3
"""Install the OaC session discipline tooling for this user (all repos).

Two pieces, installed together because they are one standard:

  oac-branch-guard.py    PreToolUse on Bash. Every repo on this machine
                         refuses to take its primary clone off main. Work
                         belongs in a worktree.
  oac-session-health.py  SessionStart. Says what needs attention before you
                         type anything, and stays silent when nothing does.

The health check is the half that matters for a new operator: it is what tells
them the guard is missing, or their statusline is stale, or their main checkout
is holding work that is blocking a cron job. Without it, all three failures
look exactly like everything being fine.

opscode-hq wires the same guard in its checked-in .claude/settings.json, but
that is a convenience and not the install: anything in a checked-in settings
file only exists on branches carrying the commit, so it disappears exactly
when you have several branches in flight. The copy in ~/.claude/ lives outside
git and survives every branch switch.

Idempotent. Safe to re-run after pulling a newer guard.

    python3 code/scripts/install-oac-branch-guard.py
    python3 code/scripts/install-oac-branch-guard.py --check
    python3 code/scripts/install-oac-branch-guard.py --uninstall

See brand/standards/session-discipline-standard.md and ADR-113.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "oac-branch-guard.py"
HEALTH_SRC = HERE / "oac-session-health.py"
BRIEF_SRC = HERE / "oac-session-brief.py"
CLAUDE_DIR = Path.home() / ".claude"
DEST = CLAUDE_DIR / "oac-branch-guard.py"
HEALTH_DEST = CLAUDE_DIR / "oac-session-health.py"
BRIEF_DEST = CLAUDE_DIR / "oac-session-brief.py"
SETTINGS = CLAUDE_DIR / "settings.json"

# The shell pre-filter is load-bearing, not decoration. This hook runs before
# EVERY Bash call, and a bare Python start costs 44ms against 1.9ms for a shell
# pattern test. Measured: code/scripts/tests/bench_branch_guard.py.
#
# The `[ -f ]` test is load-bearing too, and it was learned the hard way: a
# wrapper that invokes a missing script returns python's error, which the
# harness treats as a hook failure and blocks EVERY Bash call. The guard's
# fail-open promise lives in its exit codes, so it is worth nothing if the
# wrapper never reaches it. Missing script means allow, exactly like any other
# unexpected condition.
WANT = ('p=$(cat); case "$p" in *git*) '
        f'[ -f "{DEST}" ] || exit 0; printf %s "$p" | '
        f'python3 "{DEST}" ;; *) exit 0 ;; esac')

HEALTH_WANT = (f'h="{HEALTH_DEST}"; [ -f "$h" ] || exit 0; python3 "$h"')

# Ordered AFTER the health entry in SessionStart on purpose: a warning that the
# sweeps are blocked has to lead, not sit under a briefing. Same [ -f ] guard
# and the same reason as above.
BRIEF_WANT = (f'b="{BRIEF_DEST}"; [ -f "$b" ] || exit 0; python3 "$b"')

MARKER = "oac-branch-guard"
HEALTH_MARKER = "oac-session-health"
BRIEF_MARKER = "oac-session-brief"


def load_settings():
    if not SETTINGS.is_file():
        return {}, None
    try:
        return json.loads(SETTINGS.read_text()), None
    except json.JSONDecodeError as e:
        return None, e


def find_entries(settings):
    """Every PreToolUse entry that mentions this guard."""
    pre = (settings.get("hooks") or {}).get("PreToolUse") or []
    return [e for e in pre if MARKER in json.dumps(e)]


def main() -> int:
    check = "--check" in sys.argv
    uninstall = "--uninstall" in sys.argv

    if not SRC.is_file():
        print(f"error: {SRC} not found")
        return 1
    if not CLAUDE_DIR.is_dir():
        print(f"error: {CLAUDE_DIR} not found (is Claude Code installed?)")
        return 1

    settings, err = load_settings()
    if err:
        print(f"error: {SETTINGS} is not valid JSON ({err}).")
        print("Fix it first: a malformed settings file disables ALL your settings.")
        return 1

    src_text = SRC.read_text()
    in_sync = DEST.is_file() and DEST.read_text() == src_text
    entries = find_entries(settings)
    wired = any(h.get("command") == WANT
                for e in entries for h in (e.get("hooks") or []))

    health_sync = (HEALTH_SRC.is_file() and HEALTH_DEST.is_file()
                   and HEALTH_DEST.read_text() == HEALTH_SRC.read_text())
    health_wired = any(
        h.get("command") == HEALTH_WANT
        for e in ((settings.get("hooks") or {}).get("SessionStart") or [])
        for h in (e.get("hooks") or []))

    brief_sync = (BRIEF_SRC.is_file() and BRIEF_DEST.is_file()
                  and BRIEF_DEST.read_text() == BRIEF_SRC.read_text())
    brief_wired = any(
        h.get("command") == BRIEF_WANT
        for e in ((settings.get("hooks") or {}).get("SessionStart") or [])
        for h in (e.get("hooks") or []))

    if check:
        print(f"guard in sync   : {'yes' if in_sync else 'NO'}  ({DEST})")
        print(f"guard wired     : {'yes' if wired else 'NO'}")
        print(f"health in sync  : {'yes' if health_sync else 'NO'}  ({HEALTH_DEST})")
        print(f"health wired    : {'yes' if health_wired else 'NO'}")
        print(f"brief in sync   : {'yes' if brief_sync else 'NO'}  ({BRIEF_DEST})")
        print(f"brief wired     : {'yes' if brief_wired else 'NO'}")
        if entries and not wired:
            print("  stale entry   : found, re-run without --check to refresh")
        ok = (in_sync and wired and health_sync and health_wired
              and brief_sync and brief_wired)
        return 0 if ok else 1

    if uninstall:
        hooks = settings.setdefault("hooks", {})
        for event, marker in (("PreToolUse", MARKER),
                              ("SessionStart", HEALTH_MARKER),
                              ("SessionStart", BRIEF_MARKER)):
            kept = [e for e in (hooks.get(event) or [])
                    if marker not in json.dumps(e)]
            if kept:
                hooks[event] = kept
            else:
                hooks.pop(event, None)
        if not hooks:
            settings.pop("hooks", None)
        SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")
        for f in (DEST, HEALTH_DEST, BRIEF_DEST):
            if f.is_file():
                f.unlink()
        print("uninstalled. Guard, health check and briefing are gone from user settings.")
        print("opscode-hq's checked-in settings still wire them inside that repo.")
        return 0

    # 1. The script itself.
    if in_sync:
        print(f"guard already current: {DEST}")
    else:
        if DEST.is_file():
            backup = DEST.with_suffix(".py.bak")
            shutil.copy2(DEST, backup)
            print(f"backed up existing guard to {backup}")
        shutil.copy2(SRC, DEST)
        DEST.chmod(0o755)
        print(f"installed guard to {DEST}")

    # 2. The health check.
    if HEALTH_SRC.is_file():
        if health_sync:
            print(f"health check already current: {HEALTH_DEST}")
        else:
            if HEALTH_DEST.is_file():
                shutil.copy2(HEALTH_DEST, HEALTH_DEST.with_suffix(".py.bak"))
            shutil.copy2(HEALTH_SRC, HEALTH_DEST)
            HEALTH_DEST.chmod(0o755)
            print(f"installed health check to {HEALTH_DEST}")
    else:
        print(f"note: {HEALTH_SRC.name} not in this checkout, skipping it")

    # 3. The session briefing.
    if BRIEF_SRC.is_file():
        if brief_sync:
            print(f"briefing already current: {BRIEF_DEST}")
        else:
            if BRIEF_DEST.is_file():
                shutil.copy2(BRIEF_DEST, BRIEF_DEST.with_suffix(".py.bak"))
            shutil.copy2(BRIEF_SRC, BRIEF_DEST)
            BRIEF_DEST.chmod(0o755)
            print(f"installed briefing to {BRIEF_DEST}")
    else:
        print(f"note: {BRIEF_SRC.name} not in this checkout, skipping it")

    # 4. The wiring. Replace any previous entry rather than stacking a second.
    hooks = settings.setdefault("hooks", {})
    pre = [e for e in (hooks.get("PreToolUse") or [])
           if MARKER not in json.dumps(e)]
    pre.append({"matcher": "Bash",
                "hooks": [{"type": "command", "command": WANT}]})
    hooks["PreToolUse"] = pre

    # Health first, then the briefing: a blocked-sweeps warning has to lead.
    start = [e for e in (hooks.get("SessionStart") or [])
             if HEALTH_MARKER not in json.dumps(e)
             and BRIEF_MARKER not in json.dumps(e)]
    if HEALTH_SRC.is_file():
        start.append({"matcher": "",
                      "hooks": [{"type": "command", "command": HEALTH_WANT}]})
    if BRIEF_SRC.is_file():
        start.append({"matcher": "",
                      "hooks": [{"type": "command", "command": BRIEF_WANT}]})
    if start:
        hooks["SessionStart"] = start

    if SETTINGS.is_file():
        shutil.copy2(SETTINGS, SETTINGS.with_suffix(".json.bak"))
    SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"wired PreToolUse/Bash in {SETTINGS}")

    print()
    print("Open /hooks once, or restart the session, to pick it up.")
    print("Your primary clones now refuse to leave main. Work in a worktree:")
    print("  git worktree add ~/projects/_wt-{short} -b {user}/{description}")
    print()
    print("Standard: brand/standards/session-discipline-standard.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
