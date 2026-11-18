#!/usr/bin/env python3
"""A folder of its own for every session: /start opens it, /done closes it.

WHY THIS EXISTS
    One copy of a repo has one working folder. Two sessions in the same folder
    collide: one saves the other's half-written files, or switches the branch
    under it. OpsCode's own repo fixed that with a worktree per session
    (ADR-113), and the packs shipped the rail (the branch guard, the status
    line's two markers) but not the habit: nothing in the pack's /start or
    /done ever made one, so the markers described something a person would
    never see. Adam, 18 Nov 2026: 'hence the whole start and done skills' and
    'so has to be done now'. The commands do it, so nobody has to learn it.

WHERE THE FOLDERS GO
    Beside the repo, never inside it: <parent>/<repo>-sessions/<short>. A
    folder inside the repo would be walked by every script that reads the
    whole tree (oac-validate.py reads every .md but .git and node_modules),
    so each file would be counted twice. OpsCode's hub keeps its own outside
    for the same reason (~/projects/_wt-<short>).

VERBS
    open <short>     From the main folder. Makes <repo>-sessions/<short> on the
                     branch <handle>/<short>, from main (or the branch of that
                     name, if it already exists). Copies this machine's own
                     files across (.claude/user.json, settings.local.json,
                     checkpoint.json, .env*), which git does not carry. Prints
                     the folder's path on the last line.
    close <short>    From the main folder. Removes the session folder once its
                     work is in main and nothing in it is unsaved. Deletes the
                     branch too when it never went to GitHub; a branch on
                     GitHub is left for /done's question. --keep-branch keeps
                     it either way.
    where            Says which folder this is: 'main <path>' or
                     'session <short> <branch> <path>'.

WHAT IT NEVER DOES
    Force. Remove a folder with unsaved files, or one whose saves are not in
    main yet. Delete a branch git says is not fully merged. Reach into the
    main folder from a session folder: open and close refuse there, because
    /done leaves the session folder first.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SHORT = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
LOCAL_FILES = [".claude/user.json", ".claude/settings.local.json", ".claude/checkpoint.json", ".env"]


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


def out(cwd: Path, *args: str) -> str | None:
    r = git(cwd, *args)
    return r.stdout.strip() if r.returncode == 0 else None


def same(a: Path | str, b: Path | str) -> bool:
    return Path(a).resolve() == Path(b).resolve()


def locate(start: Path) -> tuple[Path, Path] | None:
    """(main folder, this folder), or None outside a git repo."""
    here = out(start, "rev-parse", "--show-toplevel")
    common = out(start, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not here or not common:
        return None
    c = Path(common)
    return (c.parent if c.name == ".git" else c), Path(here)


def default_branch(root: Path) -> str:
    ref = out(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if ref:
        return ref.rsplit("/", 1)[-1]
    for name in ("main", "master"):
        if out(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}"):
            return name
    return out(root, "branch", "--show-current") or "main"


def handle(root: Path) -> str:
    uj = root / ".claude" / "user.json"
    if uj.is_file():
        try:
            h = json.loads(uj.read_text(encoding="utf-8")).get("team_member", "")
            if h:
                return re.sub(r"[^a-z0-9-]+", "", str(h).strip().lower()) or "me"
        except ValueError:
            pass
    name = out(root, "config", "user.name") or ""
    first = re.sub(r"[^a-z0-9]+", "", name.split()[0].lower()) if name.split() else ""
    return first or "me"


def worktrees(root: Path) -> list[dict]:
    rows: list[dict] = []
    cur: dict = {}
    for line in (out(root, "worktree", "list", "--porcelain") or "").splitlines():
        if line.startswith("worktree "):
            cur = {"path": line[9:], "branch": None}
            rows.append(cur)
        elif line.startswith("branch "):
            cur["branch"] = line[7:].replace("refs/heads/", "", 1)
    return rows


def sessions_dir(root: Path) -> Path:
    return root.parent / f"{root.name}-sessions"


def in_main(start: Path) -> Path | None:
    """The main folder when run from it; otherwise say why not and return None."""
    loc = locate(start)
    if loc is None:
        print("This folder is not a git repository.")
        return None
    root, here = loc
    if not same(root, here):
        print(f"You're in the session folder '{here.name}'. Run this from the main folder, {root}.")
        return None
    return root


def copy_local(root: Path, dest: Path) -> list[str]:
    names = list(LOCAL_FILES) + sorted(p.name for p in root.glob(".env.*") if p.is_file())
    copied = []
    for rel in names:
        src, dst = root / rel, dest / rel
        if src.is_file() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(rel)
    return copied


def cmd_open(start: Path, short: str) -> int:
    root = in_main(start)
    if root is None:
        return 1
    branch = f"{handle(root)}/{short}"
    folder = sessions_dir(root) / short
    for w in worktrees(root):
        if same(w["path"], folder):
            if w["branch"] == branch:
                print(f"Already open: '{short}' on {branch}.")
                print(folder.resolve())
                return 0
            print(f"{folder} is already a session folder, on {w['branch']}. Pick another name.")
            return 1
        if w["branch"] == branch:
            print(f"{branch} is already open in {w['path']}. Work there, or pick another name.")
            return 1
    if folder.exists():
        print(f"{folder} already exists and is not a session folder. Pick another name.")
        return 1
    folder.parent.mkdir(parents=True, exist_ok=True)
    if out(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"):
        r = git(root, "worktree", "add", str(folder), branch)
        how = f"on {branch}, where you left it"
    else:
        base = default_branch(root)
        r = git(root, "worktree", "add", "-b", branch, str(folder), base)
        how = f"on a new branch, {branch}, from {base}"
    if r.returncode != 0:
        if folder.parent.is_dir() and not any(folder.parent.iterdir()):
            folder.parent.rmdir()
        print(f"Could not open the folder: {(r.stderr or r.stdout).strip()[:400]}")
        return 1
    copied = copy_local(root, folder)
    print(f"Opened '{short}' {how}.")
    if copied:
        print(f"Copied this machine's own files across: {', '.join(copied)}.")
    print(folder.resolve())
    return 0


def cmd_close(start: Path, short: str, keep_branch: bool) -> int:
    root = in_main(start)
    if root is None:
        return 1
    folder = sessions_dir(root) / short
    row = next((w for w in worktrees(root) if same(w["path"], folder)), None)
    if row is None:
        print(f"No session folder called '{short}' is open.")
        return 1
    branch = row["branch"]
    if folder.is_dir():
        dirty = [ln[3:] for ln in (git(folder, "status", "--porcelain").stdout or "").splitlines() if ln.strip()]
        if dirty:
            shown = ", ".join(dirty[:5]) + (" and more" if len(dirty) > 5 else "")
            print(f"'{short}' has {len(dirty)} unsaved file(s): {shown}. Save them with /done in that folder first.")
            return 1
    base = default_branch(root)
    if branch:
        ahead = out(root, "rev-list", "--count", f"{base}..{branch}")
        if ahead and ahead != "0":
            print(f"'{short}' has {ahead} save(s) that aren't in {base} yet. Bring them home first (/done does it), "
                  f"or pull if they were merged on GitHub.")
            return 1
    if folder.is_dir():
        r = git(root, "worktree", "remove", str(folder))
        if r.returncode != 0:
            print(f"Could not remove the folder: {(r.stderr or r.stdout).strip()[:400]}")
            return 1
    else:
        git(root, "worktree", "prune")
    said = f"Closed '{short}'."
    if branch and not keep_branch:
        if out(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", f"{branch}@{{upstream}}"):
            said += f" Its branch, {branch}, is on GitHub, so it stays until you say."
        else:
            d = git(root, "branch", "-d", branch)
            said += f" Its branch, {branch}, is tidied away." if d.returncode == 0 else \
                f" Its branch, {branch}, is kept: git says it is not fully merged."
    elif branch:
        said += f" Its branch, {branch}, is kept."
    parent = sessions_dir(root)
    if parent.is_dir() and not any(parent.iterdir()):
        parent.rmdir()
    print(said)
    return 0


def cmd_where(start: Path) -> int:
    loc = locate(start)
    if loc is None:
        print("This folder is not a git repository.")
        return 1
    root, here = loc
    if same(root, here):
        print(f"main {root}")
    else:
        print(f"session {here.name} {out(here, 'branch', '--show-current') or '(no branch)'} {here}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A folder of its own for every session.")
    sub = ap.add_subparsers(dest="verb", required=True)
    o = sub.add_parser("open")
    o.add_argument("short")
    c = sub.add_parser("close")
    c.add_argument("short")
    c.add_argument("--keep-branch", action="store_true")
    sub.add_parser("where")
    a = ap.parse_args(argv)
    start = Path.cwd()
    if a.verb in ("open", "close") and not SHORT.match(a.short):
        print("A short name is lowercase letters, numbers and dashes, up to 40, e.g. 'price-page'.")
        return 2
    if a.verb == "open":
        return cmd_open(start, a.short)
    if a.verb == "close":
        return cmd_close(start, a.short, a.keep_branch)
    return cmd_where(start)


if __name__ == "__main__":
    sys.exit(main())
