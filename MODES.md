---
title: "The three modes: SAC, OAC and AIDLC"
type: guide
audience: internal
topics: [operations, self-as-code, aidlc, onboarding]
tags: [opscode, oac, sac, aidlc, modes, statusline, adr-125]
---

# The three modes: SAC, OAC and AIDLC

The bottom line of Claude Code shows a word in capitals: `SAC`, `OAC` or
`AIDLC`. That word is the mode you are working in. Each mode is about a
different part of your life and work, lives in a different kind of repo, and has
its own commands. This page says what each one is, how you know you are in it,
and what to do there.

## The one-line version

| Mode | What it runs | Where it lives | The question it answers |
|---|---|---|---|
| **SAC** | You. Self as Code | Your private repo, `first-last-ops`. Only you can see it | Who am I becoming, and what will I never drop below? |
| **OAC** | A business. Operations as Code | The business's shared repo, `business-ops`. Everyone in the business can see it | What does this business run on, and what is it aiming at? |
| **AIDLC** | Software. OpsCode's build tools, added when you need them | Any repo where you are building software | What are we building, and is it built right? |

SAC comes first. OAC comes second, once for each business. AIDLC is an add-on:
you switch it on when you want to build software, and it uses what SAC and OAC
already wrote as its starting point.

## How you know which mode you are in

The bottom line reads it from the repo, so you never set it by hand.

```
adam@laptop:~/projects/jane-smith-ops · main | SAC · Opus 5 [ctx: 12%] $0.40
adam@laptop:~/projects/acme-ops · main | OAC · Opus 5 [ctx: 30%] $2.10
adam@laptop:~/projects/acme-ops · main | AIDLC ⚙ 260924-invoice-export@code-generation · Opus 5 [ctx: 55%] $9.80
```

- `SAC` or `OAC` comes from a small settings file in the repo,
  `.oac/manifest.yml`, which says whether this is your private repo or a
  business's shared one.
- `AIDLC` shows when the build tools have a piece of software work open. The
  part after `⚙` is that work and the step it is up to.
- No mode word at all means you are outside an OpsCode repo. That is fine, but
  none of the commands below will be there.

The other parts of the line: the folder, the branch (with `*` when you have
unsaved changes), the model, how full the conversation is, and what this
session has cost so far. On a narrow screen the line wraps to two or three
lines rather than dropping anything.

## What you see when you open a repo

**Getting there.** Open a new Terminal window and type one word: `sac` for
your private repo, `oac` for a business's. It opens that folder with Claude
Code running. Each pack's install sets the word up with
`bash scripts/install-shortcuts.sh`; run that yourself if it has not been,
or if a folder moves.

Two things tell you where you are before you type anything.

**The message at the top.** Claude Code shows a note when a session starts, and
it changes. The first time you open a repo, it says what the repo is, the one
command, and the daily habit. Once you have worked in it, it shows where things
stand: what changed since your last session, where you left off, the last entry
in your log, the number that matters (your next 90-day review in your private
repo, the count of jobs still done by hand in a business), and what is open. It
is written by `scripts/oac-session-brief.py --announce --write`, which runs at
the end of every session and again at the start, so the next open is always
up to date.

**The word on the bottom line.** `SAC`, `OAC` or `AIDLC`, as described above.

Then one command: `/sac` in your private repo, `/oac` in a business's repo. You
do not run scripts.

## SAC: Self as Code

**Where:** your own private repo, `first-last-ops`. Nobody else can see it.

**What it is for:** writing down why you exist, who you are becoming, the
standard you will never drop below, and every business you run, as a file your
AI reads every session. Then choosing, one line at a time, what each business is
allowed to know.

It runs on its own. Nothing else needs to be installed.

**Commands:**

| Command | When |
|---|---|
| `/sac` | The one door. Seven questions, about an hour. Writes your plan to `self-as-code.md` on a branch, which becomes yours when you merge it. Then sends what you choose to share to each business, as a pull request it accepts |
| `/sac review` | Every 90 days, when the note at the top says your review is due |
| `/sac deploy <business>` | Set up a business's own repo from what you captured |
| `/sac dashboard` | Your plan drawn as one page, on this laptop. Run it any time, and nothing leaves your laptop |
| `/sac meeting <file>` | A meeting transcript lands in your private repo first. The parts you choose go to each business as a pull request; the transcript never leaves |
| `/github` | Once. A private copy of your repo on GitHub, if the install could not make it |
| `/start`, `/done`, `/task-bridge` | Every session. The daily habit: `/start` pulls the latest version from GitHub, `/done` saves your work and pushes it |
| `/commit`, `/push`, `/pull` | Any time. Save a step, send it to GitHub, bring down the latest. You type the command; it does the git |

