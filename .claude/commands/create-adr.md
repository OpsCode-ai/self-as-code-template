---
title: "/create-adr: Record a decision"
type: guide
audience: internal
---

# /create-adr: Record a decision

A decision written down once is a debate you never have twice. This writes a
short decision record into `decisions/`, from the conversation we just had or
from four questions.

## Two modes

**From the conversation (default).** If we have been weighing a choice, the
record comes from that: the problem, the options, what was chosen, why, what
it costs.

**Interactive.** If there is no decision in the conversation, ask, one at a
time:

1. What are you deciding?
2. What is the problem or the moment that raised it?
3. What options did you consider, and what is wrong with each?
4. What did you choose, and what does it change?

## Steps

### Step 1: The number

```bash
ls decisions/[0-9]*.md 2>/dev/null | sort | tail -1
```

Next number, three digits, starting at `001`. Never reuse a number.

### Step 2: Write it

Use the shape in `decisions/template.md`. Frontmatter:

```yaml
---
title: "{Short decision title}"
type: adr
audience: internal
decision_id: NNN
status: accepted
date: YYYY-MM-DD
topics: [operations]
tags: [decision]
---
```

Then four sections, plainly: **Context** (what was true), **Decision** (what
was decided, one paragraph if possible), **Why** (the reasons that drove it,
including the options rejected), **Consequences** (what changes, what it
costs, what to watch).

File: `decisions/NNN-short-slug.md`.

### Step 3: Index it

Add a row to the table in `decisions/README.md`:

```
| NNN | [Title](NNN-short-slug.md) | Accepted | YYYY-MM-DD | one-line summary |
```

### Step 4: Confirm

Show the record. Ask whether anything is wrong. A decision record with a wrong
'why' is worse than none, because it looks settled.

## Rules

- AU English, plain language, no clichés.
- Write the reasons, not just the result. The result is in the code and the
  files; the reason is the part that gets lost.
- `status: proposed` if it is not yet agreed by whoever has to agree. Change
  it to `accepted` when they do.
