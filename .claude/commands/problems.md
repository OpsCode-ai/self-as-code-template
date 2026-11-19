---
title: "/problems: What eats your time, written down"
type: guide
audience: internal
---

# /problems: What eats your time, written down

One job: ask the person what eats their time, one question at a time, and
save the answers in this repo. It is the worksheet from a Build Day, asked
live, so nothing has to be typed up later. Everything stays on this laptop
and in this repo.

## Where the answers go

- **In a business repo** (`.oac/manifest.yml` says `plane: business`, a team's
  spoke included): `team/<first name>/problems.md`, the person's own folder.
  In a spoke, the owners see it when they bring the spoke's work into the
  brain.
- **In a private space** (`plane: self`): `evidence/problems.md`. Say that
  only they can see it, and that they can send it to an owner of the business
  when they want to.

If the file is already there, read it first. Ask only what is missing or
out of date, and add to it. Never wipe what is there.

## If they bring the paper worksheet

They can drag a photo of it in. Read it, say back what you read, and ask only
the questions it does not answer.

## The questions

Ask one at a time. Wait for each answer. Short answers are fine. If an answer
is vague, ask once for an example, then move on.

1. 'What's your name, and your role?'
2. 'What's your GitHub username?' (Skip it in a private space if they do not
   have one yet.)
3. 'What are the jobs or problems that eat your time? Tell me the first one.'
   For each one, ask: 'How often? How long each time? What do you do it in?'
   Then: 'Another one?' Stop at five, or when they say that's all.
4. 'Of those, which one would give you the most time back if it went away?'
5. 'Where does your work live? Email, spreadsheets, a shared drive, paper,
   an app?' Write down each place they name.
6. 'What questions do people keep asking you?'
7. 'If this repo could answer one thing for you, what would it be?'

## Show it, then save it

Show the whole page before saving, and ask 'Anything to change?' Then write
it in this shape, with today's date:

```markdown
---
title: "<Name>: what eats my time"
type: report
audience: team
status: active
updated: <YYYY-MM-DD>
topics: [operations]
tags: [problems, worksheet]
---

# <Name>: what eats my time

<Role>. GitHub: <username>.

## The jobs that eat my time

| Job or problem | How often | How long | Done in |
|---|---|---|---|
| ... | ... | ... | ... |

**The one that would give me the most time back:** ...

## Where my work lives

- ...

## Questions people keep asking me

- ...

## What I'd ask this repo for

...
```

It is about their work, not about them, so it is `audience: team` in a
business and `audience: internal` in a private space: an owner can add it to
the business as it is.

Then say: 'Saved. Type /done to save and share it.' Do not commit it
yourself. `/done` does that.

## Never

- Never guess an answer they did not give. Leave the row out.
- Never write anyone else's name into the problems. Say 'a customer' or 'the
  team' instead.
- Never send any of it anywhere. It stays in this repo.