**The rule:** nothing leaves this repo unless you choose to share it. Anything
you did not choose stays private.

## OAC: Operations as Code

**Where:** one shared repo for each business, `business-ops`. Everyone who works
in the business can read it.

**What it is for:** the business, written down. Two halves: `systems/` for what
runs today (software, where the work lives, which jobs are still done by hand),
and `context-core/` for what the business is aiming at and for whom. If you can
go and look, it belongs in systems. If two people could disagree about it, it
belongs in the Context Core.

**Commands:**

| Command | When |
|---|---|
| `/install` | The first time you open it. Checks the layout and shows what to fill in |
| `/oac` | The one door. Sets the business up in order (starting from your Self as Code, then software, team, the chaos exercise, connections and GitHub), then writes what the business runs on, then what it is aiming at, then one hand-run job at a time, written down by watching it. Each part waits for your yes. Typed again later, it does the next thing, not the first thing again |
| `/create-adr` | A decision worth not arguing about twice |
| `/build-log` | After a big piece of work |
| `/start`, `/done`, `/task-bridge` | Every session. The daily habit: `/start` pulls the latest version from GitHub, `/done` saves your work and pushes it |
| `/commit`, `/push`, `/pull` | Any time. Save a step, send it to GitHub, bring down the latest. You type the command; it does the git |

**The number that matters:** how many jobs are still done by hand. The register
counts it, the note at the top shows it, and the whole point is to bring it
down.

`/oac` runs the plain way, the same as `/sac`: the register, then the
business's direction, then one process at a time, each written on your yes.
Neither pack ships the build tools; they are added the day you want them.

## AIDLC: switch it on to build software

**Where:** any repo where you want to build software. It is an add-on. A repo
that builds nothing never needs it.

**What it is for:** taking a piece of software from idea to shipped code, one
step at a time, with your yes at each step. You describe what you want built.
It works out how much process the change needs, writes the design and the code,
and keeps a record of what was decided and why. It starts from your Self as Code
and your Operations as Code, so it already knows who it is building for.

AIDLC is AWS Labs' AI-DLC, free to use (MIT-0), with OpsCode's additions on top.

**What the `aidlc/` folder is.** Its record of every piece of software work: the
questions and your answers, the drafts, the reviewers' notes. It appears only
when you switch AIDLC on. Your plan, your register and your business's direction
never live there.

**Commands:**

| Command | When |
|---|---|
| `/aidlc --scope feature "<what to build>"` | Start a piece of software work |
| `/aidlc` | Carry on with the open piece of work |
| `/aidlc --doctor` | Check it is installed properly |
| `/aidlc --status` | Where the work is up to |

**The rule:** nothing moves to the next step without your say-so. When the
bottom line reads `AIDLC ⚙ …`, it is usually waiting for you.

**Do not run `aidlc plugin select`.** It switches parts of AIDLC off, and it
cannot be undone from inside AIDLC.

## The three together, in one day

1. Open your private repo. `/start` reads your log. `SAC`.
2. Open the business's repo. `/start`, then work on the register or the Context
   Core. `OAC`.
3. The business needs a small tool. `/aidlc --scope feature "…"`. The bottom
   line changes to `AIDLC ⚙` until the work ships, then back to `OAC`.
4. `/done` in each repo before you close it.

## When the bottom line is wrong

- It says `OAC` in your private repo, or `SAC` in a business's repo: the
  settings file is wrong. Fix `.oac/manifest.yml`.
- No mode word in a repo that should have one: `.oac/manifest.yml` is missing.
  Copy it from the pack.
- It shows AIDLC's own line (`[AIDLC] ready | …`) instead: the `AIDLC`
  setting is switched on in your terminal. Switch it off, or leave it if you
  prefer that line while building software.

## Where the cost comes from

Claude Code counts the words in the session (tokens), prices them at the list
price for the model, and passes the figure to the bottom line. `/clear` starts a
new session and the figure goes back to zero. On a Max or Pro plan it is what
the work would have cost if paid for directly, not a charge. Every session is
also logged on your computer, and `python3 scripts/oac-usage-report.py --write`
turns the log into `team/<you>/usage.md`, so the business can see the effort by
month.
