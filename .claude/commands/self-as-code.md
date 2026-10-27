---
title: "/self-as-code: Run your Self as Code session"
type: guide
audience: internal
summary: "The canonical Self as Code command. Runs the plain method, with no AI-DLC: it reads the Self as Code framework and speaks only in its words, writes self-as-code.md on a branch that the person merges, and sends what they choose to share to each business as a pull request. Every pack copy is generated from this file by the pack builder; edit it here only."
topics: [self-as-code, strategic-identity]
tags: [oac, sac, command, canonical, adr-125]
---

# /self-as-code: Run your Self as Code session

Runs **Self as Code**. It coaches the person through why they exist, who they
are becoming and the standard they will not drop below. It writes that into
`self-as-code.md` in their private repo, then turns it into tracked,
time-blocked work. From then on, every Claude Code session reads who they are
becoming and holds them to it.

AU English. Plain language, no clichés.

## First: read the framework, then speak only in its words

Before you say anything, get the Self as Code framework, then read it:

- **in a pack:** first run `python3 scripts/sac-brain.py fetch`. It brings the
  newest version down from the SAC brain (ADR-125 Rule 5) into
  `.oac/sac-framework.md` when this install has a key (`SAC_BRAIN_KEY` in
  `.env`), and otherwise keeps the saved copy there. It sends nothing about the
  person and never fails the session: if the brain is out of reach it says so
  and the saved copy is used. Its line is for you, not the person, so say
  nothing about it to them. Then read `.oac/sac-framework.md`.
- **in opscode-hq:** read `code/workers/sac-brain/framework.md` directly. It is
  the current version the brain serves.

It holds every question, the plain meaning of every method word and code word,
the check before moving on, and the ending. **Say only what it says, in your own
natural voice.** Its 'For the agent' section lists the words never said to the
person; follow it exactly, including in your own replies. Record its
`framework_version` in the frontmatter of `self-as-code.md`.

If there is still no copy after that, say so in one line and stop. Do not
improvise the method from memory.

This command runs the same way every time. Apart from that fetch, it never looks
for, starts or hands over to any other tool, and it writes nothing outside this
repo except the pull requests the person agrees to at the end (ADR-125).

## Modes

| Invocation | What it does |
|---|---|
| `/self-as-code` | **setup.** A private copy on GitHub, where they are today (every business they run), the seven steps, what they share with each business, `self-as-code.md` on a branch they merge and push, the CLAUDE.md rule, the next actions. |
| `/self-as-code deploy <business>` | Set up `{business}-ops` for one business, from what setup captured. Seeds its Context Core and its systems register, and writes the link back. |
| `/self-as-code review` | The 90-day review (`refactor` still works). Lift the floor on what the last three months proved; move the old version into `## history`. |
| `/self-as-code check` | The always-growing checks over who they are becoming, their floor and their recent commits. Say where they are coasting rather than growing. |
| `/self-as-code execution` | Planning the week: sort tasks, tie them to the one big leap, build the plan, propose strict time-blocks. |
| `/self-as-code dashboard` | Their plan drawn as one page, on this laptop. Reads `self-as-code.md` and the five folders, writes `.oac/dashboard.html` and opens it. Nothing leaves the laptop. |
| `/self-as-code voice` | How they want to sound, from three things they wrote, into `standards/voice.md`; what they like to look at into `standards/brand.md`. Once; also asked the first time anything is made for them while `voice.md` is still the seed. |
| `/self-as-code help` | The one page: the four words to know, where things are, when. Also what you say when `/sac` is given a word it does not know. |
| `/self-as-code meeting <file>` | A meeting transcript lands here first (`evidence/meetings/`), then the parts the person chooses go to each business as a pull request. The transcript never leaves this repo. |

**Run this in their private repo, `{first}-{last}-ops`, never in a business
repo.** It writes who they are, and everyone who works in a business can read
that business's repo (ADR-118). If the bottom line of the screen does not say
`SAC`, check where you are before going on.

## A private copy on GitHub, checked first

Git and GitHub are the method, not just the storage: the person works on their
life the way a developer works on code. Their repo lives on GitHub as a private
repository, which is also their backup and their sync across devices. The git
itself is packed into four short commands that ship beside this one:
`/github`, `/commit`, `/push` and `/pull` (`.claude/commands/`). The person
types them; they never type a git command.

