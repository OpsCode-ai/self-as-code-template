---
title: "/checkpoint: Save a long build across a context reset"
type: guide
audience: internal
---

# /checkpoint: Save a long build across a context reset

One job: when a piece of work is too big for one session, write down
everything the next session needs and hand it back cleanly on the other side.

```
/checkpoint                    save the current build
/checkpoint --restore          pick it up in a fresh session
/checkpoint --list             what checkpoints exist
```

## When to use this instead of /task-bridge

| | `/task-bridge` | `/checkpoint` |
|---|---|---|
| Answers | where was I today? | what is the state of this whole build? |
| Lives in | `team/{handle}/current.md` | `notable-plans/` |
| Size | a note | a document with evidence |
| Read by | `/start`, next session | `/checkpoint --restore`, next session |
| Survives | a night | a context reset, a week, a different machine |

A day's work ends with `/done`, which writes the task-bridge entry for you.
A multi-session build that is about to run out of context ends with
`/checkpoint`. A checkpoint is not a substitute for committing: commit and
push first, or the document describes a state that exists on one machine.

## Creating a checkpoint

1. **Work out what actually happened.** Do not ask the operator to summarise.
   Read `git log --oneline -20`, `git status --porcelain`, and the session
   itself. The commits say what changed; only the conversation says why, what
   was rejected, and what was learned the hard way.
2. **Decide the slug** from the work, not the date alone:
   `notable-plans/{YYYY-MM-DD}-{slug}.md`. If a checkpoint for this build
   already exists, **update it**. Two checkpoints for one build is how a later
   session picks the stale one.
3. **Write the document.** Frontmatter: `title`, `type: strategy`,
   `audience: internal`, `status: in-progress`, `owner`, `created`, `updated`,
   `summary`, `topics`, `tags`. Lists in flow style. Then, in this order:
   the **continuation prompt** first, immediately under the H1, as a quoted
   paragraph a fresh session can act on; **where things stand** (what is done
   and live, what is open); **what remains, in order, with the reason each
   step sits where it does**; **the evidence** (file and line for anything the
   next session must not rediscover); **what was decided against, and why**;
   **the hazards** (anything that fails silently, anything scheduled).
4. **Write the pointer** `.claude/checkpoint.json` (gitignored):
   `{"path": "notable-plans/…md", "branch": "…", "saved": "…"}`. It is a
   cursor; the document is the truth.
5. **Add one task-bridge line**: `**Next:** resume {build}: /checkpoint --restore`.
6. **Commit and push it**, then print the handoff: the path, and the two
   lines to pick it up (`/clear`, then `/checkpoint --restore`).

## Restoring a checkpoint

Assume no memory at all.

1. **Find it.** `.claude/checkpoint.json` if present, else the most recently
   modified `notable-plans/*.md` with `status: in-progress`. Several match:
   list them and ask. Never guess between two live builds.
2. **Read the whole document**, not only the prompt. The prompt aims you; the
   body stops you redoing settled work.
3. **Check reality against it**: `git log --oneline -5`, `git status`, open
   pull requests if the repo has them. If the checkpoint names something that
   has since moved, say so before doing anything else.
4. **Put the operator back in the room** in under fifteen lines: what shipped,
   what is open, what the next step is and why. Then stop and let them
   choose.

## Rules

- One checkpoint per build. Update, never accumulate.
- Close it when the build ships: `status: complete`, one line saying what
  happened, and a pointer to whatever carries the rest.
- Write the evidence, not the narrative.
- Say what was rejected. The most expensive thing a fresh session does is
  propose the idea you spent an hour ruling out.
