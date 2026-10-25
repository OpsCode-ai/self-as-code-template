#!/usr/bin/env python3
"""Say what needs attention at session start. Silent when nothing does.

WHY THIS EXISTS
    The session discipline standard (ADR-113) asks an operator to run /start,
    keep the main checkout clean, and keep their tooling installed. Every one
    of those is a thing a person has to remember, and the whole point of that
    ADR is that remembering is not a mechanism.

    Worse, the failure modes are all silent. Tooling that was never installed
    behaves exactly like tooling that is working. A main checkout holding
    uncommitted work looks identical to a clean one until an hourly cron job
    quietly refuses for the fourth time in a day.

    So this runs on SessionStart and puts the answer on screen before you type
    anything. You do not have to run /start to find out that something is
    wrong; you find out, and then you decide.

WHAT IT CHECKS
    1. Is the branch guard installed for this user, and current?
    2. Is the OaC statusline installed, and current?
    3. Is the main checkout clean and on main?

    Nothing else. This is a health check, not /start: it never opens a
    worktree, never reads your log, never asks a question, and never writes.

WHAT IT PRINTS
    Nothing at all when everything is fine, which is most days. A warning that
    fires every session is a warning that gets skipped, and the thing this
    guards against went unnoticed BECAUSE it reported into noise.

IT FAILS OPEN
    Every unexpected condition exits 0 silently. A session-start hook that
    errors is a session that starts on a stack trace.

WIRING
    SessionStart in .claude/settings.json, and installed per-user by
    install-oac-branch-guard.py so it works in every repo.

Standard: brand/standards/session-discipline-standard.md
"""

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLAUDE_DIR = Path.home() / ".claude"


def git(cwd, *args):
    try:
        r = subprocess.run(("git", "-C", str(cwd)) + args, capture_output=True,
                           text=True, timeout=3)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def tool_state(name):
    """(installed, current) for a tool that ships in code/scripts."""
    src, dest = HERE / name, CLAUDE_DIR / name
    if not dest.is_file():
        return False, False
    if not src.is_file():
        return True, True          # cannot compare, assume fine
    try:
        return True, dest.read_bytes() == src.read_bytes()
    except Exception:
        return True, True


SETTINGS = ".claude/settings.json"
ANNOUNCEMENT_KEY = "companyAnnouncements"


def announcement_only(root) -> bool:
    """True when settings.json differs from HEAD in the announcement alone.

    oac-session-brief.py keeps that key in the gitignored
    settings.local.json and strips any copy from settings.json, and the
    sweeper commits the strip, so it is not worth a warning. Mirrors the sweeper's
    is_announcement_only(), duplicate-key refusal included. Any failure
    returns False, which warns.
    """
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d:
                raise ValueError(k)
            d[k] = v
        return d
    try:
        head = git(root, "show", f"HEAD:{SETTINGS}")
        if head is None:
            return False
        before = json.loads(head, object_pairs_hook=pairs)
        after = json.loads((Path(root) / SETTINGS).read_text(encoding="utf-8"),
                           object_pairs_hook=pairs)
    except Exception:
        return False
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    before.pop(ANNOUNCEMENT_KEY, None)
    after.pop(ANNOUNCEMENT_KEY, None)
    return before == after


def blocks_the_sweep(path: str, root=None) -> bool:
    """True when a dirty path is work a person has to deal with.

    A capture the sweeper owns is NOT that. It is written by a daemon, it is
    committed on the hour, and it is present in a healthy repo most of the
    day. Counting it made this check say 'the sweeps are blocked' at a moment
    the sweeper itself reported nothing wrong, which is a warning that fires
    on a normal state, which is a warning that gets ignored. That failure mode
    is the entire reason this check exists, so it must not commit it.

    Deliberately a simplified mirror of sweep-telegram-capture.py's
    is_capture(). It cannot import the real one: this file runs from
    ~/.claude/ where the sweeper does not exist. It errs towards WARNING on
    anything it does not recognise, so a genuinely odd path still surfaces.

    The settings file needs the checkout itself (`root`) to read, because only
    its content says whether the change is the announcement. Without a root it
    warns.
    """
    if path == SETTINGS:
        return not (root and announcement_only(root))
    parts = Path(path).parts
    # The AI-DLC audit shard, appended by the engine's session hooks. The
    # sweeper commits it as machine output.
    if (len(parts) == 7 and parts[0] == "aidlc" and parts[1] == "spaces"
            and parts[3] == "intents" and parts[5] == "audit"
            and path.endswith(".md")):
        return False
    if len(parts) < 3 or parts[0] != "engagements":
        return True
    if parts[1] == "_unmapped":
        return False
    if parts[2] == "telegram":
        return not path.endswith(".md")
    if parts[2] in {"sessions", "transcripts", "a-team-sessions"}:
        # Machine output only, matching the sweeper. Authored coaching work
        # still needs a person, so it still counts as blocking. The dir names
        # are the registry's export dirs, not just `sessions`.
        if Path(path).suffix in {".srt", ".vtt", ".json"}:
            return False
        return not (path.endswith("-hq-upload.md") or path.endswith("-chat.txt"))
    return True


