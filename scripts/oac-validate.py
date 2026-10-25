#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 OpsCode
"""Report which OaC conformance level a repository sits at (ADR-098).

This reports a LEVEL. It does not pass or fail a repository.

That is the whole design. The measured baseline here is 32% typed across
2,000 documents, so a pass/fail gate would say 'fail' to every real
operation on day one and teach people to switch it off. A level says what
a consumer can offer you today, and what tidying up would buy you.

    0 readable  markdown in git, frontmatter parses
    1 typed     title, type and audience present and legal
    2 linked    declared edges resolve, big directories carry index.md
    3 live      execution conventions (the paid engine surface)

THE ROBUSTNESS RULE
-------------------
Per the spec section 2.1, a consumer MUST NOT refuse a repository. This
script holds itself to that: unreadable file, unparseable YAML, unknown
type, unknown oac_version, none of them stop the run. They lower a level
and get counted.

There is a distinction worth being precise about, because it looks like a
contradiction. The robustness rule forbids a consumer from REFUSING SERVICE
over an unknown type. It does not forbid a conformance report from saying
that an unknown type falls short of level 1. Refusing is 'I will not open
your repo'. Reporting is 'you are at level 0, here is why'. This does the
second and never the first.

ONE DEFINITION
--------------
Every legal value is read from specs/oac-vocabulary.yml. Nothing is
hardcoded here. If this script disagreed with the vocabulary there would be
two definitions again, which is the problem ADR-098 exists to end.

USAGE
  python3 code/scripts/oac-validate.py               # report on this repo
  python3 code/scripts/oac-validate.py PATH          # report on another repo
  python3 code/scripts/oac-validate.py --staged      # pre-commit gate
  python3 code/scripts/oac-validate.py --changed     # only uncommitted work
  python3 code/scripts/oac-validate.py --since main  # only what a branch adds
  python3 code/scripts/oac-validate.py --details     # list the findings
  python3 code/scripts/oac-validate.py --json        # machine readable

EXIT CODES
  0  always, when enforcement is advisory (the manifest default)
  1  when enforcement is 'blocking' and the scanned files miss the target
     level set in .oac/manifest.yml; or, under --staged, when the commit
     adds a document below level 1 or breaks one that was clean
  2  the repo could not be read at all (no markdown, bad path)
"""

# Annotations stay strings, so `str | None` parses on Python 3.9.
# The stock macOS python3 is 3.9 and the pre-commit hook calls bare
# `python3`, so without this the validator crashes before it checks
# anything and blocks every commit on that machine. Same defect and same
# fix as check-nul-bytes.py in #83.
from __future__ import annotations

import argparse
import datetime
import json
import os
import fnmatch
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    print("oac-validate: needs PyYAML  (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

# A directory holding more than this many documents should carry an index.md.
# Overridable with validate.index_threshold in the manifest.
DEFAULT_INDEX_THRESHOLD = 10

# `.claude/skills/` and `.claude/agents/` sit here for the same reason as
# `.claude/commands/`: their frontmatter is a contract with the Claude Code
# loader (`name`, `description`), not with this format. See the spec, 6.4,
# third kind: another tool's schema.
DEFAULT_EXEMPT = ["use-cases/", ".claude/commands/", ".claude/skills/",
                  ".claude/agents/", "aidlc/", "node_modules/"]

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\s*?(?:\r?\n|\Z)", re.S)
TASK_RE = re.compile(r"^[ \t]*[-*+][ \t]+\[([ xX])\]", re.M)
DEVIATION_RE = re.compile(r"^[ \t]*>[ \t]*deviation \([^,]+, \d{4}-\d{2}-\d{2}\):", re.M | re.I)
FENCE_RE = re.compile(r"^[ \t]*(```|~~~).*?^[ \t]*\1", re.S | re.M)


# ── loading the definition ───────────────────────────────────────────────────

def find_vocabulary(root: Path, override: str | None) -> Path | None:
    """Locate the vocabulary. The repo's own copy wins, then the one shipped
    beside this script, which is what a distributed pack carries."""
    if override:
        p = Path(override)
        return p if p.exists() else None
    for candidate in (
        root / "specs" / "oac-vocabulary.yml",
        root / ".oac" / "oac-vocabulary.yml",
        Path(__file__).resolve().parent.parent.parent / "specs" / "oac-vocabulary.yml",
        Path(__file__).resolve().parent / "oac-vocabulary.yml",
    ):
        if candidate.exists():
            return candidate
    return None


def path_is_exempt(rel: str, patterns: list[str]) -> bool:
    """Match an exempt entry against a path.

    Entries may be plain prefixes (`use-cases/`) or globs (`sites/*/public/`).
    A plain `startswith` silently never matches a glob, which made three
    exemptions in the manifest decorative rather than real. `*` spans `/`
    here, which is what you want for a directory pattern.
    """
    for p in patterns:
        p = p.rstrip("/")
        if rel == p or rel.startswith(p + "/"):
            return True
        if fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(rel, p + "/*"):
            return True
    return False


def load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}
    except Exception:
        return {}


