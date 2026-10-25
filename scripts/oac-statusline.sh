#!/bin/bash
# OaC standard Claude Code statusline, v3 (mode, cost, responsive).
#
# Wide terminal, one line:
#   adam@host:~/projects/opscode-hq · adam/openwiki-eval* | OAC · Opus 5 (1M) [ctx: 43%] $4.12
#   adam@host:~/projects/_wt-li ⧉ _wt-li · adam/linkedin ⌂ main +2 | OAC · Opus 5 [ctx: 43%] $4.12
#
# Narrow terminal (a vertical split), two lines:
#   adam@host:~/projects/lopez-delon-ops · main
#   SAC · Fable 5.1 [ctx: 50%] $80.82
#
# Segments: user@host, folder, the linked worktree when you are in one, WHAT
# YOU ARE WORKING ON, the home clone when it needs you; then the MODE you are
# operating in, the model, context usage, and what this session has cost.
#
# The mode is one of the three in ADR-120. SAC and OAC come from
# .oac/manifest.yml (plane: self, plane: business). AIDLC shows when the
# engine has an active intent running a software scope (feature, bugfix, ...):
# `AIDLC ⚙ 260731-projection-rollup@intent-capture`. An operations intent keeps
# the plane mode and carries the stage. Outside a plane with no intent there
# is no mode segment; the line says so by omission.
#
# The cost is Claude Code's own session figure (cost.total_cost_usd in the
# statusline JSON). Never fabricated: no figure, no segment. Every render also
# refreshes one small JSON per session under ~/.claude/oac-usage/sessions/,
# the ledger that oac-usage-report.py turns into team/<handle>/usage.md.
#
# Responsive: Claude Code passes the terminal width as $COLUMNS. At 110
# columns or more it is one line; under that, two; under 60, three (location /
# work / status). Unknown width falls back to two lines, because a wrapped
# single line is worse than a short second one.
#
# The work label is the branch by default, because our branch convention is
# {username}/{description} (CLAUDE.md rule 5), so the branch already names the
# task. Set OAC_TASK to override it with your own label.
#
# The ⌂ segment reports the PRIMARY clone, and only when something is wrong
# with it: amber for uncommitted work, red when it is parked off main. That
# clone is shared ground (cron addresses it by absolute path, every worktree
# hangs off it), so a mess there stops scheduled jobs for everyone.
#
# Portable: works in any repo and outside a repo. Uses python3, not jq (jq is
# not installed on the Pi, and depending on it silently breaks the whole line).
#
# Install for all your repos: python3 code/scripts/install-oac-statusline.py
# Standard: brand/standards/claude-code-statusline-standard.md

# Rule 5 of the standard: degrade, never vanish. python3 is not guaranteed on
# a fresh macOS (it needs Xcode Command Line Tools). Without this guard the
# statusline would silently print nothing, which is the exact failure this
# standard exists to prevent.
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s: python3 missing, statusline degraded (xcode-select --install)' "${PWD/#$HOME/~}"
  exit 0
fi

# Terminal width for the layout decision. Claude Code sets COLUMNS and LINES
# to the terminal size before running the statusline command; tput cannot see
# the terminal from here because the output is captured, not attached
# (code.claude.com/docs/en/statusline). Unset means unknown, and unknown lays
# out as two lines.
OAC_COLS="${COLUMNS:-}"
export OAC_COLS

exec python3 -c '
import json, os, platform, re, subprocess, sys

try:
    d = json.load(sys.stdin)
except Exception:
    d = {}

ws    = d.get("workspace") or {}
cwd   = ws.get("current_dir") or ws.get("project_dir") or d.get("cwd") or os.getcwd()
model = (d.get("model") or {}).get("display_name") or "?"
ctxw  = d.get("context_window") or {}
used  = ctxw.get("used_percentage")
cost  = (d.get("cost") or {}).get("total_cost_usd")

R      = "\033[00m"
GREEN  = "\033[01;32m"
BLUE   = "\033[01;34m"
CYAN   = "\033[36m"
MAGENTA= "\033[01;35m"
AMBER  = "\033[33m"
RED    = "\033[01;31m"
DIM    = "\033[02m"
BOLD   = "\033[01m"


