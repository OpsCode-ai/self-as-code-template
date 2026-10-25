#!/usr/bin/env python3
"""A meeting lands in your Self as Code first, then goes to each business (`/sac meeting`).

WHY THIS EXISTS
    Adam, 23 October 2026: 'Self as Code should be the one that has the
    meetings.' Every meeting lands in the person's own private repo. Then the
    parts they choose are proposed to each business as a pull request, never
    pushed (ADR-127 Rule 5). The Melbourne build plan, S1.4, and day two's
    1:30 slot: 'Meetings, transcribed privately into your own folders'.

WHAT IT DOES
    file <transcript>   Zoom's .vtt, any .srt, or the text Fireflies, Otter or
                        Read.ai export. The original goes to
                        evidence/meetings/raw/ as it came; a clean copy
                        (speaker turns, no timestamps) to
                        evidence/meetings/<date>-<slug>.md with frontmatter.
                        Then it names the businesses the plan knows, so the
                        session can ask which parts go where.
    businesses          The businesses the plan names (its `###` blocks and
                        the manifest's `operations:`), and where each repo is.
    propose             One business's part, written by the session and
                        approved by the person, into that business's repo as
                        meetings/<date>-<slug>.md, committed on a branch and
                        pushed, with the pull request to open. It refuses a
                        repo on main, a dirty tree, or one that is not a
                        business repo (the split's own checks). A word about
                        money, ownership or someone's job stops it until the
                        person says yes (--yes-sensitive): the same rule the
                        voice sorter uses (lib/meeting_rules.py).

WHAT NEVER HAPPENS
    The transcript never leaves this repo. Nothing lands on any business's
    main. Nothing goes anywhere the person did not say yes to.

Usage:
    python3 scripts/sac-meeting.py file <transcript> [--title T] [--date YYYY-MM-DD] [--with "A, B"]
    python3 scripts/sac-meeting.py businesses
    python3 scripts/sac-meeting.py propose --meeting <evidence/meetings/...md> --business <name> --part <file> [--target DIR] [--yes-sensitive] [--no-push]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.frontmatter import frontmatter, section  # noqa: E402
from lib.git_sync import bind, push_with_reconcile  # noqa: E402
from lib.meeting_rules import held  # noqa: E402

HERE = Path(__file__).resolve().parent
SPINE_ADDRESSES = ("self-as-code.md", "goals/self-as-code.md")
MEETINGS = Path("evidence") / "meetings"
RAW = MEETINGS / "raw"
BUSINESS_DIR = Path("meetings")
PROJECTS = Path.home() / "projects"

TIME = r"\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?"
TIMING_RE = re.compile(r"-->")
CUE_ID_RE = re.compile(r"^(\d+|[0-9a-f-]{8,})$", re.I)
VOICE_TAG_RE = re.compile(r"<v\s+([^>]+?)>(.*?)(?:</v>|$)", re.I)
TAG_RE = re.compile(r"<[^>]+>")
NAME_COLON_RE = re.compile(r"^([A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*){0,3}|Speaker\s*\d+):\s+(.+)$")
# Otter: 'Jane Smith  12:34' or 'Speaker 1  0:03'. Fireflies and Read.ai:
# 'Jane Smith (00:12):' or 'Jane Smith (12:34)'. One of these on its own line
# names the speaker of the lines that follow.
SPEAKER_LINE_RE = re.compile(rf"^([A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*){{0,3}}|Speaker\s*\d+)\s*(?:\(\s*{TIME}\s*\)|\s{{2,}}{TIME}|\s+{TIME})\s*:?\s*$")
LEADING_TIME_RE = re.compile(rf"^\[?\(?{TIME}\)?\]?\s*[-:]?\s*")
DATE_RE = re.compile(r"(20\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])")
MONTH_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(20\d{2})\b", re.I)
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}


# ── The plan: who runs what ─────────────────────────────────────────────────

def find_spine(root: Path) -> Path | None:
    for rel in SPINE_ADDRESSES:
        if (root / rel).is_file():
            return root / rel
    return None


def slugify(s: str) -> str:
    """'Jane's Courses' -> 'janes-courses': an apostrophe joins, it does not split."""
    s = re.sub(r"['\u2019]", "", s.lower())
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def bare(slug: str) -> str:
    """A business and its repo share a name: `acme` and `acme-ops` are one."""
    return slug[:-4] if slug.endswith("-ops") and len(slug) > 4 else slug