def load_manifest(root: Path) -> dict:
    manifest = root / ".oac" / "manifest.yml"
    return load_yaml(manifest) if manifest.exists() else {}


def exempt_paths(manifest: dict) -> list[str]:
    out = []
    for entry in manifest.get("exempt") or []:
        if isinstance(entry, dict) and entry.get("path"):
            out.append(str(entry["path"]))
        elif isinstance(entry, str):
            out.append(entry)
    return out or DEFAULT_EXEMPT


# ── the corpus ───────────────────────────────────────────────────────────────

def git_files(root: Path, args) -> list[str] | None:
    def run(cmd):
        # -z throughout: git quotes paths with spaces or non-ASCII otherwise,
        # and a quoted path silently fails to open.
        r = subprocess.run(cmd + ["-z"], cwd=root, capture_output=True, text=True)
        return [f for f in r.stdout.split("\0") if f] if r.returncode == 0 else None

    if args.since:
        return run(["git", "diff", "--name-only", f"{args.since}...HEAD"])
    if args.changed:
        tracked = run(["git", "diff", "--name-only", "HEAD"]) or []
        staged = run(["git", "diff", "--name-only", "--cached"]) or []
        untracked = run(["git", "ls-files", "--others", "--exclude-standard"]) or []
        return sorted(set(tracked) | set(staged) | set(untracked))
    # Tracked AND untracked-but-not-ignored. A freshly unpacked Context Core
    # has nothing committed yet, and `/install` still has to report a level on
    # first open. Ignored files stay out via --exclude-standard.
    tracked = run(["git", "ls-files", "*.md"])
    if tracked is None:
        return None
    untracked = run(["git", "ls-files", "--others", "--exclude-standard", "*.md"]) or []
    return sorted(set(tracked) | set(untracked))


def collect(root: Path, exempt: list[str], args) -> list[str]:
    files = git_files(root, args)
    if files is None:  # not a git repo, or git unavailable
        files = [
            str(p.relative_to(root))
            for p in root.rglob("*.md")
            if not any(part in {".git", "node_modules"} for part in p.parts)
        ]
    out = []
    for rel in files:
        if not rel.endswith(".md"):
            continue
        if path_is_exempt(rel, exempt):
            continue
        if (root / rel).is_file():
            out.append(rel)
    return sorted(out)


