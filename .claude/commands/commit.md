---
title: "/commit: Save one step"
type: guide
audience: internal
---

# /commit: Save one step

The person types `/commit`, or `/commit` and a short note. This does the git
for them and says what happened in plain words. They never type a git command
themselves.

A commit is one small saved step, with a note saying what it was. It stays on
this laptop until `/push` sends it to GitHub. `/done` runs these same steps at
the end of a session.

## Steps

### 1. What changed

```bash
git status --porcelain
```

Nothing changed: say so and stop.

> Nothing new to save. Everything is already saved.

### 2. Choose what to save, by path

Stage each changed file by name: `git add -- <path> <path>`. Never `git add -A`
or `git add .`, because a blanket add takes files nobody meant to save.

- A file you cannot account for: name it and ask whether it belongs in this
  save. Leave it out unless they say yes.
- Never stage `.env`, a key, or a password file, whatever they say.

### 3. The note

Use the note they typed after `/commit`. If there is none, write one short line
from what changed, in their words ('My daily non-negotiables', 'Notes from the
Acme call'), and use it without asking. In a business repo, start it with one of
`Add`, `Update`, `Fix`, `Remove` or `Docs` and a colon.

### 4. Save

```bash
git commit -m "<the note>"
```

The pre-commit hook runs first. If it blocks, say what it found in one plain
line, fix that, and try again. Never `--no-verify`.

### 5. Say what happened

One line, in plain words:

> Saved one step: '<the note>'. It's on this laptop. Type `/push` to send it to
> GitHub.

If there is no copy on GitHub yet, leave out the last sentence.

## Rules

- One save, one idea. If the changes are two different things, offer to save
  them as two.
- Never change what is saved after it is saved (no `--amend`), unless they ask.