def git(*args, at=None):
    """Run a git command in cwd (or at). Return stripped stdout, or None."""
    try:
        r = subprocess.run(("git", "-C", at or cwd) + args, capture_output=True,
                           text=True, timeout=2)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def work_label():
    """(worktree_name_or_None, branch_or_None, dirty_bool, common_git_dir, toplevel)."""
    inside = git("rev-parse", "--is-inside-work-tree")
    if inside != "true":
        return None, None, False, None, None

    gd, cd_ = git("rev-parse", "--absolute-git-dir"), git("rev-parse", "--path-format=absolute", "--git-common-dir")
    wt = None
    if gd and cd_ and os.path.normpath(gd) != os.path.normpath(cd_):
        wt = os.path.basename(gd)          # .git/worktrees/<name>

    branch = git("branch", "--show-current") or None
    if not branch:                          # detached HEAD
        sha = git("rev-parse", "--short", "HEAD")
        branch = f"detached@{sha}" if sha else None

    dirty = git("status", "--porcelain", "-uno")
    top = git("rev-parse", "--show-toplevel")
    return wt, branch, bool(dirty), cd_, top


def home_state(common_dir):
    """What the PRIMARY clone looks like, or None when it is clean on main.

    Shown only when something is actually wrong, because a segment that is
    always there is a segment nobody reads. Returns (text, is_bad).
    """
    if not common_dir:
        return None
    root = os.path.dirname(os.path.normpath(common_dir))   # .../repo/.git -> .../repo
    if not os.path.isdir(root):
        return None
    branch = (git("branch", "--show-current", at=root) or "").strip()
    if branch and branch not in ("main", "master"):
        return (f"⌂ {branch}", True)        # parked off main: the loud one
    status = git("status", "--porcelain", "-uno", at=root)
    if status is None:
        return None
    n = len([ln for ln in status.splitlines() if ln.strip()])
    if n:
        return (f"⌂ {branch or 'main'} +{n}", False)
    return None


def read_text(path, limit=65536):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except Exception:
        return None


OPS_SCOPES = {"opscode-oac-operations", "opscode-sac-operator"}


def mode_token(top):
    """The mode you are operating in (ADR-120): SAC, OAC or AIDLC.

    SAC and OAC come from the plane in .oac/manifest.yml (ADR-118). AIDLC is
    the software lifecycle: it shows when the engine has an active intent
    whose scope is not one of the two operations scopes, in a plane or not.
    An operations intent keeps the plane mode and carries the stage:
    `OAC ⚙ 260731-projection-rollup@intent-capture`. All plain file reads.
    """
    root = top or cwd
    text = read_text(os.path.join(root, ".oac", "manifest.yml"), 32768)
    mode = None
    if text:
        m = re.search(r"^plane:\s*([a-z]+)", text, re.M)
        if m:
            mode = {"self": "SAC", "business": "OAC"}.get(m.group(1))
    engine, scope = "", None
    space = (read_text(os.path.join(root, "aidlc", "active-space"), 256) or "default").strip() or "default"
    cursor = read_text(os.path.join(root, "aidlc", "spaces", space, "intents", "active-intent"), 512)
    if cursor:
        slug = cursor.strip().splitlines()[0].strip() if cursor.strip() else ""
        if slug and re.fullmatch(r"[A-Za-z0-9._-]+", slug):
            state = read_text(os.path.join(root, "aidlc", "spaces", space, "intents", slug, "aidlc-state.md"))
            stage = None
            if state:
                sm = re.search(r"\*\*Current Stage\*\*:\s*([A-Za-z0-9._-]+)", state)
                stage = sm.group(1) if sm else None
                sc = re.search(r"\*\*Scope\*\*:\s*([A-Za-z0-9._-]+)", state)
                scope = sc.group(1) if sc else None
            short = re.sub(r"-[0-9a-f]{8}$", "", slug)
            if len(short) > 28:
                short = short[:27] + "…"
            # An operations stage carries the prefix of the mode that owns it
            # (opscode-sac-self-as-code); the line already says the mode, so
            # the stage reads as itself: SAC, then self-as-code-run@self-as-code.
            # This Python sits inside a single-quoted -c string: no apostrophes
            # and no backticks in comments here, or the whole line goes dark.
            if stage:
                stage = re.sub(r"^opscode-(sac|oac)-", "", stage)
            engine = f" ⚙ {short}" + (f"@{stage}" if stage else "")
    # AIDLC when the intent runs a software scope. A record with no scope line
    # is not evidence either way: in a plane the plane wins, outside one the
    # engine is the only thing there.
    if engine and scope not in OPS_SCOPES and (scope is not None or not mode):
        return "AIDLC" + engine
    if not mode:
        return None
    return mode + engine


