#!/usr/bin/env python3
"""Is everything saved, and is everything on GitHub? Every branch, every folder.

WHY THIS EXISTS
    On 18 Nov 2026 a check across the worktrees on Adam's Pi found a session's
    notes and coach feedback that lived in one folder and nowhere else: never
    committed, never pushed. /done had only ever looked at the folder it was
    run from, and /start only measured how far behind main the current folder
    was. Work that sits on one machine is one disk failure from gone.

    This is the one check both commands run, in the HQ and in every pack, so
    the answer is the same wherever it is asked.

WHAT IT REPORTS, worst first
    not saved        files changed but not committed, in any worktree
    not on GitHub    commits that exist only on this machine: a branch with no
                     copy on GitHub, or commits ahead of the copy it has
    finished         clean, pushed, and merged: safe to close (the person
                     still decides about the branch; /done asks)
    behind main      how far each folder is behind the shared copy

    It also looks at local branches with no worktree, because a branch
    nobody has open can still hold the only copy of a commit.

WHAT IT NEVER DOES
    Commit, push, pull, delete or move anything. It fetches (so 'behind' and
    'on GitHub' are true now, not as of the last fetch), and that is all.
    --no-fetch skips even that.

IGNORED
    Files the timed jobs commit for you (Telegram captures, Zoom pulls) are
    not 'not saved'. List their patterns, one per line, in
    .oac/sync-check-ignore. They are ignored in the home checkout only,
    because that is the only place the jobs write.

USAGE
    python3 scripts/oac-sync-check.py            # the report
    python3 scripts/oac-sync-check.py --json     # for a command to read
    python3 scripts/oac-sync-check.py --risks    # only what is at risk
    Exit 1 when anything is not saved or not on GitHub, else 0.
"""
from __future__ import annotations  # runs on a Mac's own python3, 3.9

import argparse
import fnmatch
import json
import shutil
import subprocess
import sys
from pathlib import Path


