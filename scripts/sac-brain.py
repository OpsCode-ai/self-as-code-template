#!/usr/bin/env python3
"""Keep this install's Self as Code framework current from the SAC brain.

The SAC brain (opscode-hq ADR-125 Rule 5) serves the framework every /sac
session speaks from. This script brings the newest version down into
`.oac/sac-framework.md`, the saved copy the session reads. It never breaks a
session: if the brain is out of reach for any reason, the saved copy stays and
the session runs on it.

    python3 scripts/sac-brain.py fetch              # newest version, or keep the saved one
    python3 scripts/sac-brain.py fetch --version 0.4
    python3 scripts/sac-brain.py version            # which version is saved
    python3 scripts/sac-brain.py section start      # one section of the saved copy, by id or name
    python3 scripts/sac-brain.py next               # where to go next, from the brain
    python3 scripts/sac-brain.py next --show        # what `next` would send, sending nothing

`section` is how /start, /done and /sac help read their words (ADR-136 Rule
9): from the saved copy, never from memory, so one edit on the brain reaches
every install on its next fetch. A name is the word after the slash in the
section's own `For `/...`` line (start, done, help, check, week, review), or
the heading as an id (the-opening, step-4). No such section in the saved
version: exit 1, nothing on stdout, and the command's own lines stand.

A key, and the brain's tools inside Claude Code:

    python3 scripts/sac-brain.py key                # save this install's key, then connect
    python3 scripts/sac-brain.py connect            # connect with the key already saved
    python3 scripts/sac-brain.py headers            # what Claude Code runs to connect

Keys are for machines and OpsCode's own installs. People will sign in to an
account instead, and never hold a key (opscode-hq ADR-129). `key` runs in a
plain terminal, never the chat, because the key would otherwise sit in the
conversation. It checks the key with the brain before saving it to `.env`.
Then `connect` writes `.mcp.json`, which holds no key: Claude Code runs
`headers` to read it from `.env` each time it connects. No key, no
`.mcp.json`, so an install without one never shows a broken server.

Settings, from the environment or this repo's `.env` (never committed):

    SAC_BRAIN_KEY   this install's key, from OpsCode. One key opens both brains
    SAC_BRAIN_URL   default https://brain.opscode.ai/sac

Answers stay home. `next` sends which plan headings exist and the review dates
from the frontmatter, never a word of what is under them. `--show` prints the
exact object first.

The same code serves the business half: `scripts/oac-brain.py` in a business
pack is this script with the Operations as Code brain's settings (the `Brain`
record below), so the two never drift.

Every line this prints is for the agent running the session, except `key`'s,
which are for whoever is at the terminal.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

DEFAULT_URL = "https://brain.opscode.ai/sac"
CACHE = Path(".oac") / "sac-framework.md"
PLAN = Path("self-as-code.md")
TIMEOUT = float(os.environ.get("SAC_BRAIN_TIMEOUT", "5"))
USER_AGENT = "opscode-sac-brain-client/1"
VERSION_RE = re.compile(r'^framework_version:\s*["\']?(\d+\.\d+)["\']?\s*$', re.M)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Plan headings that no step of the framework writes, but a plan may carry.
LEGACY_HEADINGS = {"refactor"}
# sac-brain-key.py makes keys as "sacb_" + token_urlsafe(32): 43 characters.
KEY_RE = re.compile(r"^sacb_[A-Za-z0-9_-]{43}$")
ENV = Path(".env")
MCP_JSON = Path(".mcp.json")
SERVER = "sac-brain"
# Claude Code runs this from the repo's own folder, so the path is relative.
HEADERS_HELPER = "python3 scripts/sac-brain.py headers"
KEY_ENV = "SAC_BRAIN_KEY"


@dataclass(frozen=True)
class Brain:
    """One brain's settings: which door, where the saved copy lives, what the
    headers are called, and how to read where the person (or business) is."""

    name: str = "sac"
    default_url: str = DEFAULT_URL
    url_env: str = "SAC_BRAIN_URL"
    cache: Path = CACHE
    header: str = "SAC-Framework"
    server: str = SERVER
    helper: str = HEADERS_HELPER
    script: str = "sac-brain.py"
    progress: Callable[[Path], dict] | None = field(default=None, compare=False)


class Unreachable(Exception):
    """Any reason the brain could not be used: offline, no key, refused, bad body.

    `status` is the brain's HTTP answer when it gave one, so a refused key
    (401, 403) can be told apart from no connection."""

    def __init__(self, why: str, status: int | None = None) -> None:
        super().__init__(why)
        self.status = status


def load_env(root: Path, brain: Brain | None = None) -> dict[str, str]:
    """The repo's `.env`, then the environment on top."""
    found: dict[str, str] = {}
    env_file = root / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            k, v = line.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                v = v[1:-1]
            found[k.strip()] = v
    keys = [KEY_ENV, "SAC_BRAIN_URL"]
    if brain and brain.url_env not in keys:
        keys.append(brain.url_env)
    for k in keys:
        if os.environ.get(k):
            found[k] = os.environ[k]
    return found


