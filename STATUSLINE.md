---
title: "The statusline: know where you are"
type: guide
audience: internal
topics: [claude-code, tooling, onboarding]
tags: [opscode, oac, statusline]
---

# The statusline: know where you are

A Claude Code session has no address bar. Nothing on screen tells you which
folder you are in, which branch you are on, or how full the context is. You find
out when something has already gone wrong.

This puts one line at the bottom of every session that answers all of it.

```
you@yourmachine:~/projects/your-name-ops · main* | SAC · Opus 5 [ctx: 43%] $4.12
```

| Part | What it tells you |
| --- | --- |
| `you@yourmachine` | Which computer. Easy to forget once you have more than one |
| `~/projects/your-name-ops` | The folder you are actually in. If it is not your folder, Claude cannot see your work |
| `⧉ name` | You are in this session's own folder (git calls it a worktree). `/start` opens one for every session and `/done` closes it. Magenta, and missing in your main folder |
| `· main*` | The branch you are on. The `*` means you have changes not saved yet; `/done` saves them |
| `⌂ main +2` | Your main folder has changes not saved (amber), or is not on `main` (red). Missing when all is well |
| `SAC` / `OAC` / `AIDLC` | Where you are. `SAC` is your private space, `OAC` a business. `AIDLC` shows while a software build is running step by step. No word means you are outside your folders |
| `Opus 5` | Which Claude is answering, so a quiet change is visible |
| `[ctx: 43%]` | How full the conversation is. Green under 50, amber under 80, red from 80. At red, run `/done`, then `/clear` |
| `$4.12` | What this session would cost at list prices. On a Max or Team plan it is a guide, not a bill. `/clear` starts it again from zero |

On a narrow screen the line splits into two or three. Nothing is dropped; only
where it breaks moves.

**The line under it is Claude Code's own.** It shows how much Claude asks
before it acts: hold Shift and press Tab to change it (ask before each change,
accept file changes, or plan first and change nothing). `esc to interrupt`
means Esc stops Claude mid-answer. When helpers are working in the background
it says how many. And `/rename` gives a session a name, shown on the rule above
where you type.

## Why it is worth five minutes

**Edits land on the wrong branch.** You think you are on your working branch. You
are not. The line tells you before you type.

**A session's folder gets mistaken for the main one.** They look the same.
The magenta marker is the only visible difference.

**The context fills and the session forgets.** Claude compacts the conversation
when it runs out of room, and things quietly drop out. Watching the percentage
climb means you can wrap up on purpose rather than be surprised.

## Install it

You do this once per machine. It then applies to every repo you open, not just
this one.

The easy way: open Claude Code in this folder, paste the prompt below, and let it
run. It checks its own work.

```
Install the OaC standard Claude Code statusline on this machine, then prove it worked.

Everything you need is in this folder:
  scripts/oac-statusline.sh          the statusline itself
  scripts/install-oac-statusline.py  the installer

Do this in order and stop at the first thing that genuinely blocks you.

1. Check python3 exists: run `python3 --version`. If it is missing, stop and tell
   me how to install it for my operating system. Do not work around it, because
   the statusline needs it.

2. Before changing anything, run `python3 scripts/install-oac-statusline.py --check`
   and show me the output. If I already have a working statusline, say so and ask
   me whether to replace it before you go further.

3. Run `python3 scripts/install-oac-statusline.py`. Show me exactly what it printed.
   If it backed up an existing file, tell me where the backup went.

4. Run the check again. Both lines must say yes. If either says NO, read the
   message, work out the cause and fix it. The usual cause is that
   ~/.claude/settings.json is not valid JSON. If that is it, show me the broken
   part before you touch it, because a malformed settings file switches off ALL my
   settings and I want to see it first.

5. Read ~/.claude/settings.json back and show me the statusLine block.

6. On Windows only: confirm bash is available with `bash --version`, because the
   statusline is a bash script. If there is no bash, tell me plainly that the line
   will not render and stop, rather than reporting success.

Then tell me whether it is installed and wired, that I need to restart the session
to see it, and what each part of the line means in one short sentence.

Do not edit any file other than the ones in ~/.claude/. Do not change my project
settings. If something is already correct, say so and leave it alone.
```

By hand instead, from this folder:

```bash
python3 scripts/install-oac-statusline.py
python3 scripts/install-oac-statusline.py --check
```

Then restart Claude Code. The line appears at the bottom.

## Taking an update later

Run the installer again after you pull a newer pack. That is the whole update
path. It replaces the copy in `~/.claude/` and leaves your settings alone.

## If the line ever disappears

It is almost always settings order. Claude Code loads your user settings, then
the project's, and the later one wins. So a repo carrying its own
`.claude/settings.json` overrides yours, including when that file prints nothing.

The copy in `~/.claude/` sits outside git, so it survives branch switches. If one
particular repo keeps blanking it, say so. There is a per repo override that
fixes it and it is a two line change.

## On Windows

The statusline is a bash script, so Windows needs a bash to run it. If you
installed Claude Code the normal way you already have Git Bash and it will work.
If the bar stays blank after a restart, run `bash --version`. No bash means the
line cannot run, and that is worth a message rather than a fight.
