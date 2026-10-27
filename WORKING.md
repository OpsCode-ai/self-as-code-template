---
title: "How we work: sessions, notes and working side by side"
type: standard
audience: internal
topics: [operations, tooling, onboarding]
tags: [opscode, oac, sac, session-discipline, worktrees, checkpoint, task-bridge]
---

# How we work: sessions, notes and working side by side

A session has no memory of the last one, and a repo has one working copy.
Everything in this page follows from those two facts. It is the same way
OpsCode runs its own repos, cut down to what a business or a private space
needs on day one and on the day the second person arrives.

## The loop: every session

| | Command | What it does |
|---|---|---|
| Open | `/start` | Brings down the latest copy from GitHub, reads your log, then says where things are up to |
| Any time | `/commit`, `/push`, `/pull` | Save a step, send it to GitHub, bring down the latest. Each one does the git and says what it did. `/start` and `/done` run the same steps |
| Any time | `/task-bridge` | A note to yourself. Twenty seconds. The next session reads it |
| Close | `/done` | Checks the files, writes your note for next time, saves by name, sends it to GitHub, refreshes your usage page |

Your log is `evidence/days/current.md` in a private space, with older days
beside it by date, and `team/<you>/current.md` in a business, with older days
in `team/<you>/logs/`. The **Next** line at the top of it is the one thing you
said you would do next; `/start` leads with it. The whole point is that you
never rebuild yesterday from memory.

The message at the top of the screen when you open the repo shows the same
thing from the other side: what moved, where you left off, who else worked and
where, and a suggested focus when your log has none.

## Checkpoints: a build bigger than one session

When a piece of work is too big for one session, `/checkpoint` writes a
document into `notable-plans/`: where it is up to, what is left in order and
why, the evidence, what was ruled out, the hazards. `/checkpoint --restore`
picks it up in a fresh session on any machine. One live checkpoint at a time;
close it when the build ships. `notable-plans/README.md` has the rules.

A checkpoint is not a substitute for committing. Commit and push first.

## One person, then two: worktrees

While one person works in this repo, `/done` commits to `main` and pushes.
That is correct, and it stays correct until the day a second session touches
the same folder, whether that is a second person or you with two terminals
open on the same repo.

One copy of the repo has one working folder. Two sessions in the same copy
collide: one saves the other's half-written files, or one switches the branch
under the other. The fix is not care, it is structure.

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

## The guard, when you are ready for it

Remembering is not a mechanism. Two small checks make the rule hold without
anyone thinking about it, and they install once per machine:

```bash
python3 scripts/install-oac-branch-guard.py
```

- **The branch guard** refuses to create a branch inside a primary clone and
  prints the `git worktree add` line instead. It never locks you out:
  `OAC_ALLOW_BRANCH=1` turns it off for one command.
- **The session health check** says, at session start, when the primary clone
  is off `main` or carrying uncommitted work, and says nothing when all is
  well.

Install them the day the second session arrives, not before. A guard on a
one-person repo is a guard nobody needed yet.

## Upgrading: when the template moves

This repo started from OpsCode's template on GitHub. The template keeps
moving: a new stage, a fixed script, a better hook. You take the new one
without losing a line you wrote.

1. Get the current template somewhere outside this repo, for example
   `~/Downloads/`. Your private repo came from `self-as-code-template`, a
   business repo from `operations-as-code-template`:

```bash
git clone --depth 1 https://github.com/OpsCode-ai/operations-as-code-template ~/Downloads/operations-as-code-template
```

2. Commit or `/done` first. The upgrade refuses a tree with unsaved work, so
   the upgrade is one diff you can read. If this folder is the one your
   timed jobs write to, the branch guard will refuse a branch here; make the
   branch in a worktree (the guard prints the line), run the upgrade there,
   and merge from this folder after a pull.
3. Report, then apply:

```bash
python3 scripts/oac-upgrade.py --from ~/Downloads/operations-as-code-template
python3 scripts/oac-upgrade.py --from ~/Downloads/operations-as-code-template --apply
```

The report sorts every file into two kinds. **Tools** (scripts, commands,
this file) are refreshed only if you never touched them; a file you changed is
kept and named, and you take the new copy with `--take <path>` if you want it.
**Yours** (`self-as-code.md`, the register, `context-core/`, `decisions/`,
`team/`, `CLAUDE.md`, settings) is never written. Anything new that you do not
have is added.

Then restart Claude Code and run `/done`.

## What goes where

| Thing | Place |
|---|---|
| Today's note to yourself | `evidence/days/current.md` in a private space; `team/<you>/current.md` in a business |
| A build bigger than one session | `notable-plans/<date>-<slug>.md` |
| A decision worth not debating twice | `decisions/NNN-<slug>.md`, via `/create-adr` |
| What was built, and what surfaced | `build-logs/<date>-<slug>.md`, via `/build-log` |
| What your sessions cost | `usage.md` beside the log, refreshed by `/done` |

## Which repo you are in

The bottom line of the screen says `SAC` in your private space and `OAC` in a
business. `/sac help` in your private space, and `MODES.md` in a business, say
what each one is for. This page is the same in both.
