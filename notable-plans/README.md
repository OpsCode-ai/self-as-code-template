---
title: "Notable plans"
type: index
audience: internal
---

# Notable plans

Checkpoints. One document per build that is too big for one session: where
it stands, what remains in order and why, the evidence, what was ruled out,
and the hazards. `/checkpoint` writes one; `/checkpoint --restore` picks it up
in a fresh session, on any machine.

`status: in-progress` means live. There should be one live checkpoint at a
time. When a build ships, set it to `complete`, say what happened, and point
at whatever carries the rest.

This folder is not the daily log. That is `team/<you>/current.md`, written by
`/done` and `/task-bridge`, read by `/start`.
