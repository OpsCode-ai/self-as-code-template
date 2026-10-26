---
title: "/task-bridge: A note to yourself"
type: guide
audience: internal
---

# /task-bridge: A note to yourself

One job: write down where your head is, so next time picks the thread
straight up. `/done` does the saving. `/task-bridge` is the note to yourself.
`/start` reads it first.

`/done` writes an entry automatically at the end of every session. This
command is for the notes in between, and for the times you step away without
finishing. Run it any time:

- **Stepping away** (a call, a site visit): `/task-bridge need to finish X`
  drops the note in seconds.
- **Between sessions** on a long day: each run appends an entry.
- **End of day**: the last entry plus tomorrow's priority.

No modes, no interrogation. One file per person per day.

## The file

`team/{handle}/current.md` is today. Yesterday lives in
`team/{handle}/logs/{date}.md`.

```markdown
---
title: "Jane - daily log, 2026-09-25"
type: report
audience: team
date: 2026-09-25
owner: jane
status: open
topics: [operations]
tags: [task-bridge, daily-log, jane]
---

# Jane - 2026-09-25

## Roll-forward

**Next:** {the single current priority. Replaced on every run, never appended.}
**When:** {only if you said when, e.g. 'tomorrow morning, first thing'}

## Entries

### 14:05
{note}
```

Rules: `type: report`, flow-style lists, entries chronological and
append-only, Roll-forward always replaced. `status: open` while the day runs;
the last entry may set it to `closed`.

## Steps

1. **Who.** `git config user.name`, first name lowercase. Only ask if it
   cannot be derived.
2. **The note.** Arguments given are the note; tidy the wording, keep the
   meaning. No arguments: draft it from what this session did. If the note
   names a next step or a deadline, that becomes the Roll-forward; otherwise
   leave the standing one alone.
3. **Date roll.** If `current.md` carries a `date:` that is not today, move it
   to `team/{handle}/logs/{that-date}.md` and start fresh. Never overwrite an
   archived day.
4. **Write.** Append the `### HH:MM` entry, replace the Roll-forward if there
   is a new one, refresh `date`, `topics`, `status`.
5. **Offer to commit.** 'Commit it now, or leave it for the next `/done`?' If
   now: stage that one file, commit as `Docs: task-bridge {date}`, push if a
   remote exists.

## Rules

- Nothing `audience: owner` goes in here. In a business, `team/` is readable
  by everyone who works there. Personal notes belong in your private space.
- The log is never empty because someone was tired. `/done` makes sure of it.