# Framework 0.9: a `###` block under the baseline is one thing the person holds,
# and its `Kind:` line says which. Only a business gets its own repo; a job, a
# career, a family or a project stays in the private repo.
NON_BUSINESS_KIND = re.compile(r"\b(job|career|employ\w*|family|household|home|project|study|studies|degree|course of study)\b", re.I)
KIND_RE = re.compile(r"^\s*Kind:\s*(.+?)\s*$", re.I | re.M)


def block_kind(body: str) -> str:
    m = KIND_RE.search(body or "")
    return m.group(1).strip() if m else ""


def is_business(body: str) -> bool:
    """True unless the block's Kind line names a job, a career, a family or a project."""
    return not NON_BUSINESS_KIND.search(block_kind(body))


def baseline_blocks(base: str) -> list[tuple[str, str]]:
    """(name, body) for every `###` block under `## the baseline`, in order."""
    out: list[tuple[str, str]] = []
    heads = list(re.finditer(r"^###\s+(.+?)\s*$", base, re.M))
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(base)
        out.append((m.group(1).strip(), base[m.end():end]))
    return out


def owner_name(root: Path) -> str:
    spine = find_spine(root)
    if spine:
        t = frontmatter(spine.read_bytes()).get("title", "")
        t = re.sub(r"\s*[:—–-]\s*Self as Code.*$", "", t, flags=re.I).strip()
        if t and not t.lower().startswith("your name"):
            return t
    r = subprocess.run(["git", "-C", str(root), "config", "user.name"], capture_output=True, text=True)
    return r.stdout.strip() or "the owner"


def manifest_operations(root: Path) -> list[str]:
    m = root / ".oac" / "manifest.yml"
    if not m.is_file():
        return []
    lines = m.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[str] = []
    for i, ln in enumerate(lines):
        if not ln.startswith("operations:"):
            continue
        rest = ln.partition(":")[2].strip()
        if rest.startswith("["):
            out += [x.strip().strip("'\"") for x in rest.strip("[]").split(",") if x.strip()]
        else:
            for nxt in lines[i + 1:]:
                if re.match(r"^\s+-\s+", nxt):
                    out.append(nxt.split("-", 1)[1].strip().strip("'\""))
                elif nxt.strip() and not nxt.startswith(" "):
                    break
        break
    return [o for o in out if o]


def businesses(root: Path) -> list[dict]:
    """[{name, slug, repo}] from the plan's `###` blocks under `## the baseline`
    and the manifest's `operations:`. `repo` is the local clone when one is
    found at ~/projects/<slug> or ~/projects/<slug>-ops, else None."""
    out: list[dict] = []
    seen: set[str] = set()
    spine = find_spine(root)
    if spine:
        base = section(spine.read_bytes(), "the baseline") or ""
        for name, body in baseline_blocks(base):
            if not is_business(body):
                continue          # a job, a family, a project: it has no repo (framework 0.9)
            slug = bare(slugify(name))
            if slug and slug not in seen:
                seen.add(slug)
                out.append({"name": name, "slug": slug})
    for op in manifest_operations(root):
        slug = bare(slugify(op))
        if slug and slug not in seen:
            seen.add(slug)
            out.append({"name": op, "slug": slug})
    for b in out:
        b["repo"] = find_repo(b["slug"])
    return out


def find_repo(slug: str, projects: Path = PROJECTS) -> Path | None:
    for cand in (projects / slug, projects / f"{slug}-ops"):
        if (cand / ".oac" / "manifest.yml").is_file():
            return cand
    return None


def match_business(root: Path, want: str) -> dict | None:
    w = bare(slugify(want))
    for b in businesses(root):
        if b["slug"] == w or bare(slugify(b["name"])) == w:
            return b
    return None


# ── Reading a transcript ────────────────────────────────────────────────────

