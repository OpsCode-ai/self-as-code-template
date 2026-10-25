#!/usr/bin/env python3
"""check-grounding.py - does this document say where it came from, and does it
describe the people in it the way our own record describes them.

Two checks, because grounding has two halves.

  1. PROVENANCE. A document that declares `generated: true` must also declare
     where it came from, in `sources:` (outside the repo) or `derived_from:`
     (inside it). OaC File Format 1.12, section 3.10. A machine-written document
     that cannot name its source is a plausible-sounding document, which is the
     thing Operations as Code exists not to produce.

  2. PEOPLE. For every person in `reference/people-register.yml`, a document
     that names them must not carry one of their `never` phrases nearby, and
     must not use a gendered pronoun near anyone whose pronouns we have not
     recorded. Guessing from a name is the failure this catches.

Usage
    python3 code/scripts/check-grounding.py <path> [<path> ...]
    python3 code/scripts/check-grounding.py --staged
    python3 code/scripts/check-grounding.py --outward     # everything public

Exit codes
    0  nothing found, or findings are warnings only
    1  at least one error

Markdown, HTML and plain text are all read. HTML has its tags stripped first,
because a page is outward material whether or not it carries frontmatter.

Decision: ADR-130. Standard: brand/standards/grounding-standard.md
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("check-grounding: needs pyyaml (pip install pyyaml)\n")
    sys.exit(0)  # fail open, same as every other OaC rail

def _find_repo() -> Path:
    """Walk up for the repo root. In HQ this script sits at code/scripts/; in a
    customer pack it sits at scripts/. Looking for a marker beats counting
    parents, which is wrong in one of the two layouts whichever number you pick.
    """
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / ".oac").is_dir() or (candidate / ".git").exists():
            return candidate
    return here.parents[2] if len(here.parents) > 2 else here.parent


REPO = _find_repo()
REGISTER = REPO / "reference" / "people-register.yml"
if not REGISTER.exists():
    # a pack keeps its register beside the other references it owns
    for alt in ("people-register.yml", "standards/people-register.yml"):
        if (REPO / alt).exists():
            REGISTER = REPO / alt
            break

READABLE = {".md", ".markdown", ".html", ".htm", ".txt"}

# Paths whose content leaves the building, so the people check is an error there
# rather than a warning. Everything else is internal and only warns.
OUTWARD_PREFIXES = (
    "code/plans-pages/",
    "sites/",
    "campaigns/",
    "content/",
    "marketing/",
    "brand/",
    "curriculum/",
    "templates/",
)

GENDERED = {
    "he": "he/him", "him": "he/him", "his": "he/him",
    "she": "she/her", "her": "she/her", "hers": "she/her",
}

# Quoted speech. A pronoun inside a quotation is the speaker's word about
# whoever they were talking about, not our description of the person we named.
# Single quotes only count as a pair when they open after a space and close
# before a space or punctuation, so possessives like Courtney's stay intact.
QUOTED_RE = re.compile(
    r"\u201c[^\u201d]{0,400}\u201d"
    r"|\"[^\"]{0,400}\""
    # a straight-quoted span may contain apostrophes, as long as each one is
    # inside a word (I've, Courtney's). Only a quote at a word boundary closes.
    r"|(?<![A-Za-z])'(?:[^']|'(?=[A-Za-z])){0,400}'(?![A-Za-z])"
)


def strip_quoted(text: str) -> str:
    """Blank quoted spans, keeping length so offsets still line up."""
    return QUOTED_RE.sub(lambda m: " " * len(m.group(0)), text)


TAG_RE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
ANYTAG_RE = re.compile(r"<[^>]+>")
FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


class Finding:
    def __init__(self, path, line, level, rule, message):
        self.path, self.line, self.level = path, line, level
        self.rule, self.message = rule, message

    def __str__(self):
        return f"{self.path}:{self.line}: [{self.level}] {self.rule}: {self.message}"


def load_register():
    if not REGISTER.exists():
        return []
    data = yaml.safe_load(REGISTER.read_text()) or {}
    out = []
    for p in data.get("people", []):
        names = [p["name"]] + list(p.get("aliases") or [])
        out.append({
            "name": p["name"],
            "names": sorted(set(names), key=len, reverse=True),
            "pronouns": (p.get("pronouns") or "unknown").strip().lower(),
            "never": [n for n in (p.get("never") or []) if n.strip()],
            "is": p.get("is", ""),
        })
    return out


def visible_text(path: Path) -> tuple[str, dict]:
    """Return readable prose plus parsed frontmatter."""
    raw = path.read_text(errors="replace")
    meta = {}
    m = FM_RE.match(raw)
    if m:
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            meta = {}
    if path.suffix.lower() in {".html", ".htm"}:
        body = TAG_RE.sub(" ", raw)
        body = ANYTAG_RE.sub(" ", body)
        return body, meta
    return raw, meta


def check_provenance(path: Path, meta: dict, rel: str) -> list[Finding]:
    if not isinstance(meta, dict):
        return []
    gen = meta.get("generated")
    if gen is not True and str(gen).strip().lower() != "true":
        return []
    if meta.get("sources") or meta.get("derived_from"):
        return []
    return [Finding(
        rel, 1, "error", "provenance",
        "generated: true with no sources: and no derived_from:. "
        "A machine wrote this and it does not say what from (OaC 1.12 s3.10)",
    )]


def sentences_with_lines(text: str):
    """Yield (line_number, sentence) with a real line number.

    A sentence is the unit a name and a pronoun have to share before we treat
    the pronoun as referring to that person. The line number comes from the
    sentence's character offset, not from counting as we go, because an
    approximate line number is a finding nobody can chase."""
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)

    def line_of(offset: int) -> int:
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    pos = 0
    for chunk in re.split(r"(?<=[.!?\n])\s+", text):
        offset = text.find(chunk, pos) if chunk else pos
        if offset < 0:
            offset = pos
        yield line_of(offset), chunk
        pos = offset + len(chunk)


def check_people(text: str, rel: str, register, outward: bool) -> list[Finding]:
    findings = []
    level = "error" if outward else "warn"

    for person in register:
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(n) for n in person["names"]) + r")\b"
        )
        if not pattern.search(text):
            continue

        # a 'never' phrase anywhere in a sentence that names them
        for lineno, sent in sentences_with_lines(text):
            if not pattern.search(sent):
                continue
            low = strip_quoted(sent).lower()
            for phrase in person["never"]:
                if phrase.lower() in low:
                    findings.append(Finding(
                        rel, lineno, level, "people/never",
                        f"{person['name']} described as '{phrase}'. "
                        f"The record says: {person['is']}",
                    ))
            # a gendered pronoun for someone whose pronouns we have not recorded
            if person["pronouns"] == "unknown":
                for word in re.findall(r"\b(he|him|his|she|her|hers)\b", low):
                    findings.append(Finding(
                        rel, lineno, level, "people/pronoun",
                        f"'{word}' near {person['name']}, whose pronouns are not "
                        f"recorded. Use they/them or the name, or add the evidence "
                        f"to reference/people-register.yml",
                    ))
                    break
            else:
                wrong = {
                    w for w in re.findall(r"\b(he|him|his|she|her|hers)\b", low)
                    if GENDERED[w] != person["pronouns"]
                }
                if wrong:
                    findings.append(Finding(
                        rel, lineno, level, "people/pronoun",
                        f"'{sorted(wrong)[0]}' near {person['name']}, who is "
                        f"{person['pronouns']}",
                    ))
    return findings


def is_outward(rel: str, meta: dict) -> bool:
    if isinstance(meta, dict) and str(meta.get("audience", "")).strip() == "public":
        return True
    return rel.startswith(OUTWARD_PREFIXES)


def staged_paths():
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        cwd=REPO, capture_output=True, text=True,
    ).stdout.split()
    return [REPO / p for p in out]


def outward_paths():
    found = []
    for prefix in OUTWARD_PREFIXES:
        base = REPO / prefix
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix.lower() in READABLE:
                found.append(p)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--staged", action="store_true", help="check staged files")
    ap.add_argument("--outward", action="store_true", help="check every public surface")
    ap.add_argument("--quiet", action="store_true", help="print findings only")
    args = ap.parse_args()

    if args.staged:
        targets = staged_paths()
    elif args.outward:
        targets = outward_paths()
    else:
        targets = args.paths
    targets = [p for p in targets if p.is_file() and p.suffix.lower() in READABLE]

    if not targets:
        if not args.quiet:
            print("check-grounding: nothing to check")
        return 0

    register = load_register()
    if not register and not args.quiet:
        print(f"check-grounding: no people register at {REGISTER}, people check skipped")

    findings = []
    for path in targets:
        try:
            rel = str(path.resolve().relative_to(REPO))
        except ValueError:
            rel = str(path)
        text, meta = visible_text(path)
        findings += check_provenance(path, meta, rel)
        findings += check_people(text, rel, register, is_outward(rel, meta))

    for f in findings:
        print(f)

    errors = sum(1 for f in findings if f.level == "error")
    if not args.quiet:
        print(
            f"\ncheck-grounding: {len(targets)} file(s), "
            f"{errors} error(s), {len(findings) - errors} warning(s)"
        )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
