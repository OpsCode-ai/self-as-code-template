---
title: "Your private repo"
type: index
audience: owner
---

# Your private repo

Your self plane (first-last-ops). One private repo, yours alone, sitting above the
businesses you run. The home for everything `audience: owner`: private reads,
personal strategy, partner intelligence, decisions that are yours alone.
Nothing here ever enters a shared Operations as Code repo (opscode-hq
ADR-111), and no business repo is ever a folder inside it (ADR-118).

- `self-as-code.md` - the spine. Who you are becoming, and the standards you
  refuse to fall below. Run `/sac` to write it
- `LICENCE.md` - what is OpsCode's (the method, CC BY 4.0; the scripts, MIT)
  and what is yours (everything you write). Made from OpsCode's Self as Code
  template, `https://github.com/OpsCode-ai/self-as-code-template`; new here,
  `INSTALL.md` is the way in
The five folders spell SPADE:

- `standards/` - ongoing, a bar you hold. Your ventures live here, and
  partner intelligence at `standards/ventures/<venture>/partnerships/<name>/`.
  Each person you hold a relationship with gets one folder, always the same
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

**What you see when you open it.** Claude Code shows a message at the top,
and it changes. The first time: Self as Code, one command, the loop. After
that: a manifest of where things stand, what moved since your last session,
where you left off, when the next raise is due, what is open. It is written
into `.claude/settings.json` by `scripts/oac-session-brief.py --announce
--write` at the end of every session, so the next open is current. The engine
underneath ships its own message in that slot and never gets to show it. The
bottom line of the screen says `SAC`, read from `.oac/manifest.yml`. If it
says `OAC` you are in a business plane.

**One door.** `/sac` is the only command you need for the method. It looks
for the engine itself: when the engine is installed and `/aidlc --doctor` is
clean, it runs the seven beats on the engine with a reviewer and an approval
gate; when the engine is not there, it runs the same beats the plain way.
Either way it writes `self-as-code.md` and then routes `## the split` into
each business you named, in the same session. You never choose a path, and
you never run a script. `/sac refactor` every ninety days; `/sac deploy
<business>` to stand up a business plane.

**The loop.** `/start` pulls the latest version from GitHub and reads where
you left off; `/done` commits by path, pushes to GitHub, and writes your
continuity note. In between, `/commit`, `/push` and `/pull` each do one git
step for you. This repo lives on GitHub as a private repository (`/github` makes
it): your backup, and your sync across devices.

**When the pack moves.** Download the new zip, unzip it beside this repo, and
run `python3 scripts/oac-upgrade.py --from <that folder> --apply`. It
refreshes the engine, adds what is new, and never writes what you wrote.
`WORKING.md` has the detail.

This repo is PRIVATE. No collaborators by default. That is not tidiness: a git
host grants read at the repo, so one collaborator here would see your identity
and every business you run.
