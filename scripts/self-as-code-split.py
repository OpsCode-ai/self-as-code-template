#!/usr/bin/env python3
"""Apply the split: route what a person chose to share into a business plane.

    python3 code/scripts/self-as-code-split.py --check [--root <self-plane>]
    python3 code/scripts/self-as-code-split.py --apply --unit <name> --target <business-plane> [--venture <folder>] [--no-push]

WHY THIS EXISTS
    Self as Code captures a person. Some of what it captures belongs to one of
    their businesses, and most of it belongs to none of them. ADR-118 gave every
    captured slice exactly one routing decision, `stays-personal`,
    `routes-to-<unit>` or `promotable-unrouted`, with the default that nothing
    crosses. ADR-122 made it the sentence a room hears: 'you choose what gets
    shared from SAC to OAC.' Until this file, that sentence had no code behind
    it: no script, no spec line, no frontmatter field, and no real
    self-as-code.md had ever carried a `## the split` section.

    This is the smallest real seam. It reads the split table from the spine and
    writes the routed statements into the business plane, on a branch, as a
    pull request.

WHAT CROSSES, AND WHAT NEVER DOES
    A slice is a STATEMENT, not a file. 'The twelve-month target is X' crosses.
    Why the founder is afraid of losing the house never does. So this script
    never copies a self-plane document. It writes one new document per unit,
    made only of the statements in rows routed to that unit, stamped
    `audience: internal` because that is what it now is. Three rules fall out:

    - No owner material can leak, because none is read for the body. Only the
      split table's Slice cells are ever copied.
    - No cross-repo edge can be written. Spec 4.1 says every edge is a path
      inside the declaring repo, so provenance is a scalar (`source:`) and the
      commit message, never a `derived_from:`.
    - Nothing is moved (ADR-122 section 4). The spine is read, never written.

THE TARGET IS ALWAYS AN ARGUMENT
    The self plane's manifest lists its business planes under `operations:`.
    Those are pointers, not paths: the spec says a consumer MUST NOT try to
    resolve them and that naming a repo grants no access to it (6.3). This
    script may print them as a hint. It never resolves one.

WHAT IT REFUSES
    A target that is not on a branch (the primary clone stays on main, ADR-113;
    print the worktree line instead). A target with uncommitted changes, because
    guessing what to do with someone's unsaved work is how you lose it. A target
    whose manifest is not `plane: business`. And a destination that already
    exists with different content: it keeps both, with a `-conflict-<stamp>`
    suffix on the new one, and says so.

Standard: specs/oac-file-format.md section 7.1 (`## the split`), 1.9.
Decisions: ADR-118 section 4, ADR-122 section 1.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.frontmatter import frontmatter, section  # noqa: E402
from lib.git_sync import bind, push_with_reconcile  # noqa: E402

ROUTINGS = ("stays-personal", "routes-to", "promotable-unrouted")
SPINE_ADDRESSES = ("self-as-code.md", "goals/self-as-code.md")
DEST_DIR = Path("context-core") / "strategic-identity"
DEST_FILE = "from-self-as-code.md"
BRANCH = "route-from-self-plane"
SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|$")


# ---------------------------------------------------------------- the spine --

def find_spine(root: Path) -> Path | None:
    """The spine belongs at the root; goals/ is where it lived before ADR-118."""
    for rel in SPINE_ADDRESSES:
        p = root / rel
        if p.is_file():
            return p
    return None


def normalise(cell: str) -> str:
    return re.sub(r"\s+", " ", cell.strip().strip("*`_ ").lower())


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_split(text: str) -> tuple[list[dict], list[str]]:
    """Rows of the `## the split` table, and the problems found in them.

    Columns are found by header name, case-insensitively: Slice, Beat, Routing,
    Destination. `Routing` is closed and must be bare. `Destination` is required
    when Routing is `routes-to`, as `<unit>` or `<unit>/<venture>`.
    """
    rows: list[dict] = []
    errors: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines) - 1:
        if lines[i].strip().startswith("|") and SEPARATOR_RE.match(lines[i + 1].strip()):
            headers = [normalise(h) for h in split_row(lines[i])]
            idx = {h: n for n, h in enumerate(headers)}
            for need in ("slice", "routing"):
                if need not in idx:
                    errors.append(f"the split table has no '{need}' column")
                    return rows, errors
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = split_row(lines[j])
                j += 1
                if len(cells) <= idx["routing"]:
                    errors.append(f"row is short of the Routing column: {' | '.join(cells)[:60]}")
                    continue
                raw_routing = cells[idx["routing"]]
                routing = normalise(raw_routing)
                slice_text = cells[idx["slice"]].strip()
                beat = cells[idx["beat"]].strip() if "beat" in idx and len(cells) > idx["beat"] else ""
                dest = cells[idx["destination"]].strip() if "destination" in idx and len(cells) > idx["destination"] else ""
                if routing not in ROUTINGS:
                    errors.append(f"'{slice_text[:40]}': routing {raw_routing!r} is not one of {'/'.join(ROUTINGS)}")
                    continue
                if raw_routing.strip() != routing:
                    errors.append(f"'{slice_text[:40]}': routing cell is not bare: {raw_routing!r}. "
                                  "Emphasis defeats the grep this profile rests on.")
                if routing == "routes-to" and not dest:
                    errors.append(f"'{slice_text[:40]}': routes-to with no Destination. Name the unit.")
                unit, _, venture = dest.partition("/")
                rows.append({"slice": slice_text, "beat": beat, "routing": routing,
                             "unit": unit.strip(), "venture": venture.strip()})
            break
        i += 1
    if not rows and not errors:
        errors.append("the split section exists but holds no table")
    return rows, errors


def read_split(root: Path) -> tuple[Path | None, list[dict] | None, list[str]]:
    """(spine, rows, errors). rows is None when there is no split section yet."""
    spine = find_spine(root)
    if spine is None:
        return None, None, [f"no self-as-code.md at {root} (looked at {', '.join(SPINE_ADDRESSES)})"]
    raw = spine.read_text(encoding="utf-8", errors="replace")
    sec = section(raw, "the split")
    if sec is None:
        return spine, None, []
    rows, errors = parse_split(sec)
    return spine, rows, errors


def manifest_hint(root: Path) -> list[str]:
    """Business planes the self plane names. A hint for the human, never resolved."""
    m = root / ".oac" / "manifest.yml"
    if not m.is_file():
        return []
    for line in m.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("operations:"):
            inner = line.partition(":")[2].strip().strip("[]")
            return [x.strip().strip("\"'") for x in inner.split(",") if x.strip()]
    return []


# -------------------------------------------------------------------- check --

def check(root: Path, as_json: bool) -> int:
    spine, rows, errors = read_split(root)
    if as_json:
        print(json.dumps({"spine": str(spine) if spine else None,
                          "present": rows is not None, "rows": rows or [],
                          "errors": errors}, indent=2))
        return 1 if errors else 0

    if spine is None:
        print(f"\n  {errors[0]}\n")
        return 1
    print(f"\n  spine: {spine}")
    if rows is None:
        print("  no `## the split` section yet, so everything stays personal.")
        print("  That is the fail-closed default, not a problem. Write the table")
        print("  when there is something to route.\n")
        return 0

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["routing"]] = counts.get(r["routing"], 0) + 1
    print(f"\n  {len(rows)} slice(s) routed")
    for k in ROUTINGS:
        print(f"    {k:<22} {counts.get(k, 0)}")
    units = sorted({r["unit"] for r in rows if r["routing"] == "routes-to" and r["unit"]})
    if units:
        print(f"\n  routes to: {', '.join(units)}")
    hint = manifest_hint(root)
    if hint:
        print(f"  the manifest names: {', '.join(hint)} (pointers, never resolved here)")
    if errors:
        print(f"\n  {len(errors)} problem(s):")
        for e in errors:
            print(f"    - {e}")
        print()
        return 1
    print("\n  clean against the self-core profile\n")
    return 0


# -------------------------------------------------------------------- apply --

def git(target: Path):
    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(("git", "-C", str(target)) + args, capture_output=True, text=True)
    return run


def target_problem(target: Path) -> str | None:
    if not target.is_dir():
        return f"target {target} is not a directory"
    run = git(target)
    if run("rev-parse", "--git-dir").returncode != 0:
        return f"target {target} is not a git repository"
    m = target / ".oac" / "manifest.yml"
    if not m.is_file():
        return f"target has no .oac/manifest.yml, so it is not an OaC repo"
    plane = None
    for line in m.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("plane:"):
            plane = line.partition(":")[2].strip()
    if plane != "business":
        return f"target declares plane: {plane or 'absent'}; routed statements only go into a business plane"
    branch = run("branch", "--show-current").stdout.strip()
    if branch in ("", "main", "master"):
        return (f"target is on '{branch or 'a detached HEAD'}'. The primary clone stays on main (ADR-113).\n"
                f"  Route into a worktree instead:\n"
                f"    git -C {target} worktree add ~/projects/_wt-route -b <user>/{BRANCH}")
    if run("status", "--porcelain").stdout.strip():
        return (f"target {target} has uncommitted changes.\n"
                "  Guessing what to do with someone's unsaved work is how you lose it. Resolve it by hand.")
    return None


def render(rows: list[dict], unit: str, venture: str, today: str, *,
           setup: dict[str, str] | None = None, by: str = "self-as-code-split.py") -> str:
    """The one document a business gets from the self plane. `setup` is the
    business block's setup lines (sac-deploy.py passes them on day one); `by`
    names the tool that wrote it."""
    where = f"{unit}/{venture}" if venture else unit
    lines = [
        "---",
        f'title: "What the self plane routed here: {where}"',
        "type: strategy",
        "audience: internal",
        "status: active",
        "lifecycle: living",
        f"updated: {today}",
        f'source: "routed from the operator\'s self plane by {by}, {today}"',
        "topics: [self-as-code, positioning]",
        "tags: [routed, self-as-code, the-split]",
        "---",
        "",
        f"# What the self plane routed here",
        "",
        "These are the statements the operator chose to share with this business",
        "from their own Self as Code. What crossed is the decision, never the raw",
        "session. The business learns the target; it never learns why. Everything",
        "not listed here stayed personal, by default (ADR-118, ADR-122).",
        "",
        "## What the self plane routed here",
        "",
    ]
    for r in rows:
        beat = f"**{r['beat']}**: " if r["beat"] else ""
        lines.append(f"- {beat}{r['slice']}")
    if not rows:
        lines.append("- Nothing shared yet. Choose what to share in `/sac`, under `## the split`, and run it again.")
    if setup:
        lines += ["", "## Set up from", "",
                  "The lines this business's own repo was set up from, written in Self as",
                  "Code about this business. Confirm them in `/oac`; never ask for them again.", ""]
        for k, v in setup.items():
            lines.append(f"- **{k}**: {v}")
    lines += ["", f"Routed {today}. Regenerate by re-running the split; do not edit the",
              "statements here, change them in the self plane and route again.", ""]
    return "\n".join(lines)


def apply(root: Path, unit: str, target: Path, venture: str, push: bool) -> int:
    spine, rows, errors = read_split(root)
    if spine is None:
        print(f"\n  {errors[0]}\n")
        return 1
    if rows is None:
        print("\n  no `## the split` section in the spine, so nothing is routed anywhere.\n")
        return 1
    if errors:
        print(f"\n  refusing to apply with {len(errors)} problem(s) in the split table. Run --check.\n")
        return 1

    chosen = [r for r in rows if r["routing"] == "routes-to" and r["unit"] == unit
              and (not venture or not r["venture"] or r["venture"] == venture)]
    if not chosen:
        print(f"\n  no slices routed to '{unit}'. Nothing to write.\n")
        return 0
    row_venture = venture or next((r["venture"] for r in chosen if r["venture"]), "")

    why = target_problem(target)
    if why:
        print(f"\n  refusing: {why}\n")
        return 1

    today = _dt.date.today().isoformat()
    rel = DEST_DIR / row_venture / DEST_FILE if row_venture else DEST_DIR / DEST_FILE
    dest = target / rel
    content = render(chosen, unit, row_venture, today)

    if dest.is_file():
        existing = dest.read_text(encoding="utf-8", errors="replace")
        if existing == content:
            print(f"\n  {rel} is already exactly this. Nothing to do.\n")
            return 0
        # Same statements on a different day still differ by the date. Compare
        # the routed list itself before calling it a conflict.
        if section(existing, "What the self plane routed here") == section(content, "What the self plane routed here"):
            print(f"\n  {rel} already carries these statements. Nothing to do.\n")
            return 0
        stamp = _dt.datetime.now().strftime("%Y%m%d%H%M%S")
        rel = rel.with_name(f"{rel.stem}-conflict-{stamp}{rel.suffix}")
        dest = target / rel
        print(f"\n  {DEST_FILE} exists with different content. Keeping both; writing {rel.name}.")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")

    run = git(target)
    run("add", "--", str(rel))
    msg = (f"Add: {len(chosen)} statement(s) routed from the self plane to {unit}"
           f"{'/' + row_venture if row_venture else ''}\n\n"
           "Written by self-as-code-split.py from the operator's `## the split`\n"
           "table. What crossed is the decision, never the raw session (ADR-118,\n"
           "ADR-122). Nothing was moved and no self-plane file was copied.\n")
    c = run("commit", "-m", msg, "--", str(rel))
    if c.returncode != 0:
        print(f"\n  wrote {rel} but the commit failed:\n  {c.stderr.strip()}\n")
        return 1
    branch = run("branch", "--show-current").stdout.strip()
    print(f"\n  wrote {rel}")
    print(f"  {len(chosen)} statement(s), audience: internal, committed on {branch}")

    if push:
        ok, detail = push_with_reconcile(bind(run))
        print(f"  push: {'ok' if ok else 'held locally'} {detail}".rstrip())
    print(f"\n  open the pull request they merge:\n    gh pr create --head {branch}\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="the self plane (default: cwd)")
    ap.add_argument("--check", action="store_true", help="validate the split table. The default")
    ap.add_argument("--apply", action="store_true", help="write routed statements into a business plane")
    ap.add_argument("--unit", help="the unit to route (a Destination value's first segment)")
    ap.add_argument("--target", help="path to that unit's business plane. Always an argument, never resolved")
    ap.add_argument("--venture", default="", help="venture folder under the unit, if the destination names one")
    ap.add_argument("--no-push", action="store_true", help="commit on the branch, do not push")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.check and a.apply:
        print("--check and --apply contradict each other. Pick one.")
        return 2
    root = Path(a.root).resolve()
    if not a.apply:
        return check(root, a.json)
    if not a.unit or not a.target:
        print("--apply needs --unit <name> and --target <path>. The target is never resolved from the manifest.")
        return 2
    return apply(root, a.unit, Path(a.target).resolve(), a.venture, push=not a.no_push)


if __name__ == "__main__":
    sys.exit(main())