class Document:
    """One markdown file. Never raises: a file it cannot read becomes a
    document with no frontmatter and a recorded reason.

    `text` lets a caller supply content that is not on disk, which the
    pre-commit gate needs: it must judge the STAGED blob, not the working
    tree, or a file edited after `git add` would be checked in the wrong
    version.
    """

    def __init__(self, root: Path, rel: str, text: str | None = None):
        self.rel = rel
        self.meta: dict = {}
        self.raw_frontmatter = ""
        self.has_frontmatter = False
        self.frontmatter_broken = False
        self.unreadable = False
        self.body = ""

        if text is None:
            try:
                text = (root / rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                self.unreadable = True
                return

        m = FRONTMATTER_RE.match(text)
        self.body = text[m.end():] if m else text
        if not m:
            return
        self.has_frontmatter = True
        # The RAW frontmatter, kept because some rules are about how a value is
        # written rather than what it parses to. Flow style is the case: PyYAML
        # reads a block list perfectly, so the parsed value cannot show the
        # defect. See block_list_fields.
        self.raw_frontmatter = m.group(1)
        try:
            data = yaml.safe_load(m.group(1))
        except Exception:
            self.frontmatter_broken = True
            return
        if isinstance(data, dict):
            self.meta = data
        elif data is not None:
            self.frontmatter_broken = True

    def get(self, key):
        return self.meta.get(key)


_BLOCK_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):[ \t]*(?:#.*)?$")
_BLOCK_ITEM_RE = re.compile(r"^[ \t]+-[ \t]*(.*)$")
_SCALAR_TYPES = (str, int, float, bool, datetime.date, datetime.datetime)


def block_list_fields(raw: str, meta: dict) -> dict:
    """Keys written as a block list of SCALARS, with their span in `raw`.

    Format 3.3 requires flow style, and gives the reason: a simple reader
    splits on the first colon and keeps the scalar. Under block style it sees
    an empty value and the data silently disappears. This validator reads with
    PyYAML, which parses block lists perfectly, so `as_list` below accepts them
    and the parsed value can never reveal the defect. Only the raw text can.

    **Scalars only, deliberately.** A block list of MAPPINGS (`change_log`,
    `promotions`, `sessions`) is a structure 3.3 does not contemplate. Flow
    style cannot rescue it for a simple reader either, since what that reader
    would capture is an unusable `[{date: ..., note: ...}]` string, and forcing
    it produces a line nobody can read or diff. Those are left alone rather
    than reported as violations nobody should fix.

    Returns {key: (start, end)} where the span covers the key line and every
    item line, so a fixer can replace exactly that and nothing else.
    """
    found: dict = {}
    pos = 0
    pending_key = None
    key_start = item_end = 0

    for line in raw.splitlines(keepends=True):
        line_start, pos = pos, pos + len(line)
        stripped = line.rstrip("\n")

        item = _BLOCK_ITEM_RE.match(stripped)
        if pending_key and item:
            item_end = line_start + len(stripped)
            continue

        if pending_key and item_end:
            value = meta.get(pending_key)
            if isinstance(value, list) and value and all(
                v is None or isinstance(v, _SCALAR_TYPES) for v in value
            ):
                found[pending_key] = (key_start, item_end)
            pending_key, item_end = None, 0

        m = _BLOCK_KEY_RE.match(stripped)
        if m and stripped == stripped.lstrip():
            pending_key, key_start, item_end = m.group(1), line_start, 0
        elif stripped and stripped == stripped.lstrip():
            pending_key, item_end = None, 0

    if pending_key and item_end:
        value = meta.get(pending_key)
        if isinstance(value, list) and value and all(
            v is None or isinstance(v, _SCALAR_TYPES) for v in value
        ):
            found[pending_key] = (key_start, item_end)
    return found


def as_list(value) -> list[str]:
    """Frontmatter values that may be a scalar, a flow list or a block list.

    Block style is tolerated HERE on purpose: this function answers 'what does
    the document say', and a block list does say it. Whether it was written in a
    shape the reference client can read is a separate question, asked once by
    `block_list_fields` rather than by every consumer.
    """
    if value is None:
        return []
    if isinstance(value, str):
        v = value.strip()
        if v.startswith("[") and v.endswith("]"):
            v = v[1:-1]
            return [x.strip().strip("\"'") for x in v.split(",") if x.strip()]
        return [v] if v else []
    if isinstance(value, (list, tuple)):
        return [str(x).strip().strip("\"'") for x in value if str(x).strip()]
    return [str(value)]


def norm(value) -> str:
    return str(value).strip().strip("\"'").lower() if value is not None else ""


# ── the levels ───────────────────────────────────────────────────────────────

class Report:
    def __init__(self):
        self.findings: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.counts: Counter = Counter()
        self.stats: dict = {}

    def add(self, level: str, rel: str, why: str):
        self.findings[level].append((rel, why))
        self.counts[level] += 1


def check_level_0(docs: list[Document], rep: Report):
    for d in docs:
        if d.unreadable:
            rep.add("0", d.rel, "file could not be read")
        elif d.frontmatter_broken:
            rep.add("0", d.rel, "frontmatter is present but does not parse as YAML")
    rep.stats["documents"] = len(docs)


def check_level_1(docs: list[Document], vocab: dict, manifest: dict, rep: Report):
    required = vocab.get("required") or ["title", "type", "audience"]
    types = set(vocab.get("types") or {})
    types |= set(manifest.get("types") or {})
    type_aliases = {norm(k): v for k, v in (vocab.get("type_aliases") or {}).items()}
    manual = {norm(x) for x in (vocab.get("type_manual_review") or [])}
    audiences = set(vocab.get("audience") or {})
    aud_aliases = {norm(k): v for k, v in (vocab.get("audience_value_aliases") or {}).items()}

    ok = 0
    fixable = Counter()

    for d in docs:
        problems = []
        for field in required:
            if not d.get(field):
                problems.append(f"no `{field}`")

        t = norm(d.get("type"))
        if t and t not in types:
            if t in type_aliases:
                problems.append(f"type `{t}` is a legacy alias of `{type_aliases[t]}`")
                fixable["type alias"] += 1
            elif t in manual:
                problems.append(f"type `{t}` needs a human, it has no safe mapping")
            else:
                problems.append(f"type `{t}` is not in the vocabulary")

        a = norm(d.get("audience"))
        if a and a not in audiences:
            if a in aud_aliases:
                problems.append(f"audience `{a}` is a legacy spelling of `{aud_aliases[a]}`")
                fixable["audience alias"] += 1
            else:
                problems.append(f"audience `{a}` is not in the vocabulary")

        blocks = block_list_fields(d.raw_frontmatter, d.meta)
        if blocks:
            names = ", ".join(f"`{k}`" for k in sorted(blocks))
            problems.append(f"{names} written as a block list; 3.3 requires flow "
                            f"style, or a simple reader loses the value")
            fixable["block list"] += len(blocks)

        if problems:
            rep.add("1", d.rel, "; ".join(problems))
        else:
            ok += 1

    rep.stats["level_1_ok"] = ok
    rep.stats["level_1_coverage"] = pct(ok, len(docs))
    rep.stats["mechanically_fixable"] = dict(fixable)


def check_level_2(root: Path, docs: list[Document], vocab: dict, manifest: dict, rep: Report, whole_repo: bool):
    edge_keys = list(vocab.get("edges") or {})
    threshold = (manifest.get("validate") or {}).get("index_threshold", DEFAULT_INDEX_THRESHOLD)

    total_edges = resolved = 0
    for d in docs:
        base = (root / d.rel).parent
        for key in edge_keys:
            for target in as_list(d.get(key)):
                if not target or target.lower().startswith(("http://", "https://", "mailto:")):
                    continue
                if target.lower() in {"null", "none", "~"}:
                    continue
                total_edges += 1
                path = target.split("#", 1)[0]
                if not path or (base / path).exists():
                    resolved += 1
                else:
                    rep.add("2", d.rel, f"`{key}: {target}` does not resolve")

    # index.md in directories that have grown past the threshold. Repo-wide
    # only: counting a directory's documents from a handful of changed files
    # would say 'small directory' about a directory of sixty.
    if not whole_repo:
        rep.stats["dirs_needing_index"] = None
        rep.stats["dirs_missing_index"] = None
        return

    per_dir: Counter = Counter()
    for d in docs:
        per_dir[os.path.dirname(d.rel)] += 1
    missing_index = 0
    dirs_needing = 0
    for directory, n in sorted(per_dir.items()):
        if n <= threshold:
            continue
        dirs_needing += 1
        if not (root / directory / "index.md").exists():
            missing_index += 1
            rep.add("2", directory or ".", f"{n} documents and no index.md")

    # Titles must identify. Two documents sharing one title is not a cosmetic
    # problem: an index lists them identically, a reference to "the pricing doc"
    # has two answers, and an agent asked to open one opens a coin flip. Level 2
    # is where this belongs, because its promise is the relation graph and
    # progressive disclosure, and both are what a duplicate breaks. Level 1 only
    # promises the three fields exist with legal values, which duplicates satisfy.
    #
    # Repo-wide only, for the same reason as the index check above: a duplicate
    # cannot be seen from a subset of changed files, and reporting "unique" after
    # looking at two files would be worse than not looking.
    by_title: dict[str, list[str]] = {}
    for d in docs:
        title = (d.get("title") or "").strip()
        if title:
            by_title.setdefault(title, []).append(d.rel)
    duplicate_titles = 0
    for title, rels in sorted(by_title.items()):
        if len(rels) > 1:
            duplicate_titles += 1
            shown = ", ".join(sorted(rels)[:4])
            more = f" and {len(rels) - 4} more" if len(rels) > 4 else ""
            rep.add("2", sorted(rels)[0],
                    f"title `{title}` is used by {len(rels)} documents: {shown}{more}")

    rep.stats["edges"] = total_edges
    rep.stats["edges_resolved"] = resolved
    rep.stats["edge_coverage"] = pct(resolved, total_edges)
    rep.stats["dirs_needing_index"] = dirs_needing
    rep.stats["dirs_missing_index"] = missing_index
    rep.stats["duplicate_titles"] = duplicate_titles
    rep.stats["unique_titles"] = len(by_title)


def check_level_3(docs: list[Document], manifest: dict, rep: Report, whole_repo: bool):
    """The thinnest check here, on purpose.

    Level 3 is behavioural: boards, runs, people editing together. A static
    scan cannot see that. What it can check is that a repo claiming the
    `live` profile actually carries the grammar the engine reads, and that
    the deviation blockquotes parse. The paid engine is the real consumer.
    """
    profiles = [norm(p) for p in as_list(manifest.get("profiles"))]
    if "live" not in profiles:
        # Whether a repo uses the live profile is a property of the repo, not
        # of the files a commit happens to touch.
        if whole_repo:
            rep.add("3", ".oac/manifest.yml", "the `live` profile is not declared")
        rep.stats["task_items"] = 0
        return

    items = 0
    for d in docs:
        body = FENCE_RE.sub("", d.body)
        found = len(TASK_RE.findall(body))
        items += found
        if d.get("sprint") and not found:
            rep.add("3", d.rel, "declares `sprint` but carries no task items")
        for m in re.finditer(r"^[ \t]*>[ \t]*deviation\b.*$", body, re.M | re.I):
            if not DEVIATION_RE.match(m.group(0)):
                rep.add("3", d.rel, "a deviation note does not match `> deviation (author, YYYY-MM-DD):`")

    if items == 0 and whole_repo:
        rep.add("3", ".", "the `live` profile is declared but no task items were found")
    rep.stats["task_items"] = items


def pct(n: int, total: int) -> float:
    return round(100.0 * n / total, 1) if total else 100.0


# ── reporting ────────────────────────────────────────────────────────────────

def achieved_level(rep: Report) -> int:
    """The highest level with nothing outstanding beneath it.

    Strict on purpose: one untyped document holds the whole repo at 0. The
    coverage figures alongside are what show progress, so the level stays
    honest without being useless.
    """
    level = 0
    for n in (0, 1, 2, 3):
        if rep.counts[str(n)]:
            return level
        level = n
    return 3


def level_1_problems(doc: Document, vocab: dict, manifest: dict) -> list[str]:
    """The level 1 findings for one document, or [] if it is clean.

    Unparseable frontmatter is reported as itself. Otherwise it surfaces as
    'no title; no type; no audience', because nothing could be read, and
    that sends a person hunting for three missing fields that are sitting
    right there above a YAML error.
    """
    if doc.frontmatter_broken:
        return ["frontmatter does not parse as YAML "
                "(often an unquoted value containing ': ')"]
    rep = Report()
    check_level_1([doc], vocab, manifest, rep)
    return [why for _, why in rep.findings["1"]]


def staged_gate(root: Path, vocab: dict, manifest: dict, exempt: list[str]) -> int:
    """Pre-commit gate. Judges the staged blob against the committed one.

    The rule is 'do not make it worse', not 'everything must be perfect'.
    There are still documents that predate the standard, and blocking a
    commit because you edited one of them for an unrelated reason is how a
    gate teaches people to reach for --no-verify.

      new file, fails       -> BLOCK. No excuse for new work.
      was clean, now fails  -> BLOCK. That is a regression.
      was failing already   -> warn. Pre-existing debt, not this commit's.
    """
    def git(*args):
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None

    raw = git("diff", "--cached", "--name-only", "--diff-filter=ACM", "-z")
    if raw is None:
        return 0
    files = [f for f in raw.split("\0")
             if f.endswith(".md")
             and not path_is_exempt(f, exempt)]
    if not files:
        return 0

    blocking, warnings = [], []
    for rel in files:
        staged = git("show", f":{rel}")
        if staged is None:
            continue
        problems = level_1_problems(Document(root, rel, staged), vocab, manifest)
        if not problems:
            continue
        head = git("show", f"HEAD:{rel}")
        was_clean = head is None or not level_1_problems(Document(root, rel, head), vocab, manifest)
        (blocking if was_clean else warnings).append(
            (rel, "; ".join(problems), "new file" if head is None else "was clean")
        )

    for rel, why, _ in warnings:
        print(f"  \033[1;33m~\033[0m {rel}\n      {why}")
    if warnings:
        print(f"  \033[1;33m{len(warnings)} pre-existing, not blocked\033[0m\n")

    if not blocking:
        print("  \033[0;32m✓ Frontmatter conforms (OaC level 1)\033[0m")
        return 0

    print("\n\033[0;31m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
    print("\033[0;31m❌ BLOCKED: frontmatter below OaC level 1\033[0m")
    print("\033[0;31m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n")
    for rel, why, reason in blocking:
        print(f"  {rel}  ({reason})")
        print(f"      {why}\n")
    print("Every document needs three fields:\n")
    print("  ---")
    print('  title: "What this is called"')
    print("  type: guide          # 26 values, see specs/oac-vocabulary.yml")
    print("  audience: internal   # owner | internal | team | public")
    print("  ---\n")
    print("`type` says what a document IS, never what it is ABOUT.")
    print("Subject goes in `topics: [a, b]`, flow style, never a block list.\n")
    print("The standard: specs/oac-file-format.md   Decision: ADR-098")
    print("Check anything with: python3 code/scripts/oac-validate.py --staged\n")
    print("\033[0;31mSkip with --no-verify only if you are fixing something worse.\033[0m")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True, description="Report the OaC conformance level of a repository.")
    ap.add_argument("path", nargs="?", default=".", help="repository to check (default: here)")
    ap.add_argument("--vocabulary", help="path to oac-vocabulary.yml")
    ap.add_argument("--staged", action="store_true",
                    help="pre-commit gate: judge staged blobs, block on new files and regressions")
    ap.add_argument("--changed", action="store_true", help="only files changed since HEAD")
    ap.add_argument("--since", metavar="REF", help="only files a branch adds, versus REF")
    ap.add_argument("--details", action="store_true", help="list every finding")
    ap.add_argument("--limit", type=int, default=8, help="findings shown per level (default 8)")
    ap.add_argument("--json", action="store_true", dest="as_json", help="machine-readable output")
    args = ap.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"oac-validate: {root} is not a directory", file=sys.stderr)
        return 2

    vocab_path = find_vocabulary(root, args.vocabulary)
    if not vocab_path:
        print("oac-validate: cannot find oac-vocabulary.yml. Pass --vocabulary.", file=sys.stderr)
        return 2
    vocab = load_yaml(vocab_path)
    if not vocab:
        print(f"oac-validate: {vocab_path} did not parse", file=sys.stderr)
        return 2

    manifest = load_manifest(root)
    exempt = exempt_paths(manifest)

    if args.staged:
        return staged_gate(root, vocab, manifest, exempt)

    # Version skew. Newer than us is a warning, never a refusal (spec §9).
    declared = str(manifest.get("oac_version") or "")
    spec_version = str(vocab.get("version") or "")
    skew = None
    if declared and spec_version and declared != spec_version:
        skew = f"repo targets OaC {declared}, this validator knows {spec_version}. Reporting best effort."

    rels = collect(root, exempt, args)
    docs = [Document(root, r) for r in rels]

    rep = Report()
    if not docs:
        scope = "changed files" if (args.changed or args.since) else "this repository"
        if args.as_json:
            print(json.dumps({"level": None, "documents": 0, "note": f"no markdown in {scope}"}, indent=2))
        else:
            print(f"No markdown documents in {scope}. Nothing to report.")
        return 0

    whole_repo = not (args.changed or args.since)
    check_level_0(docs, rep)
    check_level_1(docs, vocab, manifest, rep)
    check_level_2(root, docs, vocab, manifest, rep, whole_repo)
    check_level_3(docs, manifest, rep, whole_repo)

    level = achieved_level(rep)
    names = {int(k): (v or {}).get("name", "") for k, v in (vocab.get("conformance_levels") or {}).items()}
    validate_cfg = manifest.get("validate") or {}
    target = validate_cfg.get("level")
    enforcement = norm(validate_cfg.get("enforcement")) or "advisory"
    scope_label = "changed files" if (args.changed or args.since) else "whole repository"

    if args.as_json:
        print(json.dumps({
            "level": level,
            "level_name": names.get(level, ""),
            "scope": scope_label,
            "documents": len(docs),
            "target_level": target,
            "enforcement": enforcement,
            "skew": skew,
            "stats": rep.stats,
            "findings": {k: [{"path": p, "why": w} for p, w in v] for k, v in rep.findings.items()},
        }, indent=2))
    else:
        print()
        print(f"  OaC conformance: LEVEL {level}  {names.get(level, '')}")
        print(f"  {len(docs)} documents · {scope_label} · vocabulary v{spec_version}")
        if skew:
            print(f"  note: {skew}")
        if not whole_repo:
            print("  note: directory-index and profile checks are repo-wide, so they are skipped here")
        print()
        for n in ("0", "1", "2", "3"):
            bad = rep.counts[n]
            mark = "ok  " if not bad else "    "
            label = names.get(int(n), "")
            detail = "clean" if not bad else f"{bad} finding{'s' if bad != 1 else ''}"
            print(f"  {mark}level {n} {label:<9} {detail}")
        print()
        s = rep.stats
        print(f"  typed documents      {s.get('level_1_ok', 0)}/{len(docs)}  ({s.get('level_1_coverage', 0)}%)")
        if s.get("edges"):
            print(f"  edges resolving      {s.get('edges_resolved')}/{s.get('edges')}  ({s.get('edge_coverage')}%)")
        if s.get("dirs_needing_index"):
            have = s["dirs_needing_index"] - s["dirs_missing_index"]
            print(f"  large dirs indexed   {have}/{s['dirs_needing_index']}")
        fixable = s.get("mechanically_fixable") or {}
        if fixable:
            total = sum(fixable.values())
            parts = ", ".join(f"{v} {k}" for k, v in sorted(fixable.items()))
            print(f"  mechanically fixable {total}  ({parts})")

        for n in ("0", "1", "2", "3"):
            items = rep.findings[n]
            if not items:
                continue
            shown = items if args.details else items[:args.limit]
            print(f"\n  level {n} findings ({len(items)}):")
            for path, why in shown:
                print(f"    {path}\n        {why}")
            if len(items) > len(shown):
                print(f"    ... {len(items) - len(shown)} more, use --details")

        print()
        if target is not None:
            verdict = "meets" if level >= target else "below"
            print(f"  target level {target} ({enforcement}): {verdict}")
        print()

    if enforcement == "blocking" and target is not None and level < target:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