Check the copy after the opening, before the first question:

1. **A remote exists:** check it the way `/github` step 1 does. Only `PRIVATE`
   lets you go on. Never write `self-as-code.md` into a repo others can read.
2. **No remote:** the framework's 'Your copy on GitHub' section has them type
   `/github`, which signs them in (from a plain terminal window) and makes the
   private copy.
3. **It cannot be done today:** run the session anyway, on this laptop only,
   and skip the push and the pull at the end. `/push` and `/done` offer
   `/github` again.

## Write on a branch; the merge is the yes

Self as Code is approved the git way (ADR-125 Rule 3): the plan is written on a
branch and becomes theirs when they merge it. Nothing is final until they say so.

1. **After the GitHub check, before the first question**, make the branch:
   `git switch -c sac/$(date +%Y-%m-%d)`. If a guard refuses because this is the
   main folder, run the `git worktree add` line it prints, and work there.
2. **Commit after each step**, with the step's plain name as the message
   ('Your purpose', 'Your minimum'). The framework teaches what a commit is in
   step 6; by then they have watched five. **Step 6 they save themselves**, by
   typing `/commit` with a note, as the framework says.
3. **At the end**, read the plan back in five or six sentences and ask if they
   want to merge it. On a clear yes, you merge:
   `git switch main && git merge --no-ff sac/<date> -m "Self as Code, <date>"`,
   then delete the branch. Then **they type `/push`, then `/pull`**, as the
   framework's ending says. In a worktree, run the merge from the main folder
   (`git -C <main folder> merge --no-ff sac/<date>`). `/push` still works there,
   because it sends `main` when `main` is ahead of GitHub's copy; skip `/pull`
   in a worktree and let their next `/start` teach it. On anything but a yes,
   leave the branch and tell them the one line to merge it later.
4. **Then draw it.** Once the plan is merged, run the dashboard (below) so
   they see their plan drawn before they leave. Nobody can see a folder
   structure; they can see a page.

The person takes exactly three git steps in the first session: `/commit`,
`/push` and `/pull`. You run everything else, and anything fiddly.

## How to coach

Use the framework's loop on every step: go one layer deeper, check it is
complete, look for clashes with earlier answers, say it back sharper, and push
back once on a soft answer. Who they are comes before the numbers. Credit the
ideas once each (Hardy for the floor, Sullivan and Nomura for the always-growing
checks, Ziglar for the opening line), never at every step. Match their energy.

## Where to look: inward and upward, never outward

- **Inward.** Read their own context: this repo, earlier plans, the answers so
  far. If there is none, build it from where they are today. Never require it.
- **Upward.** Ground what you say in the method's own sources (the framework,
  `methodology-self-as-code.md` where it exists), not your memory.
- **Never outward.** No live web research about the person during a session.

## setup: the run

Follow the framework in order: the opening, the copy on GitHub if it is
missing, where you are today, then steps 1 to 7. Take their work slowly, one
thing at a time: each business, the job, the family. Everything `deploy` builds
later comes from those answers, and it is often the first time someone hears
their own portfolio read back.

