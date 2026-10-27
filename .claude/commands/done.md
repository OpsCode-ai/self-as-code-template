---
title: "/done: Finish a work session"
type: guide
audience: internal
---

# /done: Finish a work session

One minute. Check the files, write your note for next time, save, send it to
GitHub.
Nothing you did today stays only on this laptop.

## Steps

### Step 1: What changed

```bash
git status --porcelain
git diff --stat
```

List what this session actually touched. Anything you cannot account for,
leave alone and mention it. Never `git add .` or `git add -A`: stage by path.

If nothing changed, say so and stop.

### Step 2: A big piece of work?

If the session added a new command, a new script, a new decision or a new
folder, and there is no `YYYY-MM-DD-*.md` for today in the build-log folder,
offer `/build-log` once. It is an offer, not a gate. The folder is
`build-logs/` in a business and `evidence/build-logs/` in a private space,
where a build log is evidence like everything else you keep.

### Step 3: Update the lists

- A new file in `decisions/` gets a row in `decisions/README.md`.
- A new folder under `context-core/` gets a row in `context-core/README.md`.

### Step 4: Check the files

```bash
python3 scripts/oac-validate.py --changed
```

Every document carries `title`, `type` and `audience`, with lists in flow
style. Fix level 1 findings on files this session wrote. Leave files it did not
touch. The pre-commit hook checks the same thing and blocks a new document
below level 1, so fixing it here saves a second round.

### Step 5: Write the note for next time

Follow `.claude/commands/task-bridge.md` for the file shape. You were there for
the session, so draft it without asking:

1. Handle from `git config user.name`.
2. If the log's `current.md` carries a `date:` that is not today, move it
   to its older-days place first: `evidence/days/{that-date}.md` in a private
   space, `team/{handle}/logs/{that-date}.md` in a business. Never overwrite
   an archived day.
3. Append a `### HH:MM` entry: what happened, one short paragraph.
4. Replace the Roll-forward only if this session produced a real next step.

Ask exactly one question, and only at the end of the day:

> Anything for tomorrow that is not already written down as next?

### Step 5a: The floor, one word per line (a private space only)

Read `## the floor` in `self-as-code.md`. Each `Value:` line is one value with
its worst-day line. If there are none, or this is a business, skip this step.
Otherwise ask once, naming every value in the order the plan lists them:

> Your floor today: {name}, {name}, {name}. A yes or a no for each.

Write the answers as the last line of today's entry, in the same order:

```
Floor: {name} yes · {name} no · {name} yes
```

One line, nothing else. If they do not answer, write nothing: a floor nobody
checked is not a no. The message at the top of the next session counts the
days held and names what slipped most.

### Step 5b: Refresh your usage page

```bash
python3 scripts/oac-usage-report.py --write
```

Writes `usage.md` beside the log (`evidence/days/` in a private space,
`team/{handle}/` in a business) from the statusline's ledger on this machine:
sessions, hours, cost, tokens by month. Cost is Claude Code's own figure, not
a bill. Include the file in the commit. If the script is missing, skip this
step and say so.

### Step 6: Commit

Follow the `/commit` steps (`.claude/commands/commit.md`): the same command the
person types, so the git lives in one place. Stage by path: each file this
session changed, plus your note and usage page from steps 5 and 5b.
The message takes this format:

```
{Action}: {brief description}

- {one bullet per significant change}
```

Actions: `Add`, `Update`, `Remove`, `Fix`, `Docs`.

```bash
git add -- {each path this session changed} {the log's current.md} {its usage.md}
git commit -m "$(cat <<'EOF'
{message}
EOF
)"
```

The pre-commit hook runs: a secret scan if gitleaks is installed, the
owner-audience check, and the frontmatter check. If it blocks, read what it
says and fix that. Do not reach for `--no-verify`.

### Step 7: Push to GitHub

Say it plainly as you do it: 'Pushing today's work to GitHub, so it is backed
up and on every device.' Git is part of the method here, so the person should
always know when it runs.

Run the `/push` steps (`.claude/commands/push.md`). It pulls first if GitHub
has work this laptop does not, and it never forces.

**No copy on GitHub yet:** the commit is safe on this laptop and nowhere else.
Say so plainly.

- **A private space** (`plane: self`): offer `/github`, which makes a private copy
  now (`.claude/commands/github.md`). On a no, leave it for next time.
- **A business** (`plane: business`): point at the GitHub step of the
  install order (`/oac` step 5) and stop here. Do not create a remote from this
  command; the business's repo names and who can see them are decided there.

### Step 8: Close

```
Saved: {n} files. {message first line}
Sent to GitHub ({remote}) | Not sent: no copy on GitHub yet
Your note for next time is written. Next: {roll-forward}
```

## One person, then two

While you are the only person in this repo, committing to `main` and pushing
is correct and this command does exactly that.

**When `team/` has more than one person** (a business with two founders, or
anyone who joined through `python3 scripts/oac-hub.py join`), nobody commits
to `main` directly:

1. Be on your own branch, `<handle>/<date>`. On `main`, run
   `python3 scripts/oac-hub.py branch` first; it makes or switches to it and
   carries your uncommitted work along.
2. Commit by path on that branch, as above, then push it:
   `git push -u origin <branch>`.
3. Open the pull request and merge it, unless the business has asked for a
   review first: `gh pr create --fill --base main && gh pr merge --merge --delete-branch`.
4. Back to `main` and up to date: `git switch main && git pull --ff-only`.
   Tomorrow's `/start` makes tomorrow's branch.

Say what happened in plain words: 'saved on your branch, merged into the
shared copy, and pulled back down'. Two people editing the same file on the
same day can still clash; when the merge says so, show them the two versions
and let them choose, never guess. Access by role, for staff who should see
only part of the repo, comes later from OpsCode.

## Rules

- Stage by path. A blanket add takes files you did not mean to commit.
- Never commit `.env`, credentials, or anything `audience: owner`. The hook
  blocks the last two; the first is on you.
- Your note for next time goes in the same save as the work it describes.