def version_of(text: str) -> str | None:
    head = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    m = VERSION_RE.search(head.group(1)) if head else None
    return m.group(1) if m else None


def saved(root: Path, brain: Brain = Brain()) -> tuple[bytes | None, str | None]:
    p = root / brain.cache
    if not p.is_file():
        return None, None
    data = p.read_bytes()
    return data, version_of(data.decode("utf-8", "replace"))


def _request(url: str, key: str | None, *, data: bytes | None = None, headers: dict | None = None):
    h = {"User-Agent": USER_AGENT, **(headers or {})}
    if key:
        h["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if data is not None else "GET")
    try:
        return urllib.request.urlopen(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return e
        raise Unreachable(f"the brain answered {e.code}", e.code) from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", e)
        raise Unreachable(f"no connection: {reason}") from None


def settings(root: Path, brain: Brain = Brain()) -> tuple[str, str]:
    env = load_env(root, brain)
    key = env.get(KEY_ENV, "").strip()
    if not key:
        raise Unreachable(f"no install key ({KEY_ENV})")
    return env.get(brain.url_env, brain.default_url).rstrip("/"), key


def write_atomic(path: Path, data: bytes) -> None:
    """Write through a temp file, so a crash never leaves half a file. mkstemp
    makes it readable by its owner only, and the result keeps that."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def fetch(root: Path, version: str | None, brain: Brain = Brain()) -> tuple[str, int]:
    have, have_v = saved(root, brain)
    try:
        base, key = settings(root, brain)
        url = f"{base}/v1/framework" + (f"/{version}" if version else "")
        headers = {"Accept": "text/markdown"}
        if have is not None:
            headers["If-None-Match"] = f'"{hashlib.sha256(have).hexdigest()}"'
        res = _request(url, key, headers=headers)
        if getattr(res, "code", None) == 304 or getattr(res, "status", None) == 304:
            if version and have_v != version:
                raise Unreachable("the brain said unchanged for a different version")
            return f"framework {have_v} from the brain (unchanged)", 0
        body = res.read()
        want_v = res.headers.get(f"{brain.header}-Version")
        want_sha = res.headers.get(f"{brain.header}-SHA256")
        got_v = version_of(body.decode("utf-8", "replace"))
        if not want_v or not want_sha:
            raise Unreachable("the answer had no version or checksum")
        if hashlib.sha256(body).hexdigest() != want_sha.lower():
            raise Unreachable("the answer failed its checksum")
        if got_v != want_v:
            raise Unreachable(f"the answer says {got_v} inside and {want_v} outside")
        if version and got_v != version:
            raise Unreachable(f"asked for {version}, got {got_v}")
    except Unreachable as why:
        if have is None:
            return (f"the brain was unreachable ({why}) and there is no saved framework at {brain.cache}. "
                    "Say so in one line and stop; do not run the method from memory."), 1
        return f"the brain was unreachable ({why}); using the saved framework {have_v}", 0

    if have == body:
        return f"framework {got_v} from the brain (unchanged)", 0
    write_atomic(root / brain.cache, body)
    was = f"was {have_v}" if have is not None else "new"
    return f"framework {got_v} from the brain ({was})", 0


# ── The saved copy's sections ───────────────────────────────────────────────

def _slug(s: str) -> str:
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", s.lower()))


def command_alias(text: str) -> str | None:
    """The word after the slash in a section's `For `/...`` line, the door's
    own word dropped: 'For `/start`' is start, 'For `/sac help`' is help. The
    same rule the brain uses, so a name works on both sides."""
    m = re.search(r"^For `/(?:sac |oac |self-as-code )?([a-z][a-z-]*)", text, re.M)
    return m.group(1) if m else None


def parse_sections(text: str) -> list[dict]:
    """The `## ` sections of a framework, in order, outside code fences, each
    with its id (step-N, or the heading as a slug) and its command name."""
    body = text
    head = re.match(r"\A---\n.*?\n---\n", text, re.S)
    if head:
        body = text[head.end():]
    out: list[dict] = []
    current: dict | None = None
    fenced = False
    for line in body.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
        m = None if fenced else re.match(r"^## (?!#)(.+?)\s*$", line)
        if m:
            current = {"heading": m.group(1), "lines": [line]}
            out.append(current)
        elif current is not None:
            current["lines"].append(line)
    seen: dict[str, int] = {}
    for s in out:
        step = re.match(r"^Step (\d+)\b", s["heading"], re.I)
        sid = f"step-{step.group(1)}" if step else _slug(s["heading"])
        seen[sid] = seen.get(sid, 0) + 1
        if seen[sid] > 1:
            sid = f"{sid}-{seen[sid]}"
        s["id"] = sid
        s["text"] = "\n".join(s.pop("lines")).strip()
        s["alias"] = command_alias(s["text"])
    return out


def section(root: Path, name: str, brain: Brain = Brain()) -> tuple[str, int]:
    """One section of the saved copy, to stdout; exit 1 and a note on stderr
    when the saved version has no such section, so the command's own lines
    stand."""
    have, have_v = saved(root, brain)
    want = name.strip().lower()
    if have is None:
        return f"no saved framework at {brain.cache}; use the lines in the command", 1
    for s in parse_sections(have.decode("utf-8", "replace")):
        if s["id"] == want or s["alias"] == want:
            return s["text"], 0
    return f"no section '{name}' in the saved framework {have_v}; use the lines in the command", 1


# ── Where the person is ─────────────────────────────────────────────────────

def plan_headings(framework_text: str) -> list[str]:
    """The closed list of plan headings, read from the saved framework itself."""
    found = re.findall(r"^Heading: `## ([^`]+)`", framework_text, re.M)
    return list(dict.fromkeys(h.strip() for h in found))


def progress(root: Path) -> dict:
    """Where the person is. Headings and dates only, never a word of content."""
    have, have_v = saved(root)
    closed = plan_headings(have.decode("utf-8", "replace")) if have else []
    allowed = {h.lower(): h for h in [*closed, *LEGACY_HEADINGS]}
    out: dict = {"today": date.today().isoformat()}
    plan = root / PLAN
    if not plan.is_file():
        out["headings_present"] = []
        return out
    text = plan.read_text(encoding="utf-8")
    head = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if head:
        for key in ("framework_version", "last_raised", "next_raise"):
            m = re.search(rf"^{key}:\s*[\"']?([^\"'\n]*?)[\"']?\s*$", head.group(1), re.M)
            if not m:
                continue
            val = m.group(1).strip()
            ok = DATE_RE.match(val) if key != "framework_version" else re.match(r"^\d+\.\d+$", val)
            if ok:
                out[key] = val
    present = []
    for line in text.splitlines():
        m = re.match(r"^## (?!#)(.+?)\s*$", line)
        if m and m.group(1).lower() in allowed:
            h = allowed[m.group(1).lower()]
            if h not in present:
                present.append(h)
    out["headings_present"] = present
    out.update(counts(root))
    return out


def load_beside(name: str):
    """A script beside this one, loaded by path (the pack ships them together)."""
    import importlib.util
    path = Path(__file__).resolve().parent / name
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name.replace("-", "_").replace(".py", ""), path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def counts(root: Path) -> dict:
    """The whole numbers the brain may take (ADR-136 Rule 5), from the session
    brief's readers beside this script. An install without the brief sends
    none, and the brain's older rules still answer."""
    try:
        brief = load_beside("oac-session-brief.py")
        if brief is None:
            return {}
        out = brief.plan_counts(root, brief.handle(root))
    except Exception:
        return {}
    return {k: int(v) for k, v in out.items() if isinstance(v, int) and 0 <= v <= 9999}


def next_step(root: Path, show: bool, brain: Brain = Brain()) -> tuple[str, int]:
    p = (brain.progress or progress)(root)
    if show:
        return "would send: " + json.dumps(p, sort_keys=True), 0
    try:
        base, key = settings(root, brain)
        res = _request(f"{base}/v1/next", key, data=json.dumps(p).encode(),
                       headers={"Content-Type": "application/json", "Accept": "application/json"})
        n = json.loads(res.read())
    except (Unreachable, ValueError) as why:
        return f"the brain was unreachable ({why}); work out the next step from the saved framework", 0
    lines = [f"next: {n.get('move')} ({n.get('reason')})"]
    if n.get("upgrade"):
        u = n["upgrade"]
        lines.append(f"newer framework: {u.get('from')} -> {u.get('to')}")
    sec = n.get("section") or {}
    if sec.get("text"):
        lines += ["", sec["text"]]
    return "\n".join(lines), 0


# ── The key, and the brain's tools inside Claude Code ────────────────────────

def headers(root: Path, brain: Brain = Brain()) -> int:
    """What Claude Code runs each time it connects: `headersHelper` in .mcp.json.

    Claude Code takes every variable named like a credential out of a project
    helper's environment, so the key is read from `.env`, never the shell.
    Prints one JSON object and nothing else. With no key it prints nothing and
    exits 1, so the connection fails with a reason, not as a request with no key."""
    key = load_env(root, brain).get(KEY_ENV, "").strip()
    if not key:
        print(f"{brain.server}: no install key ({KEY_ENV}) in .env", file=sys.stderr)
        return 1
    print(json.dumps({"Authorization": f"Bearer {key}"}))
    return 0


def check_key(base: str, key: str) -> Unreachable | None:
    """None if the brain accepts the key, otherwise why it could not be used."""
    try:
        _request(f"{base}/v1/versions", key, headers={"Accept": "application/json"}).read()
    except Unreachable as why:
        return why
    return None


def refused(why: Unreachable | None) -> bool:
    return why is not None and why.status in (401, 403)


def save_key(root: Path, key: str) -> None:
    """The key into `.env`, replacing an old one and keeping every other line."""
    p = root / ENV
    lines = p.read_text(encoding="utf-8").splitlines() if p.is_file() else []
    out: list[str] = []
    for line in lines:
        bare = line.strip()
        if bare.startswith("export "):
            bare = bare[len("export "):].lstrip()
        if not bare.startswith(f"{KEY_ENV}="):
            out.append(line)
    out.append(f"{KEY_ENV}={key}")
    write_atomic(p, ("\n".join(out) + "\n").encode("utf-8"))


def ensure_ignored(root: Path) -> bool:
    """Make sure git never saves `.env`. True if a line had to be added."""
    gi = root / ".gitignore"
    have = gi.read_text(encoding="utf-8") if gi.is_file() else ""
    if any(ln.strip() in (".env", "/.env", ".env*") for ln in have.splitlines()):
        return False
    gi.write_text(have + ("" if have.endswith("\n") or not have else "\n") + ".env\n", encoding="utf-8")
    return True


def write_mcp(root: Path, base: str, brain: Brain = Brain()) -> str:
    """Add the brain to `.mcp.json`, keeping any other server in it.

    The file holds the address and the helper, never the key, so it is safe to
    save to GitHub. Returns 'added', 'updated' or 'unchanged'."""
    p = root / MCP_JSON
    want = {"type": "http", "url": f"{base}/mcp", "headersHelper": brain.helper}
    data: dict = {}
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            raise ValueError(f"{MCP_JSON} is not valid JSON, so it was left alone") from None
        if not isinstance(data, dict) or not isinstance(data.get("mcpServers", {}), dict):
            raise ValueError(f"{MCP_JSON} has no mcpServers object, so it was left alone")
    servers = data.setdefault("mcpServers", {})
    if servers.get(brain.server) == want:
        return "unchanged"
    was = brain.server in servers
    servers[brain.server] = want
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return "updated" if was else "added"


def connect(root: Path, brain: Brain = Brain()) -> tuple[str, int]:
    """Write `.mcp.json` for the key already in `.env`, once the brain accepts it."""
    try:
        base, key = settings(root, brain)
    except Unreachable as why:
        return (f"not connected: {why}. A key is saved with `python3 scripts/{brain.script} key` "
                "in a plain terminal, never this chat."), 1
    why = check_key(base, key)
    if refused(why):
        return f"not connected: {why}, so the key in .env is not one the brain knows. Ask OpsCode for a new one.", 1
    try:
        done = write_mcp(root, base, brain)
    except ValueError as e:
        return f"not connected: {e}", 1
    msg = f"{brain.server} {done} in {MCP_JSON}"
    if why:
        msg += f" (the key was not checked: {why})"
    if done != "unchanged":
        msg += ". Claude Code connects it after a restart; save the file with /commit"
    return msg, 0


def key_cmd(root: Path, brain: Brain = Brain()) -> int:
    """In a plain terminal, never the chat: check the key, save it, connect."""
    if sys.stdin.isatty():
        print("Paste this install's key. It starts with sacb_, and it won't show as you paste.")
        raw = getpass.getpass("Key: ")
    else:
        raw = sys.stdin.readline()
    key = raw.strip()
    if not KEY_RE.match(key):
        print("That doesn't look like an OpsCode key. It starts with sacb_ and is 48 characters long. "
              "Nothing was saved.")
        return 2
    base = load_env(root, brain).get(brain.url_env, brain.default_url).rstrip("/")
    why = check_key(base, key)
    if refused(why):
        print("OpsCode's brain doesn't know this key. Check you copied all of it, or ask OpsCode "
              "for a new one. Nothing was saved.")
        return 1
    save_key(root, key)
    out = ["Saved. Your key is in .env, which stays on this computer and never goes to GitHub."]
    if ensure_ignored(root):
        out.append("I also told git never to save .env.")
    if why:
        out.append(f"It couldn't be checked just now ({why}). /{brain.name} checks it again next time.")
    try:
        write_mcp(root, base, brain)
        out.append(f"Restart Claude Code. If it asks whether to use '{brain.server}', say yes.")
    except ValueError as e:
        out.append(f"Claude Code isn't connected to it yet: {e}. Ask OpsCode to help.")
    print("\n".join(out))
    return 0


def main(argv: list[str] | None = None, brain: Brain = Brain()) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="the repo (default: here)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="bring the newest framework down, or keep the saved one")
    f.add_argument("--version", help="a specific version, e.g. 0.4")
    sub.add_parser("version", help="print the saved framework's version")
    s = sub.add_parser("section", help="print one section of the saved framework, by id or name (start, done, help)")
    s.add_argument("name", help="a section name or id, e.g. start, done, help, check, step-4")
    n = sub.add_parser("next", help="ask the brain where to go next")
    n.add_argument("--show", action="store_true", help="print what would be sent, and send nothing")
    k = sub.add_parser("key", help="save this install's key, then connect (in a plain terminal, never the chat)")
    c = sub.add_parser("connect", help="write .mcp.json for the key already in .env")
    h = sub.add_parser("headers", help="what Claude Code runs to connect; prints the key, so never by hand")
    # --root may come after the subcommand too
    for p in (f, s, n, k, c, h):
        p.add_argument("--root", dest="root_sub", default=None, help=argparse.SUPPRESS)
    sub.choices["version"].add_argument("--root", dest="root_sub", default=None, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    root = Path(args.root_sub or args.root).resolve()

    if args.cmd == "headers":
        return headers(root, brain)
    if args.cmd == "key":
        return key_cmd(root, brain)
    if args.cmd == "connect":
        msg, rc = connect(root, brain)
    elif args.cmd == "fetch":
        if args.version and not re.match(r"^\d+\.\d+$", args.version):
            print("--version takes a version like 0.4", file=sys.stderr)
            return 2
        msg, rc = fetch(root, args.version, brain)
    elif args.cmd == "version":
        _, v = saved(root, brain)
        msg, rc = (f"framework {v}", 0) if v else (f"no saved framework at {brain.cache}", 1)
    elif args.cmd == "section":
        msg, rc = section(root, args.name, brain)
        if rc:
            print(msg, file=sys.stderr)
            return rc
    else:
        msg, rc = next_step(root, args.show, brain)
    print(msg)
    return rc


if __name__ == "__main__":
    sys.exit(main())
