---
title: "How we work: sessions, continuity and parallel work"
type: standard
audience: internal
topics: [operations, tooling, onboarding]
tags: [opscode, oac, sac, session-discipline, worktrees, checkpoint, task-bridge]
---

# How we work: sessions, continuity and parallel work

An agent session has no memory of the last one, and a repo has one working
tree. Everything in this page follows from those two facts. It is the same
standard OpsCode runs on its own repos (session discipline, ADR-113), cut down
to what a business plane or a self plane needs on day one and on the day the
second person arrives.

## The loop: every session

| | Command | What it does |
|---|---|---|
| Open | `/start` | Pulls the latest version from GitHub, reads your continuity log, then the plane's numbers. Puts you back in the room |
| Any time | `/commit`, `/push`, `/pull` | Save a step, send it to GitHub, bring down the latest. Each one does the git and says what it did. `/start` and `/done` run the same steps |
| Any time | `/task-bridge` | A note to yourself. Twenty seconds. The next session reads it |
| Close | `/done` | Validates the format, writes your log, commits by path, pushes to GitHub, refreshes your usage report |

The log is `team/<you>/current.md`, one file per person per day, archived to
`team/<you>/logs/`. The **Roll-forward** in it is the single current
priority; `/start` leads with it. The whole point is that you never
reconstruct yesterday from memory.

The statusline briefing at session start shows the same loop from the other
side: what moved, what you left off, who else worked and where, and a
suggested focus when your log has none.

## Checkpoints: a build bigger than one session

When a piece of work runs past one context window, `/checkpoint` writes a
document into `notable-plans/`: where it stands, what remains in order and
why, the evidence, what was ruled out, the hazards. `/checkpoint --restore`
picks it up in a fresh session on any machine. One live checkpoint at a time;
close it when the build ships. `notable-plans/README.md` has the rules.

A checkpoint is not a substitute for committing. Commit and push first.

## One person, then two: worktrees

While one person works in this repo, `/done` commits to `main` and pushes.
That is correct, and it stays correct until the day a second session touches
the same folder, whether that is a second person or you with two terminals
open on the same repo.

One clone has one working tree, one index and one HEAD. Two sessions in the
same clone collide: one commits the other's half-written files, or one
switches the branch under the other. The fix is not care, it is structure.

**Every piece of work happens in its own worktree. The primary clone stays on
`main` and clean.**

```bash
git worktree add ~/projects/_wt-<short> -b <you>/<what>   # open one
git worktree list                                          # what is open
git worktree remove ~/projects/_wt-<short>                 # close one, refuses if dirty
```

Name the folder after the work, short enough to read in the list. Work in
it, `/done` from it (which then pushes a branch and opens a pull request when
the repo has a remote that reviews), and remove it when it merges.

**Never `git stash pop`** when worktrees are in play: the stash stack is
shared by every worktree of the clone, and `pop` takes the newest entry,
which may belong to a session you cannot see. Set work aside with a WIP
commit on your own branch instead.

## The rail, when you are ready for it

Remembering is not a mechanism. Two small hooks make the rule hold without
anyone thinking about it, and they install once per machine:

```bash
python3 scripts/install-oac-branch-guard.py
```

- **The branch guard** refuses to create a branch inside a primary clone and
  prints the `git worktree add` line instead. It fails open, and
  `OAC_ALLOW_BRANCH=1` is the escape hatch.
- **The session health check** says, at session start, when the primary clone
  is off `main` or carrying uncommitted work, and says nothing when all is
  well.

Install them the day the second session arrives, not before. A rail on a
one-person repo is a rail nobody needed yet.

## Upgrading: when the pack moves

This repo started as a pack. The pack keeps moving: a new stage, a fixed
script, a better hook. You take the new one without losing a line you wrote.

1. Download the current pack from your HQ and unzip it somewhere outside
   this repo, for example `~/Downloads/`.
2. Commit or `/done` first. The upgrade refuses a tree with unsaved work, so
   the upgrade is one diff you can read.
3. Report, then apply:

```bash
python3 scripts/oac-upgrade.py --from ~/Downloads/operations-as-code-pack
python3 scripts/oac-upgrade.py --from ~/Downloads/operations-as-code-pack --apply
```

The report sorts every file into three kinds. **Engine** files under
`.claude/` are always refreshed; nobody edits those by hand. **Tooling**
(scripts, commands, the method files, this file) is refreshed only if you
never touched it; a file you changed is kept and named, and you take the
pack's copy with `--take <path>` if you want it. **Yours** (`self-as-code.md`,
the register, `context-core/`, `decisions/`, `team/`, `CLAUDE.md`, settings)
is never written. Anything the new pack seeds that you do not have is added.

Then restart Claude Code, run `/aidlc --doctor`, and `/done`.

## What goes where

| Thing | Place |
|---|---|
| Today's note to yourself | `team/<you>/current.md` |
| A build bigger than one session | `notable-plans/<date>-<slug>.md` |
| A decision worth not debating twice | `decisions/NNN-<slug>.md`, via `/create-adr` |
| What was built, and what surfaced | `build-logs/<date>-<slug>.md`, via `/build-log` |
| What your sessions cost | `team/<you>/usage.md`, refreshed by `/done` |

## The modes

Which repo you are in decides which mode you are in, and the statusline says
so. `MODES.md` explains `SAC`, `OAC` and `AIDLC` and the commands that belong
to each. This page is the same in all three.
