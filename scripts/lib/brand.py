"""Read a person's or a business's look from standards/brand.md, one line each.

WHY THIS EXISTS
    Every output made for a person (the dashboard, a report, a page) reads the
    same few lines: ink, paper, one accent, a typeface, light or dark, how much
    things move, and the two letterhead lines (ADR-136 Rule 11; ADR-137). One
    reader, so the dashboard and the look book never disagree about what
    'my colours' means. A seed, or a missing file, is plain black on white.

THE FILE
    standards/brand.md, a list of `- Key: value` lines. The keys are the
    interface; the words after the colon are the person's. A value that still
    says TO FILL IN is unset.

    - Feel: quiet, warm, exact
    - Ink: #1f1d1a
    - Paper: #faf7f1
    - Accent: #b4532a
    - Typeface: Inter
    - Light or dark: light
    - Movement: a little
    - Letterhead: Jane Smith
    - Under it: Plumber. Teacher. Mum of two.
    - Icons: carbon

    `Icons:` names the one icon set a page draws from, carbon (the default)
    or lucide (ADR-138, 18 November 2026).

    A brand.md from before 30 October 2026 had `Colours:` with two or three
    hex values. Those are read as ink, then accent, then paper, so an older
    plane keeps its colours without a rewrite.
"""
from __future__ import annotations

import re
from pathlib import Path

BRAND = Path("standards") / "brand.md"
HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
LINE_RE = re.compile(r"^\s*[-*]\s*([A-Za-z][A-Za-z ]*?)\s*:\s*(.*?)\s*$")
UNSET_RE = re.compile(r"TO FILL IN|not written yet|^none$|^\s*$", re.I)

# Plain black on white: what everything made for a person looks like until
# they have chosen (the seed's own promise).
PLAIN = {
    "feel": "",
    "ink": "#111111",
    "paper": "#ffffff",
    "accent": "#111111",
    "typeface": "",
    "mode": "light",
    "movement": "none",
    "letterhead": "",
    "under": "",
    "icons": "carbon",
    "written": False,
}

KEYS = {
    "feel": "feel", "ink": "ink", "paper": "paper", "accent": "accent",
    "typeface": "typeface", "font": "typeface", "light or dark": "mode",
    "movement": "movement", "letterhead": "letterhead", "under it": "under",
    "icons": "icons", "icon set": "icons",
}


def norm_hex(h: str) -> str:
    h = h.strip().lower()
    if len(h) == 4:
        h = "#" + "".join(c * 2 for c in h[1:])
    return h


def rgb(h: str) -> tuple[int, int, int]:
    h = norm_hex(h)
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def hexed(c: tuple[float, float, float]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in c)


def mix(a: str, b: str, t: float) -> str:
    """The colour t of the way from a to b (0 is a, 1 is b)."""
    ra, rb = rgb(a), rgb(b)
    return hexed(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))


def is_dark(paper: str) -> bool:
    r, g, b = rgb(paper)
    return (0.299 * r + 0.587 * g + 0.114 * b) < 128


def parse(text: str) -> dict:
    """The look in a brand.md's text. Missing or unset lines fall back to plain."""
    look = dict(PLAIN)
    colours: list[str] = []
    seen = False
    mode_given = False
    for raw in text.splitlines():
        m = LINE_RE.match(raw)
        if not m:
            continue
        key, value = m.group(1).strip().lower(), m.group(2).strip().strip("*").strip()
        if key in ("colours", "colors"):
            colours = [norm_hex(h) for h in HEX_RE.findall(value)]
            continue
        field = KEYS.get(key)
        if not field or UNSET_RE.search(value):
            continue
        if field in ("ink", "paper", "accent"):
            found = HEX_RE.findall(value)
            if not found:
                continue
            value = norm_hex(found[0])
        elif field == "mode":
            value = "dark" if "dark" in value.lower() else "light"
            mode_given = True
        elif field == "movement":
            value = "none" if value.lower().startswith("non") else "a little"
        elif field == "icons":
            value = "lucide" if "lucide" in value.lower() else "carbon"
        look[field] = value
        seen = True
    if colours:  # the pre-October shape: ink, accent, paper in that order
        look["ink"] = colours[0]
        if len(colours) > 1:
            look["accent"] = colours[1]
        if len(colours) > 2:
            look["paper"] = colours[2]
        seen = True
    if seen and look["accent"] == PLAIN["accent"] and look["ink"] != PLAIN["ink"]:
        look["accent"] = look["ink"]
    if seen and not mode_given:
        look["mode"] = "dark" if is_dark(look["paper"]) else "light"
    look["written"] = seen
    return look


def read(root: Path) -> dict:
    """The look for a plane: standards/brand.md read, else plain black on white."""
    p = Path(root) / BRAND
    if not p.is_file():
        return dict(PLAIN)
    return parse(p.read_text(encoding="utf-8", errors="replace"))


def palette(look: dict) -> dict[str, str]:
    """Every colour a page may use, mixed from the three in brand.md.

    Muted text, rules and soft fills are blends of ink and paper; the accent's
    soft fill and its text shade are blends of the accent with paper and ink.
    So a page drawn from this uses only the person's colours, and the check in
    oac-vision.py can prove it."""
    ink, paper, accent = look["ink"], look["paper"], look["accent"]
    return {
        "ink": ink,
        "paper": paper,
        "accent": accent,
        "muted": mix(ink, paper, 0.45),
        "line": mix(ink, paper, 0.86),
        "soft": mix(ink, paper, 0.95),
        "accent_soft": mix(accent, paper, 0.84),
        "accent_ink": mix(accent, ink, 0.35),
    }


def on_segment(c: str, a: str, b: str, tol: int = 12) -> bool:
    """Is colour c a blend of a and b (within tol per channel)?"""
    rc, ra, rb = rgb(c), rgb(a), rgb(b)
    d = [rb[i] - ra[i] for i in range(3)]
    den = sum(x * x for x in d)
    if den == 0:
        return all(abs(rc[i] - ra[i]) <= tol for i in range(3))
    t = sum((rc[i] - ra[i]) * d[i] for i in range(3)) / den
    t = max(0.0, min(1.0, t))
    return all(abs(ra[i] + d[i] * t - rc[i]) <= tol for i in range(3))


def is_mine(c: str, look: dict) -> bool:
    """A colour belongs to the look when it is a blend of ink and paper, or of
    the accent with paper or ink. Nothing else is."""
    ink, paper, accent = look["ink"], look["paper"], look["accent"]
    return (on_segment(c, ink, paper) or on_segment(c, accent, paper)
            or on_segment(c, accent, ink))


def font_stack(look: dict, fallback: str = "Inter") -> str:
    face = look.get("typeface") or ""
    stack = "system-ui,-apple-system,'Segoe UI',sans-serif"
    if face and face.lower() != fallback.lower():
        return f"'{face}',{fallback},{stack}"
    return f"{fallback},{stack}"
