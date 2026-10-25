---
title: "/push: Send your saved work to GitHub"
type: guide
audience: internal
---

# /push: Send your saved work to GitHub

The person types `/push`. This does the git for them and says what happened in
plain words. They never type a git command themselves.

A push sends saved steps from this laptop up to the copy on GitHub, so the
work is backed up and on every device. `/done` runs these same steps at the end
of a session.

## Steps

### 1. Is there a copy on GitHub?

```bash
git remote -v
grep '^plane:' .oac/manifest.yml
```

No remote: say so, and stop.

- In a private repo (`plane: self`):

  > There's no copy on GitHub yet, so this is only on this laptop. Type
  > `/github` and I'll set up a private one.

- In a business repo (`plane: business`): the business's GitHub is set up at
  the GitHub step of `/oac`. Say that in one line and stop. Never create a
  remote from this command.

### 2. Anything not saved yet?

```bash
git status --porcelain
```

If there are changes, ask once:

> You've got changes that aren't saved yet. Save them first with `/commit`?

On a yes, run the `/commit` steps (`.claude/commands/commit.md`), then carry on.
On a no, push what is saved and leave the rest.

### 3. Push

```bash
git push
```

- **This branch is not on GitHub yet:** `git push -u origin HEAD`.
- **A merge was made from another folder** (you are not on `main`, but `main`
  is ahead of GitHub's copy): push `main` too, with `git push origin main`.
  Check with `git rev-list --count origin/main..main`.
- **GitHub refuses because it has work this laptop does not** (saved from
  another device): run the `/pull` steps (`.claude/commands/pull.md`), then push
  again, and say why in one line.
- **A conflict:** stop and walk them through it, one file at a time.

**Never force a push.** It can wipe out work saved from another device.

### 4. Say what happened

> Sent to GitHub. Your saved work is backed up now, and you can open it from any
> device.

## Rules

- Push what is saved. Never save something on their behalf just to push it.
- Never `--force`, never `--force-with-lease`, whatever the error says.