def parse_transcript(text: str, kind: str) -> list[tuple[str | None, str]]:
    """(speaker, text) turns, in order, same-speaker turns merged, no
    timestamps. `kind` is vtt, srt or text."""
    turns: list[tuple[str | None, str]] = []
    speaker: str | None = None

    def add(who: str | None, what: str) -> None:
        what = TAG_RE.sub("", what).strip()
        what = re.sub(r"\s+", " ", what)
        if not what:
            return
        if turns and turns[-1][0] == who:
            turns[-1] = (who, turns[-1][1] + " " + what)
        else:
            turns.append((who, what))

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if kind in ("vtt", "srt"):
        in_cue = False
        for raw in lines:
            ln = raw.strip()
            if not ln:
                in_cue = False
                continue
            if ln.upper().startswith(("WEBVTT", "NOTE", "KIND:", "LANGUAGE:", "STYLE")) and not in_cue:
                continue
            if TIMING_RE.search(ln):
                in_cue = True
                continue
            if not in_cue and CUE_ID_RE.match(ln):
                continue
            vm = VOICE_TAG_RE.search(ln)
            if vm:
                add(vm.group(1).strip(), vm.group(2))
                continue
            nm = NAME_COLON_RE.match(TAG_RE.sub("", ln))
            if nm:
                speaker = nm.group(1).strip()
                add(speaker, nm.group(2))
            else:
                add(speaker, ln)
        return turns

    for raw in lines:
        ln = raw.strip()
        if not ln:
            continue
        sm = SPEAKER_LINE_RE.match(ln)
        if sm:
            speaker = sm.group(1).strip()
            continue
        ln = LEADING_TIME_RE.sub("", ln)
        nm = NAME_COLON_RE.match(ln)
        if nm and not ln.lower().startswith(("http", "note")):
            speaker = nm.group(1).strip()
            add(speaker, nm.group(2))
        elif ln:
            add(speaker, ln)
    return turns


