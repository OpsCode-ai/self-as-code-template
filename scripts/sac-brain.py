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
    python3 scripts/sac-brain.py next               # where to go next, from the brain
    python3 scripts/sac-brain.py next --show        # what `next` would send, sending nothing

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

    SAC_BRAIN_KEY   this install's key, from OpsCode
    SAC_BRAIN_URL   default https://brain.opscode.ai/sac

Answers stay home. `next` sends which plan headings exist and the review dates
from the frontmatter, never a word of what is under them. `--show` prints the
exact object first.

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
from datetime import date
from pathlib import Path

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


class Unreachable(Exception):
    """Any reason the brain could not be used: offline, no key, refused, bad body.

    `status` is the brain's HTTP answer when it gave one, so a refused key
    (401, 403) can be told apart from no connection."""

    def __init__(self, why: str, status: int | None = None) -> None:
        super().__init__(why)
        self.status = status


def load_env(root: Path) -> dict[str, str]:
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
    for k in ("SAC_BRAIN_KEY", "SAC_BRAIN_URL"):
        if os.environ.get(k):
            found[k] = os.environ[k]
    return found


def version_of(text: str) -> str | None:
    head = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    m = VERSION_RE.search(head.group(1)) if head else None
    return m.group(1) if m else None


def saved(root: Path) -> tuple[bytes | None, str | None]:
    p = root / CACHE
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


def settings(root: Path) -> tuple[str, str]:
    env = load_env(root)
    key = env.get("SAC_BRAIN_KEY", "").strip()
    if not key:
        raise Unreachable("no install key (SAC_BRAIN_KEY)")
    return env.get("SAC_BRAIN_URL", DEFAULT_URL).rstrip("/"), key


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


def fetch(root: Path, version: str | None) -> tuple[str, int]:
    have, have_v = saved(root)
    try:
        base, key = settings(root)
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
        want_v = res.headers.get("SAC-Framework-Version")
        want_sha = res.headers.get("SAC-Framework-SHA256")
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
            return (f"the brain was unreachable ({why}) and there is no saved framework at {CACHE}. "
                    "Say so in one line and stop; do not run the method from memory."), 1
        return f"the brain was unreachable ({why}); using the saved framework {have_v}", 0

    if have == body:
        return f"framework {got_v} from the brain (unchanged)", 0
    write_atomic(root / CACHE, body)
    was = f"was {have_v}" if have is not None else "new"
    return f"framework {got_v} from the brain ({was})", 0


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


