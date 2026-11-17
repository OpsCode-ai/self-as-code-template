#!/usr/bin/env python3
"""Pick a look before anything is built, and keep every page to it (`/sac vision`).

WHY THIS EXISTS
    In the Melbourne room (27 and 28 October 2026) people made dashboards and
    reports from their plans, and what came out looked off the shelf: the
    vibe-coded look every AI tool makes, the same cards, the same fade, the
    same font, dark panels with green text (Adam, 30 October and 4 November).
    A thing made for a person should look made for them. Nobody can
    describe a look in words; everyone can pick one from three. So the session
    reads the plan, proposes three looks, this draws them on one page with a
    sample report, a sample dashboard and the letterhead, the person says a
    number, and the one they chose is written to standards/brand.md. From then
    on every output reads that file (ADR-136 Rule 11; ADR-137), and `check`
    proves a page kept to it.

WHAT LEAVES THE LAPTOP
    Nothing. No network call, no script tag. The two pack fonts are embedded
    from disk when the pack ships them (the self pack does); otherwise the
    page uses the system's fonts.

Usage:
    python3 scripts/oac-vision.py looks [--from .oac/looks.json] [--out PATH] [--no-open]
        Draw the look book, .oac/looks.html, and open it. Without a JSON file
        the three house looks are drawn, so there is always something to pick.
    python3 scripts/oac-vision.py pick N [--from .oac/looks.json]
        Write look N (1, 2 or 3) to standards/brand.md.
    python3 scripts/oac-vision.py check <page.html> [...]
        Exit 1 when a page uses a colour that is not a blend of the look's
        ink, paper and accent, a gradient, an inline <svg> that did not come
        from the library (no data-lib mark), or icons from both sets at once.
        The outputs gate for pages (ADR-136 Rule 11; ADR-138).
    python3 scripts/oac-vision.py show
        Print the look as read, so a session can say it back.

THE JSON the session writes, from the plan:
    {"looks": [{"name": "Quiet paper", "feel": "quiet, warm, exact",
                "ink": "#1f1d1a", "paper": "#faf7f1", "accent": "#b4532a",
                "typeface": "Inter", "movement": "a little", "icons": "carbon",
                "letterhead": "Jane Smith", "under": "Plumber. Teacher. Mum of two.",
                "because": ["'home by six', under the floor"]}]}
    Two or three looks. Every colour as hex. "icons" is carbon or lucide, the
    one set that look's pages draw from (ADR-138). Anything missing falls back
    to the house look in the same position.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import re
import sys
import webbrowser
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import brand, library  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = Path(".oac") / "looks.html"
LOOKS = Path(".oac") / "looks.json"
BRAND = Path("standards") / "brand.md"
FONT_DIRS = (HERE / "lib" / "fonts", HERE.parents[1] / "brand" / "assets" / "_fonts")
FONTS = (("Inter", "inter-variable.woff2", "100 900"),
         ("JetBrains Mono", "jetbrainsmono-variable.woff2", "100 800"))

# Three quiet looks, so there is always something to pick from. Each one is
# a page a person could read every day: one accent, space, no boxes in boxes.
HOUSE = [
    {"name": "Paper", "feel": "quiet, warm, exact", "ink": "#1f1d1a", "paper": "#faf7f1",
     "accent": "#b4532a", "typeface": "Inter", "movement": "a little", "because": []},
    {"name": "Ink", "feel": "calm, dark, steady", "ink": "#ece9e2", "paper": "#161514",
     "accent": "#d9a066", "typeface": "Inter", "movement": "none", "because": []},
    {"name": "Clear", "feel": "clear, cool, light", "ink": "#15202b", "paper": "#ffffff",
     "accent": "#0f766e", "typeface": "Inter", "movement": "a little", "icons": "lucide", "because": []},
]

NEVER = 'Nothing made for me looks like it came off the shelf. It is made for me: my\nwords, my colours, my name at the top. Never the look every AI tool makes\n(what people call vibe-coded): the purple fade, the same rounded cards, the\nsame font on every page, a badge on everything, a glow, dark panels with\nbright green text, code font for ordinary words. One accent colour, not\nthree. Space, not boxes.'
NEVER_BUSINESS = 'Nothing made for this business looks like it came off the shelf. It is made\nfor this business: its words, its colours, its name at the top. Never the\nlook every AI tool makes (what people call vibe-coded): the purple fade, the\nsame rounded cards, the same font on every page, a badge on everything, a\nglow, dark panels with bright green text, code font for ordinary words. One\naccent colour, not three. Space, not boxes.'


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def plane_of(root: Path) -> str:
    """'self' or 'business', from .oac/manifest.yml; a private space by default."""
    m = root / ".oac" / "manifest.yml"
    if m.is_file():
        hit = re.search(r"^plane:\s*(\w+)", m.read_text(encoding="utf-8", errors="replace"), re.M)
        if hit:
            return hit.group(1).strip().lower()
    return "self"


def name_of(root: Path, plane: str) -> str:
    """The name for the letterhead when a look does not give one: the plan's title
    before the colon, else the business's title, else the folder."""
    if plane == "self":
        for rel in ("self-as-code.md", "goals/self-as-code.md"):
            p = root / rel
            if p.is_file():
                t = re.search(r"^title:\s*\"?(.*?)\"?\s*$", p.read_text(encoding="utf-8", errors="replace"), re.M)
                if t:
                    return t.group(1).split(":")[0].strip() or root.name
    for rel in ("CLAUDE.md", "README.md"):
        p = root / rel
        if p.is_file():
            t = re.search(r"^title:\s*\"?(.*?)\"?\s*$", p.read_text(encoding="utf-8", errors="replace"), re.M)
            if t:
                return t.group(1).split(":")[0].strip() or root.name
    return root.name


