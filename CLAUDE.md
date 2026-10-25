---
title: "Your private repo: CLAUDE.md"
type: guide
audience: owner
---

# Your private repo

This is a self plane (opscode-hq ADR-118, OaC 1.8 profile `self-plane`).

## Self as Code

This repo contains `self-as-code.md` - my purpose, who I am becoming, and the
standards I hold. Read it at the start of work. When I ask whether to
build/take/do something, answer against my README, my `main`, and the rewrite.
Flag anything that belongs on the cut. Name it when a plan falls below the
floor. Run the Invariants over my `main`, floor and refactor, and tell me when
I am coasting rather than growing. On the `next_raise` date, prompt me to run
`/self-as-code refactor`.

## Where things go

The folders spell SPADE: standards, projects, archive, decisions, evidence.
Ask 'can I act on it, and does it end?' Projects beat standards beat evidence.
Done or dropped goes to `archive/`. `decisions/` is the record of choices
already made, so a later session never re-debates a settled one. If this repo
still has `history/` or `library/`, they are the old names for `archive/` and
`evidence/`; file into whichever exists, and never rename them unasked.

## Hard rule

Everything here is `audience: owner`. It never gets copied, summarised or
committed into a shared repo. Business material belongs in that business's own
`{business}-ops` repo, and it gets there by a routing decision I make, not by
an agent deciding it looks business-shaped.
