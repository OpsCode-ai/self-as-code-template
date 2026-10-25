---
title: "/github: A private copy on GitHub"
type: guide
audience: internal
---

# /github: A private copy on GitHub

The person types `/github`. This gives their private repo a private copy on
GitHub: their backup, and their sync across devices. It is the one step where
they also type something outside Claude, because signing in to GitHub needs a
plain terminal window.

The install runs these steps, `/sac` runs them if the install could not, and
`/push` and `/done` point here when there is no copy yet. Private repo only: a
business's GitHub is set up at the GitHub step of `/oac`.

## Steps

### 1. Is there a copy already?

```bash
git remote -v
gh repo view --json visibility,url -q '.visibility + " " + .url' 2>/dev/null
```

- **`PRIVATE`:** say so with its web address, and stop.

  > You've already got a private copy on GitHub, at <url>.

- **Anything else** (`PUBLIC`, `INTERNAL`): stop.

  > Your copy on GitHub can be seen by other people. This repo holds who you
  > are, so it needs to be private. Want me to make it private now?

  On a yes: `gh repo edit --visibility private`. Newer versions of `gh` refuse
  without `--accept-visibility-change-consequences`; add it if `gh` asks for it
  (older ones do not know the flag). Never write anything else until it is
  private.
- **A remote `gh` cannot read** (not GitHub, or `gh` not ready): ask whether
  only they can see it. Go on only on a clear yes.

### 2. Is the GitHub CLI installed?

```bash
gh --version
```

Not installed: give the one install line for their computer, to type in a new,
plain terminal window (not this one): macOS `brew install gh`, Windows
`winget install --id GitHub.cli`, anything else cli.github.com.

### 3. Are they signed in?

```bash
gh auth status
```

Not signed in:

> Next, sign in to GitHub. This part happens outside Claude. Open a new
> terminal window, a plain one, not this one, and type `gh auth login`.
>
> Choose GitHub.com, then HTTPS, then yes, then log in with a web browser. Use
> the arrow keys and enter. When the browser says you're done, come back and
> tell me.

The plain window matters. 'Type this in your terminal' reads as already done,
because they are in one, and that is exactly where people get lost. Its
arrow-key menus need a real terminal, too. Never have them paste a personal
access token instead. When they say done, check `gh auth status` again.

### 4. Make the copy, private

The name is this folder's name, which is their repo's name (`jane-smith-ops`).

```bash
gh repo create <this folder's name> --private --source . --remote origin
git push -u origin main
```

Pushing `main` by name, not whatever branch is checked out, means GitHub tracks
`main` even when this runs in the middle of a session on another branch.

- **The name is taken on their account:** ask whether that repo is this one from
  another laptop. If it is, connect to it
  (`git remote add origin <its url>`, then `/pull`) and do not create a second.

### 5. Say what happened

> Done. Your private space has a private copy on GitHub now, at <url>. Nobody
> else can see it unless you invite them. `/push` sends your work up, and
> `/pull` brings it down.

## Rules

- **Always private.** Never `--public`, never `--internal`.
- Never add a collaborator. Access to this repo is the person's choice, made on
  GitHub, never by a command.
