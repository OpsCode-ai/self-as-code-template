"""The element library: Carbon icons, our charts, our elements and effects, from one place.

WHY THIS EXISTS
    A page made for a person should be built from pieces that are ours and
    theirs, not from whatever the model reaches for (ADR-137, ADR-138). This
    is the one reader of the library: icons by name, a chart from numbers, the
    CSS for the pieces a page is built from, and the manifest that says where
    each thing came from and under what licence.

WHERE THE LIBRARY LIVES
    In opscode-hq: brand/library/ (manifest.yml, elements.css, effects.css,
    the licence files) and the icons at brand/assets/icons/<set>/, where the
    brand guidelines keep them. In a pack: scripts/lib/library/ with the icons
    under icons/<set>/. The first folder that exists wins, so the same code
    runs in both places.

TWO ICON SETS, ONE PER PAGE
    Carbon (fill, 32x32, the brand's) and Lucide (stroke, 24x24, ISC; Adam,
    18 November 2026). A look names its set in standards/brand.md (Icons:);
    every icon on that person's page comes from it, and oac-vision.py check
    refuses a page that mixes the two. The default is Carbon.

WHAT LEAVES THE LAPTOP
    Nothing. Every icon and chart is inline SVG; every colour is a CSS variable
    set by the look (standards/brand.md through lib/brand.py).

THE MARK
    Every piece carries data-lib="<source>:<name>", so `oac-vision.py check`
    can tell a library piece from one the model drew: an inline <svg> without
    the mark is a stray.
"""
from __future__ import annotations

import difflib
import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB_DIRS = (HERE / "library", HERE.parents[2] / "brand" / "library")
ICON_ROOTS = (HERE / "library" / "icons", HERE.parents[2] / "brand" / "assets" / "icons")
DEFAULT_SET = "carbon"
# How each set is drawn inline: Carbon fills, Lucide strokes.
SET_ATTRS = {
    "carbon": 'fill="currentColor"',
    "lucide": 'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"',
}
SVG_OPEN_RE = re.compile(r"<svg[^>]*>", re.S)
VIEWBOX_RE = re.compile(r'viewBox="([^"]+)"')
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def root() -> Path | None:
    for d in LIB_DIRS:
        if (d / "manifest.yml").is_file():
            return d
    return None


def icon_dir(icon_set: str = DEFAULT_SET) -> Path | None:
    """Where one set's icons are: icons/<set>/ in a pack, brand/assets/icons/<set>/ in the hub."""
    for root in ICON_ROOTS:
        d = root / icon_set
        if d.is_dir() and any(d.glob("*.svg")):
            return d
    return None


def icon_sets() -> list[str]:
    """The sets on disk, the default first."""
    found = []
    for root in ICON_ROOTS:
        if root.is_dir():
            found += [d.name for d in root.iterdir() if d.is_dir() and any(d.glob("*.svg"))]
    sets = sorted(set(found))
    return ([DEFAULT_SET] if DEFAULT_SET in sets else []) + [s for s in sets if s != DEFAULT_SET]


def set_of(look: dict | None) -> str:
    """The icon set a look names, when the library has it; Carbon otherwise."""
    want = str((look or {}).get("icons") or DEFAULT_SET).strip().lower()
    return want if want in SET_ATTRS and icon_dir(want) else DEFAULT_SET


# ── The manifest ─────────────────────────────────────────────────────────────