def load_looks(root: Path, src: Path | None) -> list[dict]:
    """The looks to draw: the session's JSON, filled from the house looks."""
    given: list[dict] = []
    path = src or (root / LOOKS)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise SystemExit(f"{path}: not JSON ({e})")
        given = data.get("looks", data) if isinstance(data, (dict, list)) else []
        if isinstance(given, dict):
            given = [given]
    looks: list[dict] = []
    for i in range(max(len(given), 0) or 3):
        base = dict(HOUSE[i % len(HOUSE)])
        if i < len(given) and isinstance(given[i], dict):
            for k, v in given[i].items():
                if v not in (None, "", []):
                    base[k] = v
        for k in ("ink", "paper", "accent"):
            if not brand.HEX_RE.fullmatch(str(base[k]).strip()):
                raise SystemExit(f"look {i + 1}: {k} must be a hex colour, got {base[k]!r}")
            base[k] = brand.norm_hex(str(base[k]))
        if isinstance(base.get("feel"), list):
            base["feel"] = ", ".join(str(x) for x in base["feel"])
        base["movement"] = "none" if str(base.get("movement", "")).lower().startswith("non") else "a little"
        base["icons"] = library.set_of(base)
        base["mode"] = "dark" if brand.is_dark(base["paper"]) else "light"
        base.setdefault("because", [])
        looks.append(base)
    return looks[:3] if not given else looks