def git(cwd: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def ok(cwd: Path, *args: str) -> str | None:
    code, out = git(cwd, *args)
    return out if code == 0 else None


def repo_root(start: Path) -> Path | None:
    """The main checkout, even when run from a worktree."""
    common = ok(start, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        return None
    p = Path(common)
    return p.parent if p.name == ".git" else p


def default_branch(root: Path) -> str:
    ref = ok(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if ref:
        return ref.rsplit("/", 1)[-1]
    for name in ("main", "master"):
        if ok(root, "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{name}"):
            return name
    return "main"


def worktrees(root: Path) -> list[dict]:
    out = ok(root, "worktree", "list", "--porcelain") or ""
    rows: list[dict] = []
    cur: dict = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            cur = {"path": line[9:], "branch": None}
            rows.append(cur)
        elif line.startswith("branch "):
            cur["branch"] = line[7:].replace("refs/heads/", "", 1)
        elif line == "detached":
            cur["branch"] = None
        elif line.startswith("prunable"):
            cur["prunable"] = True
    return rows


def ignore_patterns(root: Path) -> list[str]:
    f = root / ".oac" / "sync-check-ignore"
    if not f.is_file():
        return []
    pats = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pats.append(line)
    return pats


def changed_files(path: Path, ignore: list[str]) -> list[str]:
    # Not through ok(): it strips, and a modified file's status line starts
    # with a space (' M path'), so stripping cut the first path's first letter.
    r = subprocess.run(["git", "-C", str(path), "status", "--porcelain", "-uall"],
                       capture_output=True, text=True)
    out = r.stdout if r.returncode == 0 else ""
    files = []
    for line in out.splitlines():
        name = line[3:]
        if " -> " in name:
            name = name.split(" -> ", 1)[1]
        name = name.strip('"')
        if any(fnmatch.fnmatch(name, p) for p in ignore):
            continue
        files.append(name)
    return files


def count(path: Path, *rng: str) -> int:
    out = ok(path, "rev-list", "--count", *rng)
    return int(out) if out and out.isdigit() else 0


def merged_prs() -> dict[str, str] | None:
    """{branch: head sha} for merged PRs, or None when gh is not there.

    A squash merge leaves the branch's commits off main's history, so git
    alone would call a finished branch 'not on main'. The PR knows better."""
    if not shutil.which("gh"):
        return None
    r = subprocess.run(["gh", "pr", "list", "--state", "merged", "--limit", "300",
                        "--json", "headRefName,headRefOid"], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return {p["headRefName"]: p["headRefOid"] for p in json.loads(r.stdout or "[]")}
    except (ValueError, KeyError):
        return None


def branch_state(where: Path, branch: str, main: str, has_remote: bool, merged: dict | None) -> dict:
    tip = ok(where, "rev-parse", branch) or ""
    upstream = ok(where, "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
    if upstream and not ok(where, "rev-parse", "--verify", "--quiet", upstream):
        upstream = None  # configured, but gone from GitHub
    not_on_main = count(where, f"origin/{main}..{branch}") if has_remote else 0
    # Backed up means on GitHub ANYWHERE, not just on this branch's own copy:
    # a commit on another branch there is safe. So the count is commits no
    # remote branch has. Without a remote, every commit is the only copy.
    if has_remote:
        unpushed = count(where, f"{branch}", "--not", "--remotes=origin")
    else:
        unpushed = count(where, branch)
    pr_merged = bool(merged and merged.get(branch) == tip)
    if pr_merged:
        # Squash-merged and its GitHub copy deleted: the PR holds every
        # commit, so nothing here is the only copy.
        unpushed = 0
    return {
        "branch": branch,
        "on_github": bool(upstream),
        "unpushed": unpushed,
        "behind": count(where, f"{branch}..origin/{main}") if has_remote else 0,
        "merged": branch != main and (not_on_main == 0 or pr_merged),
        "last": ok(where, "log", "-1", "--format=%cr", branch) or "",
    }


def check(start: Path, fetch: bool = True, use_gh: bool = True) -> dict:
    root = repo_root(start)
    if root is None:
        return {"error": "not a git repository"}
    has_remote = bool(ok(root, "remote", "get-url", "origin"))
    if has_remote and fetch:
        git(root, "fetch", "--quiet", "--prune", "origin")
    main = default_branch(root)
    merged = merged_prs() if (use_gh and has_remote) else None
    ignore = ignore_patterns(root)

    rows = []
    open_branches = set()
    for w in worktrees(root):
        path = Path(w["path"])
        home = path.resolve() == root.resolve()
        if w.get("prunable") or not path.is_dir():
            rows.append({"where": str(path), "home": home, "missing": True, "branch": w["branch"]})
            continue
        files = changed_files(path, ignore if home else [])
        row = {"where": str(path), "home": home, "changed": files}
        if w["branch"]:
            open_branches.add(w["branch"])
            row.update(branch_state(path, w["branch"], main, has_remote, merged))
        else:
            row.update({"branch": None, "on_github": False, "unpushed": 0, "behind": 0, "merged": False, "last": ""})
        rows.append(row)

    # Branches nobody has open can still hold the only copy of a commit.
    loose = []
    for b in (ok(root, "for-each-ref", "--format=%(refname:short)", "refs/heads") or "").splitlines():
        if b in open_branches or b == main:
            continue
        st = branch_state(root, b, main, has_remote, merged)
        if st["unpushed"]:
            loose.append(st)

    def at_risk(r: dict) -> bool:
        return bool(r.get("changed")) or bool(r.get("unpushed"))

    return {
        "repo": str(root),
        "github": has_remote,
        "main": main,
        "pr_checked": merged is not None,
        "worktrees": rows,
        "branches_not_open": loose,
        "at_risk": [r for r in rows if at_risk(r)] + loose,
    }


def short(path: str, home: bool) -> str:
    return "home checkout" if home else Path(path).name


def render(rep: dict, risks_only: bool = False) -> str:
    if "error" in rep:
        return rep["error"]
    lines = []
    if not rep["github"]:
        lines.append("This repo has no copy on GitHub yet, so nothing in it is backed up.")
        lines.append("")

    risky = rep["at_risk"]
    if risky:
        lines.append(f"NOT BACKED UP ({len(risky)})")
        for r in risky:
            name = short(r["where"], r["home"]) if "where" in r else "(no folder open)"
            bits = []
            if r.get("changed"):
                bits.append(f"{len(r['changed'])} file(s) not saved")
            if r.get("unpushed"):
                bits.append(f"{r['unpushed']} commit(s) not on GitHub"
                            + ("" if r.get("on_github") else ", and the branch has no copy there"))
            lines.append(f"  {name:28} {r.get('branch') or '(no branch)':44} {'; '.join(bits)}")
            for f in (r.get("changed") or [])[:5]:
                lines.append(f"      {f}")
            if len(r.get("changed") or []) > 5:
                lines.append(f"      ... and {len(r['changed']) - 5} more")
    else:
        lines.append("Everything is saved and on GitHub.")

    if not risks_only:
        done = [r for r in rep["worktrees"] if not r.get("missing") and not r["home"]
                and r.get("merged") and not r.get("changed") and not r.get("unpushed")]
        if done:
            lines.append("")
            lines.append(f"FINISHED, SAFE TO CLOSE ({len(done)})")
            for r in done:
                lines.append(f"  {short(r['where'], r['home']):28} {r['branch']:44} last commit {r['last']}")
        gone = [r for r in rep["worktrees"] if r.get("missing")]
        if gone:
            lines.append("")
            lines.append("FOLDER MISSING (git worktree prune forgets these)")
            for r in gone:
                lines.append(f"  {r['where']}")
        behind = [r for r in rep["worktrees"] if not r.get("missing") and r.get("behind")
                  and r not in done]
        if behind:
            lines.append("")
            lines.append(f"BEHIND {rep['main'].upper()}")
            for r in behind:
                lines.append(f"  {short(r['where'], r['home']):28} {r['branch'] or '':44} {r['behind']} behind")
        if not rep["pr_checked"] and rep["github"]:
            lines.append("")
            lines.append("(gh not available: a squash-merged branch may show as not finished)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Is everything saved, and on GitHub? Reads only.")
    ap.add_argument("--json", action="store_true", help="the report as JSON")
    ap.add_argument("--risks", action="store_true", help="only what is not backed up")
    ap.add_argument("--no-fetch", action="store_true", help="do not fetch from GitHub first")
    ap.add_argument("--no-gh", action="store_true", help="do not ask GitHub which PRs merged")
    ap.add_argument("--repo", type=Path, default=Path.cwd(), help="any folder in the repo")
    a = ap.parse_args(argv)
    rep = check(a.repo, fetch=not a.no_fetch, use_gh=not a.no_gh)
    print(json.dumps(rep, indent=2) if a.json else render(rep, a.risks))
    if "error" in rep:
        return 2
    return 1 if rep["at_risk"] or not rep["github"] else 0


if __name__ == "__main__":
    sys.exit(main())
