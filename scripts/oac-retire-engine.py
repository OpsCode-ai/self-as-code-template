#!/usr/bin/env python3
"""Move the AI-DLC engine out of a plane that no longer runs it, and keep everything that is the person's.

    python3 scripts/oac-retire-engine.py              # show what would move; change nothing
    python3 scripts/oac-retire-engine.py --apply      # move it, by git mv, and stage; you commit with /done

Since the 0.9 pack (ADR-125), Self as Code runs with nothing else installed,
and a business pack ships no engine either. A plane installed from an older
pack still carries it: hundreds of files under `.claude/` and the `aidlc/`
workspace. Adam retired his by hand on 26 October 2026 and found the three
things this script does that a prompt did not: it keeps the person's own
skills, it exempts the archive from the validator, and it deletes the
engine's ignored runtime that `git mv` leaves behind.

WHAT MOVES
    To `archive/aidlc-engine-retired-<date>/`, paths kept under it:
    - `aidlc/`, the workspace
    - under `.claude/`: `agents`, `aidlc-common`, `hooks`, `knowledge`,
      `rules`, `scopes`, `sensors`, `tools`, `settings.local.json.example`
    - under `.claude/skills/`: the engine's own (`aidlc*`, `opscode-sac-*`,
      `opscode-oac-*`), and nothing else

    What a pack shipped is read from `.oac/pack-manifest.previous.json`, the
    manifest the upgrader keeps from the pack before this one. A plane
    upgraded before that file existed falls back to the names above. Either
    way a skill the manifest did not ship is the person's and stays.

WHAT STAYS
    `.claude/CLAUDE.md`, `.claude/commands/`, `.claude/settings.json`,
    `.claude/settings.local.json`, `.claude/checkpoint.json`, and every skill
    of the person's own. Nothing is deleted from git; the archive is the
    record.

WHAT ELSE IT DOES
    - `.claude/settings.json`: every hook entry whose command calls a path
      under `.claude/hooks/` or starts with `bun` is removed, so the next
      session does not open on errors. Nothing else in the file is touched.
    - `.oac/manifest.yml`: an exempt entry for the archive folder, so the
      validator reads it as the record it is and not as 200 new findings.
    - the engine's gitignored runtime left at the old path (`aidlc/` after
      the move, and `.claude/` leftovers): deleted, because `git mv` moves
      tracked files only and the rest would sit there forever.
    - a README in the archive folder saying what it is and when it moved.

Exit 0 when done or when there was nothing to move, 1 on a refusal.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ENGINE_DIRS = ("agents", "aidlc-common", "hooks", "knowledge", "rules", "scopes", "sensors", "tools")
ENGINE_FILES = ("settings.local.json.example",)
ENGINE_SKILL_RE = re.compile(r"^(aidlc|opscode-sac-|opscode-oac-)")
PREVIOUS = Path(".oac") / "pack-manifest.previous.json"
MANIFEST = Path(".oac") / "manifest.yml"


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def shipped_skills(root: Path) -> set[str] | None:
    """The skill names the earlier pack shipped, from the previous manifest,
    or None when there is no such record."""
    p = root / PREVIOUS
    if not p.is_file():
        return None
    try:
        files = json.loads(p.read_text(encoding="utf-8")).get("files", {})
    except (OSError, json.JSONDecodeError):
        return None
    names = set()
    for rel in files:
        m = re.match(r"^\.claude/skills/([^/]+)/", rel)
        if m:
            names.add(m.group(1))
    return names


def what_moves(root: Path) -> tuple[list[Path], list[str]]:
    """(paths to move, relative; the person's skills that stay)."""
    moves: list[Path] = []
    kept: list[str] = []
    if (root / "aidlc").is_dir():
        moves.append(Path("aidlc"))
    dot = root / ".claude"
    for d in ENGINE_DIRS:
        if (dot / d).is_dir():
            moves.append(Path(".claude") / d)
    for f in ENGINE_FILES:
        if (dot / f).is_file():
            moves.append(Path(".claude") / f)
    skills = dot / "skills"
    if skills.is_dir():
        shipped = shipped_skills(root)
        for s in sorted(p for p in skills.iterdir() if p.is_dir()):
            engine = (s.name in shipped) if shipped is not None else bool(ENGINE_SKILL_RE.match(s.name))
            if engine:
                moves.append(Path(".claude") / "skills" / s.name)
            else:
                kept.append(s.name)
    return moves, kept


def clean_hooks(settings: Path) -> int:
    """Drop every hook entry that calls the moved engine. Returns how many."""
    if not settings.is_file():
        return 0
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return 0
    dropped = 0
    for event, entries in list(hooks.items()):
        keep = []
        for entry in entries or []:
            cmds = [h.get("command", "") for h in (entry.get("hooks") or []) if isinstance(h, dict)]
            if any(".claude/hooks/" in c or c.strip().startswith("bun ") for c in cmds):
                dropped += 1
            else:
                keep.append(entry)
        if keep:
            hooks[event] = keep
        else:
            del hooks[event]
    if dropped:
        settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return dropped


def add_exempt(manifest: Path, folder: str, today: str) -> bool:
    if not manifest.is_file():
        return False
    text = manifest.read_text(encoding="utf-8")
    if f"path: {folder}" in text:
        return False
    entry = (f"  - path: {folder}\n    reason: >\n      The AI-DLC engine this repo ran before the engine-free pack, moved\n"
             f"      here on {today} by oac-retire-engine.py. Kept as the record; not authored\n      content.\n")
    if re.search(r"^exempt:\s*$", text, re.M):
        text = re.sub(r"^exempt:\s*\n", "exempt:\n" + entry, text, count=1, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n\nexempt:\n" + entry
    manifest.write_text(text, encoding="utf-8")
    return True


def ignored_leftovers(root: Path, rel: Path) -> bool:
    """True when what is left at `rel` is only ignored files, so it can go."""
    p = root / rel
    if not p.exists():
        return False
    r = git(root, "status", "--porcelain", "--ignored", "--", str(rel))
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    return bool(lines) and all(ln.startswith("!!") for ln in lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="move it; without this, show only")
    ap.add_argument("--root", type=Path, default=Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()))
    ap.add_argument("--date", help="YYYY-MM-DD, for a test")
    a = ap.parse_args(argv)
    root = a.root.resolve()
    today = a.date or datetime.date.today().isoformat()
    if not (root / MANIFEST).is_file():
        print(f"oac-retire-engine: {root} has no {MANIFEST}, so it is not an OaC plane", file=sys.stderr)
        return 1
    if git(root, "rev-parse", "--git-dir").returncode != 0:
        print("oac-retire-engine: not a git repository; this moves with git mv", file=sys.stderr)
        return 1
    moves, kept = what_moves(root)
    if not moves:
        print("nothing to retire: no engine folders here")
        return 0
    folder = f"archive/aidlc-engine-retired-{today}"
    print(f"would move to {folder}/:" if not a.apply else f"moving to {folder}/:")
    for m in moves:
        print(f"  {m.as_posix()}")
    if kept:
        print("your own skills, staying where they are: " + ", ".join(kept))
    if not a.apply:
        print("\nshow only. Add --apply to move it.")
        return 0
    if git(root, "status", "--porcelain", "-uno").stdout.strip():
        print("oac-retire-engine: there is unsaved work; commit or /done first, so this is one move you can read", file=sys.stderr)
        return 1
    dest = root / folder
    dest.mkdir(parents=True, exist_ok=True)
    moved = 0
    for m in moves:
        target = dest / m
        target.parent.mkdir(parents=True, exist_ok=True)
        r = git(root, "mv", "-k", str(m), str(target.relative_to(root)))
        if r.returncode != 0:
            print(f"oac-retire-engine: git mv {m} failed: {(r.stderr or r.stdout).strip()[:200]}", file=sys.stderr)
            return 1
        moved += 1
        if ignored_leftovers(root, m):
            shutil.rmtree(root / m, ignore_errors=True)
    dropped = clean_hooks(root / ".claude" / "settings.json")
    exempted = add_exempt(root / MANIFEST, folder + "/", today)
    (dest / "README.md").write_text(
        f"---\ntitle: \"The AI-DLC engine, retired\"\ntype: index\naudience: internal\n---\n\n"
        f"# The AI-DLC engine, retired\n\nMoved here on {today} by `scripts/oac-retire-engine.py`. This is the engine\n"
        f"this repo ran before the engine-free pack: the folders under `.claude/` and the\n"
        f"`aidlc/` workspace, paths kept as they were. The engine lives in opscode-hq;\n"
        f"this folder is the record of what ran here, and nothing reads it.\n", encoding="utf-8")
    git(root, "add", "--", folder, str(MANIFEST), ".claude/settings.json")
    print(f"\nmoved {moved} folder(s) or file(s); {dropped} hook entr{'y' if dropped == 1 else 'ies'} dropped; "
          f"exempt entry {'added' if exempted else 'already there'}; README written.")
    print("staged. Read the diff, then commit it with /done. Then restart Claude Code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