def font_css() -> str:
    rules = []
    for family, file, weights in FONTS:
        for d in FONT_DIRS:
            p = d / file
            if p.is_file():
                b64 = base64.b64encode(p.read_bytes()).decode("ascii")
                rules.append(f"@font-face{{font-family:'{family}';font-weight:{weights};font-display:swap;"
                             f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")
                break
    return "".join(rules)


CSS = """
*{box-sizing:border-box}
html{background:#f3f2ef}
body{margin:0;background:#f3f2ef;color:#1b1b1b;font:16px/1.55 Inter,system-ui,-apple-system,'Segoe UI',sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:40px 16px 64px}
header h1{font-size:30px;line-height:1.15;margin:0 0 6px;letter-spacing:-.01em}
header p{margin:0;color:#5a5955;max-width:720px}
.looks{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px;margin-top:28px}
.look{background:var(--paper);color:var(--ink);border-radius:16px;padding:22px 22px 18px;font-family:var(--font);box-shadow:0 1px 2px rgba(0,0,0,.06)}
.look .num{display:inline-block;min-width:30px;height:30px;line-height:30px;text-align:center;border-radius:999px;background:var(--ink);color:var(--paper);font-weight:600;margin-right:10px}
.look .top{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
.look .name{font-weight:600}
.look .feel{color:var(--muted);font-size:14px}
.sample{margin-top:18px;padding-top:16px;border-top:1px solid var(--line)}
.eyebrow{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:8px}
.letter .who{font-size:24px;line-height:1.15;letter-spacing:-.01em}
.letter .under{color:var(--muted);margin-top:2px}
.letter .rule{height:2px;width:56px;background:var(--accent);margin-top:12px}
.report h3{font-size:19px;line-height:1.3;margin:0 0 8px}
.report p{margin:0 0 10px}
.report table{border-collapse:collapse;width:100%;font-size:14px}
.report td{padding:6px 0;border-top:1px solid var(--line)}
.report td:last-child{text-align:right;color:var(--muted)}
.dash .line{font-size:18px;margin:0 0 12px}
.dash .line b{font-weight:600;color:var(--accent-ink)}
.ladder{position:relative;margin-left:6px;padding-left:22px;border-left:2px solid var(--line)}
.rung{position:relative;padding:0 0 12px;font-size:14px}
.rung:last-child{padding-bottom:0}
.rung::before{content:'';position:absolute;left:-29px;top:5px;width:10px;height:10px;border-radius:50%;background:var(--paper);border:2px solid var(--accent)}
.rung.now::before{background:var(--accent)}
.rung .k{color:var(--muted);display:block;font-size:12px}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;background:var(--accent-soft);color:var(--accent-ink);font-size:13px;margin:10px 6px 0 0}
.sig{font-size:14px}.sig .who{font-weight:600}.sig .under{color:var(--muted)}
.because{margin-top:16px;padding-top:12px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}
.because ul{margin:4px 0 0;padding-left:18px}
.parts .row{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:8px 0}
.parts .icons{gap:14px;color:var(--ink)}
.parts .lib-table{margin-top:8px}
.pick{margin-top:28px;color:#5a5955;max-width:720px}
.pick code{font:13px/1.4 'JetBrains Mono',ui-monospace,monospace;background:#e7e5e0;padding:1px 5px;border-radius:5px}
@media (max-width:520px){.wrap{padding-top:28px}header h1{font-size:26px}.look{padding:18px}}
@media (prefers-reduced-motion:no-preference){.look{transition:transform .2s ease}.look:hover{transform:translateY(-2px)}}
"""


def vars_css(look: dict) -> str:
    pal = brand.palette(look)
    return (f"--ink:{pal['ink']};--paper:{pal['paper']};--accent:{pal['accent']};--muted:{pal['muted']};"
            f"--line:{pal['line']};--soft:{pal['soft']};--accent-soft:{pal['accent_soft']};"
            f"--accent-ink:{pal['accent_ink']};--font:{brand.font_stack(look)}")


def look_card(n: int, look: dict, name: str, plane: str, today: str) -> str:
    who = look.get("letterhead") or name
    under = look.get("under") or ("What I'm here to do, in one line." if plane == "self" else "What this business is for, in one line.")
    going = "How I'm going" if plane == "self" else "How we're going"
    my = "my" if plane == "self" else "the"
    because = "".join(f"<li>{esc(b)}</li>" for b in look.get("because", []) if str(b).strip())
    return (
        f'<section class="look" style="{vars_css(look)}">'
        f'<div class="top"><div><span class="num">{n}</span><span class="name">{esc(look["name"])}</span></div>'
        f'<span class="feel">{esc(look["feel"])} · {esc(look["mode"])}</span></div>'
        f'<div class="letter"><div class="eyebrow">A letter, at the top</div><div class="who">{esc(who)}</div>'
        f'<div class="under">{esc(under)}</div><div class="rule"></div></div>'
        f'<div class="sample report"><div class="eyebrow">A report, this week</div>'
        f'<h3>The floor held five days of seven.</h3>'
        f'<p>Tuesday and Thursday slipped on sleep. The daily steps held every day. Two of {my} three things got done.</p>'
        f'<table><tr><td>Floor held</td><td>5 of 7</td></tr><tr><td>Daily steps</td><td>7 of 7</td></tr>'
        f'<tr><td>This week\'s three</td><td>2 of 3</td></tr></table></div>'
        f'<div class="sample dash"><div class="eyebrow">A dashboard</div>'
        f'<p class="line">{going}: <b>on track</b></p>'
        f'<div class="ladder"><div class="rung"><span class="k">In 5 years</span>Two days a week, by choice.</div>'
        f'<div class="rung now"><span class="k">This week</span>Ring the recruiter. Finish the quote.</div>'
        f'<div class="rung"><span class="k">Tomorrow</span>8am: the recruiter.</div></div>'
        f'<span class="pill">floor 5 of 7</span><span class="pill">2 businesses moved</span></div>'
        f'<div class="sample sig"><div class="eyebrow">An email, signed</div><div class="who">{esc(who)}</div>'
        f'<div class="under">{esc(under)}</div></div>'
        + parts_row(plane, look.get("icons", library.DEFAULT_SET))
        + (f'<div class="because">From {"your plan" if plane == "self" else "the Context Core"}:<ul>{because}</ul></div>' if because else "")
        + "</section>"
    )


# The same six ideas in each set, so the sets can be compared look to look.
PARTS_ICONS = {
    "carbon": ("calendar", "chart--line", "user--multiple", "checkmark--filled", "notification", "document"),
    "lucide": ("calendar", "chart-line", "users", "circle-check", "bell", "file-text"),
}
PILL_ICON = {"carbon": "checkmark", "lucide": "check"}


def parts_row(plane: str, icon_set: str = library.DEFAULT_SET) -> str:
    """The pieces a page is built from, drawn from the library in this look:
    a button, a quiet button, a pill, six icons from the look's set, a bar
    chart, a sparkline and a table. So a person picks the parts as well as
    the look (ADR-138)."""
    icons = "".join(library.icon(n, size="20px", icon_set=icon_set) for n in PARTS_ICONS[icon_set])
    return ('<div class="sample parts"><div class="eyebrow">The pieces a page is built from'
            f' · {esc(icon_set)} icons</div>'
            f'<div class="row">{library.button("Save the plan")}{library.button("Not now", quiet=True)}'
            f'{library.pill("floor 5 of 7", PILL_ICON[icon_set], icon_set=icon_set)}</div>'
            f'<div class="row icons">{icons}</div>'
            f'<div class="row">{library.chart_bar([5, 7, 6, 4, 7], ["M", "T", "W", "T", "F"], width=200, height=70, source="the log")}'
            f'{library.sparkline([3, 4, 4, 6, 5, 7])}</div>'
            + library.table([("Floor held", "5 of 7"), ("Daily steps", "7 of 7"), ("This week\'s three", "2 of 3")])
            + "</div>")


def render(looks: list[dict], name: str, plane: str, today: str) -> str:
    you = "you" if plane == "self" else "the business"
    cards = "".join(look_card(i + 1, lk, name, plane, today) for i, lk in enumerate(looks))
    n = len(looks)
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{esc(name)}: pick a look</title>"
            f"<style>{font_css()}{CSS}{library.elements_css()}{library.effects_css()}</style></head><body><div class=\"wrap\">"
            f"<header><h1>{n} looks. Say the number.</h1>"
            f"<p>Each one is the same report, the same dashboard and the same letter, drawn a different way. "
            f"Pick the one {you} could look at every day. Or say what is wrong with each, and the next three will be closer.</p></header>"
            f'<div class="looks">{cards}</div>'
            f'<p class="pick">If none of these is right, open refero.design in your browser: it shows screens from real apps and sites. '
            f'Find two you would be happy to look at every day and say what you liked about them. '
            f'Drawn on this laptop on {esc(today)}. Nothing left it.</p>'
            "</div></body></html>\n")


