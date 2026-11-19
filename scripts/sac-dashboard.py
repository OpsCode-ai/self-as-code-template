#!/usr/bin/env python3
"""Draw a Self as Code plan as one page, on this laptop (`/sac dashboard`).

WHY THIS EXISTS
    Nobody can see what they built. The Auckland room's aha came when Terminal
    talked back, and Jimmy's note from 21 October 2026 was 'they don't visually
    know what they've done; it's just a folder structure'. This reads
    self-as-code.md and the five folders, writes one page, .oac/dashboard.html,
    and opens it in the browser. The Melbourne build plan, S1.2.

WHAT LEAVES THE LAPTOP
    Nothing. No network call, no script tag, no font from a CDN: the two brand
    fonts are read from disk and embedded in the page. Delete the page any
    time; it is rebuilt from the plan.

THE LOOK
    standards/brand.md, when it is written, sets the ink, the paper, the one
    accent, the typeface and the two letterhead lines (ADR-136 Rule 11;
    ADR-137). Every other colour on the page is a blend of those three, so
    `oac-vision.py check` can prove the page kept to the look. A seed, or no
    file, is plain black on white: the promise the seed makes.

THE SHAPE: AN APP, NOT A DOCUMENT (Adam, 20 Nov 2026)
    A menu down the left, like any software people use, with an icon from the
    look's one icon set (the element library, ADR-138); on a phone it folds
    into a Menu button at the top, with no script. It opens on the timeline:
    the future you at 20 years down through 10, 5, 2 and 1 year (the ones the
    plan has), six months, the next review, this week, tomorrow and every
    day, across the page on a laptop and down it on a phone. Under it, this
    week and the floor side by side.

WHAT IT SHOWS
    The ladder (20, 10 and 5 years, the six-month leap, the next review, this
    week, tomorrow, every day); why they exist; who they are becoming; the
    floor and the cut; the daily steps; each business and how it serves why;
    anything parked; what they share with each business; the five folders and
    what is in them; the last few saves.

HOW IT READS
    Headings the way the OaC client does (products/oac-client/src/lib/
    parseSelfAsCode.ts): case-insensitive, a leading 'the' optional, and the
    old `## refactor` read as `## review`. The lines framework 0.8 fixes are
    found by their first words: `In N years:` under `## main`, `Tomorrow:` and
    `This week:` at the end of `## commits`, `Parked:` under any heading, and a
    business's `Kind:`, `Years:`, `People:`, `Runs on:`, `Build first:` and
    `Serves why:`. A plan missing a heading draws the rest. A seeded plan (the
    pack's `TO FILL IN` placeholders) says to run /sac. Never a blank page.

Usage:
    python3 scripts/sac-dashboard.py [root] [--out PATH] [--no-open]
"""
from __future__ import annotations

import argparse
import base64
import html
import importlib.util
import re
import subprocess
import sys
import webbrowser
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.frontmatter import body as fm_body, frontmatter  # noqa: E402
from lib.brand import PLAIN, palette, font_stack, read as read_brand  # noqa: E402
try:
    from lib import library  # noqa: E402  the icons for the menu, from the look's one set
except ImportError:                       # an old pack without the library: a menu without icons
    library = None

HERE = Path(__file__).resolve().parent
SPINE_ADDRESSES = ("self-as-code.md", "goals/self-as-code.md")
OUT = Path(".oac") / "dashboard.html"
FONT_DIRS = (HERE / "lib" / "fonts", HERE.parents[1] / "brand" / "assets" / "_fonts")
FONTS = (("Inter", "inter-variable.woff2", "100 900"),
         ("JetBrains Mono", "jetbrainsmono-variable.woff2", "100 800"))