**One question at a time, in the framework's order.** Ask it, wait for the
answer, then the next. Never two questions in one turn, never a step before
the one that comes first, never a question the framework does not ask. If
they answer a later question early, keep the answer and still walk the steps
in order. The order is the method; a session that drifts from it is not
running Self as Code (Adam's run, 27 October 2026).

Then write `self-as-code.md`: frontmatter with `last_raised`, `next_raise` and
`framework_version`; a `##` section per step plus `## the baseline`, headings
exactly as the framework lists them, each with its one plain line underneath.
Then install the context rule below.

## Sharing with each business, before you finish

The framework's 'Sharing with your businesses' section is what you say. This is
the mechanics.

Go through their answers once more. Give every line exactly one decision,
recorded as a table under `## the split`. The columns are fixed because a script
reads them (OaC spec 7.1): `Slice | Beat | Routing | Destination`. A slice is a
one-line **statement** in their words, not a file: 'the six-month target for
OpsCode is 40 businesses on the platform'.

| Routing | Where it goes | Typical |
|---|---|---|
| `stays-personal` | here, and nowhere else | health, family, the fear underneath the revenue number |
| `routes-to` | the business named in `Destination`, as `<business>` or `<business>/<venture>`, into its `context-core/strategic-identity/` | this business's six-month target, the roles its cut implies |
| `promotable-unrouted` | here, parked | a real business idea that belongs to none of them yet |

Write each value bare, `| routes-to |`, never bold or in ticks. Check the table
with `python3 scripts/self-as-code-split.py --check`.

Three rules. The third matters most:

1. **They decide, you suggest.** Never send something to a business on their
   behalf.
2. **`promotable-unrouted` is a real answer**, not a failure to decide.
3. **Anything not decided stays personal.** Fail closed. Holding something back
   costs a quarter's delay. Sending private material to a repo their bookkeeper
   can read cannot be undone.

Only the decision crosses, never the session. A business learns 'the
six-month target is X', never why.

## Send it, after the merge

A decision nobody acts on is not finished, so the session that writes the table
also sends it, once the plan is merged.

1. Check the table: `python3 scripts/self-as-code-split.py --check`. Fix
   anything it names first.
2. Read `operations:` in `.oac/manifest.yml`: the businesses they have said they
   run. For each one with at least one `routes-to` row:
   - Find its repo. Look in `~/projects/<business>` first, then
     `~/projects/<business>-ops`. Confirm in one plain line: 'I'll send these
     to your OpsCode repo at ~/projects/opscode-hq. Okay?' Never guess past a
     no, and never write into a repo they did not name.
   - If that repo is on `main`, put it on a branch in a worktree first. The
     script refuses `main` and prints the exact `git worktree add` line; run it,
     then target the worktree.
   - Send: `python3 scripts/self-as-code-split.py --apply --unit <business> --target <the worktree>`.
     It writes one document into `context-core/strategic-identity/`, commits it
     on the branch, pushes, and prints the pull request to open.
   - If the business has no repo yet, say so and stop for that one. `deploy`
     makes it.
3. Report in one short list: business, where, how many lines went, the pull
   request. Businesses that got nothing are not mentioned.

Nothing marked `stays-personal` or `promotable-unrouted` crosses. No file from
this repo is copied. Nothing is moved. Those are the script's rules, not yours to
relax.

## Storage and privacy

`self-as-code.md` lives in their private repo, `{first}-{last}-ops` (ADR-111,
ADR-118). Nobody else is a collaborator on it by default. It is a repo and not a
folder for one reason: access is granted per repository, so the first person
they invited into any business would otherwise read who they are, their goals
and their other companies.

Personal material stays private by default. A business sees a line only through
the sharing step, and only on their say-so. Their deepest personal work belongs
somewhere more private still, and never enters Self as Code.

## Install the context rule (first run only)

Append to this repo's `CLAUDE.md` (create the section if it is missing):

```markdown
## Self as Code
This repo contains `self-as-code.md`: why I exist, who I am becoming, and the standards I hold.
Read it at the start of work. When I ask whether to build, take or do something, answer against
my purpose, who I am becoming and my one big leap. Flag anything that belongs on the cut. Say so
when a plan drops below my floor. Run the always-growing checks (future bigger than past,
contribution bigger than reward, learning bigger than experience, purpose bigger than money, and
the rest) over who I am becoming, my floor and my reviews, and tell me when I am coasting rather
than growing. On my `next_raise` date, prompt me to run `/sac review`.
Anything made for me (an email, a page, a report, an app) reads `standards/voice.md`, `standards/brand.md` and the page for its kind in `standards/outputs/` first, and is shown to me before it goes anywhere. If `standards/voice.md` is still the seed, ask me the voice questions once (`/sac voice`) before making the first thing.
```

## deploy: set up one business

`/self-as-code deploy <business>`. Once per business, and only after setup.
Ask which one first; do not offer all of them at once, because the first one is
the one they learn on. The framework's 'Setting up a business' section is what
you say.

It makes a **separate repo**, `{business}-ops`, never a folder in here. The
mechanics are one script, `scripts/sac-deploy.py`; the words are yours.

1. **Show what crosses first.** Run
   `python3 scripts/sac-deploy.py <business> --show`. It names the
   business as the plan spells it, where the repo will go, the lines its block
   carries (kind, years, people, what it runs on, what to build first, how it
   serves their why) and the statements they chose to share with it under
   `## the split`. Read that back to them. Nothing else from this repo crosses:
   not their words about the business, not another heading, not a file. If the
   plan does not name the business, it says which ones it does; add the block
   with `/sac` rather than typing a name past it.
2. **On their yes, run it without `--show`.** It unpacks the Operations as
   Code pack (the copy in `.oac/`, so no download; `--fetch` refreshes that
   copy from plans.opscode.ai) into `~/projects/{business}-ops`, names it,
   points its manifest back here, and writes the seeds before the first
   commit: the shared statements and the setup lines in
   `context-core/strategic-identity/from-self-as-code.md`, one software row
   per thing in 'runs on' and the 'build first' line as the first process in
   `systems/register.md`, and `systems/team.md`. Then one commit on `main`,
   'Operations as Code: day one', through the pack's own hook.
3. **GitHub, private.** When they are signed in, the pack's hub tool makes the
   private repo and pushes. When they are not, it says so and the repo stays
   on this laptop; `python3 scripts/oac-hub.py create` in that folder does it
   later. `--local` skips it on purpose.
4. **The link back is written for you.** This repo's manifest lists the new
   repo under `operations:`, committed by path. `/push` sends it.

Then say plainly what just happened: they now have one repo they can give
people access to, and one they never will. Their next step is `/oac` in the
new repo, which reads what was shared first and never asks for it again. If two
people share the business, the second joins through GitHub afterwards; the
business repo's own `/oac` says how.

## week: Sunday plans it, Friday reviews it

`/self-as-code week`, or `execution`, the older name. The framework's
'Planning your week' is what you say. The day decides what happens: on a
Sunday, or any day they ask to plan, you write the week; on a Friday, or any
day they ask to review, you finish it; on any other day you read it back and
change nothing.

The page is `projects/weeks/<year>-w<NN>.md`, ISO week, one per week:

```markdown
---
title: "Week 44, 27 October to 2 November"
type: report
audience: owner
week: 2026-W44
from: 2026-10-27
to: 2026-11-02
status: planned
---

## the three
- {the thing}: serves the leap | holds the floor. From {the plan | OpsCode's goal | the inbox}.

## each business
- {Business}: {the one thing this week}

## the days
- Mon: {daily steps first}; {fixed things}; {the work}
- Tue: ...

## parked
- {thing}, settled by {date}

## Friday
- moved: ...
- held: the floor {n} of {m} days; {line} slipped
- carries: ...
- one line for the review: ...
```

Before you ask anything on a Friday, read: the page; the log's `Floor:` lines
for the week (`team/<handle>/current.md` and `logs/`); each business repo's
commits this week (`~/projects/<business>` or `<business>-ops`, `git log
--since` of the Monday). Say what you found, then ask the framework's three.
Set `status: reviewed` when Friday is written. Commit the page by path; they
merge and `/push` as always.

Never log their deepest private material, and never write a business's own
documents into this repo: one line per business is a pointer, not a copy.

## dashboard: see your plan drawn

`/self-as-code dashboard`. Any time, and always straight after the first
plan is merged. Run:

```bash
python3 scripts/sac-dashboard.py
```

It reads `self-as-code.md` and the five folders, writes `.oac/dashboard.html`
and opens it in the browser. It makes no network call and loads nothing from
the web; the fonts are embedded from disk. Then say, in one line, what the
page shows: the ladder from the future back to tomorrow, why they exist, who
they are becoming, the leap, the floor, the cut, the daily steps, each
business, anything parked, what they share, and their folders.

If the script says there is no plan yet, say so and offer `/sac`. If a
browser does not open, give them the path to open themselves. Never edit the
page by hand; it is rebuilt from the plan every time.

## meeting: a meeting lands here first, then goes to each business

`/self-as-code meeting <file>`. The file is a transcript: Zoom's `.vtt`, any
`.srt`, or the text Fireflies, Otter or Read.ai export. Adam, 23 October 2026:
'Self as Code should be the one that has the meetings.' It lands here, in the
private repo, and only the parts the person chooses go to each business, as a
pull request they merge (ADR-127 Rule 5). The mechanics are
`scripts/sac-meeting.py`; the words are yours.

1. **File it.** `python3 scripts/sac-meeting.py file <file>`, with
   `--title`, `--date` or `--with "Name, Name"` when the file name does not
   say. It keeps the original in `evidence/meetings/raw/`, writes a clean copy
   with speaker turns to `evidence/meetings/<date>-<slug>.md`, and names the
   businesses the plan knows. Commit it: 'Meeting: <title>'.
2. **Read it, and write the summary.** Under `## Summary` in that file: what
   was decided, what is owed and by when, five to ten lines, in the person's
   words. Under `## Actions`: one line each, with a who and a day. Say the
   summary back to them. Commit.
3. **Then each business's part, one at a time.** For each business the plan
   names that the meeting touched, draft its part into
   `.oac/meeting-part-<business>.md`: the facts, decisions and actions about
   that business only. Nothing about the person's private life, nothing about
   another business, and nothing about anyone's pay, ownership or job unless
   the person says yes to that line. Show it to them and ask: does this go to
   <business>? The three rules from sharing hold: they decide, a part can go
   nowhere, and anything not decided stays here.
4. **On a yes,** run
   `python3 scripts/sac-meeting.py propose --meeting evidence/meetings/<date>-<slug>.md --business <business> --part .oac/meeting-part-<business>.md`.
   It finds the business's repo (`~/projects/<business>`, then
   `<business>-ops`), refuses `main` and prints the worktree line if it must,
   writes `meetings/<date>-<slug>.md` there, commits on the branch, pushes,
   and prints the pull request to open. If it stops on a word about money,
   ownership or a job, ask the person about that line; on their yes, run it
   again with `--yes-sensitive`. On a no, delete the draft and say nothing
   went. If the business has no repo yet, say so; `deploy` makes it.