def write_brand(root: Path, look: dict, plane: str, today: str) -> Path:
    """standards/brand.md from one look, one line each, with the plan lines it came from."""
    name = look.get("letterhead") or name_of(root, plane)
    under = look.get("under") or ""
    p = root / BRAND
    kept: list[str] = []
    if p.is_file():
        old = p.read_text(encoding="utf-8", errors="replace")
        hit = re.search(r"^## Where I looked\s*\n(.*?)(?=^## |\Z)", old, re.S | re.M)
        if hit:
            kept = [l for l in hit.group(1).splitlines() if l.startswith("- ") and "refero.design shows" not in l]
    title = "What I like to look at" if plane == "self" else "What this business looks like"
    audience = "owner" if plane == "self" else "internal"
    me = "my" if plane == "self" else "this business's"
    because = "\n".join(f"- {b}" for b in look.get("because", []) if str(b).strip()) or "- *The lines this came from, when a plan says them.*"
    looked = "\n".join(kept) or "- *Add a line when a real page helped you choose. refero.design shows screens from real apps and sites.*"
    text = f"""---
title: "{title}"
type: standard
audience: {audience}
status: active
updated: {today}
---

# {title}

Picked on {today} from three looks drawn from {me} {"plan" if plane == "self" else "Context Core"}
(`/sac vision`). One line each. The words before each colon are read by
everything made {"for me" if plane == "self" else "for the business"}, so keep them as they are.

- Feel: {look['feel']}
- Ink: {look['ink']}
- Paper: {look['paper']}
- Accent: {look['accent']}
- Typeface: {look.get('typeface') or 'none'}
- Light or dark: {look['mode']}
- Movement: {look['movement']}
- Letterhead: {name}
- Under it: {under}
- Icons: {look.get('icons', library.DEFAULT_SET)}

## Why this look

{because}

## Never

{NEVER if plane == "self" else NEVER_BUSINESS}

## Where I looked

{looked}
"""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def strays(page: str, look: dict) -> list[str]:
    """Every hex colour on a page that is not a blend of the look's three."""
    body = re.sub(r"data:[^)\"' ]+", "", page)
    seen: dict[str, int] = {}
    for h in brand.HEX_RE.findall(body):
        c = brand.norm_hex(h)
        if not brand.is_mine(c, look):
            seen[c] = seen.get(c, 0) + 1
    return [f"{c} ({n})" for c, n in sorted(seen.items(), key=lambda kv: -kv[1])]


