#!/usr/bin/env python3
"""What comes in lands in your inbox, tagged to where it belongs (`/capture`).

WHY THIS EXISTS
    ADR-136 Rule 1: `/capture` is its own command, because it is an input, not
    a moment. The Melbourne plan's test 5, 'it is fed, not only asked': notes,
    messages and meeting lines flow in without a question being asked. Until
    28 October 2026 the only /capture was Adam's own skill in his private repo,
    so test 5 was his feed alone; the pack had nothing. This is the pack's,
    in the framework's words: no estimates, no owners, no priorities. The week
    decides what matters, with the leap, the floor and the cut.

WHAT IT DOES
    tags    The places a line can belong: every block the plan names under its
            baseline (a business, a job, the family, a project), the
            manifest's operations, and `you`. One reader, shared with
            /sac meeting, so the names agree.
    add     Lines from stdin (or --item, repeated), one per line, each
            `[tag] what to do`, or tagged by --tag. Appended to inbox.md
            under today's date as `- [ ] [tag] text`, with `(from <where>)`
            when --from says where it came from. inbox.md is made the first
            time. A tag the plan does not know is refused unless --any-tag.
    open    Every unticked line, by tag, with how old it is: the count the
            message at the top of a session shows, and what /sac week goes
            through.

WHAT NEVER HAPPENS
    Nothing is committed here; /done saves the inbox with the rest of the day.
    Nothing leaves this repo. The session parses what a person said and shows
    it to them; this writes exactly the lines they confirmed, and no more.
    In a business's repo it refuses: files from other laptops come in through
    scripts/oac-hub.py inbox.

Usage:
    python3 scripts/sac-capture.py tags [--json]
    printf '%s\\n' '[acme] call the accountant' '[you] book the dentist' \\
        | python3 scripts/sac-capture.py add [--from "a voice note, 28 Oct"] [--tag T] [--any-tag]
    python3 scripts/sac-capture.py add --item '[acme] call the accountant'
    python3 scripts/sac-capture.py open [--json] [--count]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INBOX = "inbox.md"
YOU = "you"
DAY_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")
ITEM_RE = re.compile(r"^\s*[-*]\s*\[( |x|X)\]\s*(?:\[([^\]]+)\]\s*)?(.*?)\s*$")
LEAD_RE = re.compile(r"^\s*(?:[-*]\s+)?(?:\[(?: |x|X)\]\s*)?")
TAG_RE = re.compile(r"^\[([^\]]+)\]\s*(.*)$")
UPDATED_RE = re.compile(r"^updated:.*$", re.M)

_MT = None


def fail(msg: str, code: int = 2) -> None:
    print(f"sac-capture: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _meeting():
    """sac-meeting.py reads the plan's blocks and the manifest's businesses.
    One reader, so a tag here is the name /sac meeting routes by."""
    global _MT
    if _MT is None:
        script = HERE / "sac-meeting.py"
        if not script.is_file():
            fail("scripts/sac-meeting.py is missing; the pack ships them together")
        spec = importlib.util.spec_from_file_location("sac_meeting", script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MT = mod
    return _MT


def plane_of(root: Path) -> str | None:
    m = root / ".oac" / "manifest.yml"
    if not m.is_file():
        return None
    for line in m.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("plane:"):
            return line.partition(":")[2].strip() or None
    return None


def norm_tag(tag: str) -> str:
    mt = _meeting()
    return mt.bare(mt.slugify(tag))


def tags(root: Path) -> list[dict]:
    """[{tag, name, kind}]: every block under the baseline, whatever its
    kind, then the manifest's operations, then `you`."""
    mt = _meeting()
    out: list[dict] = []
    seen: set[str] = set()
    spine = mt.find_spine(root)
    if spine:
        base = mt.section(spine.read_bytes(), "the baseline") or ""
        for name, body in mt.baseline_blocks(base):
            tag = norm_tag(name)
            if tag and tag != YOU and tag not in seen:
                seen.add(tag)
                kind = mt.block_kind(body) or ("a business" if mt.is_business(body) else "")
                out.append({"tag": tag, "name": name, "kind": kind})
    for op in mt.manifest_operations(root):
        tag = norm_tag(op)
        if tag and tag != YOU and tag not in seen:
            seen.add(tag)
            out.append({"tag": tag, "name": op, "kind": "a business"})
    out.append({"tag": YOU, "name": "you", "kind": "the person"})
    return out


