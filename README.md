---
title: "Your private repo"
type: index
audience: owner
---

# Your private repo

Your private space (first-last-ops). One private repo, yours alone, sitting above the
businesses you run. The home for everything that is yours alone: private
notes, your own plans, what you know about the people you work with, the
decisions only you make. Nothing here ever enters a shared business repo, and
no business repo is ever a folder inside it.

- `self-as-code.md` - your plan. Who you are becoming, and what you refuse
  to drop below. Run `/sac` to write it
- `LICENCE.md` - what is OpsCode's (the method, CC BY 4.0; the scripts, MIT)
  and what is yours (everything you write). Made from OpsCode's Self as Code
  template, `https://github.com/OpsCode-ai/self-as-code-template`; new here,
  `INSTALL.md` is the way in
The five folders spell SPADE:

- `standards/` - what you keep up, with no end date. Your businesses live
  here, and your private notes on a partner at
  `standards/ventures/<venture>/partnerships/<name>/`.
  Each person or firm you deal with gets one folder, always the same
  shape: `meetings/`, `meetings/raw/`, `correspondence/`
- `projects/` - has an end date
- `archive/` - done or dropped
- `decisions/` - one file per decision you make, so a settled choice stays
  settled
- `evidence/` - what you look things up in and cite

Dig up the evidence, make the call, record it. Filing by what you can act on
rather than by subject is PARA, by Tiago Forte; SPADE is the same idea with a
name you can say.

## How this works

**What you see when you open it.** Claude Code shows a short message at the
top, and it changes. The first time, it tells you the one command. After that,
it tells you where things stand: what moved since last time, where you left
off, when your next review is due, what is open. The bottom line of the screen
says `SAC`. That means you are in your own private space. If it says `OAC`,
you are in a business.

**One command.** `/sac` is the only command you need for the method. It asks
you the questions, writes your plan to `self-as-code.md`, and sends the lines
you choose to share to each business you named, in the same sitting. You never
run a script. `/sac check` any time, to see how you are going. `/sac review`
every ninety days. `/sac deploy <business>` to set up a business of your own.

**The loop.** `/start` brings down the latest copy from GitHub and reads where
you left off. `/done` saves what changed, writes your note for next time, and
sends it all to GitHub. In between, `/commit`, `/push` and `/pull` each do one
step for you. This repo lives on GitHub as a private repository (`/github`
makes it): your backup, and your copy on every device.

**When a new version comes out.** Get the latest template with
`git clone --depth 1 https://github.com/OpsCode-ai/self-as-code-template ~/Downloads/self-as-code-template`,
then run `python3 scripts/oac-upgrade.py --from ~/Downloads/self-as-code-template`.
It shows what would change first; add `--apply` to take it. It adds what is
new, refreshes the tools, and never touches what you wrote. `WORKING.md` has
the detail.

This repo is PRIVATE. No collaborators by default. That is not tidiness: a git
host grants read at the repo, so one collaborator here would see your identity
and every business you run.
