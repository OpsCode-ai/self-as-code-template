#!/usr/bin/env python3
"""Open a session in an OaC repo with a briefing of what changed (ADR-118).

WHY THIS EXISTS
    Entering an operations repo should tell you where the operation is up to.
    Today it tells you nothing: you open a session, and the state of the
    business is whatever you can remember or go and grep for.

    This puts the answer on screen before you type. What moved since
    yesterday, what you left for yourself in the task-bridge log, who else
    worked and where, what the shared brain learned, which intents are open,
    what is still in progress, and, when the log has no focus, the honest next
    move read from the files (added 24 September 2026 at Adam's ask).

WHY IT IS A HOOK AND NOT A PLUGIN
    The obvious home is the OAC AI-DLC plugin, and the plugin cannot host it.
    A plugin's contribution seam is stages, overlays, agents, scopes, sensors,
    knowledge and tools; there is no `hooks` key, and the projection GENERATES
    hooks.json, overwriting anything authored. A sensor is the wrong shape too:
    sensors are advisory PostToolUse verification manifests.

    So it is a SessionStart hook, and it is the sibling of
    oac-session-health.py: same event, same plain-stdout contract, same
    fail-open discipline, installed by the same installer. One install path,
    two surfaces. The statusline says where you are; this says what changed.

IT BRIEFS THE MODE, NOT JUST THE REPO
    `.oac/manifest.yml` says which plane this is (ADR-118), and the briefing
    matches it. A business plane opens on OAC: what moved, what the shared
    brain learned, open intents, the manual count. A self plane opens on SAC:
    when the next raise is due, whether the beats are whole, whether the
    coasting signal is dark. SessionStart fires before any scope is resolved,
    so the plane is the only discriminator available here, and it is the right
    one anyway: a mode follows from whose operation you are in.

WHAT IT WILL NOT READ
    Nothing outside CLAUDE_PROJECT_DIR. In a BUSINESS plane, nothing marked
    `audience: owner`: ADR-111 makes owner material a placement rule, it never
    enters a shared repo, so anything found there carrying that label is
    already an incident and this skips it silently. A document with no
    `audience` at all is treated as the most restricted value, per the OaC
    spec's fail-closed rule for tools that gate on it.

    In a SELF plane that inverts, and the inversion is the spec applied
    correctly rather than relaxed. Section 3.5 defines `owner` as 'the owner
    only' and makes the placement rule about where a document may LIVE. A self
    plane is the repo the owner alone controls, everything in it is `owner` by
    default, and this runs on the owner's machine and prints to the owner.
    Refusing there is what left the briefing blind in the one repo the method
    is about (ADR-120).

IT FAILS OPEN
    Every unexpected condition exits 0 silently, and every subprocess is
    bounded. A session that starts on a stack trace is worse than a session
    that starts with no briefing.

WIRING
    SessionStart, installed per-user by install-oac-branch-guard.py so it
    works in every OaC repo. Silent in a repo with no .oac/manifest.yml.

Standard: specs/oac-file-format.md. Decision: ADR-118.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

DEADLINE = 2.5          # seconds, whole run
CMD_TIMEOUT = 3         # seconds, any one subprocess
MAX_LINES = 36          # a briefing nobody reads is worse than no briefing
START = time.monotonic()

OWNER_RE = re.compile(r"^audience:\s*[\"']?(owner|adam)[\"']?\s*$", re.M)
AUDIENCE_RE = re.compile(r"^audience:\s*", re.M)
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)

# The self-core body grammar, published in specs/oac-vocabulary.yml under the
# `self-core` profile. Read from the same definition the OaC client's
# parseSelfAsCode.ts implements, so the two readers cannot drift apart.
BEATS = ("baseline", "readme", "main", "rewrite", "floor", "cut",
         "commits", "refactor")
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
COASTING_RE = re.compile(r"\[coasting\]\s*$", re.I | re.M)


def out_of_time() -> bool:
    return (time.monotonic() - START) > DEADLINE


def git(root: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(("git", "-C", str(root)) + args,
                           capture_output=True, text=True, timeout=CMD_TIMEOUT)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def readable(path: Path, self_plane: bool = False) -> bool:
    """False for anything owner-audience, or with no audience at all.

    Fail closed on a missing value: the spec says a tool gating on `audience`
    treats an absent one as the most restricted, never the least. A file with
    no frontmatter is not a classified document, so it is judged on location
    alone by the caller, not here.

    IN A SELF PLANE THIS INVERTS, and the inversion is the spec applied
    correctly rather than relaxed. Section 3.5 defines `owner` as 'the owner
    only' and makes it a PLACEMENT rule: an owner document must not live in a
    shared repo. It never said no tool may read one. A self plane is the repo
    the owner alone controls, every document in it is `owner` by default
    (`audience_default.self`), and this runs on the owner's machine and prints
    to the owner. Refusing here is what made the briefing blind in the one repo
    the method is about.

    The refusal stays absolute in a business plane, where an owner document is
    already an incident (ADR-111, ADR-120).
    """
    if self_plane:
        return True
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:4000]
    except Exception:
        return False
    m = FRONTMATTER_RE.search(head)
    if not m:
        return False
    block = m.group(1)
    if OWNER_RE.search(block):
        return False
    return bool(AUDIENCE_RE.search(block))


def manifest_plane(manifest: Path) -> str | None:
    """`self` or `business`, from .oac/manifest.yml (ADR-118).

    The file is already the gate for this whole hook; this reads the one key
    that says which kind of operation the repo is, so the briefing can match.
    """
    try:
        text = manifest.read_text(encoding="utf-8", errors="replace")[:4000]
    except Exception:
        return None
    value = field(text, "plane")
    return value if value in {"self", "business"} else None


def field(text: str, name: str) -> str | None:
    """A plain `key: value` line, as in YAML frontmatter."""
    m = re.search(rf"^{re.escape(name)}:\s*(.+?)\s*$", text, re.M)
    if not m:
        return None
    return m.group(1).strip().strip("\"'") or None


def state_field(text: str, name: str) -> str | None:
    """A `- **Key**: value` line, as in aidlc-state.md.

    A separate reader on purpose. Passing the decorated form to field() means
    re.escape() escapes the asterisks and backslashes, and the pattern then
    matches a literal `- \\*\\*Scope\\*\\*` that no file contains. It fails
    silently to '?', which is exactly the kind of wrong that survives review.
    """
    m = re.search(rf"^-\s*\*\*{re.escape(name)}\*\*:\s*(.+?)\s*$", text, re.M)
    if not m:
        return None
    return m.group(1).strip().strip("\"'") or None


def recent_commits(root: Path) -> list[str]:
    log = git(root, "log", "--since=36.hours", "--no-merges",
              "--pretty=%h  %s", "-n", "8")
    return [ln for ln in (log or "").splitlines() if ln.strip()]


def dirty_count(root: Path) -> int:
    st = git(root, "status", "--porcelain", "-uno")
    return len([ln for ln in (st or "").splitlines() if ln.strip()])


def brain_moves(root: Path) -> list[str]:
    """Directories of the shared brain that changed this week."""
    log = git(root, "log", "--since=7.days", "--name-only", "--pretty=format:",
              "--", "context-core", "specs", "decisions")
    seen: list[str] = []
    for ln in (log or "").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        d = str(Path(ln).parent)
        if d not in seen:
            seen.append(d)
        if len(seen) >= 5:
            break
    return seen


def open_intents(root: Path) -> list[str]:
    """Read aidlc-state.md with a regex. Never shell out to bun.

    A session-start hook that invokes the engine turns every new session into
    a cold bun start, and the engine is not guaranteed installed.
    """
    rows: list[str] = []
    try:
        states = sorted(root.glob("aidlc/spaces/*/intents/*/aidlc-state.md"))
    except Exception:
        return rows
    for st in states[:8]:
        if out_of_time():
            break
        try:
            text = st.read_text(encoding="utf-8", errors="replace")[:8000]
        except Exception:
            continue
        status = (state_field(text, "Status") or "").lower()
        if status in {"complete", "completed", "closed"}:
            continue
        scope = state_field(text, "Scope") or "?"
        stage = state_field(text, "Current Stage") or "?"
        rows.append(f"{st.parent.name} — {scope} · {stage}")
        if len(rows) >= 5:
            break
    return rows


def open_plans(root: Path) -> list[str]:
    rows: list[str] = []
    plans = root / "notable-plans"
    if not plans.is_dir():
        return rows
    try:
        files = sorted(plans.glob("*.md"), reverse=True)
    except Exception:
        return rows
    for f in files[:25]:
        if out_of_time() or len(rows) >= 3:
            break
        if not readable(f):
            continue
        try:
            head = f.read_text(encoding="utf-8", errors="replace")[:2000]
        except Exception:
            continue
        if (field(head, "status") or "").lower() != "in-progress":
            continue
        rows.append(field(head, "title") or f.stem)
    return rows


def manual_processes(root: Path) -> int | None:
    """Count manual rows in a systems register, if this repo has one.

    The whole reason `Runs` is a closed column (ADR-118): the count is the
    measurement Checklist/Automate/Hire never had.
    """
    reg = root / "systems" / "register.md"
    if not reg.is_file() or not readable(reg):
        return None
    try:
        text = reg.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    return len(re.findall(r"^\|.*\|\s*manual\s*\|", text, re.M)) or None


def normalise_heading(h: str) -> str:
    """A beat key from an H2, per the `self-core` body grammar.

    Case-insensitive, an optional leading 'the', and the two spelling variants
    the spec names: 'read me' for readme, 'commit' for commits.

    IT ALSO DROPS A TRAILING DESCRIPTOR, which the client's parser does not,
    and that difference is deliberate. The method tells you to write
    `## the floor - minimum standard` and `## refactor (next: YYYY-MM-DD)`, so
    a descriptor after a dash, colon or bracket is the documented house style.
    `products/oac-client/src/lib/parseSelfAsCode.ts` strips only a leading
    'the' and trailing punctuation, so measured against a real spine written to
    the method's own instructions it resolves ONE beat of eight. That is a bug
    in the client, not a rule this should copy. Raised 13 September 2026;
    when the client is fixed, the two readers agree again.
    """
    h = h.strip().lower()
    h = re.split(r"\s*[(\[]|\s+[-‐-―]\s+|\s*:\s+", h, maxsplit=1)[0]
    h = re.sub(r"^the\s+", "", h)
    h = re.sub(r"[^a-z ]", "", h).strip()
    if h == "read me":
        return "readme"
    if h == "commit":
        return "commits"
    if h == "review":  # the 90-day review; 'review' is the 1.10 heading (spec 7.1)
        return "refactor"
    return h.replace(" ", "")


def self_core(root: Path) -> list[str]:
    """The spine: when the next raise is due, and whether the beats are whole.

    `next_raise` is the one date the method runs on, and the coasting marker is
    the one machine-readable health signal in the profile. Both were sitting in
    this file unread (ADR-120).
    """
    spine = root / "self-as-code.md"
    if not spine.is_file():
        return ["  Self as Code: no self-as-code.md at the top of this repo yet"]
    try:
        text = spine.read_text(encoding="utf-8", errors="replace")[:20000]
    except Exception:
        return []

    rows: list[str] = []
    m = FRONTMATTER_RE.search(text)
    front, body = (m.group(1), text[m.end():]) if m else ("", text)

    nxt = field(front, "next_raise")
    if nxt:
        try:
            days = (datetime.date.fromisoformat(nxt) - datetime.date.today()).days
            if days < 0:
                rows.append(f"  Next review: {nxt}, OVERDUE by {abs(days)} day(s)")
            elif days == 0:
                rows.append(f"  Next review: {nxt}, today")
            else:
                rows.append(f"  Next review: {nxt}, in {days} day(s)")
        except ValueError:
            rows.append(f"  Next review: {nxt}")

    found = {normalise_heading(h) for h in H2_RE.findall(body)}
    missing = [b for b in BEATS if b not in found]
    if missing:
        said = ["review" if b == "refactor" else b for b in missing]
        rows.append(f"  Steps: {len(BEATS) - len(missing)}/{len(BEATS)}"
                    f", missing {', '.join(said)}")

    if "invariants" in found:
        coasting = len(COASTING_RE.findall(body))
        if coasting:
            rows.append(f"  Your floor: {coasting} marked coasting")
    return rows


def open_project_names(root: Path) -> list[str]:
    """Titles of the projects still open, for the manifest. A project file
    with status done, closed, complete or archived is finished."""
    d = root / "projects"
    if not d.is_dir():
        return []
    names: list[str] = []
    try:
        for f in sorted(d.glob("*.md")):
            if f.stem.lower() in {"readme", "index", "overview"}:
                continue
            head = f.read_text(encoding="utf-8", errors="replace")[:3000]
            status = (field(head, "status") or "").lower()
            if status in {"done", "closed", "complete", "completed", "archived", "dropped"}:
                continue
            names.append(field(head, "title") or f.stem)
    except Exception:
        return []
    return names


def open_projects(root: Path) -> int:
    """Projects have an end date by definition (ADR-118), so an open one is work."""
    d = root / "projects"
    if not d.is_dir():
        return 0
    try:
        return len([f for f in d.glob("*.md")
                    if f.stem.lower() not in {"readme", "index", "overview"}])
    except Exception:
        return 0


def inbox_open(root: Path) -> int:
    """Unticked items in the single intake, counted with the `live` grammar."""
    f = root / "inbox.md"
    if not f.is_file():
        return 0
    try:
        return len(re.findall(r"^\s*[-*]\s*\[ \]",
                              f.read_text(encoding="utf-8", errors="replace"), re.M))
    except Exception:
        return 0


# ── The person, and what they left for themselves ───────────────────────────

def handle(root: Path) -> str | None:
    """First name, lowercase, from git user.name: the task-bridge convention."""
    name = git(root, "config", "user.name") or ""
    first = re.sub(r"[^a-z0-9]+", "", name.split()[0].lower()) if name.split() else ""
    return first or None


DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def log_home(root: Path, who: str | None, self_plane: bool) -> tuple[Path, Path] | None:
    """Where the daily log lives: (today's file, the folder of older days).

    A private space keeps its days at evidence/days/ (ADR-136 Rule 8): one
    person, so no handle folder, and the days are evidence like everything
    else they keep. A private space that still has team/<who>/ from an
    earlier pack is read there until the person moves it; nobody renames by
    hand. A business keeps team/<who>/current.md and team/<who>/logs/."""
    if self_plane:
        days = root / "evidence" / "days"
        legacy = root / "team" / who if who else None
        if (days / "current.md").is_file():
            return days / "current.md", days
        if legacy and ((legacy / "current.md").is_file() or (legacy / "logs").is_dir()):
            return legacy / "current.md", legacy / "logs"
        return days / "current.md", days
    if not who:
        return None
    return root / "team" / who / "current.md", root / "team" / who / "logs"


def older_days(folder: Path) -> list[Path]:
    """The archived days in a folder, by date, oldest first."""
    if not folder.is_dir():
        return []
    return sorted(f for f in folder.glob("*.md") if DAY_RE.match(f.stem))


def roll_forward(root: Path, who: str | None, self_plane: bool, limit: int | None = 160) -> list[str]:
    """What /done and /task-bridge left in team/<handle>/current.md.

    The Roll-forward is the single current priority; the last entry is what
    happened. Both are printed verbatim, because the whole point of the log is
    that the answer is already written down. Falls back to the newest archived
    day when today has no log yet.
    """
    home = log_home(root, who, self_plane)
    if home is None:
        return []
    log, folder = home
    if not log.is_file():
        archive = older_days(folder)
        if not archive:
            return []
        log = archive[-1]
    if not readable(log, self_plane):
        return []
    try:
        text = log.read_text(encoding="utf-8", errors="replace")[:60000]
    except Exception:
        return []
    out: list[str] = []
    nxt = re.search(r"^\*\*Next:\*\*\s*(.+?)(?=\n\s*\n|\n\*\*|\Z)", text, re.M | re.S)
    when = re.search(r"^\*\*When:\*\*\s*(.+?)(?=\n\s*\n|\n\*\*|\Z)", text, re.M | re.S)
    date = field(text, "date") or log.stem
    if nxt:
        line = " ".join(nxt.group(1).split())
        if limit and len(line) > limit:
            line = line[:limit - 3] + "..."
        out.append(f"  You left off ({date}): {line}")
        if when:
            w = " ".join(when.group(1).split())
            out.append(f"    When: {w[:limit - 23] + '...' if limit and len(w) > limit - 20 else w}")
    entries = list(re.finditer(r"^###\s+(\d{1,2}:\d{2})\s*\n(.*?)(?=^###\s|\Z)", text, re.M | re.S))
    if entries:
        stamp, body = entries[-1].group(1), " ".join(entries[-1].group(2).split())
        if limit and len(body) > limit - 20:
            body = body[:limit - 23] + "..."
        if body:
            out.append(f"    Last entry {stamp}: {body}")
    return out


def who_worked(root: Path) -> list[str]:
    """Who committed in the last seven days, and where. Shown only when more
    than one person did: a team of one does not need telling who it is."""
    log = git(root, "log", "--since=7.days", "--no-merges", "--pretty=%an%x00", "--name-only")
    if not log:
        return []
    counts: dict[str, int] = {}
    areas: dict[str, dict[str, int]] = {}
    author = None
    for raw in log.splitlines():
        if raw.endswith("\x00"):
            # Key by first name: one person commits under two spellings more
            # often than two people share a first name in one small business.
            full = raw[:-1].strip() or "?"
            author = full.split()[0] if full.split() else full
            counts[author] = counts.get(author, 0) + 1
            areas.setdefault(author, {})
        elif raw.strip() and author:
            top = raw.strip().split("/")[0]
            areas[author][top] = areas[author].get(top, 0) + 1
    if len(counts) < 2:
        return []
    parts = []
    for name, n in sorted(counts.items(), key=lambda kv: -kv[1])[:5]:
        where = ", ".join(k for k, _ in sorted(areas[name].items(), key=lambda kv: -kv[1])[:2])
        parts.append(f"{name} {n} ({where})" if where else f"{name} {n}")
    return ["  Who worked (7 days): " + " · ".join(parts)]


def suggestions(root: Path, self_plane: bool, have_focus: bool, dirty: int) -> list[str]:
    """The honest next move when the log has none, read from the files.

    One idea when a focus is already written down, up to three when it is
    not. Every line names a command, so it is a move and not a mood.
    """
    ideas: list[str] = []
    if dirty:
        ideas.append("uncommitted work from last time is still here: /done first")
    if self_plane:
        spine = root / "self-as-code.md"
        try:
            text = spine.read_text(encoding="utf-8", errors="replace")[:6000] if spine.is_file() else ""
        except Exception:
            text = ""
        status = field(text, "status") if text else None
        nxt = field(text, "next_raise") if text else None
        if not text or status == "seeded":
            ideas.append("your plan is still the starter copy: /sac writes it with you")
        elif nxt:
            try:
                due = datetime.date.fromisoformat(nxt[:10])
                if due <= datetime.date.today():
                    ideas.append(f"your 90-day review was due {nxt[:10]}: /sac review")
            except ValueError:
                pass
        split = "## the split" in text if text else False
        if text and status != "seeded" and not split:
            ideas.append("nothing shared with a business yet: /sac asks what to share")
    else:
        reg = root / "systems" / "register.md"
        try:
            rtext = reg.read_text(encoding="utf-8", errors="replace")[:4000] if reg.is_file() else ""
        except Exception:
            rtext = ""
        if not rtext or field(rtext, "status") == "seeded":
            ideas.append("the register is still the seed: /ops-audit writes what the business runs on")
        else:
            manual = manual_processes(root)
            if manual:
                ideas.append(f"{manual} process(es) still manual: pick one and write it down")
        cc = root / "context-core"
        if cc.is_dir():
            folders = [d for d in cc.iterdir() if d.is_dir()]
            empty = [d for d in folders if all(f.name == "README.md" for f in d.iterdir() if f.is_file())]
            if folders and len(empty) >= max(1, len(folders) // 2):
                ideas.append(f"{len(empty)} of {len(folders)} Context Core folders are empty: /install shows the fill-map")
        dec = root / "decisions"
        if dec.is_dir() and not any(dec.glob("[0-9]*.md")):
            ideas.append("no decision recorded yet: /create-adr the next choice you make")
    if not ideas:
        return []
    keep = ideas[:1] if have_focus else ideas[:3]
    label = "  Also worth doing: " if have_focus else "  Suggested focus: "
    out = [label + keep[0]]
    for extra in keep[1:]:
        out.append("                    " + extra)
    return out


# ── The announcement: what Claude Code shows first, every session ─────────────
#
# `companyAnnouncements` is rendered at session start as a message from the
# organisation. It is static config, so this script rewrites it at the end of
# every session (and again at the start, in case the last one crashed): a
# first-time note until the plane has been worked in, then a manifest of where
# things stand. The engine ships its own 33-stage table in that slot; the
# installer and the pack builder replace it with these, chosen by plane (found
# 24 September 2026, the night before the first Build Day, opening a self plane
# and reading about NFR design).
#
# It lives in .claude/settings.local.json, which git ignores. It used to live
# in settings.json, so every session left a tracked file changed: a commit on
# main for every session and a false alarm in /start (moved 7 October 2026).
# See write_announcement for why a pack still seeds the shared file.
ANNOUNCEMENT_KEY = "companyAnnouncements"

# Plain text, on purpose. Claude Code prints this box verbatim in a monospace
# font: no markdown, so a `#`, a `**` or a table pipe shows up as itself.
# Alignment is done with box-drawing characters, and lines stay under 100.

# The wordmark: OPSCODE in the ANSI Shadow face, 58 columns, six lines.
WORDMARK = "\n".join((
    " ██████╗ ██████╗ ███████╗ ██████╗ ██████╗ ██████╗ ███████╗",
    "██╔═══██╗██╔══██╗██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝",
    "██║   ██║██████╔╝███████╗██║     ██║   ██║██║  ██║█████╗  ",
    "██║   ██║██╔═══╝ ╚════██║██║     ██║   ██║██║  ██║██╔══╝  ",
    "╚██████╔╝██║     ███████║╚██████╗╚██████╔╝██████╔╝███████╗",
    " ╚═════╝ ╚═╝     ╚══════╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝",
))

BOX_WIDTH = 80          # the wordmark is 58; 80 fits a tablet, a laptop and a split pane


def _dw(s: str) -> int:
    """Display width: East Asian wide and fullwidth characters take two cells."""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - _dw(s))


def box(rows: list[tuple[str, str]], width: int = BOX_WIDTH) -> list[str]:
    """A ruled two-column table in box-drawing characters. Values wrap at
    word boundaries onto continuation rows with an empty label cell."""
    import textwrap
    if not rows:
        return []
    lw = max(len(k) for k, _ in rows)
    vw = max(24, width - lw - 7)
    out = [f"┌{'─' * (lw + 2)}┬{'─' * (vw + 2)}┐"]
    for k, v in rows:
        lines = textwrap.wrap(v, width=vw, break_long_words=False, break_on_hyphens=False) or [""]
        out.append(f"│ {_pad(k, lw)} │ {_pad(lines[0], vw)} │")
        out.extend(f"│ {' ' * lw} │ {_pad(ln, vw)} │" for ln in lines[1:])
    out.append(f"└{'─' * (lw + 2)}┴{'─' * (vw + 2)}┘")
    return out


FIRST_TIME_BODY = {
    "self": """◆ Self as Code · SAC

This is your private space. Only you can see it.

One command: /sac
  Asks you seven questions about who you are becoming, writes your plan to
  self-as-code.md, and sends what you choose to share to each business you
  run. About an hour, one sitting.

Every session: /start at the beginning, /done at the end.

SAC on the bottom line means you are in the right place.""",
    "business": """◆ Operations as Code · OAC

This is your business's shared space. Everyone who works in the business can see it.

One command: /oac
  Writes what the business runs on, then what it is aiming at, then one process
  at a time. Typed again later, it does the next thing.

Every session: /start at the beginning, /done at the end.

OAC on the bottom line means you are in the right place.
Self as Code runs first, in your own repo, with /sac.""",
}
FIRST_TIME = {plane: WORDMARK + "\n" + body for plane, body in FIRST_TIME_BODY.items()}


def _section_lines(text: str, heading_starts: str) -> list[str]:
    """Non-empty lines under the first H2 whose text starts with the given
    words (the spine's headings carry descriptors: '## the rewrite — the one
    leap'), up to the next H2. Markdown marks stripped."""
    m = re.search(rf"^##\s+{re.escape(heading_starts)}\b[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    if not m:
        return []
    out = []
    for ln in m.group(1).splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            out.append(_cell(ln.lstrip("-*• ").strip(), 400))
    return out


# ── How you're going: the day, read from the log and the businesses ──────────
# ADR-136 Rule 2. The box at the top of every session is the check-in. It reads;
# it never asks. `/done` writes one `Floor:` line per day (Rule 6), the plan's
# `Tomorrow:` line names today's one thing, and each business repo's last
# commit says whether it moved.
VALUE_RE = re.compile(r"^\s*Value:\s*([^:]+?)\s*(?::\s*(.+?))?\s*$", re.I)
FLOOR_LOG_RE = re.compile(r"^\s*Floor:\s*(.+?)\s*$", re.I | re.M)
FIXED_RE = re.compile(r"^\s*(Tomorrow|This week):\s*(.+?)\s*$", re.I)
GOAL_RE = re.compile(r"\[goal:\s*([^\]]+)\]\s*")
GOAL_STATUSES = ("not started", "on track", "at risk", "done", "dropped")


def goal_counts(repo: Path) -> dict[str, int] | None:
    """What the business says about each goal it was sent, as counts by
    status, read from goals.md under context-core/strategic-identity/ (the
    root one, or one per venture). Only the status column is read; the
    private repo never copies a business document (standard 6.2). None when
    the business has no goals.md at all."""
    base = repo / "context-core" / "strategic-identity"
    files = [base / "goals.md"] + sorted(base.glob("*/goals.md")) if base.is_dir() else []
    counts: dict[str, int] = {}
    found = False
    for f in files:
        if not f.is_file():
            continue
        found = True
        try:
            text = f.read_text(encoding="utf-8", errors="replace")[:40000]
        except Exception:
            continue
        for ln in text.splitlines():
            s = ln.strip()
            if not s.startswith("|") or re.match(r"^\|[\s:|-]+\|$", s):
                continue
            cells = [c.strip().lower() for c in s.strip("|").split("|")]
            if len(cells) >= 2 and GOAL_RE.search(cells[0]) and cells[1] in GOAL_STATUSES:
                counts[cells[1]] = counts.get(cells[1], 0) + 1
    return counts if found else None


def goal_status(repo: Path) -> str | None:
    counts = goal_counts(repo)
    if not counts:
        return "no goal shared yet"
    return "goals: " + ", ".join(f"{s} {counts[s]}" for s in GOAL_STATUSES if s in counts)


def business_repo(name: str) -> Path | None:
    slug = _slug(name)
    return next((p for p in (projects_dir() / slug, projects_dir() / f"{slug}-ops") if (p / ".git").exists()), None)


def days_since_note(root: Path, who: str | None, today: datetime.date | None = None) -> int | None:
    """Days since the person last wrote in their log, or None with no log."""
    home = log_home(root, who, True)
    if home is None:
        return None
    cur, folder = home
    today = today or datetime.date.today()
    dates: list[str] = []
    if cur.is_file() and readable(cur, True):
        try:
            d = field(cur.read_text(encoding="utf-8", errors="replace")[:4000], "date")
            if d:
                dates.append(d)
        except Exception:
            pass
    dates += [f.stem for f in older_days(folder)]
    if not dates:
        return None
    try:
        last = max(datetime.date.fromisoformat(d) for d in dates if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d))
    except ValueError:
        return None
    return max(0, (today - last).days)


def plan_counts(root: Path, who: str | None) -> dict[str, int]:
    """The whole numbers the brain may be sent about where a person is
    (ADR-136 Rule 5). Never a word of the plan; counts only."""
    spine = root / "self-as-code.md"
    out: dict[str, int] = {}
    if not spine.is_file() or not readable(spine, True):
        return out
    try:
        text = spine.read_text(encoding="utf-8", errors="replace")[:120000]
    except Exception:
        return out
    commits = _section_lines(text, "commits")
    out["daily_steps"] = len([ln for ln in commits if not FIXED_RE.match(ln) and not ln.lower().startswith("parked:")])
    out["floor_lines"] = len(floor_names(text))
    days = floor_days(root, who)
    out["floor_days_checked"] = len(days)
    out["floor_days_held"] = sum(1 for _, m in days if m and all(m.values()))
    names = plan_ventures(root, text)
    out["businesses"] = len(names)
    red = amber = green = with_goal = 0
    for name in names:
        repo = business_repo(name)
        counts = goal_counts(repo) if repo else None
        if counts:
            with_goal += 1
            red += counts.get("at risk", 0)
            amber += counts.get("not started", 0)
            green += counts.get("on track", 0) + counts.get("done", 0)
    out["businesses_with_goal"] = with_goal
    out["goals_red"], out["goals_amber"], out["goals_green"] = red, amber, green
    out["parked"] = len(re.findall(r"^\s*Parked:", text, re.M | re.I))
    out["inbox_open"] = inbox_open(root)
    out["week_page"] = 1 if week_page(root) else 0
    since = days_since_note(root, who)
    if since is not None:
        out["days_since_note"] = min(since, 9999)
    return out


def projects_dir() -> Path:
    """Where business repos live on this machine: ~/projects, or
    OAC_PROJECTS_DIR for a test."""
    return Path(os.environ.get("OAC_PROJECTS_DIR") or (Path.home() / "projects"))


def _slug(name: str) -> str:
    s = re.sub(r"['\u2019]", "", name.lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def plan_ventures(root: Path, text: str) -> list[str]:
    """The businesses the plan names: the `###` blocks under the baseline,
    else the folders under standards/ventures/, else `operations:`."""
    ventures: list[str] = []
    m = re.search(r"^##\s+the baseline\b.*?(?=^##\s|\Z)", text, re.M | re.S | re.I)
    if m:
        ventures = [_cell(v, 60) for v in re.findall(r"^###\s+(.+?)\s*$", m.group(0), re.M)
                    if not v.lower().startswith("how ")]
    if not ventures:
        vdir = root / "standards" / "ventures"
        if vdir.is_dir():
            ventures = sorted(d.name for d in vdir.iterdir()
                              if d.is_dir() and not d.name.startswith(("_", ".")))
    if not ventures and (root / ".oac" / "manifest.yml").is_file():
        mm = re.search(r"^operations:\s*\[([^\]]*)\]",
                       (root / ".oac" / "manifest.yml").read_text(encoding="utf-8", errors="replace"), re.M)
        if mm:
            ventures = [v.strip().strip("'\"") for v in mm.group(1).split(",") if v.strip()]
    return ventures


def floor_names(text: str) -> list[str]:
    """The values on the floor, in the plan's order."""
    out = []
    for ln in _section_lines(text, "the floor"):
        m = VALUE_RE.match(ln)
        if m:
            out.append(m.group(1).strip())
    return out


def _parse_floor_line(line: str) -> dict[str, bool]:
    marks: dict[str, bool] = {}
    for part in re.split(r"\s*[·,;]\s*", line):
        words = part.strip().split()
        if len(words) >= 2 and words[-1].lower() in ("yes", "no"):
            marks[" ".join(words[:-1]).strip().lower()] = words[-1].lower() == "yes"
    return marks


def floor_days(root: Path, who: str | None, days: int = 7) -> list[tuple[str, dict[str, bool]]]:
    """For each of the last `days` calendar days that carries a `Floor:` line
    in the person's log, that day's marks (the last line written that day)."""
    home = log_home(root, who, True)
    if home is None:
        return []
    current, folder = home
    out: list[tuple[str, dict[str, bool]]] = []
    today = datetime.date.today()
    current_text = ""
    if current.is_file() and readable(current, True):
        try:
            current_text = current.read_text(encoding="utf-8", errors="replace")[:60000]
        except Exception:
            current_text = ""
    current_date = field(current_text, "date") if current_text else None
    for back in range(days):
        d = (today - datetime.timedelta(days=back)).isoformat()
        if current_text and (current_date == d or (current_date is None and back == 0)):
            text = current_text
        else:
            f = folder / f"{d}.md"
            if not (f.is_file() and readable(f, True)):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")[:60000]
            except Exception:
                continue
        lines = FLOOR_LOG_RE.findall(text)
        if lines:
            marks = _parse_floor_line(lines[-1])
            if marks:
                out.append((d, marks))
    return out


def floor_row(text: str, root: Path, who: str | None) -> str | None:
    names = floor_names(text)
    if not names:
        return None
    days = floor_days(root, who)
    if not days:
        return "not checked yet. /done asks, one word per line"
    held = sum(1 for _, marks in days if marks and all(marks.values()))
    n = len(days)
    row = f"held {held} of the last {n} day{'s' if n != 1 else ''} you checked"
    slipped: dict[str, int] = {}
    for _, marks in days:
        for k, v in marks.items():
            if not v:
                slipped[k] = slipped.get(k, 0) + 1
    if slipped:
        worst = max(slipped.items(), key=lambda kv: kv[1])
        row += f"; slipped most: {worst[0]} ({worst[1]} day{'s' if worst[1] != 1 else ''})"
    return row


def business_moves(names: list[str]) -> str | None:
    """One phrase per business: moved n days ago, quiet since a date, or no
    repo yet. The repo is ~/projects/<slug> or ~/projects/<slug>-ops."""
    if not names:
        return None
    today = datetime.date.today()
    parts = []
    for name in names[:6]:
        slug = _slug(name)
        repo = next((p for p in (projects_dir() / slug, projects_dir() / f"{slug}-ops")
                     if (p / ".git").exists()), None)
        if repo is None:
            parts.append(f"{name}: no repo yet")
            continue
        last = git(repo, "log", "-1", "--format=%cs")
        if not last:
            parts.append(f"{name}: nothing saved yet")
            continue
        try:
            ago = (today - datetime.date.fromisoformat(last)).days
        except ValueError:
            parts.append(f"{name}: last moved {last}")
            continue
        if ago <= 0:
            moved = f"{name} moved today"
        elif ago <= 7:
            moved = f"{name} moved {ago} day{'s' if ago != 1 else ''} ago"
        else:
            moved = f"{name} quiet since {last}"
        status = goal_status(repo)
        parts.append(f"{moved}; {status}" if status else moved)
    return " · ".join(parts)


def week_page(root: Path, today: datetime.date | None = None) -> Path | None:
    """This ISO week's page, `projects/weeks/<year>-w<NN>.md`, if it exists."""
    today = today or datetime.date.today()
    y, w, _ = today.isocalendar()
    p = root / "projects" / "weeks" / f"{y}-w{w:02d}.md"
    return p if p.is_file() and readable(p, True) else None


def today_row(root: Path, text: str) -> str | None:
    """Today's one thing: this week's page if it has a line for today, else
    the plan's `Tomorrow:` line, else `This week:`, else the first daily step."""
    page = week_page(root)
    if page is not None:
        try:
            ptext = page.read_text(encoding="utf-8", errors="replace")[:40000]
        except Exception:
            ptext = ""
        day = datetime.date.today().strftime("%a")
        for ln in _section_lines(ptext, "the days"):
            m = re.match(rf"{day}\w*:\s*(.+)$", ln, re.I)
            if m:
                return m.group(1).strip()
    commits = _section_lines(text, "commits")
    fixed = {}
    for ln in commits:
        m = FIXED_RE.match(ln)
        if m:
            fixed[m.group(1).lower()] = m.group(2).strip()
    if "tomorrow" in fixed:
        return fixed["tomorrow"]
    if "this week" in fixed:
        return fixed["this week"]
    steps = [ln for ln in commits if not FIXED_RE.match(ln) and not ln.lower().startswith("parked:")]
    return f"your daily steps: {steps[0]}" if steps else None


def next_moment(front: str) -> str | None:
    """The next moment the plan itself sets: the two-week check, the 90-day
    review when it is close, else the week."""
    today = datetime.date.today()
    last = field(front, "last_raised")
    nxt = field(front, "next_raise")
    try:
        if last:
            check = datetime.date.fromisoformat(last) + datetime.timedelta(days=14)
            if check >= today:
                when = "today" if check == today else check.isoformat()
                return f"the two-week check, {when} (/sac check)"
    except ValueError:
        pass
    try:
        if nxt:
            review = datetime.date.fromisoformat(nxt)
            if 0 <= (review - today).days <= 14:
                return f"your 90-day review, {'today' if review == today else nxt}"
    except ValueError:
        pass
    if today.weekday() == 4:
        return "your week's review, today (/sac week)"
    sunday = today + datetime.timedelta(days=(6 - today.weekday()) % 7)
    return f"your week: /sac week on Sunday {sunday.isoformat()}"


def how_youre_going(root: Path, who: str | None) -> list[tuple[str, str]]:
    """The check-in rows for a self plane. Everything is read; nothing is
    asked. Empty when there is no plan yet."""
    spine = root / "self-as-code.md"
    if not spine.is_file() or not readable(spine, True):
        return []
    try:
        text = spine.read_text(encoding="utf-8", errors="replace")[:120000]
    except Exception:
        return []
    m = FRONTMATTER_RE.search(text)
    front = m.group(1) if m else ""
    if field(front, "status") == "seeded":
        return []
    rows: list[tuple[str, str]] = []
    fl = floor_row(text, root, who)
    if fl:
        rows.append(("Floor", fl))
    bm = business_moves(plan_ventures(root, text))
    if bm:
        rows.append(("Your businesses", _cell(bm, 300)))
    td = today_row(root, text)
    if td:
        rows.append(("Today", _cell(td, 220)))
    nm = next_moment(front)
    if nm:
        rows.append(("Next", nm))
    return rows


def spine_goals(root: Path) -> list[tuple[str, str]]:
    """The reminder rows for a self plane, read from self-as-code.md: the
    rewrite (the twelve-month leap), the venture goal the commits hang off,
    a quarter line if the spine carries one, and the ventures."""
    spine = root / "self-as-code.md"
    if not spine.is_file() or not readable(spine, self_plane=True):
        return []
    try:
        text = spine.read_text(encoding="utf-8", errors="replace")[:120000]
    except Exception:
        return []
    rows: list[tuple[str, str]] = []
    rewrite = _section_lines(text, "the rewrite")
    if rewrite:
        rows.append(("The rewrite", _cell(rewrite[0], 220)))
    quarter = _section_lines(text, "this quarter") or _section_lines(text, "the quarter")
    if quarter:
        rows.append(("This quarter", _cell(quarter[0], 220)))
    else:
        for ln in _section_lines(text, "commits")[:3]:
            if re.search(r"\bgoal\b|\btarget\b", ln, re.I):
                rows.append(("Venture goal", _cell(ln, 220)))
                break
    ventures = plan_ventures(root, text)
    if ventures:
        rows.append(("Ventures", " · ".join(ventures[:6])))
    return rows


def routed_goals(root: Path) -> list[tuple[str, str]]:
    """The reminder rows for a business plane: what the self plane routed
    here, from context-core/strategic-identity/from-self-as-code.md."""
    f = root / "context-core" / "strategic-identity" / "from-self-as-code.md"
    if not f.is_file() or not readable(f):
        return [("Goals", "nothing shared here yet. Run /sac in your private repo and choose what to share")]
    try:
        text = f.read_text(encoding="utf-8", errors="replace")[:60000]
    except Exception:
        return []
    rows: list[tuple[str, str]] = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("|") and not re.match(r"^\|\s*-", s) and "Slice" not in s and "Statement" not in s:
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells and cells[0]:
                rows.append(("Shared here" if not rows else "", _cell(cells[0], 200)))
        elif s.startswith(("- ", "* ")):
            rows.append(("Shared here" if not rows else "", _cell(GOAL_RE.sub("", s[2:]), 200)))
        if len(rows) >= 4:
            break
    return rows


def first_time(root: Path, is_self: bool, who: str | None) -> bool:
    """True until the plane has been worked in: no continuity log for this
    person yet, and the spine (self) or register (business) still the seed."""
    home = log_home(root, who, is_self)
    if home is not None:
        current, folder = home
        if current.is_file() or older_days(folder):
            return False
    target = root / ("self-as-code.md" if is_self else "systems/register.md")
    if not target.is_file():
        return True
    try:
        status = field(target.read_text(encoding="utf-8", errors="replace")[:4000], "status")
    except Exception:
        return True
    return status in (None, "seeded")


def _cell(text: str, limit: int = 600) -> str:
    """One line of plain text. The log is markdown; the box is not, so the
    emphasis and code marks a task-bridge entry carries are dropped here."""
    text = " ".join(text.split()).replace("**", "").replace("`", "")
    return text[: limit - 3] + "..." if len(text) > limit else text


def _split_label(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if ": " not in line:
        return None
    label, value = line.split(": ", 1)
    return label.strip(), value.strip()


def announcement(root: Path) -> str | None:
    """The markdown for `companyAnnouncements`, or None outside an OaC repo."""
    manifest = root / ".oac" / "manifest.yml"
    if not manifest.is_file():
        return None
    plane = manifest_plane(manifest)
    if plane is None:
        return None
    is_self = plane == "self"
    who = handle(root)
    if first_time(root, is_self, who):
        return FIRST_TIME[plane]

    mode = "SAC" if is_self else "OAC"
    door = "/sac" if is_self else "/oac"
    branch = git(root, "branch", "--show-current") or "?"
    today = datetime.date.today().strftime("%A %-d %B")
    # The repo's name, not the worktree folder's: a worktree is called
    # _wt-oac and nobody thinks of their plane by that name.
    origin = git(root, "remote", "get-url", "origin") or ""
    repo = re.sub(r"\.git$", "", origin.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]) or root.name
    rows: list[tuple[str, str]] = []

    commits = recent_commits(root)
    dirty = dirty_count(root)
    if commits or dirty:
        since = f"{len(commits)} commit(s)" if commits else "no commits"
        if dirty:
            since += f" · {dirty} file(s) uncommitted"
        rows.append(("Since last session", since))
        if commits:
            rows.append(("Latest", _cell(commits[0].split(" ", 1)[-1])))

    for line in roll_forward(root, who, is_self, limit=None):
        parsed = _split_label(line)
        if not parsed:
            continue
        label, value = parsed
        if label.startswith("You left off"):
            rows.append(("You left off", _cell(f"{label[len('You left off'):].strip(' ()')} · {value}")))
        elif label == "When":
            rows.append(("When", _cell(value)))
        elif label.startswith("Last entry"):
            rows.append(("Last entry", _cell(f"{label.split()[-1]} · {value}")))

    if is_self:
        for line in self_core(root):
            parsed = _split_label(line)
            if parsed and parsed[0] in ("Next review", "Steps", "Your floor"):
                rows.append((parsed[0], _cell(parsed[1], 90)))
        names = open_project_names(root)
        if names:
            rows.append(("Open projects", " · ".join(names)))
    else:
        manual = manual_processes(root)
        if manual:
            rows.append(("Register", f"{manual} process(es) still manual. The number to watch"))
        intents = open_intents(root)
        if intents:
            rows.append(("Open work", _cell(" · ".join(intents[:2]), 120)))
        for line in who_worked(root):
            parsed = _split_label(line)
            if parsed:
                rows.append(("Who worked", _cell(parsed[1], 120)))

    # Tasks: what is open. A self plane counts its projects; a business plane
    # names its open intents (above) and the plans still in progress.
    if not is_self:
        plans = open_plans(root)
        if plans:
            rows.append(("In progress", _cell(" · ".join(plans[:2]), 200)))

    # The same structure for both planes: the wordmark, the mode line, the
    # goals to be reminded of, then where things stand, then the door.
    goals = spine_goals(root) if is_self else routed_goals(root)
    long_name = "Self as Code" if is_self else "Operations as Code"
    out = [WORDMARK, f"◆ {long_name} · {mode}", f"{repo} · {branch} · {today}", ""]
    if goals:
        out += ["GOALS"] + box(goals) + [""]
    if is_self:
        going = how_youre_going(root, handle(root))
        if going:
            out += ["HOW YOU'RE GOING"] + box(going) + [""]
    out += ["STATUS"] + box(rows) + [""]
    out.append(f"{door} review when your 90 days are up · /start to begin · /done to finish"
               if is_self else f"{door} does the next thing · /start to begin · /done to finish")
    return "\n".join(out)


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_announcement(root: Path, text: str) -> bool:
    """Put the announcement in .claude/settings.local.json, touching no other
    key, and take it out of .claude/settings.json if it is still there.

    The local file is gitignored, so a rewrite every session no longer leaves
    the checkout dirty. The shared file must not keep a copy: Claude Code
    merges the two lists and shows one of them at random, so a stale seed
    would come up every other session (both tested 7 October 2026). A pack
    still seeds the shared file, because a hook's write only shows from the
    next session and a learner's very first open needs the note; this is
    where that seed moves out, once. Atomic, and silent on any failure: a
    hook must never break a session."""
    claude = root / ".claude"
    local, shared = claude / "settings.local.json", claude / "settings.json"
    try:
        data = json.loads(local.read_text(encoding="utf-8")) if local.is_file() else {}
        if not isinstance(data, dict):
            return False
        if data.get(ANNOUNCEMENT_KEY) != [text]:
            claude.mkdir(exist_ok=True)
            data[ANNOUNCEMENT_KEY] = [text]
            _write_json(local, data)
    except Exception:
        return False
    try:
        seed = json.loads(shared.read_text(encoding="utf-8")) if shared.is_file() else None
        if isinstance(seed, dict) and ANNOUNCEMENT_KEY in seed:
            del seed[ANNOUNCEMENT_KEY]
            _write_json(shared, seed)
    except Exception:
        pass                    # the local copy is written; a stale seed is not fatal
    return True


def main() -> int:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    manifest = root / ".oac" / "manifest.yml"
    if not manifest.is_file():
        return 0                              # not an OaC repo: say nothing
    if git(root, "rev-parse", "--git-dir") is None:
        return 0

    plane = manifest_plane(manifest)
    is_self = plane == "self"

    if "--announce" in sys.argv:
        text = announcement(root)
        if text is None:
            return 0
        if "--write" in sys.argv:
            write_announcement(root, text)
        else:
            sys.stdout.write(text + "\n")
        return 0

    branch = git(root, "branch", "--show-current") or "?"
    mode = "SAC" if is_self else "OAC"
    lines = [f"◆ OpsCode · {mode} · {root.name} · {branch}"]

    commits = recent_commits(root)
    dirty = dirty_count(root)
    if commits or dirty:
        head = f"  Since yesterday: {len(commits)} commit(s)"
        if dirty:
            head += f", {dirty} file(s) uncommitted"
        lines.append(head)
        for c in commits[:5]:
            lines.append(f"    {c}")
        if len(commits) > 5:
            lines.append(f"    +{len(commits) - 5} more")

    who = handle(root)
    focus = roll_forward(root, who, is_self) if not out_of_time() else []
    lines.extend(focus)
    if not out_of_time():
        lines.extend(who_worked(root))

    if is_self:
        # SAC mode opens on the spine, not on the systems register. A self plane
        # has no context-core/ and no systems/, so the OaC sections below would
        # be empty or meaningless here (ADR-120).
        if not out_of_time():
            lines.extend(self_core(root))

        if not out_of_time():
            for k, v in how_youre_going(root, who):
                lines.append(f"  {k}: {v}")

        if not out_of_time():
            projects = open_projects(root)
            if projects:
                lines.append(f"  Open projects: {projects}")

        if not out_of_time():
            inbox = inbox_open(root)
            if inbox:
                lines.append(f"  Inbox: {inbox} item(s) not actioned")
    else:
        if not out_of_time():
            moved = brain_moves(root)
            if moved:
                lines.append("  Shared brain moved: " + ", ".join(moved))

        if not out_of_time():
            intents = open_intents(root)
            if intents:
                lines.append(f"  Open intents ({len(intents)})")
                for i in intents:
                    lines.append(f"    · {i}")

        if not out_of_time():
            plans = open_plans(root)
            if plans:
                lines.append(f"  In progress ({len(plans)})")
                for p in plans:
                    lines.append(f"    · {p}")

        if not out_of_time():
            manual = manual_processes(root)
            if manual:
                lines.append(f"  Systems register: {manual} process(es) still manual")

    if not out_of_time():
        lines.extend(suggestions(root, is_self, bool(focus), dirty))

    if len(lines) == 1:
        return 0                              # nothing moved: stay quiet

    if len(lines) > MAX_LINES:
        extra = len(lines) - MAX_LINES + 1
        lines = lines[:MAX_LINES - 1] + [f"  · +{extra} more"]

    sys.stdout.write("\n" + "\n".join(lines) + "\n\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)                  # never start a session on a stack trace
