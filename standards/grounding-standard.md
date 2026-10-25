---
title: "Grounding standard"
type: standard
audience: team
status: active
lifecycle: living
date: 2026-10-08
summary: "Everything this system produces says what it was built from, and anything it cannot ground it marks rather than guesses."
topics: [operations-as-code, self-as-code, provenance, writing]
tags: [oac, sac, standard, grounding]
---

# Grounding standard

**Anything this system produces says where it came from. Anything it cannot
ground, it marks rather than guesses.**

That is the whole rule. The rest of this page is what it means in practice.

## Why it matters more than it sounds

Anyone can point an AI at a folder of notes and get a confident document out.
It will read just like yours. The difference is whether someone can pull on any
sentence in it and find the record underneath.

Your operation has that record. So a document it produces that cannot point at
a source is not a small tidiness problem. It is the system failing at the one
thing that makes it worth running.

## The two halves

### 1. A generated document names its source

Anything a model wrote carries `generated: true`, and then it must also carry
one of these:

```yaml
generated: true
derived_from: [../decisions/004-pricing.md]   # something in this repo
sources: ['board call, 12 March']             # something outside it
```

If the generator cannot name a source, it has not found one. The honest output
is to say so in the document, not to leave the field off.

### 2. The record beats the conversation

**A transcript is evidence of what somebody said. Your repo is the record of
what is true.** They disagree more often than you would think. People misspeak,
round up, and use a loose word for a deal that is still being negotiated.

When they disagree, the record wins, or you settle it before the thing ships.
Where the record is silent, say less. Do not fill the gap from the shape of the
sentence.

## People

`people-register.yml` is the record for how you describe a named person: the
spelling, their pronouns where you have evidence, what they actually are, and
the phrases that must never appear near them.

1. **Never guess pronouns from a name.** A name tells you nothing. Where the
   register says `unknown`, use they/them or use the name again.
2. **Never write an unsettled deal as settled.** If nothing is signed, it is
   not a fact about your business yet. Outwardly, say less.
3. **Add the person before you write about them**, if it is going outside.

## The check

```bash
python3 scripts/check-grounding.py --staged     # what you are committing
python3 scripts/check-grounding.py --outward    # everything public
```

A finding on something public is an error. The same finding in an internal note
is a warning, because internal notes are drafts and the cost of being wrong is
a conversation, not a customer.

A pronoun inside a quotation belongs to whoever said it, so quoted text is
skipped. If the checker flags a pronoun near two different people in one
sentence, that sentence is ambiguous to a human reader too. Rewrite it.

## A real example

A page prepared for a large partner described a business partner as 'our
investor' and used the wrong pronoun. Nine words, two errors, about a real
person, on a link that had already been sent.

Neither fact was unknown. Both were right in the record and had been for
months. They went wrong because the sentence was written from what someone said
in a meeting instead of from the record.

The page had passed every writing check. They all measure how a sentence reads.
None of them knows whether it is true.
