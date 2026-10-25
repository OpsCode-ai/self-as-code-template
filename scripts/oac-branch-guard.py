#!/usr/bin/env python3
"""Refuse to take a primary clone off main. Work belongs in a worktree.

WHY THIS EXISTS
    A clone has one HEAD, one index and one set of files. Two Claude sessions
    in the same clone therefore share them. When one runs `git checkout -b`,
    the other's files change underneath it mid-edit, and both then fight over
    the same staging area at commit time.

    On this machine the primary clone is worse than shared, it is scheduled.
    On the OpsCode Pi, seven cron jobs address the primary clone by absolute path.
    Two of them refuse to run when it is off main or dirty with work that is
    not theirs, which is correct and is also silent: on 2026-09-08 a one-line
    doc edit blocked every hourly Telegram sweep for most of a day, and the
    only evidence was a line in a log file nobody opens.

    Rules in a document did not prevent that and would not prevent the next
    one. This is the same rule expressed as a rail.

WHAT IT BLOCKS
    Any git command that would leave a PRIMARY clone on something other than
    main: `checkout -b`, `switch -c`, `checkout <branch>`, `switch <branch>`.
    It reads through `cd`, `&&` and `;`, and it resolves an explicit repo path
    flag so a worktree session cannot reach into the primary clone sideways.

WHAT IT DOES NOT BLOCK
    Anything inside a linked worktree, which is where work is supposed to
    happen. Returning to main. File restores (`git checkout -- path`, and any
    invocation carrying `--`). Committing directly to main, which is still the
    right move for housekeeping, and is how the sweepers themselves work.

    Set OAC_ALLOW_BRANCH=1 for the rare case that genuinely needs a branch in
    the primary clone. The escape hatch is deliberate. A guard with no way
    round it gets uninstalled the first time it is wrong.

IT FAILS OPEN, ON PURPOSE
    Every unexpected condition exits 0 and allows the command. A leak guard
    should fail closed; this is a tidiness guard, and one that failed closed
    would stop all work on this machine the first time it met a git version
    it did not expect. The cost of a miss is a mess you can clean up. The cost
    of a false block is a person who turns the hook off.

WIRING
    PreToolUse on Bash, in .claude/settings.json. Exit 2 blocks the call and
    shows stderr to Claude.

Standard: brand/standards/session-discipline-standard.md
"""

import json
import os
import shlex
import subprocess
import sys

SPLITTERS = {"&&", "||", ";", "|", "&"}
# Subcommands that can move HEAD onto a different branch.
MOVERS = {"checkout", "switch"}
# git's own flags that take a value, so the parser can skip past them.
VALUED = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def git(cwd, *args):
    try:
        r = subprocess.run(("git", "-C", cwd) + args, capture_output=True,
                           text=True, timeout=3)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def segments(command):
    """Split a shell line into token runs, one per chained command."""
    try:
        tokens = shlex.split(command, comments=True)
    except ValueError:
        return []                       # unbalanced quotes: not ours to judge
    out, run = [], []
    for t in tokens:
        if t in SPLITTERS:
            if run:
                out.append(run)
            run = []
        else:
            run.append(t)
    if run:
        out.append(run)
    return out


def is_linked_worktree(path):
    """True when path sits in a linked worktree rather than the primary clone."""
    gd = git(path, "rev-parse", "--absolute-git-dir")
    cd = git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not gd or not cd:
        return False
    return os.path.normpath(gd) != os.path.normpath(cd)


def target_branch(run):
    """(subcommand, branch) when this run would move HEAD off main, else None.

    Returns None for file restores, for returns to main, and for anything that
    is not a checkout/switch.
    """
    if "git" not in run:
        return None
    rest = run[run.index("git") + 1:]

    # Skip git's own options, e.g. `git -c foo=bar checkout ...`
    j = 0
    while j < len(rest) and rest[j].startswith("-"):
        j += 2 if rest[j] in VALUED else 1
    if j >= len(rest) or rest[j] not in MOVERS:
        return None
    sub, args = rest[j], rest[j + 1:]

    # `--` means paths follow: a file restore, never a branch move.
    if "--" in args:
        return None

    new_branch = any(a in ("-b", "-B", "-c", "-C") for a in args)
    positional = [a for a in args if not a.startswith("-")]

    if new_branch:
        return (sub, positional[0] if positional else "(new branch)")

    if not positional:
        return None                     # bare `git switch` is an error anyway
    name = positional[0]
    if name in ("main", "master", "-"):
        return None                     # going home is always allowed
    if name.startswith(".") or os.path.exists(name):
        return None                     # looks like a path, not a branch
    return (sub, name)


def resolve_cwd(run, base):
    """Honour an explicit repo path flag so the guard cannot be stepped around."""
    for k, tok in enumerate(run):
        if tok == "-C" and k + 1 < len(run):
            p = run[k + 1]
            return p if os.path.isabs(p) else os.path.join(base, p)
    return base


def main():
    if os.environ.get("OAC_ALLOW_BRANCH"):
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if "git" not in command:
        return 0

    base = (payload.get("cwd")
            or (payload.get("workspace") or {}).get("current_dir")
            or os.getcwd())

    for run in segments(command):
        hit = target_branch(run)
        if not hit:
            continue
        sub, branch = hit
        cwd = resolve_cwd(run, base)
        if not os.path.isdir(cwd):
            continue
        if git(cwd, "rev-parse", "--is-inside-work-tree") != "true":
            continue
        if is_linked_worktree(cwd):
            continue                    # a worktree is exactly where this belongs

        slug = branch if branch != "(new branch)" else "<name>"
        short = slug.split("/")[-1][:12] or "work"
        sys.stderr.write(
            "BLOCKED: `git " + sub + "` would take the primary clone off main.\n"
            "\n"
            "  clone:  " + cwd + "\n"
            "  branch: " + slug + "\n"
            "\n"
            "The primary clone stays on main and stays clean, because cron\n"
            "jobs address it by absolute path and stop when it is neither.\n"
            "Work goes in a worktree. Create one and switch this session:\n"
            "\n"
            "  git worktree add ~/projects/_wt-" + short + " -b " + slug + "\n"
            "\n"
            "then EnterWorktree with that path. `/start` does both for you.\n"
            "Standard: brand/standards/session-discipline-standard.md\n"
            "Genuinely need a branch here? OAC_ALLOW_BRANCH=1 skips this.\n"
        )
        return 2

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)                     # fail open, always