def parse_item(line: str, default_tag: str | None) -> tuple[str | None, str]:
    """('acme', 'Call the accountant') from '[acme] Call the accountant', from
    a `- [ ] [acme] ...` line already shaped, or from a bare line with --tag."""
    s = LEAD_RE.sub("", line.strip(), count=1).strip()
    m = TAG_RE.match(s)
    if m:
        return norm_tag(m.group(1)), m.group(2).strip()
    return (norm_tag(default_tag) if default_tag else None), s


def header(today: str) -> str:
    return "\n".join([
        "---",
        'title: "Inbox"',
        "type: report",
        "audience: owner",
        "status: active",
        "lifecycle: living",
        f"updated: {today}",
        'summary: "What came in and is not yet sorted. /capture adds a line; /sac week goes through them."',
        "topics: [self-as-code]",
        "tags: [inbox, capture]",
        "---",
        "",
        "# Inbox",
        "",
        "What came in, before it is sorted. `/capture` adds a line under the day it",
        "came. `/sac week` goes through each one with three questions: the leap, the",
        "floor, the cut. A keeper goes into a day, a 'later' is parked with a date,",
        "and the rest is dropped. Tick a line when it has been sorted.",
        "",
    ])


def _bump_updated(text: str, today: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end < 0:
        return text
    head, tail = text[:end], text[end:]
    if UPDATED_RE.search(head):
        head = UPDATED_RE.sub(f"updated: {today}", head, count=1)
    return head + tail


def _append_under_day(text: str, today: str, lines: list[str]) -> str:
    """Under `## <today>` if it is there (after its last line), else a new
    heading at the end. Days grow down the file, newest last, like a log."""
    rows = text.splitlines()
    start = next((i for i, ln in enumerate(rows) if DAY_RE.match(ln) and DAY_RE.match(ln).group(1) == today), None)
    if start is None:
        body = text.rstrip("\n") + "\n" if text.strip() else text
        return body + f"\n## {today}\n" + "\n".join(lines) + "\n"
    end = next((i for i in range(start + 1, len(rows)) if rows[i].startswith("## ")), len(rows))
    while end > start + 1 and not rows[end - 1].strip():
        end -= 1
    rows[end:end] = lines
    out = "\n".join(rows)
    return out if out.endswith("\n") else out + "\n"


def add(root: Path, raw_items: list[str], *, default_tag: str | None, source: str | None,
        any_tag: bool, today: str) -> list[str]:
    known = {t["tag"] for t in tags(root)}
    lines: list[str] = []
    bad: list[str] = []
    for raw in raw_items:
        if not raw.strip():
            continue
        tag, text = parse_item(raw, default_tag)
        if not text:
            continue
        if tag is None:
            bad.append(f"no tag: {text}")
        elif tag not in known and not any_tag:
            bad.append(f"[{tag}] is not a place the plan knows: {text}")
        else:
            suffix = f" (from {source.strip()})" if source and source.strip() else ""
            lines.append(f"- [ ] [{tag}] {text}{suffix}")
    if bad:
        fail("nothing written.\n  " + "\n  ".join(bad)
             + "\n  the places the plan knows: " + ", ".join(sorted(known))
             + "\n  (--tag <place> tags every bare line; --any-tag keeps a tag the plan does not know)")
    if not lines:
        fail("nothing to add")
    path = root / INBOX
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else header(today)
    text = _append_under_day(_bump_updated(text, today), today, lines)
    path.write_text(text, encoding="utf-8")
    return lines


def open_items(root: Path, today: _dt.date) -> list[dict]:
    """Every unticked line, with its tag, its day and its age in days."""
    path = root / INBOX
    if not path.is_file():
        return []
    day: str | None = None
    out: list[dict] = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = DAY_RE.match(ln)
        if m:
            day = m.group(1)
            continue
        im = ITEM_RE.match(ln)
        if not im or im.group(1) != " " or not im.group(3).strip():
            continue
        age = None
        if day:
            try:
                age = (today - _dt.date.fromisoformat(day)).days
            except ValueError:
                pass
        out.append({"tag": (im.group(2) or "").strip().lower() or None, "text": im.group(3).strip(),
                    "date": day, "age": age})
    return out


def _age(age: int | None) -> str:
    if age is None:
        return ""
    if age <= 0:
        return "today"
    return f"{age} day{'s' if age != 1 else ''}"


def print_tags(root: Path, as_json: bool) -> None:
    rows = tags(root)
    if as_json:
        print(json.dumps(rows, indent=2))
        return
    width = max(len(r["tag"]) for r in rows) + 2
    print("  the places a line can belong:")
    for r in rows:
        kind = f"  {r['kind']}" if r["kind"] and r["kind"] != r["name"] else ""
        print(f"  [{r['tag']}]".ljust(width + 4) + f"{r['name']}{kind}")


def print_open(items: list[dict], as_json: bool, count: bool) -> None:
    if count:
        print(len(items))
        return
    if as_json:
        print(json.dumps(items, indent=2))
        return
    if not items:
        print("  your inbox is empty")
        return
    print(f"  {len(items)} open")
    ordered = sorted(items, key=lambda i: (i["tag"] or "~", items.index(i)))
    width = max(len(i["tag"] or "-") for i in ordered) + 2
    for i in ordered:
        age = _age(i["age"])
        print(f"  [{i['tag'] or '-'}]".ljust(width + 4) + i["text"] + (f"   {age}" if age else ""))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="What comes in lands in your inbox, tagged to where it belongs.")
    ap.add_argument("--root", default=".", help="your private repo (default: here)")
    ap.add_argument("--today", help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tags", help="the places a line can belong")
    t.add_argument("--json", action="store_true")
    a = sub.add_parser("add", help="lines from stdin or --item, into inbox.md under today")
    a.add_argument("--item", action="append", default=[], help="one line; repeat for more")
    a.add_argument("--tag", help="the place for every line that has no [tag] of its own")
    a.add_argument("--from", dest="source", help="where it came from, when it was not typed here")
    a.add_argument("--any-tag", action="store_true", help="keep a tag the plan does not know")
    o = sub.add_parser("open", help="every unticked line, by tag, with its age")
    o.add_argument("--json", action="store_true")
    o.add_argument("--count", action="store_true")
    ns = ap.parse_args(argv)

    root = Path(ns.root).resolve()
    today = _dt.date.fromisoformat(ns.today) if ns.today else _dt.date.today()
    if plane_of(root) == "business":
        fail("this is a business's repo. Files from other laptops come in through\n"
             "  python3 scripts/oac-hub.py inbox <path>. /capture is for your own repo.")

    if ns.cmd == "tags":
        print_tags(root, ns.json)
        return 0
    if ns.cmd == "open":
        print_open(open_items(root, today), ns.json, ns.count)
        return 0
    items = list(ns.item)
    if not sys.stdin.isatty():
        items += sys.stdin.read().splitlines()
    lines = add(root, items, default_tag=ns.tag, source=ns.source, any_tag=ns.any_tag, today=today.isoformat())
    print(f"  added {len(lines)} to {INBOX} under {today.isoformat()}:")
    for ln in lines:
        print(f"  {ln}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
