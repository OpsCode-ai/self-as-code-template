"""Read YAML frontmatter without a YAML parser, the way every OaC tool does.

WHY THIS EXISTS
    Four scripts in this repo each carried their own copy of the same regex and
    the same scalar-only line reader (customer-repo-sync, backfill-frontmatter,
    oac-validate, oac-session-brief). A fifth was about to be written. This is
    the one copy, lifted verbatim from customer-repo-sync.py, so the readers
    cannot drift from each other.

WHY NO YAML LIBRARY
    ADR-104: a regex reader is what the client ships, and the standard's flow-
    style rule exists so that a scalar reader is enough. Depending on PyYAML
    here would make the tool disagree with the client about what a document
    says. Scalars in, scalars out. A block list is not read; that is the point.
"""
from __future__ import annotations

import re

FM = re.compile(r"\A---\n.*?\n---\n", re.S)
H2 = re.compile(r"^##\s+(.+?)\s*$", re.M)


def _text(raw: bytes | str) -> str | None:
    if isinstance(raw, str):
        return raw
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def body(raw: bytes | str) -> str:
    """Content with the frontmatter block and surrounding blank lines removed."""
    text = _text(raw)
    if text is None:
        return ""
    return FM.sub("", text, count=1).strip()


def frontmatter(raw: bytes | str) -> dict[str, str]:
    """Top-level scalar fields, keys lowercased, quotes stripped.

    Indented lines, comments and list items are skipped on purpose: a block
    list read by a scalar reader comes back wrong rather than missing
    (ADR-104), so it is not read at all.
    """
    text = _text(raw)
    if text is None:
        return {}
    m = FM.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(0).splitlines()[1:-1]:
        if ":" in line and not line.startswith((" ", "\t", "#", "-")):
            k, _, v = line.partition(":")
            out[k.strip().lower()] = v.strip().strip("\"'")
    return out


def headings(raw: bytes | str) -> list[str]:
    text = _text(raw)
    if text is None:
        return []
    return [ln.rstrip() for ln in text.splitlines() if re.match(r"^#{1,3} \S", ln)]


def section(raw: bytes | str, name: str) -> str | None:
    """The body of one level-two section, matched case-insensitively.

    `name` is compared after lowercasing and dropping a leading 'the', so
    'the split' and 'Split' both find `## the split`. Returns None when absent,
    which callers must treat as 'not captured', never as an error.
    """
    text = body(raw)
    want = re.sub(r"^the\s+", "", name.strip().lower())
    marks = [(m.start(), m.end(), re.sub(r"^the\s+", "", m.group(1).strip().lower()))
             for m in H2.finditer(text)]
    for i, (start, end, title) in enumerate(marks):
        if title == want:
            stop = marks[i + 1][0] if i + 1 < len(marks) else len(text)
            return text[end:stop].strip()
    return None