5. **Report** in one short list: business, file, pull request. The transcript
   never leaves this repo, and nothing lands on any business's `main`.

## voice: how they sound, and what they like to look at

`/self-as-code voice`, and the first time anything is made for the person (an
email, a page, a report) while `standards/voice.md` still says 'Not written
yet'. The framework's 'Your voice' section is what you say. Write
`standards/voice.md` and `standards/brand.md` as it describes, on a branch;
they merge. From then on, before making anything for them, read both files
and the page for its kind under `standards/outputs/`, and show the thing to
them before it goes anywhere. Nothing made for a person may look or sound
like a machine made it.

## help: the one page

`/self-as-code help`, and what you say when `/sac` is given a word you do not
know. Print this, as it is, and nothing else. Fill the three numbers from the
plan's frontmatter and this week's page; leave a line out if it has nothing to
say.

```
Self as Code. One plan, written once, that steers every day.

Four words to know
  /start      begin. Reads your plan and your last note, says how you're going.
  /done       finish. Writes today down, asks your floor, saves, sends it to GitHub.
  /sac        the questions, the first time. Then /sac check, /sac week, /sac review.
  /sac help   this page.

Where things are
  self-as-code.md         your plan
  evidence/days/          your days
  projects/weeks/         this week
  evidence/               what happened, and your reviews

When
  Every day: /start, then /done.      Two weeks in: /sac check, on {date}.
  Sunday: /sac week.  Friday: /sac week.   Every 90 days: /sac review, next on {date}.

Stuck? Say what you want in plain words. SAC on the bottom line means you're
in the right place.
```

## review: the 90-day review

`/self-as-code review`, or `refactor`, the older name. Never say 'refactor' to
the person: it sounds like hard code. Say 'your 90-day review'.

Follow the framework's '90-day review' section, on a branch as above.

Before step 1, read each business's `goals.md` (under
`context-core/strategic-identity/` in the repo at `~/projects/<business>` or
`<business>-ops`) and its register's count of what still runs by hand, and
write what you found into `evidence/reviews/<date>.md`: one row per goal id,
its status and when it was updated, one line per business. That page is the
proof the quarter stands on. Say it back before you ask anything.

1. Read the current `self-as-code.md` and say it back in five or six sentences.
2. Step by step: still true? Did the floor hold? What can it lift to now? What
   else comes off onto the cut?
3. Rewrite the changed sections; move the old version into a `## history` block
   with the date.
4. Set `last_raised` to today, `next_raise` 90 days out, and `framework_version`
   to the version you ran.
5. Merge on their yes, then they type `/push`, as at the end of setup.

The point is not to start again. It is to **lift the floor** on what the last
three months proved.
