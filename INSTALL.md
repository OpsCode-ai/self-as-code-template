---
title: "Install: Self as Code"
type: guide
audience: internal
---

# Install: Self as Code

Five minutes to install. About an hour to run.

This is your **private space**: one repo, yours alone, that sits above every
business you run. Only you can see it. Operations as Code runs a business. This
runs you. Everyone does their own, on their own laptop, even when two people
share a business.

You need a free GitHub account. Your private space lives there as a private
repository, which is also your backup and your sync across devices, and you
use it the way people who write code do: you save your work, then send it up,
every day.

## Steps

1. On GitHub, open `https://github.com/OpsCode-ai/self-as-code-pack` and press **Use this template**,
   then **Create a new repository**. Name it `first-last-ops` with your own
   name, and choose **Private**. Or, in a terminal with GitHub's tool signed in:
   ```bash
   gh repo create first-last-ops --template OpsCode-ai/self-as-code-pack --private --clone
   ```
2. Get it onto your computer if the line above did not: on your new
   repository's page, the green **Code** button, then **Open with GitHub
   Desktop**, or copy the address and `git clone` it into `~`.
3. Open Claude Code in that folder and paste the installer prompt below.
4. When it says it is done, restart Claude Code and run `/sac`.

**Done looks like:** the folder has a git history, its private copy is on
GitHub, the bottom line of Claude Code says `SAC`, typing `sac` in a new
Terminal window opens this folder with Claude Code running, and
`self-as-code.md` has your seven steps and what you share with each business,
written by the session, not typed into a template by you.

---

## The installer prompt (paste everything below into Claude Code, running in the folder)

Hi Claude. OpsCode's Self as Code template made this private repo on GitHub and
it is sitting in this folder. Do these steps in order and tell me what you did
after each one.

1. **Check the layout.** Confirm this folder contains `CLAUDE.md`,
   `README.md`, `self-as-code.md`, `INSTALL.md`, `STATUSLINE.md`, `.oac/`,
   `.oac/sac-framework.md`, `.claude/commands/`, `.githooks/`, `scripts/`,
   `specs/`, `team/`, and the five folders that spell SPADE: `standards/`,
   `projects/`, `archive/`, `decisions/` and `evidence/`. If anything is
   missing, stop and tell me.
2. **Check the copy is private.** Run `git remote get-url origin` and
   `gh repo view --json visibility -q .visibility`. Only `PRIVATE` lets you
   go on. If it says anything else, stop and tell me how to make it private
   (`gh repo edit --visibility private`). If `gh` is not signed in, tell me
   to sign in from a new, plain terminal window, not this one, and wait.
3. **Put my name in.** Ask me my first and last name. Then replace
   'Your name' in `self-as-code.md` with my name, 'Your private repo' in
   `README.md` and `CLAUDE.md` with my name followed by 'private repo', and
   `first-last-ops` in `README.md` with the same pattern spelt with my name.
   If this repo is not already called that, tell me how to rename it on
   GitHub.
4. **Turn the hook on and make my folder.** Run
   `git config core.hooksPath .githooks`. Create `team/<firstname>/logs/`
   with a `.gitkeep` inside, using my first name in lowercase. Then commit
   everything as `Day one` and push. If the hook warns that gitleaks is not
   installed, tell me the install command for my computer and carry on.
5. **Install the bottom line.** `python3 scripts/install-oac-statusline.py`
   and tell me what it did.
6. **Install the one word.** `bash scripts/install-shortcuts.sh` and tell me
   what it printed. From then on, a new Terminal window and the word `sac`
   opens this folder with Claude Code running.
7. **Check the files.** `python3 scripts/oac-validate.py .` Tell me the level
   it reports. Do not fix anything.
8. **Read `CLAUDE.md`** and tell me in two lines what this repo is for and why
   it is private.
9. **Tell me you are done**, and what happens next, in order: Claude Code may
   ask me to approve this project's settings, and I should approve them; then I
   fully restart Claude Code; then I run `/sac`. To get back here any day, I
   open a new Terminal window and type `sac`. After today, every session
   starts with `/start`, which pulls the latest version from GitHub, and ends
   with `/done`, which saves my work and pushes it there. In between, `/commit`
   saves a step, `/push` sends it to GitHub and `/pull` brings down the latest.
   And once my plan is written, `/sac dashboard` draws it as a page I can see.

Do not write anything into `self-as-code.md` during this install. That is the
session's job, not the installer's. Install only.