def kind_of(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".vtt":
        return "vtt"
    if ext == ".srt":
        return "srt"
    return "text"


def app_of(path: Path, text: str) -> str:
    name = path.name.lower()
    if name.startswith("gmt") or "zoom" in name or (kind_of(path) == "vtt" and "zoom" in text[:400].lower()):
        return "zoom"
    for app in ("fireflies", "otter", "read.ai", "readai", "fathom", "teams", "meet"):
        if app in name or app in text[:400].lower():
            return app.replace("readai", "read.ai")
    return kind_of(path)


def date_of(path: Path, given: str | None) -> str:
    if given:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", given):
            sys.exit(f"--date must be YYYY-MM-DD, not {given!r}")
        return given
    m = DATE_RE.search(path.name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = MONTH_RE.search(path.name)
    if m:
        return f"{m.group(3)}-{MONTHS[m.group(1).lower()[:3]]:02d}-{int(m.group(2)):02d}"
    return _dt.date.fromtimestamp(path.stat().st_mtime).isoformat()


def title_of(path: Path, given: str | None) -> str:
    if given:
        return given.strip()
    stem = path.name
    for suf in (".transcript", ".vtt", ".srt", ".txt", ".md", ".docx"):
        stem = re.sub(re.escape(suf) + "$", "", stem, flags=re.I)
    stem = re.sub(r"GMT\d{8}-\d{6}", " ", stem)
    stem = DATE_RE.sub(" ", stem)
    stem = MONTH_RE.sub(" ", stem)
    stem = re.sub(r"\b\d{1,2}[.:]\d{2}(?:[.:]\d{2})?\b", " ", stem)
    # Separators become spaces first: '_Recording' has no word boundary before
    # the R, so the filler words are only found once the underscores are gone.
    stem = re.sub(r"[_\-.]+", " ", stem)
    stem = re.sub(r"\b(recording|transcript|audio|video|meeting notes|notes by [\w.]+)\b", " ", stem, flags=re.I)
    stem = re.sub(r"\s+", " ", stem).strip(" -")
    return stem[:1].upper() + stem[1:] if stem else "Meeting"


def _yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _flow(items: list[str]) -> str:
    return "[" + ", ".join(_yaml_str(i) if re.search(r"[,:#\[\]{}\"']", i) else i for i in items) + "]"


def unique_path(p: Path) -> Path:
    if not p.exists():
        return p
    n = 2
    while p.with_name(f"{p.stem}-{n}{p.suffix}").exists():
        n += 1
    return p.with_name(f"{p.stem}-{n}{p.suffix}")


# ── file ─────────────────────────────────────────────────────────────────────

def cmd_file(root: Path, src: Path, title: str | None, date: str | None, with_: str | None) -> int:
    if not src.is_file():
        print(f"no such file: {src}")
        return 1
    if src.suffix.lower() == ".docx":
        print("a .docx cannot be read here yet. Export the transcript as text (.txt) and run again.")
        return 1
    text = src.read_text(encoding="utf-8", errors="replace")
    kind = kind_of(src)
    turns = parse_transcript(text, kind)
    if not turns:
        print(f"nothing readable in {src.name}: no lines of speech were found")
        return 1
    when = date_of(src, date)
    name = title_of(src, title)
    slug = slugify(name)[:60] or "meeting"
    speakers = []
    for who, _ in turns:
        if who and who not in speakers:
            speakers.append(who)
    attendees = [a.strip() for a in with_.split(",")] if with_ else speakers
    app = app_of(src, text)

    raw_dest = unique_path(root / RAW / f"{when}-{slug}{src.suffix.lower()}")
    raw_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, raw_dest)

    md_dest = unique_path(root / MEETINGS / f"{when}-{slug}.md")
    today = _dt.date.today().isoformat()
    body = []
    for who, what in turns:
        body.append(f"**{who}:** {what}" if who else what)
        body.append("")
    doc = "\n".join([
        "---",
        f"title: {_yaml_str(f'{name}, {when}')}",
        "type: transcript",
        "audience: owner",
        f"date: {when}",
        f"source_app: {app}",
        f"attendees: {_flow(attendees)}" if attendees else "attendees: []",
        f"raw: {raw_dest.relative_to(root).as_posix()}",
        "status: filed",
        "topics: [meetings]",
        "tags: [sac-meeting]",
        "---",
        "",
        f"# {name}, {when}",
        "",
        f"Filed by `/sac meeting` on {today}. The original is in `raw/`, as it came.",
        "The summary, the actions and what went to each business are written below",
        "it by the session, with the person.",
        "",
        "## What was said",
        "",
        *body,
    ])
    md_dest.write_text(doc, encoding="utf-8")

    print(f"filed: {md_dest.relative_to(root).as_posix()}")
    print(f"  {len(turns)} turn{'s' if len(turns) != 1 else ''}" + (f", speakers: {', '.join(speakers)}" if speakers else ", no speaker names found"))
    print(f"  original kept: {raw_dest.relative_to(root).as_posix()}")
    print_businesses(root)
    print("next: read it, write the summary and the actions under it, then propose each business's part")
    return 0


def print_businesses(root: Path) -> None:
    bs = businesses(root)
    if not bs:
        print("businesses in the plan: none named yet, so every part stays here")
        return
    print("businesses in the plan:")
    for b in bs:
        where = f"repo at {b['repo']}" if b["repo"] else "no repo on this laptop yet (/sac deploy makes it)"
        print(f"  {b['name']}  ({b['slug']}): {where}")


# ── propose ──────────────────────────────────────────────────────────────────

def _split_module():
    script = HERE / "self-as-code-split.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("sac_split", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(target: Path):
    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(("git", "-C", str(target)) + args, capture_output=True, text=True)
    return run


def cmd_propose(root: Path, meeting: Path, business: str, part: Path, target: Path | None,
                yes_sensitive: bool, push: bool) -> int:
    if not meeting.is_file():
        print(f"no such meeting file: {meeting}")
        return 1
    if not part.is_file():
        print(f"no such part file: {part}")
        return 1
    fm = frontmatter(meeting.read_bytes())
    when = fm.get("date") or _dt.date.today().isoformat()
    title = re.sub(r",\s*\d{4}-\d{2}-\d{2}$", "", fm.get("title") or meeting.stem)
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", meeting.stem)
    part_text = part.read_text(encoding="utf-8", errors="replace").strip()
    if not part_text:
        print(f"{part} is empty, so there is nothing to send")
        return 1

    words = held(part_text)
    if words and not yes_sensitive:
        print(f"stopped: this part mentions {', '.join(words)}.")
        print("  Money, ownership and someone's job never go to a business unless the person says yes to that line.")
        print("  Ask them. On a yes, run again with --yes-sensitive. On a no, take the line out.")
        return 1

    b = match_business(root, business)
    name = b["name"] if b else business
    bslug = b["slug"] if b else slugify(business)
    if target is None:
        target = b["repo"] if b else find_repo(bslug)
    if target is None:
        print(f"no repo for {name} on this laptop (looked at ~/projects/{bslug} and ~/projects/{bslug}-ops).")
        print("  /sac deploy makes it. Or name one with --target.")
        return 1
    target = Path(target).resolve()

    split = _split_module()
    if split is None:
        print("self-as-code-split.py is missing beside this script, so the repo cannot be checked")
        return 1
    why = split.target_problem(target)
    if why:
        print(f"refusing: {why}")
        return 1

    owner = owner_name(root)
    today = _dt.date.today().isoformat()
    rel = BUSINESS_DIR / f"{when}-{slug}.md"
    dest = unique_path(target / rel)
    rel = dest.relative_to(target)
    doc = "\n".join([
        "---",
        f"title: {_yaml_str(f'{title}, {when}: the {name} part')}",
        "type: session",
        "audience: internal",
        f"date: {when}",
        f"source: {_yaml_str(f'proposed from {owner} Self as Code meeting {meeting.stem}, by sac-meeting.py on {today}')}",
        "status: proposed",
        "topics: [meetings]",
        "tags: [sac-meeting, proposed]",
        "---",
        "",
        f"# {title}, {when}",
        "",
        f"The part of this meeting that is about {name}, chosen by {owner} line by",
        "line. The rest of the meeting stays in their own private space.",
        "",
        part_text,
        "",
    ])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(doc, encoding="utf-8")

    run = git(target)
    run("add", "--", str(rel))
    msg = (f"Add: the {name} part of {title}, {when}\n\n"
           f"Proposed from {owner}'s Self as Code by sac-meeting.py. Only the lines they\n"
           "chose; the meeting itself stays in their private repo. Review and merge.\n")
    c = run("commit", "-m", msg, "--", str(rel))
    if c.returncode != 0:
        # Leave their tree as it was: a half-done proposal is worse than none.
        run("reset", "-q", "--", str(rel))
        dest.unlink(missing_ok=True)
        try:
            dest.parent.rmdir()  # only when it was empty before, so only when it is empty now
        except OSError:
            pass
        print(f"nothing sent: the commit in {target} failed, so {rel} was taken back out.")
        print(f"  git said: {(c.stderr or c.stdout).strip()[:300]}")
        return 1
    branch = run("branch", "--show-current").stdout.strip()
    print(f"wrote {rel} in {target}")
    print(f"  committed on {branch}")
    if push:
        ok, detail = push_with_reconcile(bind(run))
        print(f"  push: {'ok' if ok else 'held locally'} {detail}".rstrip())
    print(f"  open the pull request they merge:\n    gh pr create --head {branch}")
    return 0


# ── main ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A meeting lands in your Self as Code first, then goes to each business.")
    ap.add_argument("--root", default=".", help="your private repo (default: here)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("file", help="file a transcript here")
    f.add_argument("transcript", type=Path)
    f.add_argument("--title")
    f.add_argument("--date", help="YYYY-MM-DD, when the file name does not say")
    f.add_argument("--with", dest="with_", help="who was there, comma-separated, when the transcript does not say")
    sub.add_parser("businesses", help="the businesses the plan names, and where each repo is")
    p = sub.add_parser("propose", help="one business's part, to that business's repo as a pull request")
    p.add_argument("--meeting", type=Path, required=True)
    p.add_argument("--business", required=True)
    p.add_argument("--part", type=Path, required=True, help="the part the person approved, as markdown")
    p.add_argument("--target", type=Path, help="the business repo, when it is not at ~/projects")
    p.add_argument("--yes-sensitive", action="store_true", help="the person said yes to a line about money, ownership or a job")
    p.add_argument("--no-push", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    if a.cmd == "file":
        return cmd_file(root, a.transcript, a.title, a.date, a.with_)
    if a.cmd == "businesses":
        print_businesses(root)
        return 0
    return cmd_propose(root, a.meeting, a.business, a.part, a.target, a.yes_sensitive, not a.no_push)


if __name__ == "__main__":
    sys.exit(main())
