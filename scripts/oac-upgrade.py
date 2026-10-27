#!/usr/bin/env python3
"""Upgrade an installed OaC plane to a newer pack without losing what you wrote.

    python3 scripts/oac-upgrade.py --from ~/Downloads/self-as-code-pack            # report, change nothing
    python3 scripts/oac-upgrade.py --from ~/Downloads/self-as-code-pack --apply    # write
    python3 scripts/oac-upgrade.py --from <pack> --apply --take scripts/oac-validate.py

Every plane starts as a pack: a zip, unzipped once, then edited for months.
The pack keeps moving (a new stage, a fixed script, a better hook) and until
today there was no way to take the new pack without either overwriting the
operator's work or copying files by hand. This closes it.

The rule is three classes of file, decided by path, and one question per
file: has it changed since the pack that installed it?

  engine    `.claude/` except CLAUDE.md, settings*.json and commands/.
            Shipped by the AI-DLC engine and the OpsCode plugin, never edited
            by hand, so the new pack's copy always wins. This is also how a
            plugin upgrade lands, because the engine's own compose hook
            refuses to overwrite a file it already wrote.
  tooling   scripts/, .claude/commands/, .claude/CLAUDE.md, .githooks/, the
            method files under aidlc/spaces/*/memory/, WORKING.md, MODES.md,
            STATUSLINE.md, INSTALL.md, specs/, the READMEs the pack seeds in
            team/ and notable-plans/, decisions/template.md, .gitignore.
            Ours to ship and yours to edit. Overwritten only if your copy is
            byte-identical to the pack that installed it; otherwise kept, and
            named in the report, so you decide with --take.
  yours     Everything else: self-as-code.md, systems/register.md, your
            context-core/, decisions/, team/, CLAUDE.md, README.md, the
            manifest, the changelog. Never written if present. Added if the
            new pack seeds one you do not have.

The pack that installed you is known from `.oac/pack-manifest.json`, which
every pack cut on or after 24 September 2026 carries: one hash per file.
A plane installed from an older pack has no old manifest, so its first
upgrade is additive (engine refreshed, missing files added, everything that
exists and differs kept and named). From then on it has one.

Never touches git. Refuses to run on a dirty tree, so the upgrade is one
reviewable diff you commit with /done. Exit 0 clean, 1 on a refusal, 2 on
a bad invocation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

MANIFEST_REL = Path(".oac") / "pack-manifest.json"
PLANE_MANIFEST_REL = Path(".oac") / "manifest.yml"

ENGINE_KEEP = {".claude/CLAUDE.md"}
ENGINE_KEEP_PREFIX = (".claude/commands/",)
ENGINE_KEEP_GLOB_PREFIX = ".claude/settings"   # settings.json, settings.local.json

TOOLING_EXACT = {
    ".claude/CLAUDE.md", "WORKING.md", "MODES.md", "STATUSLINE.md", "INSTALL.md",
    "team/README.md", "notable-plans/README.md", "decisions/template.md", ".gitignore",
    # The business pack the self pack carries for /sac deploy: never hand-edited,
    # so a newer self pack always brings the newer business pack with it.
    ".oac/operations-as-code-pack.zip",
}
TOOLING_PREFIX = ("scripts/", ".claude/commands/", ".githooks/", "specs/")
TOOLING_METHOD = ("aidlc/spaces/",)          # .../memory/**.md is the method layer


SETTINGS_REL = ".claude/settings.json"
# Everything in settings.json is the operator's (model, permissions, env)
# except the session hooks, which the merge adds when missing. The pack's
# `companyAnnouncements` is a first-open seed for a fresh unzip only: a plane
# that has run a session keeps its banner in the gitignored
# settings.local.json, and copying the seed back would put two banners in
# play, which Claude Code picks between at random (7 October 2026). So the
# upgrader never writes it; the plane's next session moves out any old copy.


def _load_json(path: Path) -> dict | None:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def merged_settings(pack: Path, plane: Path) -> dict | None:
    """The plane's settings.json with the pack's session hooks folded in, and
    never the pack's announcement. None when either file is unreadable, so
    the caller leaves the file alone rather than guessing."""
    theirs, mine = _load_json(pack), _load_json(plane)
    if theirs is None or mine is None:
        return None
    out = json.loads(json.dumps(mine))
    mine_hooks = out.setdefault("hooks", {})
    for event, entries in (theirs.get("hooks") or {}).items():
        have = [json.dumps(e, sort_keys=True) for e in mine_hooks.get(event, [])]
        for e in entries:
            if json.dumps(e, sort_keys=True) not in have:
                mine_hooks.setdefault(event, []).append(e)
    return out


def settings_needs_merge(pack: Path, plane: Path) -> bool:
    merged = merged_settings(pack, plane)
    return merged is not None and merged != _load_json(plane)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(rel: str) -> str:
    """engine | tooling | yours, by path alone."""
    if rel.startswith(".claude/"):
        if rel in ENGINE_KEEP or rel.startswith(ENGINE_KEEP_PREFIX) or rel.startswith(ENGINE_KEEP_GLOB_PREFIX):
            return "tooling" if rel in TOOLING_EXACT or rel.startswith(TOOLING_PREFIX) else "yours"
        return "engine"
    if rel in TOOLING_EXACT or rel.startswith(TOOLING_PREFIX):
        return "tooling"
    if rel.startswith(TOOLING_METHOD) and "/memory/" in rel:
        return "tooling"
    return "yours"


def read_manifest(path: Path) -> dict | None:
    """The manifest, with `files` normalised to {rel: sha256-hex}.

    On disk each file is an object, `{"sha256": "..."}`, hash on its own
    line, so a path containing 'api' or 'key' never shares a line with a
    64-hex value and gitleaks' generic-api-key rule stays quiet. A flat
    {rel: hex} table is read too.
    """
    if not path.is_file():
        return None
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"oac-upgrade: {path} is not valid JSON ({e})")
    if not isinstance(d.get("files"), dict):
        sys.exit(f"oac-upgrade: {path} has no files table")
    d["files"] = {rel: (v["sha256"] if isinstance(v, dict) else v) for rel, v in d["files"].items()}
    return d


def plane_of(root: Path) -> str | None:
    m = root / PLANE_MANIFEST_REL
    if not m.is_file():
        return None
    for line in m.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("plane:"):
            return line.partition(":")[2].strip() or None
    return None


def git_dirty(root: Path) -> bool | None:
    """True dirty, False clean, None not a git repo."""
    r = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return bool(r.stdout.strip())


# SPADE (ADR-126, OaC 1.11). A plane made before 1.11 has history/ and library/.
# The pack now ships archive/ and evidence/; adding them beside the old folders
# would give a person two folders for one job. The old name is read as the new
# one, and a person's folders move only when they move them.
LEGACY_FOLDERS = {"archive/": "history/", "evidence/": "library/"}


def legacy_home(target: Path, rel: str) -> str | None:
    """The older folder this new SPADE path lives in on this plane, if any."""
    for new_dir, old_dir in LEGACY_FOLDERS.items():
        if rel.startswith(new_dir) and not (target / new_dir).exists() and (target / old_dir).is_dir():
            return old_dir
    return None


def plan(src: Path, target: Path, new: dict, old: dict | None, take: set[str],
         skip: set[str] = frozenset(), remembered: set[str] = frozenset()) -> dict[str, list]:
    """Decide every file. Returns lists keyed by outcome; nothing is written.
    `remembered` is the part of `skip` the plane's manifest carried in from an
    earlier upgrade, so the report can say where a skip came from."""
    out: dict[str, list] = {
        "add": [], "engine": [], "update": [], "unchanged": [],
        "kept": [], "kept-pack-unchanged": [], "take": [], "gone": [], "skip": [], "skipped": [],
        "skipped_remembered": [], "clash": [], "merge": [], "legacy": [],
    }
    old_files = (old or {}).get("files", {})
    for rel, new_hash in sorted(new["files"].items()):
        if rel == MANIFEST_REL.as_posix():
            continue
        cls = classify(rel)
        dest = target / rel
        if rel in skip:
            out["skipped_remembered" if rel in remembered else "skipped"].append((rel, cls))
            continue
        # A pack command whose name a skill in this plane already owns would
        # give two commands of one name (Adam's /start, 26 October 2026). The
        # plane's own skill wins; the pack's copy is not written and is named.
        if rel.startswith(".claude/commands/") and (target / ".claude" / "skills" / Path(rel).stem).is_dir():
            out["clash"].append((rel, cls))
            continue
        if not dest.exists():
            if legacy_home(target, rel):
                out["legacy"].append((rel, cls))
                continue
            out["add"].append((rel, cls))
            continue
        cur = sha256(dest)
        if cur == new_hash:
            out["unchanged"].append((rel, cls))
            continue
        if rel in take:
            out["take"].append((rel, cls))
            continue
        if cls == "engine":
            out["engine"].append((rel, cls))
            continue
        if rel == SETTINGS_REL:
            # Yours, but two keys in it are the pack's: the announcement the
            # operator reads at session start, and the session hooks the pack
            # ships. Merge those in; touch nothing else in the file.
            out["merge" if settings_needs_merge(src / rel, dest) else "unchanged"].append((rel, cls))
            continue
        if cls == "yours":
            out["skip"].append((rel, cls))
            continue
        # tooling: overwrite only when untouched since the pack that installed it
        old_hash = old_files.get(rel)
        if old_hash is not None and cur == old_hash:
            out["update"].append((rel, cls))
        elif old_hash is not None and old_hash == new_hash:
            out["kept-pack-unchanged"].append((rel, cls))
        else:
            out["kept"].append((rel, cls))
    for rel in sorted(old_files):
        if rel not in new["files"] and rel != MANIFEST_REL.as_posix() and (target / rel).exists():
            out["gone"].append((rel, classify(rel)))
    return out


def copy_one(src: Path, target: Path, rel: str) -> None:
    s, d = src / rel, target / rel
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(s, d)
    mode = s.stat().st_mode
    if rel.startswith("scripts/") and (rel.endswith(".py") or rel.endswith(".sh")) or rel.endswith("/pre-commit"):
        mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    os.chmod(d, stat.S_IMODE(mode))


def report(p: dict[str, list], new: dict, old: dict | None, apply: bool) -> None:
    verb = "wrote" if apply else "would write"
    print(f"pack:   {new.get('pack', '?')}  plane: {new.get('plane', '?')}  content: {str(new.get('content_id', '?'))[:12]}")
    print(f"from:   {'pack ' + str(old.get('content_id', '?'))[:12] if old else 'no pack manifest (first upgrade: additive only)'}")
    print()
    rows = (
        ("add", f"{verb}, new in this pack"),
        ("engine", f"{verb}, engine file refreshed"),
        ("update", f"{verb}, tooling unchanged since your pack"),
        ("take", f"{verb}, --take"),
        ("merge", f"{verb}, the pack's announcement and session hooks merged in; the rest of the file is yours"),
        ("kept", "KEPT: you changed it and the pack changed it too. Diff it; --take <path> to take the pack's"),
        ("kept-pack-unchanged", "kept: you changed it, the pack did not"),
        ("skip", "kept: yours, never written"),
        ("skipped", "skipped: --skip, this plane does not want it"),
        ("skipped_remembered", "skipped, remembered from an earlier upgrade of this plane; --take <path> to undo"),
        ("clash", "NOT written: a skill of the same name in .claude/skills/ owns that command; archive the skill, or --skip the pack's"),
        ("gone", "left in place: no longer shipped by the pack"),
        ("legacy", "not added: your history/ is read as archive/ and library/ as evidence/ (SPADE). Rename them when you like"),
    )
    for key, label in rows:
        items = p[key]
        if not items:
            continue
        print(f"{label} ({len(items)})")
        for rel, cls in items:
            print(f"  {cls:8} {rel}")
        print()
    print(f"unchanged: {len(p['unchanged'])}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--from", dest="src", required=True, type=Path,
                    help="the unzipped new pack (the folder holding .oac/pack-manifest.json)")
    ap.add_argument("--target", type=Path, default=None,
                    help="the plane to upgrade (default: the repo this script lives in, else cwd)")
    ap.add_argument("--apply", action="store_true", help="write. Without it, report only")
    ap.add_argument("--take", action="append", default=[], metavar="PATH",
                    help="take the pack's copy of a tooling file you had changed (repeatable)")
    ap.add_argument("--skip", action="append", default=[], metavar="PATH",
                    help="leave this pack file out entirely, for example a command this plane has its own version of (repeatable)")
    ap.add_argument("--allow-dirty", action="store_true", help="run on an uncommitted tree anyway")
    args = ap.parse_args()

    src = args.src.expanduser().resolve()
    if (src / MANIFEST_REL).is_file() is False and (src.name.endswith(".zip")):
        print("oac-upgrade: unzip the pack first, then point --from at the folder", file=sys.stderr)
        return 2
    new = read_manifest(src / MANIFEST_REL)
    if new is None:
        print(f"oac-upgrade: {src} has no {MANIFEST_REL}. Packs cut before 24 September 2026 cannot be "
              "upgraded from; download the current pack.", file=sys.stderr)
        return 2

    if args.target:
        target = args.target.expanduser().resolve()
    else:
        here = Path(__file__).resolve().parent.parent
        target = here if (here / PLANE_MANIFEST_REL).is_file() else Path.cwd().resolve()
    if not (target / PLANE_MANIFEST_REL).is_file():
        print(f"oac-upgrade: {target} has no {PLANE_MANIFEST_REL}, so it is not an OaC plane", file=sys.stderr)
        return 1
    if src == target:
        print("oac-upgrade: --from and the target are the same folder", file=sys.stderr)
        return 2

    have, want = plane_of(target), new.get("plane")
    if want and have != want:
        print(f"oac-upgrade: this pack is for a {want} plane and {target} declares plane: {have or 'absent'}. "
              "Use the other pack.", file=sys.stderr)
        return 1

    dirty = git_dirty(target)
    if dirty and args.apply and not args.allow_dirty:
        print(f"oac-upgrade: {target} has uncommitted changes. Commit or /done first, so the upgrade "
              "is one diff you can read. (--allow-dirty to proceed anyway)", file=sys.stderr)
        return 1

    old = read_manifest(target / MANIFEST_REL)
    take = {t.strip("/") for t in args.take}
    cli_skip = {t.strip("/") for t in args.skip}
    for flag, names in (("--take", take), ("--skip", cli_skip)):
        unknown = [t for t in names if t not in new["files"]]
        if unknown:
            print(f"oac-upgrade: {flag} names files the pack does not ship: {', '.join(unknown)}", file=sys.stderr)
            return 2
    # A skip is a decision about this plane, not about one upgrade: a plane
    # that keeps its own /start keeps it next time too. The plane's manifest
    # remembers every skip ever given, and --take of a remembered skip undoes it.
    skip = (set((old or {}).get("skip", [])) | cli_skip) - take
    if cli_skip & take:
        print(f"oac-upgrade: --take and --skip name the same file: {', '.join(sorted(cli_skip & take))}", file=sys.stderr)
        return 2

    remembered = set((old or {}).get("skip", [])) - take
    p = plan(src, target, new, old, take, skip, remembered)
    report(p, new, old, args.apply)

    if not args.apply:
        print("\nreport only. Add --apply to write.")
        return 0

    written = 0
    for key in ("add", "engine", "update", "take"):
        for rel, _ in p[key]:
            copy_one(src, target, rel)
            written += 1
    for rel, _ in p["merge"]:
        merged = merged_settings(src / rel, target / rel)
        if merged is not None:
            (target / rel).write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
            written += 1
    (target / MANIFEST_REL).parent.mkdir(parents=True, exist_ok=True)
    # Keep the manifest of the pack before this one beside the new one, so a
    # later step (retiring the engine, telling a shipped file from a personal
    # one) can still read what the earlier pack shipped.
    if old is not None and (target / MANIFEST_REL).is_file() and old.get("content_id") != new.get("content_id"):
        shutil.copyfile(target / MANIFEST_REL, target / MANIFEST_REL.with_name("pack-manifest.previous.json"))
    recorded = json.loads((src / MANIFEST_REL).read_text(encoding="utf-8"))
    recorded["skip"] = sorted(skip)
    (target / MANIFEST_REL).write_text(json.dumps(recorded, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {written} file(s) and {MANIFEST_REL}" + (f" (remembering {len(skip)} skip(s))." if skip else "."))
    print("next:")
    print("  1. read the diff, then commit it with /done")
    print("  2. restart Claude Code")
    print("  3. python3 scripts/install-oac-statusline.py && python3 scripts/install-oac-branch-guard.py")
    print("  4. bash scripts/install-shortcuts.sh, once, if the one word (sac or oac) does not open this folder yet")
    if p["kept"]:
        print(f"  4. {len(p['kept'])} tooling file(s) kept because you changed them; diff each against the pack")
    return 0


if __name__ == "__main__":
    sys.exit(main())
