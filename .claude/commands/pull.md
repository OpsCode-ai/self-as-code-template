---
title: "/pull: Bring down the latest version"
type: guide
audience: internal
---

# /pull: Bring down the latest version

The person types `/pull`. This does the git for them and says what happened in
plain words. They never type a git command themselves.

A pull is the opposite of a push. It brings down the latest version from
GitHub, so whichever device they are on, they start from where they left off.
`/start` runs these same steps at the start of a session.

## Steps

### 1. Is there a copy on GitHub?

```bash
git remote -v
```

No remote: say so in one line and stop. In a private repo (`plane: self` in
`.oac/manifest.yml`), add that `/github` sets one up.

> There's no copy on GitHub yet, so there's nothing to bring down.

### 2. Does this branch have a copy on GitHub?

```bash
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null
```

Nothing printed: this branch was made for one piece of work and is not on
GitHub yet. Run `git fetch --quiet`, say so in one line, and stop. `/push` puts
it there.

### 3. Pull

```bash
before=$(git rev-parse HEAD)
git pull --ff-only
```

- **Changes not saved yet are in the way:** say which files, and offer `/commit`
  first. Never throw their changes away to make the pull work.
- **This laptop and GitHub have both moved** (work saved in both places):
  `git pull --rebase`, and say in one line that you are putting their new steps
  after the ones from GitHub.
- **A conflict:** stop and walk them through it, one file at a time.

### 4. Say what happened

When something came down (count it with
`git rev-list --count $before..HEAD`):

> Pulled 3 changes from GitHub. You're up to date.

When nothing did:

> Already up to date. This laptop and GitHub match.

## Rules

- Never `git reset --hard`, never `git checkout -- .`, never `git clean`. A pull
  never costs them unsaved work.
