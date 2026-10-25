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
you@yourmachine:~/Documents/your-ops · main* | Opus 5 (1M) [ctx: 43%]
```

| Part | What it tells you |
| --- | --- |
| `you@yourmachine` | Which machine. Easy to forget once you have more than one |
| `~/Documents/your-ops` | The folder you are actually in |
| `⧉ name` | You are in a worktree, a second copy of the repo. Magenta, and missing when you are in the normal folder |
| `· main*` | The branch you are on. The `*` means you have unsaved changes |
| `Opus 5 (1M)` | Which model, so a quiet downgrade is visible |
| `[ctx: 43%]` | How full the context is. Green under 50, amber under 80, red from 80 |

## Why it is worth five minutes

**Edits land on the wrong branch.** You think you are on your working branch. You
are not. The line tells you before you type.

**A second copy gets mistaken for the real one.** Worktrees are handy and they
look identical. The magenta marker is the only visible difference.

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
