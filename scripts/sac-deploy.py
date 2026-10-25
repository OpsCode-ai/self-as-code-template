#!/usr/bin/env python3
"""Make one business's repo from your Self as Code (`/sac deploy <business>`).

WHY THIS EXISTS
    Self as Code captures every business a person runs: one `###` block each
    under `## the baseline`, carrying the lines its own repo is set up from
    (`Kind:`, `Years:`, `People:`, `Runs on:`, `Build first:`, `Serves why:`),
    and under `## the split` the statements they chose to share with it.
    Until this file, 'deploy' was a page of instructions: unzip the business
    pack by hand, rename it, go back to the private repo, send the split, then
    open the new repo and run /oac. Adam, 25 October 2026: Self as Code feeds
    Operations as Code; each business repo fetches its initial data from Self
    as Code when it is set up. This is that, as one command. The Melbourne
    plan's bridge; ADR-125 Rule 2; the Self as Code standard, section 6.1.

WHAT IT DOES
    1. Finds the business in the plan (its `###` block) or in the manifest's
       `operations:`. Refuses a name the plan does not know.
    2. Unpacks the Operations as Code pack into ~/projects/<business>-ops. The
       pack rides inside the Self as Code pack (.oac/operations-as-code-pack.zip)
       so this works offline; --fetch refreshes that copy from plans.opscode.ai;
       --pack names a folder or a zip. Never a second scaffold: the pack is the
       one build-oac-packs.py makes.
    3. Names the repo after the business and points it back at this private
       repo (`parent_operation` in its manifest, a pointer, never a path).
    4. Writes the seeds before the first commit, directly, because the split's
       own tool refuses a repo on main and this repo has no branch yet:
         context-core/strategic-identity/from-self-as-code.md
             the statements routed to this business, rendered by the split's
             own renderer, plus the setup lines under 'Set up from'
         systems/register.md
             one Software row per thing in 'runs on', to confirm; the 'build
             first' line as the first Processes row, manual
         systems/team.md
             the owner's row, and the 'people' line to fill the rest from
    5. git init on main, the hook on, one commit: 'Operations as Code: day one'.
    6. The private hub on GitHub, through the pack's own oac-hub.py, when gh is
       signed in. Otherwise the repo stays on this laptop and it says so.
    7. Writes the link back: this repo's manifest lists the new repo under
       `operations:`, committed by path.

WHAT CROSSES, AND WHAT NEVER DOES
    Only the setup lines of that business's block and the split rows routed to
    it. Not the person's words about the business, not any other heading, not
    a file. Nothing `audience: owner` is written and no file from this repo is
    copied. --show prints exactly what would cross and writes nothing.

Usage:
    python3 scripts/sac-deploy.py <business> --show
    python3 scripts/sac-deploy.py <business> [--dest DIR] [--pack DIR|ZIP] [--fetch] [--local] [--owner ORG]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK_NAME = "operations-as-code-pack"
PACK_ZIP = Path(".oac") / f"{PACK_NAME}.zip"
PACK_URL = f"https://plans.opscode.ai/nz-cohort/pack/{PACK_NAME}.zip"
# Cloudflare answers Python's default user agent with a 403 (plans-live-mirror.py found it).
USER_AGENT = "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
PROJECTS = Path.home() / "projects"
DAY_ONE = "Operations as Code: day one"
SETUP_LINES = ("Kind", "Years", "People", "Runs on", "Build first", "Serves why")
PLACEHOLDER_PARENT = "first-last-ops"

TEAM_MD = """---
title: "Team"
type: reference
audience: internal
status: seeded
lifecycle: living
updated: {today}
summary: "Who works in this business today and what each person is responsible for, then the roles it needs next."
topics: [operations]
tags: [oac, team, seeded]
---

# Team

Who works in this business today, and what each person is responsible for.
One row per person. Then the roles that do not exist yet, because that
question is where the next hire and the AI staff come in.
{people_line}
## People

| Name | Role | Responsible for |
|---|---|---|
| {owner} | owner | TO FILL IN |

## Future

The roles this business needs next. *TO FILL IN [source: head-only].*

