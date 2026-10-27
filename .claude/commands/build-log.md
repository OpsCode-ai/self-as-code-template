---
title: "/build-log: Capture what was built"
type: guide
audience: internal
---

# /build-log: Capture what was built

Turn what we just built into a short record: a summary anyone can read in a
minute at the top, the steps and the lessons below. The build is the
documentation; the documentation is the product.

## Modes

| Invocation | What it does |
|---|---|
| `/build-log` | New log for this session. Infer the title |
| `/build-log <title>` | New log with that title |
| `/build-log --append <path>` | Add a dated entry to an existing log |

## Step 1: Gather the real record

```bash
git config user.name
git log --oneline -30
git diff --name-only HEAD~5 2>/dev/null | head -40
ls -t decisions/*.md 2>/dev/null | head -3
```

Then add what only you hold: the order things were built in, what was tried
and dropped, what surfaced by doing rather than planning.

## Step 2: Where it lives

`build-logs/YYYY-MM-DD-<slug>.md` in a business, `evidence/build-logs/YYYY-MM-DD-<slug>.md`
in a private space (`plane: self` in `.oac/manifest.yml`). Create the folder if
it is the first one.
Today's date comes from the environment, never guessed.

## Step 3: The shape

Frontmatter: `title`, `type: build-log`, `audience: internal`, `status`,
`created`, `owner`, `topics`, `related` (the files and decisions it touched).

Then, summary first:

1. **Summary.** Three to six lines: what shipped, why it matters, what is next.
2. **The sequence.** What was built in what order, and why the order mattered.
3. **The decisions.** Each choice with a one-line reason. Link the decision
   record if one exists.
4. **What surfaced.** The gaps, the surprises, the course corrections. This
   is the most useful section and the one people skip.
5. **What exists now.** Files, tables, pages. Make it openable.
6. **Open.** What is not done, honestly.

## Step 4: Writing standard

Australian English. Plain language. Honest: log what was skipped, what broke,
what is unverified. A build log that only lists wins is marketing.

## Step 5: Close

Print the summary block in chat. State the path. Offer to include it in the
next `/done`; do not commit from here.
