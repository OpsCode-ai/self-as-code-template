---
title: "/sac: Self as Code, the one door"
type: guide
audience: internal
summary: "The one command for Self as Code. Runs the plain method from the Self as Code framework, with no AI-DLC, writes self-as-code.md on a branch the person merges, and sends what they choose to share to each business before it ends. The person types this and nothing else."
topics: [self-as-code, onboarding]
tags: [oac, sac, command, door, adr-125]
---

# /sac: Self as Code, the one door

Type `/sac`. That is the whole instruction for the person.

`/sac` and `/self-as-code` are the same command. The short name is the one
people are told; the long name is where the method lives. Every argument passes
straight through:

| You type | It runs |
|---|---|
| `/sac` | the first run: where you are today, the seven steps, what you share with each business, then sending it, then your plan drawn |
| `/sac review` | your 90-day review (`/sac refactor` still works) |
| `/sac check` | the always-growing checks over who you're becoming, your floor and your recent commits |
| `/sac week` | your week: on Sunday it plans it, on Friday it reviews it, any other day it says where the week is up to (`/sac execution` still works) |
| `/sac deploy <business>` | set up one business's own repo from what you captured |
| `/sac dashboard` | your plan drawn as one page, on this laptop. Run it any time |
| `/sac voice` | how you want to sound and what you like to look at, asked once; everything made for you reads them first |
| `/sac help` | the one page: the four words to know, where things are, when |
| `/sac meeting <file>` | a meeting transcript lands here first; the parts you choose go to each business as a pull request |

One more command is yours to type: `/capture`, when something comes in. It
writes one line per thing into `inbox.md`, tagged to the business, job, family
or project it is about, or `you`. `/sac week` sorts the inbox.

## What to do when this runs

Invoke the `self-as-code` command with exactly the arguments given to `/sac`,
and nothing else. It reads the Self as Code framework first and speaks only in
its words, writes `self-as-code.md` on a branch that becomes theirs when they
merge it, and sends what they chose to share to each business as a pull
request, in the same session.

It runs the same way every time, with nothing else installed (ADR-125). There
is no other path to explain. A word it does not know gets the help page, not
a guess.

**Run this in your private repo only**, the one named `first-last-ops`. The
bottom line of the screen says `SAC` when you are in it. In a business repo the
door is `/oac`.