def counts(root: Path) -> dict:
    """The whole numbers the brain may take (ADR-136 Rule 5), from the session
    brief's readers beside this script. An install without the brief sends
    none, and the brain's older rules still answer."""
    brief_path = Path(__file__).resolve().parent / "oac-session-brief.py"
    if not brief_path.is_file():
        return {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("oac_session_brief", brief_path)
        brief = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(brief)
        out = brief.plan_counts(root, brief.handle(root))
    except Exception:
        return {}
    return {k: int(v) for k, v in out.items() if isinstance(v, int) and 0 <= v <= 9999}


def next_step(root: Path, show: bool) -> tuple[str, int]:
    p = progress(root)
    if show:
        return "would send: " + json.dumps(p, sort_keys=True), 0
    try:
        base, key = settings(root)
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

def headers(root: Path) -> int:
    """What Claude Code runs each time it connects: `headersHelper` in .mcp.json.

    Claude Code takes every variable named like a credential out of a project
    helper's environment, so the key is read from `.env`, never the shell.
    Prints one JSON object and nothing else. With no key it prints nothing and
    exits 1, so the connection fails with a reason, not as a request with no key."""
    key = load_env(root).get("SAC_BRAIN_KEY", "").strip()
    if not key:
        print("sac-brain: no install key (SAC_BRAIN_KEY) in .env", file=sys.stderr)
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
        if not bare.startswith("SAC_BRAIN_KEY="):
            out.append(line)
    out.append(f"SAC_BRAIN_KEY={key}")
    write_atomic(p, ("\n".join(out) + "\n").encode("utf-8"))


def ensure_ignored(root: Path) -> bool:
    """Make sure git never saves `.env`. True if a line had to be added."""
    gi = root / ".gitignore"
    have = gi.read_text(encoding="utf-8") if gi.is_file() else ""
    if any(ln.strip() in (".env", "/.env", ".env*") for ln in have.splitlines()):
        return False
    gi.write_text(have + ("" if have.endswith("\n") or not have else "\n") + ".env\n", encoding="utf-8")
    return True


def write_mcp(root: Path, base: str) -> str:
    """Add the brain to `.mcp.json`, keeping any other server in it.

    The file holds the address and the helper, never the key, so it is safe to
    save to GitHub. Returns 'added', 'updated' or 'unchanged'."""
    p = root / MCP_JSON
    want = {"type": "http", "url": f"{base}/mcp", "headersHelper": HEADERS_HELPER}
    data: dict = {}
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            raise ValueError(f"{MCP_JSON} is not valid JSON, so it was left alone") from None
        if not isinstance(data, dict) or not isinstance(data.get("mcpServers", {}), dict):
            raise ValueError(f"{MCP_JSON} has no mcpServers object, so it was left alone")
    servers = data.setdefault("mcpServers", {})
    if servers.get(SERVER) == want:
        return "unchanged"
    was = SERVER in servers
    servers[SERVER] = want
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return "updated" if was else "added"


def connect(root: Path) -> tuple[str, int]:
    """Write `.mcp.json` for the key already in `.env`, once the brain accepts it."""
    try:
        base, key = settings(root)
    except Unreachable as why:
        return (f"not connected: {why}. A key is saved with `python3 scripts/sac-brain.py key` "
                "in a plain terminal, never this chat."), 1
    why = check_key(base, key)
    if refused(why):
        return f"not connected: {why}, so the key in .env is not one the brain knows. Ask OpsCode for a new one.", 1
    try:
        done = write_mcp(root, base)
    except ValueError as e:
        return f"not connected: {e}", 1
    msg = f"sac-brain {done} in {MCP_JSON}"
    if why:
        msg += f" (the key was not checked: {why})"
    if done != "unchanged":
        msg += ". Claude Code connects it after a restart; save the file with /commit"
    return msg, 0


def key_cmd(root: Path) -> int:
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
    base = load_env(root).get("SAC_BRAIN_URL", DEFAULT_URL).rstrip("/")
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
        out.append(f"It couldn't be checked just now ({why}). /sac checks it again next time.")
    try:
        write_mcp(root, base)
        out.append("Restart Claude Code. If it asks whether to use 'sac-brain', say yes.")
    except ValueError as e:
        out.append(f"Claude Code isn't connected to it yet: {e}. Ask OpsCode to help.")
    print("\n".join(out))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="the private repo (default: here)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="bring the newest framework down, or keep the saved one")
    f.add_argument("--version", help="a specific version, e.g. 0.4")
    sub.add_parser("version", help="print the saved framework's version")
    n = sub.add_parser("next", help="ask the brain where to go next")
    n.add_argument("--show", action="store_true", help="print what would be sent, and send nothing")
    k = sub.add_parser("key", help="save this install's key, then connect (in a plain terminal, never the chat)")
    c = sub.add_parser("connect", help="write .mcp.json for the key already in .env")
    h = sub.add_parser("headers", help="what Claude Code runs to connect; prints the key, so never by hand")
    # --root may come after the subcommand too
    for p in (f, n, k, c, h):
        p.add_argument("--root", dest="root_sub", default=None, help=argparse.SUPPRESS)
    sub.choices["version"].add_argument("--root", dest="root_sub", default=None, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    root = Path(args.root_sub or args.root).resolve()

    if args.cmd == "headers":
        return headers(root)
    if args.cmd == "key":
        return key_cmd(root)
    if args.cmd == "connect":
        msg, rc = connect(root)
    elif args.cmd == "fetch":
        if args.version and not re.match(r"^\d+\.\d+$", args.version):
            print("--version takes a version like 0.4", file=sys.stderr)
            return 2
        msg, rc = fetch(root, args.version)
    elif args.cmd == "version":
        _, v = saved(root)
        msg, rc = (f"framework {v}", 0) if v else (f"no saved framework at {CACHE}", 1)
    else:
        msg, rc = next_step(root, args.show)
    print(msg)
    return rc


if __name__ == "__main__":
    sys.exit(main())
