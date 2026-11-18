---
title: "/start: Begin a work session"
type: guide
audience: internal
---

# /start: Begin a work session

Thirty seconds. Bring down the latest copy, then know who you are, where you
left off, and what needs doing before you type anything else.

## Steps

### Step 1: Who

```bash
git config user.name
```

Map the name to a handle: first name, lowercase (`Jane Smith` becomes `jane`).
Save it once to `.claude/user.json` as `{"team_member": "jane"}`. That file is
gitignored. Only ask if the name cannot be derived.

### Step 2: Where you left off

Read your log **first**. It is how you pick up the thread:

```
evidence/days/current.md          today's log, in a private space; older days beside it, by date
team/{handle}/current.md          today's log, in a business
team/{handle}/logs/               a business's older days; the newest file if today has none yet
```

Read out, word for word and before anything else, the **Next** line under
`## Roll-forward` (and **When**, if there is one) and the last one or two
`### HH:MM` entries.

If there is no log at all, fall back to what git remembers:

```bash
git log --since="7 days ago" --name-only --pretty=format: | sort -u | head -20
```

### Step 3: Where things are up to

```bash
grep '^plane:' .oac/manifest.yml
```

**A business** (`plane: business`). Two numbers, read from files, never
invented:

```bash
python3 scripts/systems-register.py --check
python3 scripts/oac-validate.py . | head -8
```

The first is how many processes still run by hand, from
`systems/register.md`. That is the number this repo exists to bring down. The
second is how complete the files are, a level from 0 to 3. If the register
still says `status: seeded`, say so: nothing has been written down yet and the
next step is `/oac`.

**A private space** (`plane: self`). Read the top of `self-as-code.md`:
`status`, `last_raised`, `next_raise`. If it is still `seeded`, the next step
is `/sac`. If `next_raise` has passed, the next step is `/sac review`.
Otherwise say how many days until the next review and move on. Then the
level, same command as above.

### Step 4: Pull the latest version

Say it plainly as you do it: 'Pulling the latest version from GitHub.' Git is
part of the method here, so the person should always know when it runs.

Run the `/pull` steps (`.claude/commands/pull.md`): the same command the person
types, so the git lives in one place. It says what came down, or that this
laptop and GitHub already match, or that there is no copy on GitHub yet. If it
stops on something (unsaved changes in the way, a conflict), sort that out
before any work starts.

Then check nothing is waiting to be saved, on any branch:

```bash
python3 scripts/oac-sync-check.py --no-fetch --risks
```

It only looks. If it lists anything, say it in plain words and offer to save
it: 'You have 2 files from last time that are not saved yet' or 'Your
branch from Tuesday has work that is not on GitHub yet. Send it now?' On a
yes, run the `/commit` steps for files and the `/push` steps for that branch.
If it says everything is saved, say nothing about it.

### Step 4b: A folder of its own for this session

Every session works in its own folder, beside the repo, so nothing else on
this laptop can save or switch something under it: not a second window, not
a timed job. The person never types a command for this. This step does it,
and `/done` brings the work back and closes the folder.

```bash
python3 scripts/oac-worktree.py where
```

**It says `session <short> <branch> <path>`:** this session already has its
folder. Say so in one line, 'Working in `{short}`', and go to step 5.

**It says `main <path>`:** first look at the folders already open.

```bash
git worktree list
```

Any listed under `{repo}-sessions/` were left by an earlier session. Another
window may still be using one, so ask once, naming them, before you touch
any: 'You have 2 other session folders open: `price-page` and `nov-17`. If no
other window is using them, close them?' On a yes, run
`python3 scripts/oac-worktree.py close <short>` for each. It only closes a
folder whose work is saved and already in `main`. When it refuses, say why
in plain words and offer the fix:

- **Unsaved files:** leave it. That window still has work in it.
- **Saves not in `main` yet:** one person, offer to bring them home now. Run
  `git merge --no-edit <branch>`, then the `/push` steps, then `close` again.
  More than one person, the branch goes by pull request, as `/done` does it.

Then open this session's folder. Name it from the work, two or three
lowercase words joined by dashes (`price-page`): the **Next** line from step
2, or what they typed after `/start`. With nothing named, use today's date
(`2026-11-18`).

```bash
python3 scripts/oac-worktree.py open <short>
```

Its last line is the folder's path. Move this session into it with the
`EnterWorktree` tool, `path:` that line. Then say it once:

> This session has its own folder, `{short}`, so nothing else on this laptop
> can get in its way. `/done` brings the work back and closes it.

The status line shows `⧉ {short}` from here on. If `EnterWorktree` is not
there (an older Claude Code), run `close <short>` at once and carry on in the
main folder as before. `/done` works there too.

### Step 5: Say where they are

**The words come from the saved method, by version**, so every install says
the same thing and one edit reaches them all:

```bash
python3 scripts/sac-brain.py section start     # a private space
python3 scripts/oac-brain.py section start     # a business
```

Say what it prints, each line filled from the files above and never made up.
If it exits 1 (no saved copy yet, or an older version without the section),
say the lines below instead; they are the same words.

Lead with what they said they would do next, always:

```
Last time you said: "{roll_forward_text}" ({date})
   When: {when, if given}

Your business: {n} processes written down, {m} still by hand. Files at level {k}.   (a business)
Your plan: next review {date}, in {n} days. Files at level {k}.                    (a private space)
GitHub: {n} changes came down | you are up to date | no copy on GitHub yet.
Unsaved: nothing | {n} files from last time. On {branch}.
```

In a private space, the box headed HOW YOU'RE GOING at the top of the screen
is the check-in: the floor held so many of the days you checked, each
business moved or quiet, today's one thing, the next moment. Read it out, one
line each, and offer the Today line as the first thing to do.

**If the note names one clear next thing**, offer to start it. Do not
present a menu when the answer is already written down.

**If there is nothing** (new repo, empty log), say that in one line and name
the honest first move: `/oac` in a business that has not started, `/sac` in
a private space that has not, otherwise ask what they are working on.

### Step 6: The loop

```
Work in this folder. Finish with /done: it checks the files, writes your note
for next time, saves, and sends it to GitHub. /task-bridge leaves a note any time.
```

## One person, then two

Step 4b gives every session its own folder on its own branch,
`<handle>/<short>`, so one person with two windows open is safe from the
first day. The only thing that changes when **`team/` has more than one
person** is the end: `/done` merges your branch by pull request on GitHub,
never straight into `main`. Each laptop's files come in with
`python3 scripts/oac-hub.py inbox <path>...`, into `inbox/<you>/`, so nothing
collides. `WORKING.md` says how it all fits.

## Files

| File | Purpose |
|---|---|
| `.claude/user.json` | Local identity, gitignored. `oac-worktree.py open` copies it into each session folder |
| `{repo}-sessions/<short>/` | This session's folder, beside the repo. `/start` opens it, `/done` closes it |
| `evidence/days/current.md` | Your log in a private space. `/done` writes it, `/start` reads it; older days beside it, by date |
| `team/{handle}/current.md` | Your log in a business; older days in `team/{handle}/logs/` |
| `systems/register.md` | What the business runs on today (a business) |
| `self-as-code.md` | Your plan, with `next_raise` (a private space) |
