---
title: "Standards"
type: index
audience: owner
---

# Standards

The S in SPADE. Ongoing responsibilities with a bar you hold. No end date.
Your health, your money, your family, and each venture you run.

Your ventures live here: `ventures/<venture>/`. Owner-only intelligence about
a partner goes at `ventures/<venture>/partnerships/<name>/`, the pattern set by
lopez-delon-ops ADR-018 and opscode-hq ADR-111. The shared repo's gitignored
`engagements/*/private/` folders are drop zones only; anything written there
gets swept to the matching partnerships folder here.

## Engagements

A relationship you hold is an engagement: one folder per person or firm,
`<area>/<who>/`. A business partner might be
`ventures/<venture>/partnerships/<name>/`, your accountant
`finance/<name>/`. Every one has the same shape (opscode-hq ADR-126):

| Part | Holds |
|---|---|
| `README.md` | Who they are, where it stands, the open questions |
| `meetings/` | One summary per meeting, date first |
| `meetings/raw/` | Transcripts and recordings |
| `correspondence/` | Emails sent and received that matter |
| the top level | Your reads: private notes, prep, analysis |

Make a subfolder the first time something needs it. To file a conversation,
ask: who was it with? If it was someone you hold a relationship with, it goes
in their folder. A talk, a course or a note to yourself goes in `evidence/`.

A venture folder here is NOT that business's Operations as Code repo. This is
your private read on it. The business itself lives in `{business}-ops`, shared
with the people who work in it (ADR-118).