def record_usage(mode, top, w):
    """One JSON file per session under ~/.claude/oac-usage/sessions/, refreshed
    while the figures move. This is the ledger oac-usage-report.py turns into
    team/<handle>/usage.md, so a business can see what its people spend.
    Writes only when something changed, never inside the repo, and never
    raises: a statusline that fails on a ledger write is a statusline that
    fails.
    """
    sid = d.get("session_id")
    if not sid or not re.fullmatch(r"[A-Za-z0-9._-]{4,80}", str(sid)):
        return
    try:
        import time
        ledger = os.path.join(os.path.expanduser("~"), ".claude", "oac-usage", "sessions")
        os.makedirs(ledger, exist_ok=True)
        path = os.path.join(ledger, f"{sid}.json")
        c = d.get("cost") or {}
        row = {
            "session_id": sid,
            "repo": top or cwd,
            "repo_name": os.path.basename(top or cwd),
            "mode": (mode or "").split(" ")[0] or None,
            "user": os.environ.get("USER") or os.environ.get("USERNAME"),
            "git_user": git("config", "user.name", at=top) if top else None,
            "host": host,
            "model": model,
            "version": d.get("version"),
            "cost_usd": c.get("total_cost_usd"),
            "duration_ms": c.get("total_duration_ms"),
            "api_ms": c.get("total_api_duration_ms"),
            "lines_added": c.get("total_lines_added"),
            "lines_removed": c.get("total_lines_removed"),
            "input_tokens": ctxw.get("total_input_tokens"),
            "output_tokens": ctxw.get("total_output_tokens"),
            "context_pct": used,
            "cols": w,
            "last_seen": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        prev = {}
        old = read_text(path, 8192)
        if old:
            try:
                prev = json.loads(old)
            except Exception:
                prev = {}
        row["started"] = prev.get("started") or row["last_seen"]
        same = all(prev.get(k) == row[k] for k in ("cost_usd", "input_tokens", "output_tokens", "lines_added", "lines_removed"))
        if same and prev:
            return
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(row, fh)
        os.replace(tmp, path)
    except Exception:
        return


def cols():
    v = os.environ.get("OAC_COLS", "").strip()
    try:
        n = int(v)
        return n if n > 0 else None
    except ValueError:
        return None


# ── Segments ─────────────────────────────────────────────────────────────────
home = os.path.expanduser("~")
show = "~" + cwd[len(home):] if cwd.startswith(home + os.sep) else ("~" if cwd == home else cwd)
user = os.environ.get("USER") or os.environ.get("USERNAME") or "user"
# platform.node() rather than os.uname(): os.uname does not exist on Windows,
# and $USER is not set there either. Found by a cohort builder on a
# corporate Windows laptop, week three of his cohort, and fixed in his own repo.
host = (platform.node() or "host").split(".")[0]
location = f"{GREEN}{user}@{host}{R}:{BLUE}{show}{R}"

wt, branch, dirty, common_dir, top = work_label()

work = []
if wt:
    work.append(f"{MAGENTA}⧉ {wt}{R}")
label = os.environ.get("OAC_TASK") or branch
if label:
    if len(label) > 38:
        label = label[:37] + "…"
    work.append(f"{DIM}·{R} {CYAN}{label}{R}" + (f"{CYAN}*{R}" if dirty else ""))
hs = home_state(common_dir)
if hs:
    text, bad = hs
    work.append(f"{RED if bad else AMBER}{text}{R}")

status = []
mode = mode_token(top)
if mode:
    status.append(f"{BOLD}{mode}{R} {DIM}·{R}")
status.append(model)
if isinstance(used, (int, float)):
    colour = "\033[32m" if used < 50 else ("\033[33m" if used < 80 else "\033[31m")
    status.append(f"{colour}[ctx: {used:.0f}%]{R}")
if isinstance(cost, (int, float)) and cost > 0:
    status.append(f"{DIM}${cost:.2f}{R}")

# ── Layout: one line wide, two narrow, three very narrow, two when unknown ──
w = cols()
work_s = " ".join(work)
status_s = " ".join(status)
if w is not None and w >= 110:
    line = location + (" " + work_s if work_s else "") + f" {DIM}|{R} " + status_s
    out = line
elif w is not None and w < 60:
    out = "\n".join(x for x in (location, work_s, status_s) if x)
else:
    out = location + (" " + work_s if work_s else "") + "\n" + status_s

sys.stdout.write(out)
record_usage(mode, top, w)
'