GRADIENT_RE = re.compile(r"\b(?:linear|radial|conic)-gradient\s*\(", re.I)
SVG_RE = re.compile(r"<svg\b[^>]*>", re.I | re.S)


def stray_marks(page: str) -> list[str]:
    """What is on a page that did not come from the look or the library: a
    gradient, or an inline svg without the library's data-lib mark (ADR-138)."""
    out = []
    g = len(GRADIENT_RE.findall(page))
    if g:
        out.append(f"a gradient ({g})")
    unmarked = sum(1 for m in SVG_RE.findall(page) if "data-lib=" not in m)
    if unmarked:
        out.append(f"an svg not from the library ({unmarked})")
    sets = sorted({m for m in re.findall(r'''data-lib=["']([a-z]+):''', page) if m in library.SET_ATTRS})
    if len(sets) > 1:
        out.append(f"two icon sets on one page ({' and '.join(sets)})")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pick a look once; keep every page to it.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    lk = sub.add_parser("looks", help="draw the look book")
    lk.add_argument("--root", default=".", help="the repo (default: here)")
    lk.add_argument("--from", dest="src", type=Path, default=None, help=f"the looks JSON (default: {LOOKS})")
    lk.add_argument("--out", type=Path, default=None, help=f"where to write the page (default: {OUT})")
    lk.add_argument("--no-open", action="store_true")
    pk = sub.add_parser("pick", help="write look N to standards/brand.md")
    pk.add_argument("n", type=int)
    pk.add_argument("--root", default=".")
    pk.add_argument("--from", dest="src", type=Path, default=None)
    ck = sub.add_parser("check", help="a page's colours are the look's, or exit 1")
    ck.add_argument("pages", nargs="+", type=Path)
    ck.add_argument("--root", default=".")
    sh = sub.add_parser("show", help="print the look as read")
    sh.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    plane = plane_of(root)
    today = date.today().isoformat()

    if args.cmd == "looks":
        looks = load_looks(root, args.src)
        out = (args.out or (root / OUT)).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(looks, name_of(root, plane), plane, today), encoding="utf-8")
        print(f"drawn: {out}")
        print("say the number: " + ", ".join(f"{i + 1} {lk['name']}" for i, lk in enumerate(looks)))
        if not args.no_open:
            try:
                webbrowser.open(out.as_uri())
            except Exception as e:  # a headless machine, or no browser registered
                print(f"could not open a browser ({e}); open the file yourself")
        return 0

    if args.cmd == "pick":
        looks = load_looks(root, args.src)
        if not 1 <= args.n <= len(looks):
            print(f"pick a number from 1 to {len(looks)}", file=sys.stderr)
            return 2
        p = write_brand(root, looks[args.n - 1], plane, today)
        print(f"written: {p.relative_to(root)} ({looks[args.n - 1]['name']})")
        print("everything made from now on reads it first. Run the dashboard again to see it.")
        return 0

    if args.cmd == "check":
        look = brand.read(root)
        bad = 0
        for page in args.pages:
            if not page.is_file():
                print(f"{page}: not found", file=sys.stderr)
                bad += 1
                continue
            text = page.read_text(encoding="utf-8", errors="replace")
            s = strays(text, look)
            marks = stray_marks(text)
            if s or marks:
                bad += 1
                which = "the look in standards/brand.md" if look["written"] else "plain black on white (no look chosen yet)"
                if s:
                    print(f"{page}: colours that are not {which}: " + ", ".join(s))
                if marks:
                    print(f"{page}: not from the library: " + ", ".join(marks))
            else:
                print(f"{page}: every colour is the look's, every piece is the library's")
        return 1 if bad else 0

    if args.cmd == "show":
        look = brand.read(root)
        print(json.dumps({k: v for k, v in look.items()}, indent=1))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
