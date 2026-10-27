#!/usr/bin/env python3
"""A nudge that quotes only your own plan. Opt in; one message a day at most.

    python3 scripts/sac-nudge.py --show      # what today's nudge would say, sent nowhere
    python3 scripts/sac-nudge.py --send      # send it to your own chat, once today

ADR-136 Rule 7, from the plan's test 7, 'it holds you to it'. The two-week
check and the 30-day nudge, by Telegram, in the person's own words: the plan's
`Tomorrow:` line, the review's date, the day of the week. Never research,
never a business's content, never a comparison with anyone. Opt in, and the
private repo is the only source.

HOW IT DECIDES
    The same ladder the brain uses for the next moment (ADR-136 Rule 5), run
    here beside the plan, so nothing leaves this folder to work it out:
    the two-week check on its day; three days without a note; Friday and
    Sunday for the week; the day before the 90-day review. Nothing else, and
    nothing at all on a day with no moment.

OPT IN
    Two lines in `.env`, both yours to add, neither ever committed:
        TELEGRAM_BOT_TOKEN=...      a bot you made with @BotFather
        SAC_NUDGE_CHAT_ID=...       your own chat with that bot
    Without them this prints nothing and exits 0, so a cron line is harmless
    until you choose. One message a day: a stamp at `.oac/nudge-sent` holds
    the last date. The cron line, yours to install, every morning at eight:
        0 8 * * * cd ~/projects/<first>-<last>-ops && python3 scripts/sac-nudge.py --send >> .oac/nudge.log 2>&1

The send is `curl -4` to the Telegram Bot API, as every send on the Pi is. A
test never reaches it: the tests run with a PATH of nothing but a fake curl.
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAMP = Path(".oac") / "nudge-sent"


def brief_module():
    """The session brief's readers, beside this script in every pack."""
    p = HERE / "oac-session-brief.py"
    if not p.is_file():
        return None
    spec = importlib.util.spec_from_file_location("oac_session_brief", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_env(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    p = root / ".env"
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if s.startswith("export "):
            s = s[7:].strip()
        if "=" in s and not s.startswith("#"):
            k, v = s.split("=", 1)
            out[k.strip()] = v.strip().strip("'\"")
    return out


def tomorrow_line(text: str, brief) -> str | None:
    for ln in brief._section_lines(text, "commits"):
        m = brief.FIXED_RE.match(ln)
        if m and m.group(1).lower() == "tomorrow":
            return m.group(2).strip()
    return None


def decide(root: Path, today: datetime.date | None = None, brief=None) -> str | None:
    """Today's nudge, in the person's own words, or None on a day with no
    moment. Reads the plan and the log; writes nothing."""
    brief = brief or brief_module()
    if brief is None:
        return None
    spine = root / "self-as-code.md"
    if not spine.is_file():
        return None
    text = spine.read_text(encoding="utf-8", errors="replace")[:120000]
    m = brief.FRONTMATTER_RE.search(text)
    front = m.group(1) if m else ""
    if brief.field(front, "status") == "seeded":
        return None
    today = today or datetime.date.today()
    who = brief.handle(root)
    last = brief.field(front, "last_raised")
    nxt = brief.field(front, "next_raise")

    def iso(s):
        try:
            return datetime.date.fromisoformat(s) if s else None
        except ValueError:
            return None

    last_d, next_d = iso(last), iso(nxt)
    if next_d and (next_d - today).days == 1:
        return f"Your 90-day review is tomorrow, {nxt}. Type sac, then /sac review."
    if next_d and next_d <= today:
        return f"Your 90-day review was due on {nxt}. Type sac, then /sac review."
    if last_d and today == last_d + datetime.timedelta(days=14):
        return "Two weeks since you wrote your plan. Today is the check: type sac, then /sac check."
    since = brief.days_since_note(root, who, today)
    if since is not None and since >= 3:
        tm = tomorrow_line(text, brief)
        quote = f" Your plan's line for the next day was: '{tm}'. Did it happen?" if tm else ""
        return f"No note for {since} days.{quote} Type sac, then /start, and /done tonight with your floor one word per line."
    if today.weekday() == 4:
        return "Friday. Your week's review: what moved, what held, what carries. Type sac, then /sac week."
    if today.weekday() == 6:
        return "Sunday. Plan the week from your next review. Type sac, then /sac week."
    return None


def sent_today(root: Path, today: datetime.date) -> bool:
    p = root / STAMP
    return p.is_file() and p.read_text(encoding="utf-8", errors="replace").strip() == today.isoformat()


def stamp(root: Path, today: datetime.date) -> None:
    p = root / STAMP
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(today.isoformat() + "\n", encoding="utf-8")


def send(token: str, chat: str, text: str) -> bool:
    """curl -4 to the Bot API. The text is the whole message; nothing else
    goes with it."""
    try:
        r = subprocess.run(
            ["curl", "-4", "-s", "-X", "POST", f"https://api.telegram.org/bot{token}/sendMessage",
             "-d", f"chat_id={chat}", "--data-urlencode", f"text={text}",
             "-d", "disable_web_page_preview=true"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return '"ok":true' in r.stdout.replace(" ", "")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--show", action="store_true", help="print today's nudge; send nothing")
    g.add_argument("--send", action="store_true", help="send it to your own chat, once today")
    ap.add_argument("--today", help="YYYY-MM-DD, for a test")
    ap.add_argument("--root", type=Path, default=Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()))
    a = ap.parse_args(argv)
    root = a.root
    try:
        today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    except ValueError:
        print("sac-nudge: --today must be YYYY-MM-DD", file=sys.stderr)
        return 2
    text = decide(root, today)
    if a.show:
        print(text if text else "no nudge today")
        return 0
    env = load_env(root)
    token, chat = env.get("TELEGRAM_BOT_TOKEN", ""), env.get("SAC_NUDGE_CHAT_ID", "")
    if not token or not chat:
        return 0                                   # not switched on; say nothing
    if not text or sent_today(root, today):
        return 0
    if send(token, chat, text):
        stamp(root, today)
        print(f"sent: {text}")
        return 0
    print("sac-nudge: the send did not go through; nothing stamped, it will try again tomorrow", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
