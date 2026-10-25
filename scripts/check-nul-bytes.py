#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 DCDIGITAL GROUP Pty Ltd (trading as OpsCode)
"""Refuse a NUL byte in a text source file.

A NUL is a fine SENTINEL. It cannot appear in a heading or a sprint name, so
it is a safe join separator and a safe 'no value' marker. The bug is only ever
how it is WRITTEN: the literal 0x00 byte instead of the two-character escape
`\\0`.

Written literally, it does three things, none of them obvious:

  1. `grep` and `rg` SILENTLY SKIP the file. Not 'no useful match', no match
     and no warning. Under ADR-082 and CLAUDE.md rule 9, retrieval here is
     Grep/Glob/Read with no vector store, so a file grep skips is a file the
     agents cannot find.
  2. If the NUL falls in the first 8000 bytes, git calls the file BINARY.
     Diffs become 'Binary files differ' on the CLI and in a pull request, and
     blame and merge-conflict resolution degrade with them.
  3. Nothing warns you. The code runs correctly, so it survives review.

Both effects hit products/oac-client in August 2026: BoardView.tsx was
undiffable and checklist.ts was unsearchable, and three greps for 'sprint'
came back empty before anyone realised grep was refusing to read the file.

Checks the STAGED blob, so a file edited after `git add` is judged in the
version being committed.

USAGE
  python3 code/scripts/check-nul-bytes.py            # staged files (hook)
  python3 code/scripts/check-nul-bytes.py --all      # every tracked file
"""

# Annotations stay strings, so `str | None` parses on Python 3.9.
# The stock macOS python3 is 3.9 and the pre-commit hook calls bare
# `python3`, so without this the hook crashes before it checks anything
# and blocks every commit on that machine.
from __future__ import annotations

import subprocess
import sys

# Extensions where a NUL is always a mistake. An allow-list, so that images,
# fonts, archives and other genuinely binary files are never considered.
TEXT_EXT = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".css", ".scss",
    ".html", ".md", ".mdx", ".txt", ".py", ".sh", ".bash", ".zsh", ".yml",
    ".yaml", ".toml", ".ini", ".cfg", ".sql", ".rs", ".go", ".java", ".rb",
    ".php", ".c", ".h", ".cpp", ".hpp", ".svg", ".xml", ".csv", ".tsv",
}


def git(*args) -> str | None:
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def is_text(path: str) -> bool:
    dot = path.rfind(".")
    return dot != -1 and path[dot:].lower() in TEXT_EXT


def main() -> int:
    every = "--all" in sys.argv
    if every:
        raw = git("ls-files", "-z")
        read = lambda p: open(p, "rb").read()
    else:
        raw = git("diff", "--cached", "--name-only", "--diff-filter=ACM", "-z")
        def read(p):
            r = subprocess.run(["git", "show", f":{p}"], capture_output=True)
            return r.stdout if r.returncode == 0 else b""

    if raw is None:
        return 0

    offenders = []
    for path in (f for f in raw.split("\0") if f and is_text(f)):
        try:
            blob = read(path)
        except OSError:
            continue
        n = blob.count(b"\x00")
        if n:
            line = blob[: blob.index(b"\x00")].count(b"\n") + 1
            offenders.append((path, n, line))

    if not offenders:
        if every:
            print("No NUL bytes in any tracked text file.")
        return 0

    print()
    print("\033[0;31m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
    print("\033[0;31m❌ BLOCKED: raw NUL byte in a text file\033[0m")
    print("\033[0;31m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
    print()
    for path, n, line in offenders:
        print(f"  {path}   {n} NUL, first on line {line}")
    print()
    print("Write it as the two-character escape \\0 instead of the byte itself.")
    print('  wrong:  join("<a real 0x00 here>")')
    print('  right:  join("\\0")')
    print()
    print("The two are the same string at runtime. The literal byte makes the")
    print("file invisible to grep, and binary to git if it lands in the first")
    print("8000 bytes, so the change is free and the cost of leaving it is not.")
    print()
    print("Example of the correct form already in the tree:")
    print("  products/oac-client/src/lib/git/gitExt.ts  ->  path.includes(\"\\0\")")
    return 1


if __name__ == "__main__":
    sys.exit(main())