| Role | Why | When |
|---|---|---|
"""

INSTALL_MD = """---
title: "How this repo was made"
type: guide
audience: internal
---

# How this repo was made

`/sac deploy` made it on {today}, from {owner}'s Self as Code, with the
Operations as Code pack ({pack_id}). Nothing to install: git is set up with the
hook on, the first commit is in, and what the owner chose to share is in
`context-core/strategic-identity/from-self-as-code.md`.

On each machine that opens it, once:

- the bottom line of Claude Code: `python3 scripts/install-oac-statusline.py`
- the one word: `bash scripts/install-shortcuts.sh`, then `oac` in a new
  Terminal window opens this folder with Claude Code running

Then `/oac`. It reads what was shared first and never asks for it again.
"""


# ── The other tools, loaded beside this one ──────────────────────────────────

def _load(name: str, filename: str):
    p = HERE / filename
    if not p.is_file():
        sys.exit(f"{filename} is missing beside this script; the pack ships it")
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


split = _load("sac_split", "self-as-code-split.py")
meeting = _load("sac_meeting", "sac-meeting.py")
dashboard = _load("sac_dashboard", "sac-dashboard.py")


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


def detail(p: subprocess.CompletedProcess) -> str:
    return ((p.stderr or "").strip() or (p.stdout or "").strip() or "no output")[:400]


def bare(slug: str) -> str:
    """A business and its repo share a name: `acme` and `acme-ops` are one."""
    return slug[:-4] if slug.endswith("-ops") and len(slug) > 4 else slug


def handle(root: Path, owner: str) -> str:
    uj = root / ".claude" / "user.json"
    if uj.is_file():
        try:
            h = json.loads(uj.read_text(encoding="utf-8")).get("team_member", "")
            if h:
                return str(h).strip().lower()
        except ValueError:
            pass
    first = re.sub(r"[^a-z0-9]+", "", owner.split()[0].lower()) if owner.split() else ""
    return first or "me"


# ── The plan: which business, what crosses ───────────────────────────────────

def plane_of(root: Path) -> str | None:
    m = root / ".oac" / "manifest.yml"
    if not m.is_file():
        return None
    for ln in m.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.startswith("plane:"):
            return ln.partition(":")[2].strip().strip("'\"")
    return None


def candidates(root: Path, spine: Path | None) -> list[dict]:
    """Every business the plan names: its `###` blocks first, then the
    manifest's `operations:`, one entry per business whatever the spelling."""
    out: list[dict] = []
    seen: set[str] = set()
    plan = dashboard.read_plan(spine, root)
    for b in plan["businesses"]:
        slug = bare(meeting.slugify(b["name"]))
        if slug and slug not in seen:
            seen.add(slug)
            setup = {k: b["setup"][k.lower()] for k in SETUP_LINES if k.lower() in b["setup"]}
            out.append({"name": b["name"], "slug": slug, "setup": setup, "in_plan": True})
    for op in meeting.manifest_operations(root):
        slug = bare(meeting.slugify(op))
        if slug and slug not in seen:
            seen.add(slug)
            out.append({"name": op, "slug": slug, "setup": {}, "in_plan": False})
    return out


def pick(cands: list[dict], want: str) -> dict | None:
    w = bare(meeting.slugify(want))
    if not w:
        return None
    exact = [c for c in cands if c["slug"] == w]
    if len(exact) == 1:
        return exact[0]
    part = [c for c in cands if w in c["slug"] or c["slug"] in w]
    return part[0] if len(part) == 1 else None


def routed_to(rows: list[dict], slug: str) -> list[dict]:
    return [r for r in rows if r["routing"] == "routes-to" and bare(meeting.slugify(r["unit"])) == slug]


def software_items(runs_on: str) -> list[str]:
    """'Xero, Gmail and a shared Google Drive' -> ['Xero', 'Gmail', 'a shared Google Drive']."""
    parts = re.split(r",|;|\band\b|&|\+|\bplus\b", runs_on)
    out: list[str] = []
    for p in parts:
        p = re.sub(r"^(roughly|mostly|just|then|also|some)\s+", "", p.strip(" ."), flags=re.I).strip()
        if p and p.lower() not in ("etc", "nothing", "not much", "that's it") and p.lower() not in {o.lower() for o in out}:
            out.append(p)
    return out