# The plan's headings, as the OaC client reads them: lowercased, 'the ' dropped.
HEADING_KEYS = {
    "baseline": "baseline", "readme": "readme", "read me": "readme", "main": "main",
    "rewrite": "rewrite", "floor": "floor", "cut": "cut", "commits": "commits",
    "commit": "commits", "review": "review", "refactor": "review", "split": "split",
    "history": "history",
}
SETUP_LINES = ("Kind", "Years", "People", "Runs on", "Build first", "Serves why")
FOLDERS = (
    ("standards", "What I hold myself to"),
    ("projects", "What ends on a date"),
    ("archive", "Done, dropped or replaced"),
    ("decisions", "Choices I have made"),
    ("evidence", "What I look things up in"),
)
OLD_FOLDER_NAMES = {"archive": "history", "evidence": "library"}
RUNG_RE = re.compile(r"^\s*In (\d+) years?:\s*(.+?)\s*$", re.I)
PARKED_RE = re.compile(r"^\s*Parked:\s*(.+?)\s*$", re.I)
# Framework 0.9: `Value: <name>: <what it looks like on my worst day>` under the floor.
VALUE_RE = re.compile(r"^\s*Value:\s*([^:]+?)\s*(?::\s*(.+?))?\s*$", re.I)
FIXED_RE = re.compile(r"^\s*(" + "|".join(re.escape(k) for k in SETUP_LINES + ("Tomorrow", "This week")) + r"):\s*(.+?)\s*$", re.I)
SEEDED_RE = re.compile(r"^\s*\*?\s*TO FILL IN\b", re.I)
# The one plain line the session writes under each heading to say what it
# means (framework: 'how to speak'). The page has its own headings, so it is
# dropped when it leads a section, and only then.
MEANING_LINES = {
    "where i am today", "why i exist", "who i am becoming", "my one big leap in the next six months",
    "what i never drop below", "what i hand over, stop, or say no to", "what i do every day, no matter what",
    "when i next review this, and what i check", "what i share with each business, and what stays mine",
}


# ── Reading the plan ─────────────────────────────────────────────────────────

def find_spine(root: Path) -> Path | None:
    for rel in SPINE_ADDRESSES:
        if (root / rel).is_file():
            return root / rel
    return None


def norm_heading(h: str) -> str:
    return re.sub(r"^the\s+", "", h.strip().lower()).rstrip(":.").strip()


def split_h2(text: str) -> tuple[str | None, list[tuple[str, str]]]:
    """(the H1 title, [(heading, body)]) for every `## ` section, in order.
    Fenced code is skipped, so a `##` inside a code block is not a heading."""
    title = None
    sections: list[tuple[str, list[str]]] = []
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if not fenced:
            h1 = re.match(r"^#\s+(.+?)\s*$", line)
            h2 = re.match(r"^##\s+(?!#)(.+?)\s*$", line)
            if h2:
                sections.append((h2.group(1).strip(), []))
                continue
            if h1 and title is None and not sections:
                title = h1.group(1).strip()
                continue
        if sections:
            sections[-1][1].append(line)
    return title, [(h, "\n".join(ls).strip()) for h, ls in sections]


def strip_seed(text: str) -> str:
    """The section without the pack's placeholder paragraphs. A placeholder
    starts `*TO FILL IN` and may run over several lines, so whole paragraphs
    go, never single lines."""
    kept = []
    for para in re.split(r"\n\s*\n", text.strip()):
        first = para.strip().lstrip("*_ ")
        if not SEEDED_RE.match(first):
            kept.append(para.strip())
    return "\n\n".join(kept)


def is_written(text: str) -> bool:
    """A section counts as written when something other than the seed is there."""
    return bool(strip_seed(text).strip())


def plain_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def drop_meaning(lines: list[str]) -> list[str]:
    """Without the heading's one-line meaning, when it leads the block."""
    if not lines:
        return lines
    first = lines[0].strip().strip("*_").strip().rstrip(".").lower()
    if first in MEANING_LINES or re.match(r"^[*_].*[*_]$", lines[0].strip()):
        return lines[1:]
    return lines


def pull_fixed(lines: list[str]) -> tuple[dict[str, str], list[str]]:
    """The fixed first-word lines out of a block, and what is left."""
    fixed: dict[str, str] = {}
    rest: list[str] = []
    for ln in lines:
        m = FIXED_RE.match(ln.lstrip("-*• "))
        if m:
            fixed[m.group(1).lower()] = m.group(2)
        else:
            rest.append(ln)
    return fixed, rest


def pull_values(lines: list[str]) -> tuple[list[tuple[str, str]], list[str]]:
    """The `Value:` lines out of the floor, as (name, worst-day line), and what is left."""
    values: list[tuple[str, str]] = []
    rest: list[str] = []
    for ln in lines:
        m = VALUE_RE.match(ln.lstrip("-*• "))
        if m:
            values.append((m.group(1).strip(), (m.group(2) or "").strip()))
        else:
            rest.append(ln)
    return values, rest


