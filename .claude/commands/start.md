---
title: "/start: Begin a work session"
type: guide
audience: internal
---

# /start: Begin a work session

Thirty seconds. Pull the latest version, then know who you are, where you
left off, and what the business needs before you type anything else.

## Steps

### Step 1: Who

```bash
git config user.name
```

Map the name to a handle: first name, lowercase (`Jane Smith` becomes `jane`).
Save it once to `.claude/user.json` as `{"team_member": "jane"}`. That file is
gitignored. Only ask if the name cannot be derived.

### Step 2: Where you left off

Read the continuity log **first**. It is the primary resume signal:

```
team/{handle}/current.md          today's log
team/{handle}/logs/               the newest file here if today has none yet
```

Surface, verbatim and before anything else, the **Roll-forward** (`**Next:**`
and `**When:**` if present) and the last one or two `### HH:MM` entries.

If there is no log at all, fall back to what git remembers:

```bash
git log --since="7 days ago" --name-only --pretty=format: | sort -u | head -20
```

### Step 3: The state of the plane

```bash
grep '^plane:' .oac/manifest.yml
```

**Business plane** (`plane: business`). Two numbers, read from files, never
invented:

```bash
python3 scripts/systems-register.py --check
python3 scripts/oac-validate.py . | head -8
```

The first gives the manual-process count from `systems/register.md`. That is
the number this repo exists to move. The second gives the OaC conformance
level. If the register still says `status: seeded`, say so: nothing has been
written down yet and the next step is `/oac`.

**Self plane** (`plane: self`). Read the frontmatter of `self-as-code.md`:
`status`, `last_raised`, `next_raise`. If it is still `seeded`, the next step
is `/sac`. If `next_raise` has passed, the next step is
`/sac review`. Otherwise name the days until the next raise and
move on. Then the conformance level, same command as above.

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

### Step 5: Put the operator back in the room

Lead with the roll-forward, always:

```
Roll-forward from {date}:
   "{roll_forward_text}"
   When: {when, if given}

Register: {n} processes, {m} still manual. Level {k}.        (business plane)
Your plan: {status}, next review {date} ({n} days). Level {k}. (self plane)
GitHub: pulled {n} changes | already up to date | no copy on GitHub yet.
Repo: clean | {n} uncommitted. On {branch}.
```

**If the roll-forward names one clear next thing**, offer to start it. Do not
present a menu when the answer is already written down.

**If there is nothing** (new repo, empty log), say that in one line and name
the honest first move: `/oac` if the register is seeded, `/sac`
if the spine is, otherwise ask what they are working on.

### Step 6: The loop

```
Work in this folder. Finish with /done: it validates, writes your continuity
note, commits, and pushes to GitHub. /task-bridge drops a note any time.
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
| `team/{handle}/current.md` | The continuity log. `/done` writes it, `/start` reads it |
| `team/{handle}/logs/{date}.md` | Archived days |
| `systems/register.md` | What the business runs on today (business plane) |
| `self-as-code.md` | The spine, with `next_raise` (self plane) |
