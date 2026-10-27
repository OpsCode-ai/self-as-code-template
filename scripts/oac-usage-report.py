#!/usr/bin/env python3
"""Turn the statusline's usage ledger into a report a business can read.

THE LEDGER
    The OaC statusline (oac-statusline.sh) refreshes one small JSON per Claude
    Code session under ~/.claude/oac-usage/sessions/ while the figures move:
    repo, mode, user, model, cost, duration, tokens, lines changed. It is
    per machine and outside every repo, so a statusline render never dirties
    a working tree.

THE COST
    `cost_usd` is Claude Code's own figure: token counts, including cache
    reads and writes, priced at list price per model, reset by /clear. For a
    Max or Pro subscriber it is what the session WOULD have cost via the API,
    not a charge (code.claude.com/docs/en/costs). Report it as usage, not as
    a bill.

THE REPORT
    One file per person, in the repo, at team/<handle>/usage.md: this month
    and the last, sessions, hours, cost, tokens, lines. Each person's machine
    writes their own file, so two people never write the same one. A repo
    total is the sum of the files, and this script prints it with --all.

Usage:
    python3 scripts/oac-usage-report.py                 # print, this repo, this machine
    python3 scripts/oac-usage-report.py --write         # write team/<handle>/usage.md
    python3 scripts/oac-usage-report.py --all           # every repo this machine has seen
    python3 scripts/oac-usage-report.py --repo <path>   # another repo's rows
    # --ledger <dir>  the sessions directory (tests)
    # --handle <name> override the git-derived handle
    # --today YYYY-MM-DD  pin the month boundaries (tests)

Runs from a pack (scripts/) or from opscode-hq (code/scripts/); no imports
beyond the standard library.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

LEDGER = Path.home() / ".claude" / "oac-usage" / "sessions"


def load(ledger: Path) -> list[dict]:
    rows = []
    if not ledger.is_dir():
        return rows
    for p in sorted(ledger.glob("*.json")):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(r, dict) and r.get("session_id"):
            rows.append(r)
    return rows


def repo_root(path: Path) -> Path:
    try:
        out = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except Exception:
        pass
    return path.resolve()


def same_repo(row: dict, root: Path) -> bool:
    """A row belongs to a repo when its recorded root is that repo or one of
    its linked worktrees (same basename family is not enough: compare the git
    common dir when we can, else the path)."""
    rp = Path(str(row.get("repo") or ""))
    if not str(rp):
        return False
    if rp.resolve() == root.resolve():
        return True
    try:
        a = subprocess.run(["git", "-C", str(rp), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                           capture_output=True, text=True, timeout=5).stdout.strip()
        b = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                           capture_output=True, text=True, timeout=5).stdout.strip()
        return bool(a) and a == b
    except Exception:
        return False


def handle_of(root: Path) -> str:
    try:
        name = subprocess.run(["git", "-C", str(root), "config", "user.name"],
                              capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        name = ""
    first = re.sub(r"[^a-z0-9]+", "", name.split()[0].lower()) if name.split() else ""
    return first or (os.environ.get("USER") or "user").lower()


def month_of(row: dict) -> str:
    return str(row.get("started") or row.get("last_seen") or "")[:7]


def hours(ms) -> float:
    try:
        return round(float(ms) / 3_600_000, 2)
    except (TypeError, ValueError):
        return 0.0


def fnum(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "0"
    if n >= 1e6:
        return f"{n / 1e6:.1f}M"
    if n >= 1e3:
        return f"{n / 1e3:.1f}k"
    return f"{int(n)}"


def summarise(rows: list[dict]) -> dict:
    s = {"sessions": len(rows), "hours": 0.0, "api_hours": 0.0, "cost": 0.0,
         "in": 0, "out": 0, "added": 0, "removed": 0, "modes": defaultdict(int), "models": defaultdict(int)}
    for r in rows:
        s["hours"] += hours(r.get("duration_ms"))
        s["api_hours"] += hours(r.get("api_ms"))
        s["cost"] += float(r.get("cost_usd") or 0)
        s["in"] += int(r.get("input_tokens") or 0)
        s["out"] += int(r.get("output_tokens") or 0)
        s["added"] += int(r.get("lines_added") or 0)
        s["removed"] += int(r.get("lines_removed") or 0)
        s["modes"][r.get("mode") or "none"] += 1
        s["models"][r.get("model") or "?"] += 1
    s["hours"] = round(s["hours"], 2)
    s["api_hours"] = round(s["api_hours"], 2)
    s["cost"] = round(s["cost"], 2)
    return s


def render(rows: list[dict], *, handle: str, repo_name: str, today: dt.date, all_repos: bool) -> str:
    this_m = today.strftime("%Y-%m")
    last_m = (today.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    by_month: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_month[month_of(r)].append(r)

    lines = [
        "---",
        f'title: "Usage: {handle}' + ("" if all_repos else f", {repo_name}") + '"',
        "type: report",
        "audience: team",
        f"owner: {handle}",
        f"updated: {today.isoformat()}",
        "topics: [operations, tooling]",
        "tags: [usage, claude-code, ledger]",
        "---",
        "",
        f"# Usage: {handle}" + ("" if all_repos else f", {repo_name}"),
        "",
        "What Claude Code sessions in this repo used, written by",
        "`oac-usage-report.py` from the statusline's ledger on this person's",
        "machine. Cost is Claude Code's own figure: tokens at list price per model,",
        "cache included, reset by `/clear`. On a Max or Pro plan it is what the work",
        "would have cost through the API, not a charge. Read it as effort, not as",
        "a bill.",
        "",
        "## By month",
        "",
        "| Month | Sessions | Hours | API hours | Cost (USD) | Tokens in | Tokens out | Lines +/- | Modes |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    months = sorted(by_month, reverse=True)
    for m in months:
        s = summarise(by_month[m])
        modes = ", ".join(f"{k} {v}" for k, v in sorted(s["modes"].items(), key=lambda kv: -kv[1]))
        lines.append(f"| {m} | {s['sessions']} | {s['hours']} | {s['api_hours']} | {s['cost']:.2f} | "
                     f"{fnum(s['in'])} | {fnum(s['out'])} | +{s['added']} / -{s['removed']} | {modes} |")
    if not months:
        lines.append("| (no sessions recorded yet) | | | | | | | | |")

    total = summarise(rows)
    lines += ["", f"**All time:** {total['sessions']} sessions, {total['hours']} hours, "
                  f"{total['cost']:.2f} USD, {fnum(total['in'])} in / {fnum(total['out'])} out."]

    recent = [r for r in rows if month_of(r) in (this_m, last_m)]
    recent.sort(key=lambda r: str(r.get("started") or ""), reverse=True)
    if recent:
        lines += ["", f"## Sessions, {last_m} and {this_m}", "",
                  "| Started | Mode | Model | Hours | Cost | Tokens in/out | Lines +/- | Repo |" if all_repos else
                  "| Started | Mode | Model | Hours | Cost | Tokens in/out | Lines +/- |",
                  "|---|---|---|---|---|---|---|---|" if all_repos else "|---|---|---|---|---|---|---|"]
        for r in recent[:60]:
            cost = r.get("cost_usd")
            row = (f"| {str(r.get('started') or '')[:16].replace('T', ' ')} | {r.get('mode') or ''} | {r.get('model') or '?'} | "
                   f"{hours(r.get('duration_ms'))} | {('%.2f' % cost) if isinstance(cost, (int, float)) else ''} | "
                   f"{fnum(r.get('input_tokens'))} / {fnum(r.get('output_tokens'))} | "
                   f"+{int(r.get('lines_added') or 0)} / -{int(r.get('lines_removed') or 0)} |")
            if all_repos:
                row += f" {r.get('repo_name') or ''} |"
            lines.append(row)
        if len(recent) > 60:
            lines.append(f"| +{len(recent) - 60} more | | | | | | |" + (" |" if all_repos else ""))
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="write team/<handle>/usage.md in the repo")
    ap.add_argument("--all", action="store_true", help="every repo this machine has seen")
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    ap.add_argument("--handle")
    ap.add_argument("--today")
    args = ap.parse_args()

    root = repo_root(args.repo)
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    handle = args.handle or handle_of(root)
    rows = load(args.ledger)
    if not args.all:
        rows = [r for r in rows if same_repo(r, root)]
    text = render(rows, handle=handle, repo_name=root.name, today=today, all_repos=args.all)

    if args.write:
        if args.all:
            sys.exit("oac-usage-report: --write is per repo; drop --all")
        out = root / "team" / handle / "usage.md"
        # A private space keeps its days at evidence/days/ (ADR-136 Rule 8),
        # unless it still has team/<handle>/ from an earlier pack.
        mf = root / ".oac" / "manifest.yml"
        try:
            is_self = mf.is_file() and re.search(r"^plane:\s*self\b", mf.read_text(encoding="utf-8"), re.M) is not None
        except OSError:
            is_self = False
        if is_self and ((root / "evidence" / "days").is_dir() or not (root / "team" / handle).is_dir()):
            out = root / "evidence" / "days" / "usage.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out.relative_to(root)}: {len(rows)} session(s)")
        return 0
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
