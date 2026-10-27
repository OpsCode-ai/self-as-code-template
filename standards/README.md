---
title: "Standards"
type: index
audience: owner
---

# Standards

The S in SPADE. The things you keep up, with no end date: your health, your
money, your family, and each business you run.

Your businesses live here: `ventures/<venture>/`. Your private notes about a
business partner go in `ventures/<venture>/partnerships/<name>/`. They stay
here, in your own repo, and never in the business's shared one.

How you sound is `voice.md`, what you like to look at is `brand.md`, and
`outputs/` holds one page per kind of thing made for you. Everything made
for you reads them first.

## The people you deal with

Each person or firm you deal with gets one folder, `<area>/<who>/`. A
business partner might be `ventures/<venture>/partnerships/<name>/`, your
accountant `finance/<name>/`. Every one has the same shape:

| Part | Holds |
|---|---|
| `README.md` | Who they are, where it stands, the open questions |
| `meetings/` | One summary per meeting, date first |
| `meetings/raw/` | Transcripts and recordings |
| `correspondence/` | Emails sent and received that matter |
| the top level | Your own notes, prep and thinking |

Make a subfolder the first time something needs it. To file a conversation,
ask: who was it with? If it was someone you deal with, it goes in their
folder. A talk, a course or a note to yourself goes in `evidence/`.

A business folder here is not that business's own repo. This is your private
view of it. The business itself lives in `{business}-ops`, shared with the
people who work in it.
