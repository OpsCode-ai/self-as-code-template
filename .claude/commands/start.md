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

Uncommitted files from last time get one line too:

```bash
git status --porcelain | wc -l
```

### Step 5: Say where they are

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

While one person works in this repo, everything happens on `main` and `/done`
pushes straight there. **When `team/` has more than one person**, start the
day on `main` and up to date, then on your own branch:

```bash
git switch main && git pull --ff-only
python3 scripts/oac-hub.py branch
```

`/done` merges that branch at the end of the session. Each laptop's files come
in with `python3 scripts/oac-hub.py inbox <path>...`, into `inbox/<you>/`, so
nothing collides. Worktrees, for one person running two sessions, are in
`WORKING.md`.

## Files

| File | Purpose |
|---|---|
| `.claude/user.json` | Local identity, gitignored |
| `evidence/days/current.md` | Your log in a private space. `/done` writes it, `/start` reads it; older days beside it, by date |
| `team/{handle}/current.md` | Your log in a business; older days in `team/{handle}/logs/` |
| `systems/register.md` | What the business runs on today (a business) |
| `self-as-code.md` | Your plan, with `next_raise` (a private space) |