def main_checkout():
    """(path, branch, blocking_count) for the primary clone, or None."""
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        return None
    root = os.path.dirname(os.path.normpath(common))
    if not os.path.isdir(root):
        return None
    branch = git(root, "branch", "--show-current") or "?"
    status = git(root, "status", "--porcelain", "-uno")
    if status is None:
        return None
    n = len([p for p in porcelain_paths(status) if blocks_the_sweep(p, root)])
    return root, branch, n


def porcelain_paths(status: str) -> list[str]:
    """Paths out of `status --porcelain`, tolerating a stripped first column.

    Do NOT slice by a fixed offset here. git() strips its output, so a line
    that left git as ' M path' arrives as 'M path' and a two-char slice eats
    the first letter of the path. That silently turned every path into an
    unrecognised one, which the noise-floor check then counted as blocking,
    which is exactly the false alarm this function exists to prevent. Splitting
    on whitespace is immune to whether the column survived.
    """
    out = []
    for ln in status.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = ln.split(None, 1)
        if len(parts) != 2:
            continue
        path = parts[1].strip().strip('"')
        if " -> " in path:                 # a rename; the new name is the file
            path = path.split(" -> ", 1)[1].strip().strip('"')
        out.append(path)
    return out


def main() -> int:
    notes, actions = [], []

    guard_in, guard_cur = tool_state("oac-branch-guard.py")
    if not guard_in:
        notes.append("branch guard is NOT installed for your user, so only "
                     "this repo is protected")
        actions.append("python3 code/scripts/install-oac-branch-guard.py")
    elif not guard_cur:
        notes.append("branch guard is out of date")
        actions.append("python3 code/scripts/install-oac-branch-guard.py")

    line_dest = CLAUDE_DIR / "statusline-command.sh"
    line_src = HERE / "oac-statusline.sh"
    if not line_dest.is_file():
        notes.append("OaC statusline is NOT installed for your user")
        actions.append("python3 code/scripts/install-oac-statusline.py")
    elif line_src.is_file():
        try:
            if line_dest.read_bytes() != line_src.read_bytes():
                notes.append("statusline is out of date, so the ⌂ marker may "
                             "be missing")
                actions.append("python3 code/scripts/install-oac-statusline.py")
        except Exception:
            pass

    mc = main_checkout()
    if mc:
        root, branch, dirty = mc
        short = root.replace(str(Path.home()), "~")
        if branch not in ("main", "master", "?"):
            notes.append(f"main checkout {short} is parked on '{branch}', "
                         "so scheduled jobs there are stopped")
            actions.append(f"git -C {short} checkout main")
        elif dirty:
            notes.append(f"main checkout {short} has {dirty} uncommitted "
                         "file(s), which blocks the hourly sweeps")
            actions.append(f"git -C {short} status")

    if not notes:
        return 0                     # the quiet, normal case

    out = ["", "⚠ OaC session health"]
    for n in notes:
        out.append(f"  · {n}")
    if actions:
        out.append("")
        out.append("  Fix:")
        for a in dict.fromkeys(actions):
            out.append(f"    {a}")
    out.append("")
    out.append("  Then /start to open a worktree for today's work.")
    out.append("  Standard: brand/standards/session-discipline-standard.md")
    out.append("")
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)                  # never start a session on a stack trace