def pull_parked(lines: list[str], where: str, parked: list[tuple[str, str]]) -> list[str]:
    rest = []
    for ln in lines:
        m = PARKED_RE.match(ln.lstrip("-*• "))
        if m:
            parked.append((where, m.group(1)))
        else:
            rest.append(ln)
    return rest


def read_plan(spine: Path | None, root: Path) -> dict:
    """Everything the page needs, as plain Python. No markdown reaches the
    renderer unescaped."""
    plan: dict = {
        "name": name_from_folder(root), "fields": {}, "written": False,
        "sections": {}, "about": [], "businesses": [], "rungs": [], "picture": [],
        "steps": [], "tomorrow": None, "this_week": None, "parked": [], "split": None,
        "values": [],
    }
    if spine is None:
        return plan
    raw = spine.read_text(encoding="utf-8", errors="replace")
    fields = frontmatter(raw)
    plan["fields"] = fields
    title, sections = split_h2(fm_body(raw))
    plan["name"] = name_from_title(fields.get("title") or title or "") or plan["name"]
    where_label = {"baseline": "Where I am now", "readme": "Why I exist", "main": "Who I'm becoming",
                   "rewrite": "My one big leap", "floor": "My floor", "cut": "My cut",
                   "commits": "Every day", "review": "My next review"}
    for heading, text in sections:
        key = HEADING_KEYS.get(norm_heading(heading))
        if key is None or key in plan["sections"]:
            continue
        if not is_written(text):
            continue
        plan["sections"][key] = strip_seed(text)
    plan["written"] = any(k in plan["sections"] for k in ("baseline", "readme", "main", "rewrite", "floor", "cut", "commits"))
    parked: list[tuple[str, str]] = plan["parked"]

    # Now: the plain lines above the first business, then one block per business.
    base = plan["sections"].get("baseline", "")
    about_lines: list[str] = []
    current: dict | None = None
    for ln in base.splitlines():
        h3 = re.match(r"^###\s+(.+?)\s*$", ln)
        if h3:
            current = {"name": h3.group(1).strip(), "lines": []}
            plan["businesses"].append(current)
        elif current is not None:
            current["lines"].append(ln)
        else:
            about_lines.append(ln)
    plan["about"] = pull_parked(drop_meaning(plain_lines("\n".join(about_lines))), "Where I am now", parked)
    for biz in plan["businesses"]:
        lines = pull_parked(plain_lines("\n".join(biz.pop("lines"))), biz["name"], parked)
        biz["setup"], biz["words"] = pull_fixed(lines)

    # Who: the picture, then the rungs.
    for ln in pull_parked(drop_meaning(plain_lines(plan["sections"].get("main", ""))), "Who I'm becoming", parked):
        m = RUNG_RE.match(ln.lstrip("-*• "))
        if m:
            plan["rungs"].append((int(m.group(1)), m.group(2)))
        else:
            plan["picture"].append(ln)
    plan["rungs"].sort(key=lambda r: -r[0])

    # Every day: the steps, then tomorrow and this week.
    fixed, steps = pull_fixed(pull_parked(drop_meaning(plain_lines(plan["sections"].get("commits", ""))), "Every day", parked))
    plan["steps"] = steps
    plan["tomorrow"] = fixed.get("tomorrow")
    plan["this_week"] = fixed.get("this week")

    for key in ("readme", "rewrite", "floor", "cut", "review"):
        if key in plan["sections"]:
            kept = pull_parked(drop_meaning(plain_lines(plan["sections"][key])), where_label[key], parked)
            if key == "floor":
                plan["values"], kept = pull_values(kept)
            plan["sections"][key] = "\n".join(kept)

    plan["split"] = read_split_rows(plan["sections"].get("split"))
    return plan


