# This repo and its tools

This is the person's private space: one repo, theirs alone, above every
business they run. Only they can see it. It runs on its own, with nothing else
installed (opscode-hq ADR-125).

- **`/sac`** is the one command. It reads the Self as Code framework in
  `.oac/sac-framework.md`, asks its questions in its words, writes
  `self-as-code.md` on a branch, and once they merge it, sends what they chose
  to share to each business as a pull request.
- **The questions stay current.** Before it asks anything, `/sac` runs
  `scripts/sac-brain.py fetch`, which brings the newest questions down from
  OpsCode when `SAC_BRAIN_KEY` is set in `.env` (never committed), and keeps
  the saved copy otherwise. It sends nothing about the person.
- **OpsCode's brain, inside a session.** When this repo is connected to the
  brain (`sac-brain` in `.mcp.json`), its tools are here: `whats_new` (what
  changed in the method since a version), `next_step` (where they are up to)
  and `get_section`. `next_step` takes plan headings and dates only: build its
  input with `python3 scripts/sac-brain.py next --show` and never pass a word
  they wrote. `/sac` still reads the saved copy, because the script checks it
  byte for byte. Not connected, nothing is missing from `/sac`.
- **`/sac dashboard`** draws their plan as one page, `.oac/dashboard.html`,
  from `self-as-code.md` and the five folders, and opens it in the browser.
  It runs `python3 scripts/sac-dashboard.py`. Nothing leaves the laptop.
  Offer it the moment a plan is merged, and whenever they ask to see it.
- **`/sac deploy <business>`** makes one business's own repo from the plan:
  the business pack unpacked at `~/projects/<business>-ops`, named, seeded
  with that business's setup lines and what they chose to share, the first
  commit in, the private hub on GitHub when they are signed in, and this
  repo's manifest pointing at it. It runs `python3 scripts/sac-deploy.py
  <business> --show` first, so they see what crosses, then the same without
  `--show` on their yes. Then `/oac` in the new repo.
- **`/sac meeting <file>`** files a meeting transcript here first
  (`evidence/meetings/`, the original kept under `raw/`), and only the parts
  they say yes to go to a business, as a pull request (`scripts/sac-meeting.py`).
  The transcript itself never leaves this repo, and nothing about anyone's pay,
  ownership or job goes anywhere without their yes to that line.
- **One word opens this repo.** `bash scripts/install-shortcuts.sh` installs
  `sac`: typed in a new Terminal window, it opens this folder with Claude Code
  running, and `sacr` picks up the last conversation. If they ask how to get
  back here, that is the answer. Run it again if the folder moves.
- **No secrets in the chat.** Never ask the person to paste a key or a
  password here, and never print `.env`.
- **`/start`** begins a session by pulling the latest version from GitHub, and
  **`/done`** ends one by committing and pushing.
- **The git is packed into commands:** `/commit` saves a step, `/push` sends it
  to GitHub, `/pull` brings down the latest, and `/github` makes the private
  copy. Git is part of the method here, not just storage: the person takes each
  step by typing the command, and never types a git command. Say what each one
  did, in plain words.
- **The repo on GitHub is private, always.** If it is ever not, stop and say so.
- If they later want to build software from here, OpsCode's build tools can be
  added then. Never install them unasked.

## How to write

Everything Claude writes or says in this repo follows OpsCode's rules against
the signs of AI writing (from Wikipedia's 'Signs of AI writing'):

1. Say the specific thing: the fact, the number, the person's own words. Never a general claim of importance.
2. Use 'is', 'has' and plain verbs. Never `serves as`, `stands as`, `boasts`, `features` or `utilises`.
3. Don't write `not X, it's Y` or `not only X, but Y`. Say what it is.
4. Don't list three things for rhythm. Give the one that matters, or all of them.
5. Never use `delve`, `tapestry`, `testament`, `underscore`, `showcase`, `pivotal`, `vibrant`, `nestled`, `intricate`, `meticulous`, `interplay` or `garner`. Use `crucial`, `enhance`, `foster`, `robust` and `landscape` almost never.
6. Don't end with a summary, a lesson or a forecast. Stop when the point is made.
7. No dashes, no curly quotes, no emoji and no bold for emphasis in what you say. Single straight quotes.
8. Don't open with `Great question`, `Certainly` or `Of course`. Don't close with `I hope this helps` or `Let me know if`.
9. Don't say what experts or sources say unless you name them. If you don't know, say 'I don't know'.
10. No disclaimers about your training or your knowledge, and no `may vary`.
11. Don't praise the person's answers (`profound`, `powerful`, `great insight`). Say them back, sharper.
12. Never leave a placeholder like `[Your Name]` in anything a person reads.
13. Australian English, short sentences, grade 5.