# ── The pack ─────────────────────────────────────────────────────────────────

def download(dest: Path) -> None:
    req = urllib.request.Request(PACK_URL, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    except Exception as e:  # noqa: BLE001
        sys.exit(f"could not fetch the business pack from {PACK_URL}: {e}")
    if not zipfile.is_zipfile(io.BytesIO(data)):
        sys.exit(f"what came back from {PACK_URL} is not a zip")
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(data)
    part.replace(dest)


def locate_pack(root: Path, explicit: str | None, fetch: bool) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.exists():
            sys.exit(f"--pack {explicit}: nothing there")
        return p
    cached = root / PACK_ZIP
    if fetch:
        download(cached)
        return cached
    return cached if cached.is_file() else None


def _safe_names(zf: zipfile.ZipFile) -> str:
    names = zf.namelist()
    tops: set[str] = set()
    for n in names:
        parts = n.split("/")
        if n.startswith("/") or ".." in parts or not parts[0]:
            sys.exit(f"the zip holds an unsafe path: {n}")
        tops.add(parts[0])
    if len(tops) != 1:
        sys.exit("the zip does not hold one top folder, so it is not an OpsCode pack")
    return tops.pop()


def unpack(pack: Path, dest: Path) -> dict:
    """The pack's files at dest, with the modes git needs. Returns the pack manifest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if pack.is_dir():
        shutil.copytree(pack, dest)
    else:
        with zipfile.ZipFile(pack) as zf:
            top = _safe_names(zf)
            with tempfile.TemporaryDirectory(dir=dest.parent, prefix=".sac-deploy-") as tmp:
                zf.extractall(tmp)
                shutil.move(str(Path(tmp) / top), str(dest))
    for p in dest.rglob("*"):
        if p.is_file() and (p.suffix == ".sh" or p.name == "pre-commit"):
            p.chmod(0o755)
    mf = dest / ".oac" / "pack-manifest.json"
    try:
        manifest = json.loads(mf.read_text(encoding="utf-8")) if mf.is_file() else {}
    except ValueError:
        manifest = {}
    if plane_of(dest) != "business":
        shutil.rmtree(dest, ignore_errors=True)
        sys.exit(f"{pack} is not the Operations as Code pack (no business manifest inside), so nothing was made")
    return manifest


# ── Naming and seeding ───────────────────────────────────────────────────────

def name_it(text: str, name: str) -> str:
    """'this business' becomes the name, in the title line and the first heading only."""
    safe = name.replace("\\", "\\\\").replace('"', '\\"')
    lines = text.split("\n")
    did_title = did_h1 = False
    for i, ln in enumerate(lines):
        if not did_title and ln.startswith("title:") and "this business" in ln:
            lines[i] = ln.replace("this business", safe, 1)
            did_title = True
        elif not did_h1 and ln.startswith("# ") and "this business" in ln:
            lines[i] = ln.replace("this business", name, 1)
            did_h1 = True
    return "\n".join(lines)


def set_parent(text: str, parent: str) -> str:
    if re.search(r"^parent_operation:.*$", text, re.M):
        return re.sub(r"^parent_operation:.*$", f"parent_operation: {parent}", text, count=1, flags=re.M)
    return re.sub(r"^(plane:\s*business\s*)$", rf"\1\nparent_operation: {parent}", text, count=1, flags=re.M)


def insert_rows(text: str, heading: str, rows: list[str]) -> tuple[str, bool]:
    """Rows into the first table under `## {heading}`, straight after its separator."""
    lines = text.split("\n")
    start = next((i for i, ln in enumerate(lines) if re.match(rf"^##\s+{re.escape(heading)}\s*$", ln, re.I)), None)
    if start is None:
        return text, False
    i = start + 1
    while i < len(lines) - 1:
        if lines[i].startswith("## "):
            return text, False
        if lines[i].strip().startswith("|") and split.SEPARATOR_RE.match(lines[i + 1].strip()):
            lines[i + 2:i + 2] = rows
            return "\n".join(lines), True
        i += 1
    return text, False


def seed_register(text: str, items: list[str], build_first: str | None, owner_first: str, today: str) -> tuple[str, int, int]:
    text = re.sub(r"^last_updated:.*$", f"last_updated: {today}", text, count=1, flags=re.M)
    sw = [f"| {it} | TO CONFIRM, named in Self as Code under 'runs on' | {owner_first} | | | keep |" for it in items]
    n_sw = 0
    if sw:
        text, ok = insert_rows(text, "Software", sw)
        n_sw = len(sw) if ok else 0
    n_pr = 0
    if build_first:
        row = f"| {build_first} | TO CONFIRM, from Self as Code under 'build first' | manual | {owner_first} | | keep |"
        text, ok = insert_rows(text, "Processes", [row])
        n_pr = 1 if ok else 0
    return text, n_sw, n_pr


def add_operation(text: str, name: str) -> tuple[str, bool]:
    """`operations:` in a self plane's manifest gains one name, flow style."""
    m = re.search(r"^operations:[ \t]*\[([^\]]*)\][ \t]*$", text, re.M)
    if m:
        items = [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]
        if name in items:
            return text, False
        items.append(name)
        return text[:m.start()] + f"operations: [{', '.join(items)}]" + text[m.end():], True
    m = re.search(r"^operations:[ \t]*\n((?:[ \t]+-[^\n]*\n?)*)", text, re.M)
    if m:
        items = [ln.split("-", 1)[1].strip().strip("'\"") for ln in m.group(1).splitlines() if ln.strip()]
        if name in items:
            return text, False
        items.append(name)
        return text[:m.start()] + f"operations: [{', '.join(items)}]\n" + text[m.end():], True
    plane = re.search(r"^plane:.*$", text, re.M)
    if plane:
        return text[:plane.end()] + f"\noperations: [{name}]" + text[plane.end():], True
    return text.rstrip("\n") + f"\noperations: [{name}]\n", True


# ── The run ──────────────────────────────────────────────────────────────────

def say_crossing(biz: dict, groups: dict[str, list[dict]]) -> None:
    if biz["setup"]:
        print(f"  from its block in your plan, {len(biz['setup'])} setup line{'s' if len(biz['setup']) != 1 else ''}:")
        for k, v in biz["setup"].items():
            print(f"    {k}: {v}")
    else:
        print("  no setup lines in your plan for it (Kind, Years, People, Runs on, Build first, Serves why), so the register starts empty")
    n = sum(len(v) for v in groups.values())
    if n:
        print(f"  from what you chose to share, {n} statement{'s' if n != 1 else ''}:")
        for venture, rows in groups.items():
            for r in rows:
                where = f" ({venture})" if venture else ""
                print(f"    - {r['slice']}{where}")
    else:
        print("  nothing shared with it yet under `## the split`; the file says so and /oac carries on")
    print("  nothing else from this repo crosses: not your words about it, not another heading, not a file")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Make one business's repo from your Self as Code.")
    ap.add_argument("business", help="the business, as your plan names it")
    ap.add_argument("--root", default=".", help="your private repo (default: here)")
    ap.add_argument("--show", action="store_true", help="say what would cross and where; write nothing")
    ap.add_argument("--dest", type=Path, help="where to make it (default: ~/projects/<business>-ops)")
    ap.add_argument("--pack", help="the Operations as Code pack, a folder or a zip (default: the copy in .oac/)")
    ap.add_argument("--fetch", action="store_true", help="refresh the copy in .oac/ from plans.opscode.ai first")
    ap.add_argument("--local", action="store_true", help="make it on this laptop only; no GitHub")
    ap.add_argument("--owner", help="a GitHub organisation to own the repo (default: your account)")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()

    plane = plane_of(root)
    if plane != "self":
        print(f"this is not your private repo (its manifest says plane: {plane or 'nothing'}). Run this where /sac runs.")
        return 1
    spine, rows, errors = split.read_split(root)
    if spine is None:
        print(f"  {errors[0]}")
        return 1
    if errors:
        print(f"the sharing table in your plan has {len(errors)} problem(s); fix them first:")
        for e in errors:
            print(f"  - {e}")
        print("  check: python3 scripts/self-as-code-split.py --check")
        return 1
    rows = rows or []

    cands = candidates(root, spine)
    biz = pick(cands, a.business)
    if biz is None:
        names = ", ".join(c["name"] for c in cands) or "none yet"
        print(f"your plan does not name a business called '{a.business}'. It names: {names}.")
        print("  Add it under `## the baseline` with /sac, or name one of those.")
        return 1
    slug = biz["slug"]
    repo_name = f"{slug}-ops"
    dest = (a.dest.expanduser().resolve() if a.dest else PROJECTS / repo_name)
    owner = meeting.owner_name(root)
    owner_first = owner.split()[0] if owner.split() else owner
    today = _dt.date.today().isoformat()

    chosen = routed_to(rows, slug)
    groups: dict[str, list[dict]] = {}
    for r in chosen:
        groups.setdefault(r["venture"], []).append(r)
    if biz["setup"]:
        groups.setdefault("", [])

    print(f"{biz['name']}: its own repo at {dest}")
    if not biz["in_plan"]:
        print("  named in your manifest but with no block in your plan, so no setup lines")
    say_crossing(biz, groups)

    if dest.exists():
        print(f"\n  {dest} already exists, so nothing was made. Open it and run /oac there, or pick another place with --dest.")
        return 1
    existing = meeting.find_repo(slug)
    if existing is not None and existing != dest:
        print(f"\n  {biz['name']} already has a repo at {existing}. Open it and run /oac there.")
        return 1

    pack = None if a.show else locate_pack(root, a.pack, a.fetch)
    if a.show:
        cached = root / PACK_ZIP
        where = f"the copy in {PACK_ZIP.as_posix()}" if cached.is_file() else f"no copy in {PACK_ZIP.as_posix()} yet, so run with --fetch or --pack"
        print(f"  the business pack: {where}")
        print("\nshown only; nothing written. Run again without --show to make it.")
        return 0
    if pack is None:
        print(f"\n  no business pack here ({PACK_ZIP.as_posix()}). Run again with --fetch to get it from plans.opscode.ai, or --pack <folder or zip>.")
        return 1

    manifest = unpack(pack, dest)
    pack_id = (manifest.get("content_id") or "unknown")[:12]

    # Name it and point it home.
    for rel in ("README.md", "CLAUDE.md"):
        f = dest / rel
        if f.is_file():
            f.write_text(name_it(f.read_text(encoding="utf-8"), biz["name"]), encoding="utf-8")
    mf = dest / ".oac" / "manifest.yml"
    mf.write_text(set_parent(mf.read_text(encoding="utf-8"), root.name), encoding="utf-8")
    h = handle(root, owner)
    logs = dest / "team" / h / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / ".gitkeep").touch()

    # The seeds.
    written: list[str] = []
    for venture, vrows in groups.items():
        rel = split.DEST_DIR / venture / split.DEST_FILE if venture else split.DEST_DIR / split.DEST_FILE
        content = split.render(vrows, slug, venture, today,
                               setup=biz["setup"] if not venture else None, by="sac-deploy.py")
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_text(content, encoding="utf-8")
        written.append(rel.as_posix())
    items = software_items(biz["setup"].get("Runs on", "")) if biz["setup"].get("Runs on") else []
    reg = dest / "systems" / "register.md"
    n_sw = n_pr = 0
    if reg.is_file():
        text, n_sw, n_pr = seed_register(reg.read_text(encoding="utf-8"), items, biz["setup"].get("Build first"), owner_first, today)
        reg.write_text(text, encoding="utf-8")
    people = biz["setup"].get("People")
    people_line = f"\nSelf as Code says: {people}. Add a row for each. [source: self-as-code, 'people']\n" if people else ""
    (dest / "systems" / "team.md").write_text(
        TEAM_MD.format(today=today, owner=owner, people_line=people_line), encoding="utf-8")
    (dest / "INSTALL.md").write_text(INSTALL_MD.format(today=today, owner=owner, pack_id=pack_id), encoding="utf-8")
    pm = dest / ".oac" / "pack-manifest.json"
    if manifest:
        manifest["skip"] = sorted(set(manifest.get("skip", [])) | {"INSTALL.md"})
        pm.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    ch = dest / "CHANGELOG.md"
    if ch.is_file():
        n_rows = sum(len(v) for v in groups.values())
        ch.write_text(ch.read_text(encoding="utf-8").rstrip("\n") + "\n\n"
                      f"Set up by `/sac deploy` on {today} from {owner}'s Self as Code: "
                      f"{len(biz['setup'])} setup line(s) and {n_rows} shared statement(s) in "
                      f"`context-core/strategic-identity/`, {n_sw} software row(s) to confirm and "
                      f"{n_pr} process in `systems/register.md`, and `systems/team.md`.\n", encoding="utf-8")

    # Day one, on main, through the hook.
    r = git(dest, "init", "-q", "-b", "main")
    if r.returncode != 0:
        git(dest, "init", "-q")
        git(dest, "symbolic-ref", "HEAD", "refs/heads/main")
    git(dest, "config", "core.hooksPath", ".githooks")
    git(dest, "add", "-A")
    c = git(dest, "commit", "-q", "-m", DAY_ONE)
    print(f"\n  made it from the business pack {pack_id}")
    print(f"  wrote {', '.join(written) if written else 'no shared file'}; "
          f"{n_sw} software row{'s' if n_sw != 1 else ''} to confirm and {n_pr} process in systems/register.md; systems/team.md")
    if c.returncode != 0:
        print(f"  the first commit did not go through, so the folder is there but not saved yet:\n    {detail(c)}")
        if "who you are" in detail(c).lower():
            print("    tell git your name once: git config --global user.name 'Your Name' && git config --global user.email you@example.com")
        print(f"  then, in {dest}: git add -A && git commit -m '{DAY_ONE}'")
        return 1
    print(f"  committed '{DAY_ONE}' on main, through the hook")

    # GitHub, through the pack's own hub tool.
    if a.local:
        print("  on GitHub: not yet (--local). Later, in that folder: python3 scripts/oac-hub.py create")
    else:
        hub = dest / "scripts" / "oac-hub.py"
        if hub.is_file():
            args = [sys.executable, str(hub), "--root", str(dest), "create"] + (["--owner", a.owner] if a.owner else [])
            hr = subprocess.run(args, cwd=str(dest), capture_output=True, text=True, timeout=300)
            if hr.returncode == 0:
                url = git(dest, "remote", "get-url", "origin").stdout.strip()
                print(f"  on GitHub, private: {url or 'yes'}")
            else:
                print("  on GitHub: not yet. " + (hr.stdout + hr.stderr).strip().splitlines()[0][:300])
                print("    when you are: python3 scripts/oac-hub.py create, in that folder")
        else:
            print("  on GitHub: not yet; this pack has no scripts/oac-hub.py")

    # The link back.
    m = root / ".oac" / "manifest.yml"
    new, changed = add_operation(m.read_text(encoding="utf-8"), repo_name)
    if not changed:
        print(f"  your manifest already lists {repo_name}")
    else:
        m.write_text(new, encoding="utf-8")
        if git(root, "rev-parse", "--git-dir").returncode != 0:
            print(f"  your manifest now lists {repo_name} (this folder is not a git repo, so nothing was committed)")
        else:
            git(root, "add", "--", ".oac/manifest.yml")
            lc = git(root, "commit", "-q", "-m", f"Update: {repo_name} joins operations", "--", ".oac/manifest.yml")
            if lc.returncode == 0:
                branch = git(root, "branch", "--show-current").stdout.strip() or "this branch"
                print(f"  your manifest now lists {repo_name}, committed on {branch}; /push sends it")
            else:
                print(f"  your manifest now lists {repo_name}; the commit did not go through, so /done will carry it: {detail(lc)[:160]}")

    print(f"\nnext: open {dest} in Claude Code and run /oac. For the one word there, run bash scripts/install-shortcuts.sh in it once.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