def _parse_yaml(text: str) -> dict:
    """Enough YAML for manifest.yml: top-level keys, top-level lists whose items
    are mappings (`- name: x` then indented keys) or quoted strings, and one
    list inside a mapping (`take:`). PyYAML is used when present."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        pass
    out: dict = {}
    top_list: str | None = None
    cur: dict | None = None
    cur_list: str | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        s = raw.strip()
        if indent == 0:
            cur, cur_list = None, None
            k, _, v = s.partition(":")
            if v.strip() == "":
                top_list = k.strip()
                out[top_list] = []
            else:
                top_list = None
                out[k.strip()] = v.strip().strip('"')
        elif indent == 2 and s.startswith("- ") and top_list:
            item = s[2:].strip()
            if re.match(r"^[A-Za-z_][\w-]*:(\s|$)", item):
                cur, cur_list = {}, None
                out[top_list].append(cur)
                k, _, v = item.partition(":")
                cur[k.strip()] = v.strip().strip('"')
            else:
                cur = None
                out[top_list].append(item.strip('"'))
        elif cur is not None and indent == 4:
            k, _, v = s.partition(":")
            if v.strip() == "":
                cur_list = k.strip()
                cur[cur_list] = []
            else:
                cur_list = None
                cur[k.strip()] = v.strip().strip('"')
        elif cur is not None and cur_list and s.startswith("- "):
            cur[cur_list].append(s[2:].strip().strip('"'))
    return out


def manifest() -> dict:
    r = root()
    if r is None:
        return {"sources": []}
    return _parse_yaml((r / "manifest.yml").read_text(encoding="utf-8"))


def source(name: str) -> dict | None:
    for s in manifest().get("sources", []):
        if s.get("name") == name:
            return s
    return None


# ── Icons ────────────────────────────────────────────────────────────────────

def icons(icon_set: str = DEFAULT_SET) -> list[str]:
    d = icon_dir(icon_set)
    return sorted(p.stem for p in d.glob("*.svg")) if d else []


def icon(name: str, size: int | str = "1.1em", label: str | None = None, cls: str = "lib-icon",
         icon_set: str = DEFAULT_SET) -> str:
    """One icon from one set, inline, in the surrounding text colour.

    A name the set does not have raises KeyError naming the nearest three (and
    the other set, when it has the name), so a session never ships a guess."""
    icon_set = icon_set if icon_set in SET_ATTRS else DEFAULT_SET
    d = icon_dir(icon_set)
    p = (d / f"{name}.svg") if d else None
    if p is None or not p.is_file():
        near = difflib.get_close_matches(name, icons(icon_set), n=3, cutoff=0.4)
        elsewhere = [s for s in icon_sets() if s != icon_set and name in icons(s)]
        raise KeyError(f"no icon '{name}' in the {icon_set} set"
                       + (f"; nearest: {', '.join(near)}" if near else "")
                       + (f"; the {elsewhere[0]} set has it, but a page uses one set" if elsewhere else ""))
    svg = COMMENT_RE.sub("", p.read_text(encoding="utf-8")).strip()
    vb = VIEWBOX_RE.search(svg)
    viewbox = vb.group(1) if vb else ("0 0 24 24" if icon_set == "lucide" else "0 0 32 32")
    inner = SVG_OPEN_RE.sub("", svg, count=1).rsplit("</svg>", 1)[0].strip()
    inner = re.sub(r"\s*\n\s*", "", inner)
    dim = f"{size}px" if isinstance(size, int) else str(size)
    a11y = f'role="img" aria-label="{html.escape(label, quote=True)}"' if label else 'aria-hidden="true"'
    return (f'<svg class="{cls}" data-lib="{icon_set}:{name}" viewBox="{viewbox}" width="{dim}" height="{dim}" '
            f'{SET_ATTRS[icon_set]} {a11y}>{inner}</svg>')


# ── CSS ──────────────────────────────────────────────────────────────────────

def _read(name: str) -> str:
    r = root()
    p = (r / name) if r else None
    return p.read_text(encoding="utf-8") if p and p.is_file() else ""


def elements_css() -> str:
    """The pieces a page is built from: button, pill, card, table, letterhead,
    ladder, eyebrow. Every colour a variable the look sets."""
    return _read("elements.css")


def effects_css() -> str:
    """Gentle movement, and none when the computer asks for less."""
    return _read("effects.css")


# ── Charts, from numbers ─────────────────────────────────────────────────────

def _nums(values) -> list[float]:
    out = []
    for v in values:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            out.append(0.0)
    return out


def _caption(source: str | None, width: int, height: int) -> str:
    if not source:
        return ""
    return (f'<text x="0" y="{height - 2}" font-size="10" style="fill:var(--muted)">'
            f'from {html.escape(source)}</text>')


def chart_bar(values, labels=None, width: int = 240, height: int = 90, source: str | None = None,
              label: str = "bar chart") -> str:
    """Bars from numbers, the accent for the bars, the look's muted for labels.
    `source` says where the numbers came from, drawn under the chart."""
    vals = _nums(values)
    labels = list(labels or [])
    n = max(len(vals), 1)
    top = max(vals) if vals and max(vals) > 0 else 1.0
    pad_b = 26 if source else 14
    plot_h = height - pad_b - 4
    gap = 6
    bw = max(4, (width - gap * (n - 1)) / n)
    parts = []
    for i, v in enumerate(vals):
        h = (v / top) * plot_h
        x = i * (bw + gap)
        y = 4 + plot_h - h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="2" style="fill:var(--accent)"/>')
        if i < len(labels):
            parts.append(f'<text x="{x + bw / 2:.1f}" y="{4 + plot_h + 11}" font-size="10" text-anchor="middle" '
                         f'style="fill:var(--muted)">{html.escape(str(labels[i]))}</text>')
    parts.append(f'<line x1="0" y1="{4 + plot_h}" x2="{width}" y2="{4 + plot_h}" style="stroke:var(--line)"/>')
    return (f'<svg class="lib-chart" data-lib="chart:bar" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'role="img" aria-label="{html.escape(label, quote=True)}">{"".join(parts)}{_caption(source, width, height)}</svg>')


def _points(vals: list[float], width: int, height: int, pad: int) -> str:
    n = len(vals)
    if n == 0:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    step = (width - 2 * pad) / max(n - 1, 1)
    return " ".join(f"{pad + i * step:.1f},{pad + (height - 2 * pad) * (1 - (v - lo) / span):.1f}" for i, v in enumerate(vals))


def chart_line(values, width: int = 240, height: int = 90, source: str | None = None, label: str = "line chart") -> str:
    """A line from numbers, the accent for the line, a dot on the last point."""
    vals = _nums(values)
    pad = 6
    h = height - (18 if source else 0)
    pts = _points(vals, width, h, pad)
    last = pts.rsplit(" ", 1)[-1] if pts else ""
    dot = ""
    if last:
        cx, cy = last.split(",")
        dot = f'<circle cx="{cx}" cy="{cy}" r="3" style="fill:var(--accent)"/>'
    return (f'<svg class="lib-chart" data-lib="chart:line" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'role="img" aria-label="{html.escape(label, quote=True)}">'
            f'<polyline points="{pts}" fill="none" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" '
            f'style="stroke:var(--accent)"/>{dot}{_caption(source, width, height)}</svg>')


def sparkline(values, width: int = 96, height: int = 24, label: str = "trend") -> str:
    """A small line for a table cell or a sentence end."""
    vals = _nums(values)
    pts = _points(vals, width, height, 2)
    return (f'<svg class="lib-spark" data-lib="chart:spark" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'role="img" aria-label="{html.escape(label, quote=True)}">'
            f'<polyline points="{pts}" fill="none" stroke-width="1.5" stroke-linejoin="round" style="stroke:var(--accent)"/></svg>')


def table(rows, head=None, cls: str = "lib-table") -> str:
    """A small table: the first cell left, the last right, numbers tabular."""
    th = ""
    if head:
        th = "<thead><tr>" + "".join(f"<th>{html.escape(str(h))}</th>" for h in head) + "</tr></thead>"
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}" data-lib="table:plain">{th}<tbody>{body}</tbody></table>'


def button(text: str, href: str | None = None, quiet: bool = False) -> str:
    cls = "lib-btn quiet" if quiet else "lib-btn"
    t = html.escape(text)
    if href:
        return f'<a class="{cls}" data-lib="element:button" href="{html.escape(href, quote=True)}">{t}</a>'
    return f'<button type="button" class="{cls}" data-lib="element:button">{t}</button>'


def pill(text: str, icon_name: str | None = None, icon_set: str = DEFAULT_SET) -> str:
    ico = icon(icon_name, size="1em", icon_set=icon_set) if icon_name else ""
    return f'<span class="lib-pill" data-lib="element:pill">{ico}{html.escape(text)}</span>'


def letterhead(who: str, under: str = "") -> str:
    return (f'<div class="lib-letterhead" data-lib="element:letterhead"><div class="who">{html.escape(who)}</div>'
            + (f'<div class="under">{html.escape(under)}</div>' if under else "") + '<div class="rule"></div></div>')