def read_split_rows(text: str | None) -> dict | None:
    """What they share: counts only, through the split script's own reader,
    which ships beside this one. Without it, the panel is left out."""
    if not text:
        return None
    script = HERE / "self-as-code-split.py"
    if not script.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("sac_split", script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rows, _errors = mod.parse_split(text)
    except Exception:
        return None
    out = {"mine": 0, "parked": 0, "to": {}}
    for r in rows:
        if r["routing"] == "stays-personal":
            out["mine"] += 1
        elif r["routing"] == "promotable-unrouted":
            out["parked"] += 1
        else:
            dest = r["unit"] + (f"/{r['venture']}" if r["venture"] else "")
            out["to"][dest] = out["to"].get(dest, 0) + 1
    return out


def name_from_title(title: str) -> str:
    t = title.strip().strip("\"'")
    t = re.sub(r"\s*[:—–-]\s*Self as Code.*$", "", t, flags=re.I)
    t = re.sub(r"^Self as Code\s*[:—–-]?\s*", "", t, flags=re.I)
    return t.strip()


def name_from_folder(root: Path) -> str:
    stem = re.sub(r"-ops$", "", root.resolve().name)
    return " ".join(w.capitalize() for w in stem.split("-") if w) or "You"


def folder_counts(root: Path) -> list[dict]:
    out = []
    for folder, meaning in FOLDERS:
        path = root / folder
        if not path.is_dir() and folder in OLD_FOLDER_NAMES and (root / OLD_FOLDER_NAMES[folder]).is_dir():
            path = root / OLD_FOLDER_NAMES[folder]
        if not path.is_dir():
            out.append({"name": folder, "meaning": meaning, "count": None, "recent": []})
            continue
        files = [p for p in path.rglob("*") if p.is_file() and p.name not in ("README.md", ".gitkeep")
                 and not any(part.startswith(".") for part in p.relative_to(path).parts)]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        out.append({"name": folder, "meaning": meaning, "count": len(files),
                    "recent": [p.relative_to(path).as_posix() for p in files[:4]]})
    return out


def recent_saves(root: Path) -> list[tuple[str, str]]:
    if not (root / ".git").exists():
        return []
    try:
        r = subprocess.run(["git", "-C", str(root), "log", "-5", "--format=%cs%x09%s"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return []
    if r.returncode != 0:
        return []
    return [tuple(ln.split("\t", 1)) for ln in r.stdout.splitlines() if "\t" in ln]


# ── Drawing the page ─────────────────────────────────────────────────────────

def esc(s: str) -> str:
    return html.escape(s, quote=True)


def inline(s: str) -> str:
    """Escaped text with the little markdown people write: bold, italics, code."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)([^*]+?)\*(?![\w*])", r"<em>\1</em>", s)
    return s


def prose(lines: list[str] | str) -> str:
    """Paragraphs and lists from plain lines. The one-line meaning the session
    writes under each heading reads as the first paragraph, as intended."""
    if isinstance(lines, str):
        lines = plain_lines(lines)
    out: list[str] = []
    items: list[str] = []
    def flush():
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            items.clear()
    for ln in lines:
        m = re.match(r"^(?:[-*•]|\d+[.)])\s+(.+)$", ln)
        if m:
            items.append(m.group(1))
        else:
            flush()
            out.append(f"<p>{inline(ln)}</p>")
    flush()
    return "".join(out)


def empty(what: str = "Not written yet.") -> str:
    return f'<p class="empty">{esc(what)}</p>'


def first_line(text: str | None) -> str | None:
    if not text:
        return None
    lines = plain_lines(text)
    return re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", lines[0]) if lines else None


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


def root_css(look: dict) -> str:
    """The page's colours and type, from the look: three colours and their blends."""
    pal = palette(look)
    return (f":root{{--ink:{pal['ink']};--paper:{pal['paper']};--accent:{pal['accent']};--muted:{pal['muted']};"
            f"--line:{pal['line']};--soft:{pal['soft']};--accent-soft:{pal['accent_soft']};"
            f"--accent-ink:{pal['accent_ink']};--font:{font_stack(look)}}}")


CSS = """
*{box-sizing:border-box}
html{background:var(--paper);scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 var(--font);-webkit-font-smoothing:antialiased}
.app{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100vh}
.side{position:sticky;top:0;height:100vh;overflow-y:auto;border-right:1px solid var(--line);background:var(--soft);padding:28px 14px}
.side .brand{font-weight:700;font-size:17px;line-height:1.25;margin:0 10px 4px}
.side .brand-sub{font:600 11px/1.3 var(--font);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 10px 22px}
.nav a{display:flex;align-items:center;gap:10px;padding:9px 10px;margin:2px 0;border-radius:10px;color:var(--ink);text-decoration:none;font-size:15px}
.nav a:hover,.nav a:focus-visible{background:var(--accent-soft);color:var(--accent-ink);outline:none}
.nav a svg{flex:none;color:var(--muted)}
.nav a:hover svg{color:var(--accent-ink)}
.topbar{display:none}
.main{min-width:0;max-width:1120px;padding:40px 44px 72px}
.eyebrow{font:600 12px/1.2 var(--font);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
h1{font-size:34px;line-height:1.15;letter-spacing:-.01em;margin:8px 0 6px}
h2{font-size:20px;margin:0 0 12px;letter-spacing:-.005em}
.meta{color:var(--muted);margin:0}
section{margin-top:44px;scroll-margin-top:72px}
.card{border:1px solid var(--line);border-radius:14px;padding:18px 20px;background:var(--paper)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin-top:44px}
.pair section{margin-top:0}
.why p{font-size:22px;line-height:1.45;margin:0 0 10px}
p{margin:0 0 10px}p:last-child{margin-bottom:0}
ul{margin:0 0 10px;padding-left:20px}ul:last-child{margin-bottom:0}li{margin:4px 0}
.empty{color:var(--muted);font-style:italic}
.timeline{overflow-x:auto;padding:4px 2px 10px;margin:0 -2px}
.track{list-style:none;margin:0;padding:0;display:grid;grid-auto-flow:column;grid-auto-columns:minmax(112px,1fr);gap:0}
.stop{position:relative;padding:0 12px 0 0;min-width:0}
.stop .when{font-weight:700;font-size:14px;line-height:1.25;min-height:2.5em}
.stop .rail{position:relative;height:22px;margin:6px 0 10px}
.stop .rail::before{content:'';position:absolute;left:0;right:-12px;top:10px;height:2px;background:var(--line)}
.stop:last-child .rail::before{right:50%}
.stop .rail::after{content:'';position:absolute;left:0;top:4px;width:14px;height:14px;border-radius:50%;background:var(--paper);border:2px solid var(--accent)}
.stop.near .rail::after{background:var(--accent-soft)}
.stop.now .rail::after{background:var(--accent);box-shadow:0 0 0 6px var(--accent-soft)}
.stop .what{font-size:13.5px;line-height:1.5;color:var(--ink)}
.stop .what .empty{font-size:13px}
dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;margin:12px 0 0}
dt{color:var(--muted)}dd{margin:0}
.folders{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.folder .n{font-size:28px;font-weight:600;line-height:1.1;margin:6px 0 2px}
.folder .meaning{color:var(--muted);font-size:14px}
.folder ul{font-size:13px;color:var(--muted);margin-top:8px;padding-left:16px}
.pill{display:inline-block;padding:3px 10px;border-radius:999px;background:var(--accent-soft);color:var(--accent-ink);font-size:13px;margin:2px 6px 2px 0}
.saves li{display:flex;gap:12px}.saves time{color:var(--muted);font:13px/1.6 'JetBrains Mono',ui-monospace,monospace;white-space:nowrap}
.where{white-space:nowrap}
footer{margin-top:60px;color:var(--muted);font-size:14px;border-top:1px solid var(--line);padding-top:16px}
code{font:13px/1.4 'JetBrains Mono',ui-monospace,monospace;background:var(--soft);padding:1px 5px;border-radius:5px}
@media (max-width:860px){
.app{grid-template-columns:minmax(0,1fr)}
.side{display:none}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:12px;position:sticky;top:0;z-index:5;background:var(--paper);border-bottom:1px solid var(--line);padding:10px 16px}
.topbar .brand{font-weight:700;font-size:16px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.menu{position:relative}
.menu summary{list-style:none;cursor:pointer;padding:7px 12px;border:1px solid var(--line);border-radius:10px;font-size:14px;font-weight:600}
.menu summary::-webkit-details-marker{display:none}
.menu .nav{position:absolute;right:0;top:calc(100% + 8px);background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:6px;min-width:220px;box-shadow:0 12px 30px var(--soft)}
.main{padding:22px 16px 64px}
.track{grid-auto-flow:row;grid-auto-columns:auto}
.stop{padding:0 0 18px 30px}
.stop .when{min-height:0}
.stop .rail{position:absolute;left:0;top:0;bottom:0;height:auto;width:16px;margin:0}
.stop .rail::before{left:7px;right:auto;top:0;bottom:0;width:2px;height:auto}
.stop:last-child .rail::before{right:auto;bottom:calc(100% - 10px)}
.stop .rail::after{top:3px}
}
@media (max-width:520px){h1{font-size:28px}.why p{font-size:19px}.card{padding:16px}}
"""


MENU_ICONS = {
    "carbon": {"timeline": "time", "week": "calendar", "floor": "security", "why": "favorite",
               "who": "user", "now": "enterprise", "parked": "flag", "shared": "dashboard",
               "folders": "folder", "saves": "save"},
    "lucide": {"timeline": "clock", "week": "calendar", "floor": "shield", "why": "heart",
               "who": "user", "now": "briefcase", "parked": "flag", "shared": "users",
               "folders": "folder", "saves": "save"},
}


def menu_icon(key: str, look: dict) -> str:
    if library is None:
        return ""
    try:
        icon_set = library.set_of(look)
        name = MENU_ICONS.get(icon_set, MENU_ICONS["carbon"]).get(key)
        return library.icon(name, size=18, icon_set=icon_set) if name else ""
    except (KeyError, OSError, ValueError):
        return ""


def menu(items: list[tuple[str, str]], look: dict) -> str:
    return '<nav class="nav">' + "".join(
        f'<a href="#{k}">{menu_icon(k, look)}<span>{esc(label)}</span></a>' for k, label in items) + "</nav>"


def render(plan: dict, folders: list[dict], saves: list[tuple[str, str]], today: str,
           look: dict | None = None) -> str:
    look = look or dict(PLAIN)
    s = plan["sections"]
    f = plan["fields"]
    # The letterhead in brand.md names the page when it is written; the plan's title otherwise.
    name = look.get("letterhead") or plan["name"]
    parts: list[str] = []

    # Header
    meta = []
    if look.get("under"):
        meta.append(esc(look["under"]))
    if f.get("framework_version"):
        meta.append(f"Written on version {esc(f['framework_version'])}")
    if f.get("last_raised"):
        meta.append(f"last reviewed {esc(f['last_raised'])}")
    if f.get("next_raise"):
        meta.append(f"next review {esc(f['next_raise'])}")
    parts.append('<header><div class="eyebrow">Self as Code</div>'
                 f"<h1>{esc(name)}</h1>"
                 + (f'<p class="meta">{" · ".join(meta)}</p>' if meta else "")
                 + "</header>")

    if not plan["written"]:
        parts.append('<section class="card"><h2>Nothing written yet</h2>'
                     "<p>Type <code>/sac</code> and answer the questions. It writes your plan, and this page draws it.</p></section>")

    # The ladder
    rungs = plan["rungs"]
    horizon = rungs[0][0] if rungs else 20
    ladder: list[tuple[str, str | None, bool]] = []
    by_years = {y: t for y, t in rungs}
    for y in sorted({horizon, *by_years.keys(), 10, 5}, reverse=True):
        if y > horizon:
            continue
        text = by_years.get(y)
        if text is None and y == horizon and plan["picture"]:
            text = plan["picture"][0]
        ladder.append((f"In {y} year{'s' if y != 1 else ''}", text, False))
    ladder.append(("In six months", first_line(s.get("rewrite")), False))
    review_text = first_line(s.get("review"))
    nr = f.get("next_raise")
    if nr and review_text and nr[:4] not in review_text:
        review = f"{nr}. {review_text}"
    else:
        review = review_text or nr
    ladder.append(("My next review", review, False))
    ladder.append(("This week", plan["this_week"], False))
    ladder.append(("Tomorrow", plan["tomorrow"], False))
    steps = plan["steps"]
    ladder.append(("Every day", (f"{len(steps)} step{'s' if len(steps) != 1 else ''}, below" if steps else None), True))
    near = {"This week", "Tomorrow"}
    parts.append('<section id="timeline"><div class="eyebrow">The bridge back</div><h2>From the future you to today</h2>'
                 '<div class="timeline"><ol class="track">'
                 + "".join(f'<li class="stop{" now" if now else (" near" if label in near else "")}">'
                           f'<div class="when">{esc(label)}</div><div class="rail"></div>'
                           + (f'<div class="what">{inline(text)}</div>' if text else f'<div class="what">{empty()}</div>')
                           + "</li>" for label, text, now in ladder)
                 + "</ol></div></section>")

    # This week, and the floor, side by side under the timeline
    daily = prose(steps) if steps else ""
    extra = []
    if plan["this_week"]:
        extra.append(f"<dt>This week</dt><dd>{inline(plan['this_week'])}</dd>")
    if plan["tomorrow"]:
        extra.append(f"<dt>Tomorrow</dt><dd>{inline(plan['tomorrow'])}</dd>")
    parts.append('<div class="pair">'
                 '<section id="week"><div class="eyebrow">This week</div><h2>What I do every day, no matter what</h2><div class="card">'
                 + (daily or empty()) + (f"<dl>{''.join(extra)}</dl>" if extra else "") + "</div></section>"
                 '<section id="floor"><div class="eyebrow">My floor</div><h2>The line I won\'t drop below</h2>'
                 + floor_card(plan["values"], s.get("floor")) + "</section></div>")

    # Why
    parts.append('<section class="why" id="why"><div class="eyebrow">Why</div><h2>Why I exist</h2><div class="card">'
                 + (prose(s["readme"]) if s.get("readme") else empty()) + "</div></section>")

    # Who
    parts.append('<section id="who"><div class="eyebrow">Who</div><h2>Who I\'m becoming</h2><div class="card">'
                 + (prose(plan["picture"]) if plan["picture"] else empty()) + "</div></section>")

    # How: the leap and the cut (the floor sits beside this week, above)
    parts.append('<section><div class="eyebrow">How</div><h2>The leap and the cut</h2><div class="grid">'
                 + card("My one big leap", "In the next six months", s.get("rewrite"))
                 + card("My cut", "What I hand over, stop or say no to", s.get("cut"))
                 + "</div></section>")

    # Now: where I am, each thing I hold (a business, a job, a family, a project)
    now_html = prose(plan["about"]) if plan["about"] else ""
    biz_html = ""
    for b in plan["businesses"]:
        setup = b["setup"]
        rows = "".join(f"<dt>{esc(k)}</dt><dd>{inline(setup[k.lower()])}</dd>" for k in SETUP_LINES if k.lower() in setup)
        kind = setup.get("kind", "")
        biz_html += (f'<div class="card">' + (f'<div class="eyebrow">{esc(kind)}</div>' if kind else "") + f'<h2>{esc(b["name"])}</h2>'
                     + (prose(b["words"]) if b["words"] else "")
                     + (f"<dl>{rows}</dl>" if rows else "")
                     + ("" if b["words"] or rows else empty())
                     + "</div>")
    parts.append('<section id="now"><div class="eyebrow">Now</div><h2>Where I am now</h2>'
                 + (f'<div class="card">{now_html}</div>' if now_html else "")
                 + (f'<div class="grid" style="margin-top:16px">{biz_html}</div>' if biz_html else "")
                 + ("" if now_html or biz_html else f'<div class="card">{empty()}</div>')
                 + "</section>")

    # Parked
    if plan["parked"]:
        parts.append('<section id="parked"><div class="eyebrow">Parked</div><h2>Not sure yet, with a date to come back</h2><div class="card"><dl>'
                     + "".join(f'<dt class="where">{esc(w)}</dt><dd>{inline(t)}</dd>' for w, t in plan["parked"])
                     + "</dl></div></section>")

    # Shared
    sp = plan["split"]
    if sp is not None:
        pills = [f'<span class="pill">{sp["mine"]} stay with me</span>']
        for dest, n in sorted(sp["to"].items()):
            pills.append(f'<span class="pill">{n} to {esc(dest)}</span>')
        if sp["parked"]:
            pills.append(f'<span class="pill">{sp["parked"]} parked for later</span>')
        parts.append('<section id="shared"><div class="eyebrow">Shared</div><h2>What I share with each business</h2><div class="card">'
                     + "".join(pills) + "<p class=\"meta\" style=\"margin-top:10px\">Only what I said yes to, line by line. Only the decision, never the reason.</p></div></section>")

    # Folders
    tiles = ""
    for fo in folders:
        n = fo["count"]
        tiles += (f'<div class="card folder"><div class="eyebrow">{esc(fo["name"])}</div>'
                  + (f'<div class="n">{n}</div>' if n is not None else '<div class="n">–</div>')
                  + f'<div class="meaning">{esc(fo["meaning"]) if n is not None else "Not made yet"}</div>'
                  + ("<ul>" + "".join(f"<li>{esc(r)}</li>" for r in fo["recent"]) + "</ul>" if fo["recent"] else "")
                  + "</div>")
    parts.append(f'<section id="folders"><div class="eyebrow">My folders</div><h2>What is in my private space</h2><div class="folders">{tiles}</div></section>')

    # Saves
    if saves:
        parts.append('<section id="saves"><div class="eyebrow">Saved</div><h2>My last saves</h2><div class="card saves"><ul>'
                     + "".join(f"<li><time>{esc(d)}</time><span>{esc(m)}</span></li>" for d, m in saves)
                     + "</ul></div></section>")

    parts.append(f"<footer>Drawn on this laptop by <code>/sac dashboard</code> on {esc(today)}. Nothing left it. Run it again any time.</footer>")

    items = [("timeline", "Timeline"), ("week", "This week"), ("floor", "My floor"), ("why", "Why"),
             ("who", "Who I'm becoming"), ("now", "Where I am now")]
    if plan["parked"]:
        items.append(("parked", "Parked"))
    if plan["split"] is not None:
        items.append(("shared", "Shared"))
    items.append(("folders", "My folders"))
    if saves:
        items.append(("saves", "Saves"))
    nav = menu(items, look)
    shell = ('<div class="app"><aside class="side"><div class="brand">' + esc(name) + "</div>"
             '<div class="brand-sub">Self as Code</div>' + nav + "</aside>"
             '<div><div class="topbar"><div class="brand">' + esc(name) + "</div>"
             '<details class="menu"><summary>Menu</summary>' + nav + "</details></div>"
             '<main class="main">' + "".join(parts) + "</main></div></div>")
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{esc(name)}: Self as Code</title>"
            f"<style>{root_css(look)}{font_css()}{CSS}</style></head><body>"
            + shell + "</body></html>\n")


def floor_card(values: list[tuple[str, str]], text: str | None) -> str:
    """The floor: the values first, each with its worst-day line, then the conditions."""
    rows = "".join(f"<dt>{esc(n)}</dt><dd>{inline(w) if w else empty('What this looks like on my worst day: not written yet.')}</dd>"
                   for n, w in values)
    body = (f'<p><strong>What I stand for</strong></p><dl>{rows}</dl>' if rows else "") + (prose(text) if text else "")
    return f'<div class="card">{body or empty()}</div>'


def card(title: str, meaning: str, text: str | None) -> str:
    return (f'<div class="card"><div class="eyebrow">{esc(meaning)}</div><h2>{esc(title)}</h2>'
            + (prose(text) if text else empty()) + "</div>")


# ── Main ─────────────────────────────────────────────────────────────────────

def build(root: Path, out: Path, today: str | None = None) -> Path:
    spine = find_spine(root)
    plan = read_plan(spine, root)
    page = render(plan, folder_counts(root), recent_saves(root), today or date.today().isoformat(),
                  look=read_brand(root))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Draw your Self as Code plan as one page, on this laptop.")
    ap.add_argument("root", nargs="?", default=".", help="your private repo (default: here)")
    ap.add_argument("--out", type=Path, default=None, help=f"where to write the page (default: {OUT})")
    ap.add_argument("--no-open", action="store_true", help="write the page, do not open the browser")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    out = (args.out or (root / OUT)).resolve()
    spine = find_spine(root)
    build(root, out)
    print(f"drawn: {out}")
    if spine is None:
        print("no self-as-code.md here yet, so the page says to run /sac")
    if not args.no_open:
        try:
            webbrowser.open(out.as_uri())
        except Exception as e:  # a headless machine, or no browser registered
            print(f"could not open a browser ({e}); open the file yourself")
    return 0


if __name__ == "__main__":
    sys.exit(main())
