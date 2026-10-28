---
title: "/capture: What comes in, into your inbox"
type: guide
audience: internal
---

# /capture: what comes in, into your inbox

Something came in: a thought, a voice note, a message, a line from a meeting,
a reply to a nudge. Write each thing down where it belongs, one line each,
and move on. Sorting it is the job of `/sac week`, not of this moment.

## Steps

### Step 1: The places a line can belong

```bash
python3 scripts/sac-capture.py tags
```

Every business, job, family or project the plan names, plus `you`. A line
belongs to the one it is about. If it is about the person themself, it is
`you`.

### Step 2: Read what came in

The person types it, pastes it, or names a file. Split it into lines, one
thing to do or to remember per line. Keep their words and cut the filler. Tag
each line with one place from step 1. When a line could be two places, ask
which; do not guess. A line about someone's pay, ownership or job stays `you`
until they say otherwise.

### Step 3: Show the lines, then write them

> {n} lines. Look right?

Show them as they will be written, `[tag] text`, one per line. On yes, or
'just add':

```bash
printf '%s\n' '[acme] Call the accountant about the BAS' '[you] Book the dentist' \
  | python3 scripts/sac-capture.py add --from "a voice note, 28 Oct"
```

`--from` says where it came from, when it was not typed here. Leave it off for
something they just said. The script writes `inbox.md` under today's date and
makes the file the first time.

### Step 4: Close

> Added {n} to your inbox. /sac week sorts it. /done saves it.

Do not commit. `/done` saves the inbox with the rest of the day.

## Rules

- One line, one thing. No estimates, no owners, no priorities: the week
  decides what matters, with the leap, the floor and the cut.
- A tag the plan does not know is refused. Ask, then use `--any-tag` only if
  they want that tag kept.
- Nothing leaves this repo. The inbox is `audience: owner`.
- This is for the person's own repo. In a business's repo the script refuses,
  and files from other laptops come in through `python3 scripts/oac-hub.py inbox`.
