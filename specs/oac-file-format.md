---
title: "OaC File Format v1.13"
type: spec
audience: public
status: active
lifecycle: static
version: 1.13
owner: adam
updated: 2026-10-20
license: CC-BY-4.0
summary: "The open standard for running an operation as version-controlled markdown that both people and agents can read."
topics: [frontmatter, repo-structure, agents, self-as-code, context-core, operations, tooling]
tags: [oac, standard, open-standard, okf]
depends_on: [./oac-vocabulary.yml]
references: [../decisions/098-oac-file-format-v1.md, ../decisions/099-licensing-the-oac-standard.md, ../decisions/118-two-planes-and-the-systems-register.md, ../decisions/126-spade-the-private-repos-folders-and-the-shape-of-the-steps.md]
related: [../decisions/090-oac-client-open-core.md, ../context-core/strategic-identity/oac-client-vision.md]
---

# OaC File Format v1.13

**Operations as Code.** Run a business as plain markdown in git, so that people
and agents read the same source of truth.

This document is the human standard. `oac-vocabulary.yml` beside it is the
machine standard: the closed lists a validator reads. Where the two disagree,
the vocabulary file wins, because there must be exactly one place a value can
be legal.

- **Version:** 1.13
- **Status:** active
- **Licence:** CC BY 4.0. See 'Using this spec' at the end.
- **Decision of record:** ADR-098. Licensing: ADR-099. Planes and the systems register: ADR-118.

---

## 1. What this is

An OaC repository is a git repository of markdown files with a little
structure. The structure is there so an agent can find things without a search
index, and so a product can offer more when a repo is tidier.

Three design rules hold the whole thing together.

**1. It must work with nothing but a text editor and git.** The format adds
structure. It never requires an app. If you delete every tool, you still have
your operation.

**2. Retrieval is agentic.** There is no vector database in the format. An
agent finds things with grep, glob and read. Frontmatter is the metadata layer
that makes that work, which is why frontmatter is not decoration.

**3. `type` says what a document IS, never what it is ABOUT.** A transcript
about pricing has `type: transcript` and `topics: [pricing]`. Never
`type: pricing-discussion`.

That third rule is the one people break. Breaking it is how our own vocabulary
grew to 198 values before v1 collapsed it to 26.

### How to read the requirement words

- **MUST** means a consumer or repo is not conformant at that level without it.
- **SHOULD** means do it unless you have a reason not to.
- **MAY** means optional.

---

## 2. Conformance is graded

A repo is never simply 'conformant' or 'not conformant'. It sits at a level.
The level says what a consumer may offer.

This matters because real repositories are messy. A binary gate would make a
product useless to every new customer on day one. A ladder gives them something
that works now and a reason to climb.

| Level | A repo qualifies when | A consumer can then offer |
|---|---|---|
| **0 readable** | Markdown in git. Frontmatter, where present, parses as YAML | Open, render, full-text search |
| **1 typed** | Every document carries `title`, `type` and `audience`, with legal values | Filter by kind, route by audience, honour the privacy gate |
| **2 linked** | Declared edges resolve to real paths. Directories over 10 documents carry `index.md`. Every `title` is unique within the repo | Relation graph, impact analysis, progressive disclosure |
| **3 live** | The execution and presence conventions in section 7 | Board, runs, collaboration |

A consumer MUST report the level it found. A repo at Level 0 is a valid OaC
repo. It just unlocks less.

### 2.1 The robustness rule

**A consumer MUST NOT refuse a repository.** Specifically, a consumer MUST NOT
reject or error out because of:

- an unknown `type` value
- unknown extra frontmatter keys
- a cross-link that does not resolve
- a missing `index.md`
- an `oac_version` it does not recognise

It degrades to the highest level it can satisfy, says so, and carries on.

This rule is not politeness. Without it, every revision of this standard
becomes a flag day for every repository built against an older one. It is
adapted from the Open Knowledge Format's robustness section.

---

## 3. The document

Every structured document is markdown with YAML frontmatter.

```markdown
---
title: "Pricing the second cohort"
type: report
audience: internal
lifecycle: record
status: complete
owner: adam
updated: 2026-08-08
summary: "What we charged, what landed, and what to change next time."
topics: [pricing, cohort]
tags: [q3-review]
references: [../standards/pricing-policy.md]
---

# Pricing the second cohort

The body is for humans.
```

Frontmatter is the machine layer. The body is for people.

### 3.1 Required fields

Three, and no more:

| Field | Meaning |
|---|---|
| `title` | What this document is called. Plain text |
| `type` | What kind of document it is. From the closed list |
| `audience` | Who may read it |

Every extra required field is a tax on every document in the repo, and a reason
for a person to skip frontmatter altogether. Three is the whole list.

`audience` earns its place because privacy tooling reads it, and such tooling is
blind to any file that leaves it out.

### 3.2 Recommended fields

`summary`, `status`, `lifecycle`, `owner`, `updated`, `topics`, `tags`.

`summary` should be one plain sentence. Generated index files use it.

### 3.3 Lists MUST use flow style

```yaml
topics: [positioning, pricing]     # correct
```

```yaml
topics:                            # WRONG
  - positioning
  - pricing
```

This looks like taste. It is not.

Simple frontmatter readers are common, and they do not parse YAML. They find a
key with a regular expression and keep whatever follows it. Under block style
nothing follows it on that line, and what such a reader does next is worse than
returning nothing: it commonly matches on across the line break and returns the
first list item with its dash still attached, `- positioning`, then drops every
item after it. The document does not fail. It quietly acquires a value nobody
wrote.

That is measured, not hypothetical. It is the behaviour of this format's own
reference client, whose reader is a regular expression whose whitespace class
happens to match a newline. Under flow style the same reader captures
`[positioning, pricing]`, a string it can store, round-trip and parse later.

**There are two obligations here, not one.** They pull in opposite directions
on purpose, and a format that means to survive needs both:

- A **writer MUST** use flow style for lists of scalars. Be conservative in
  what you produce, because you cannot know what will read it.
- A **consumer SHOULD** parse frontmatter as YAML rather than by regular
  expression. Be liberal in what you accept, because a document is not wrong
  merely because a reader is thin.

The obligation on writers is not a licence for weak readers. It exists because
the world contains readers you did not write, and a document that survives all
of them is worth two square brackets.

**This rule covers lists of scalars, which is what the reason above is about.**
A block list whose items are mappings is a different shape:

```yaml
change_log:                        # NOT covered by this rule
  - date: 2026-08-05
    note: what changed
```

Flow style cannot rescue that for a simple reader. What it would capture is
`[{date: 2026-08-05, note: what changed}]`, a string it can store but nobody can
use, and the one-line form is unreadable and undiffable at the twenty entries
these fields reach in practice. So structured records stay in block style, and
`oac-validate.py` does not report them. Reading those is exactly what the
consumer obligation above is for: the answer is a better reader, not a worse
document.

### 3.4 `type`

What kind of document this is. Closed list of 26 values, in
`oac-vocabulary.yml`. A summary:

`adr`, `spec`, `standard`, `template`, `index`, `lesson`, `guide`, `strategy`,
`market-intel`, `audience-def`, `messaging`, `offer`, `brand`, `engagement`,
`session`, `coach-feedback`, `transcript`, `correspondence`, `contract`,
`campaign`, `build-log`, `report`, `reference`, `case-study`, `agent`,
`profile`.

**There is deliberately no `document` fallback.** A catch-all is exactly how a
type list grows to 198 values. If a document genuinely fits nothing, a human
decides, and either it fits after all or the list gains a value on purpose.

A repo MAY add its own values in `.oac/manifest.yml` (section 6.3). A consumer
MUST NOT reject a value it does not know.

#### 3.4.1 Typing a repo that has no types yet

Adopting the format on an existing repo means typing documents that were
written before it existed. Doing that by hand does not finish, so the rule is
machine-readable: `path_types` in `oac-vocabulary.yml` maps where a document
lives to what kind it is.

The table is **keyed by plane** ([ADR-118](../decisions/118-two-planes-and-the-systems-register.md)),
because the two planes hold different furniture. A business plane has
engagements, campaigns and curriculum. A self plane has a spine, five folders
filed by actionability (SPADE, section 7.4), and a life in them.

Three properties make it safe to run unattended:

1. **Ordered.** First match wins, so the specific precedes the general.
2. **No fallback.** A path that matches nothing is left for a human. A
   fallback is how a type list grows back to 198 values.
3. **Fails closed on `audience`.** `audience_default` gives each plane a
   floor: `owner` for a self plane, `internal` for a business plane. A
   backfill MUST NOT stamp anything more shared than the floor, because
   over-sharing is the one mistake it cannot undo.

The reference implementation is `code/scripts/backfill-frontmatter.py`. It
reads this table rather than carrying its own, which is the point: a rule we
ask an operator to follow has to be one we can hand them.

**Where `audience` holds a sentence.** Repos in the wild write things like
`audience: owner only - do not paste into any partner channel`. That sentence
is worth keeping, so it moves to `audience_note` (section 3.5) and `audience`
takes the most restrictive enum value the sentence names, or the plane's
floor, whichever is tighter.

### 3.5 `audience`

| Value | Meaning |
|---|---|
| `owner` | The owner only |
| `internal` | The organisation, including trusted delivery partners |
| `team` | Named collaborators on one specific engagement |
| `public` | Safe to publish |

**`audience` is a routing signal, not a security boundary.** It tells a
consumer where a document may be shown. It does not encrypt anything and it
does not enforce anything. Real access control belongs to the git host.

Saying this plainly is deliberate. A format that implies security it cannot
deliver is worse than one that admits the limit.

`audience_note` is an optional free-text companion, for when the real
readership is richer than four values can hold ('internal, and share-ready
with the client's lead'). `audience` stays the enum a tool routes on; the note
is for people. Never put the sentence in `audience` itself.

Tools that gate on `audience` SHOULD **fail closed**: a document with no
`audience` is treated as the most restricted value, never the least.

**`owner` is also a placement rule.** A shared repo is readable by every
collaborator, so an owner document does not belong in one at all: labelling
it `owner` and committing it anyway publishes it to the whole tree. An
owner document lives in a repo the owner alone controls, a private personal
repo beside the shared one (OpsCode's convention names it
`{first}-{last}-ops`). A shared repo MAY expose a gitignored drop zone
where machinery writes owner material, provided something sweeps that
material into the owner's repo rather than letting it accumulate on one
machine, unversioned. Commit tooling SHOULD refuse a staged owner document
in a shared repo. The one legitimate exception is template or pack material
that ships INTO another repo and carries the label on the destination's
behalf.

### 3.6 `lifecycle`

How a document behaves over time. This is the answer to 'static versus dynamic'.

| Value | Meaning |
|---|---|
| `static` | A reference the operation reads and does not change |
| `living` | Updated as the operation runs |
| `record` | Written once, never edited |

The consequence that matters: **only `record` may be quoted verbatim by an
agent.**

Quoting a `living` document as though it were speech is how a summary someone
wrote about a meeting ends up attributed to a person as a quote from that
meeting. `record` is the only class where the words on the page are the words
that were said or signed.

### 3.7 `status`

`draft`, `active`, `complete`, `superseded` in general use. Decision records
use `proposed`, `accepted`, `rejected`, `superseded`.

### 3.8 `topics` and `tags`

- **`topics`** is what the document is about. Closed list, extensible per repo.
- **`tags`** is free text. Use it for provenance: where a file came from, which
  batch or campaign produced it.

Keeping them apart is what makes subject search work. If every artefact from one
pipeline carries the same four provenance tags, nothing is findable by subject,
which is the failure this split exists to prevent.

### 3.9 Fields some types add

The three required fields apply to every document. A few kinds of document
carry extra fields that matter for them alone. All are optional, and a missing
one never costs a conformance level.

| Type | Adds |
|---|---|
| `adr` | `adr` (the number), `date`, `decision_date`, `supersedes`, `superseded_by` |
| `spec`, `standard` | `version` |
| `lesson` | `module` |
| `engagement`, `correspondence`, `contract`, `offer` | `engagement`, `date` |
| `session`, `coach-feedback` | `engagement`, `session_date` |
| `transcript` | `engagement`, `session_date`, `speaker_attribution`, `speakers` |
| `build-log` | `date` |

The full list is `type_fields` in `oac-vocabulary.yml`.

Resist adding to this. A field that only one document uses belongs in that
document, not in the standard, and per-type schemas are how a format grows
five incompatible dialects.

### 3.10 Trust fields

Borrowed unchanged from the Open Knowledge Format so their tooling reads our
documents at no cost: `generated`, `verified`, `sources`, `stale_after`.

Use `generated: true` on anything a model wrote.

**A document with `generated: true` MUST also carry `sources` or
`derived_from`.** `sources` for anything outside the repo, a transcript, a
call, a page. `derived_from` (section 4) for anything inside it. `verified` and
`stale_after` stay optional.

```yaml
generated: true
derived_from: [../engagements/aws/relationship-notes.md]
sources: ['2026Oct07-110417-Rec42.transcript.md']
```

This is the one rule in the format that is about truth rather than structure,
and it is the reason the format is worth adopting. Anyone can point a model at
a folder of markdown and get back a confident document. The difference is
whether a reader can pull on a sentence and find the record underneath it. A
machine-written document that will not say what it was built from has none of
that guarantee and reads exactly like one that does.

A generator that cannot name a source has not found one, and the honest output
is to say so in the document rather than to leave the field off.

Additive in practice: a repo that generates nothing is untouched, and a repo
that already marks generated documents is only affected where it claimed a
machine wrote something and declined to say what from. ADR-130.

---

## 4. Edges

Edges are relationships between documents. They are **flat frontmatter keys**,
never a nested block.

```yaml
depends_on: [../standards/pricing-policy.md]
references: [../brand/writing-style-guide.md]
```

```yaml
edges:                             # WRONG
  depends_on:
    - ../standards/pricing-policy.md
```

Flat, because `grep -rn '^depends_on:'` has to work. Nested YAML does not grep
as one token, and grep is the entire retrieval mechanism under design rule 2.

| Key | Meaning |
|---|---|
| `supersedes` | This replaces that |
| `superseded_by` | The inverse. Always pair them |
| `depends_on` | This breaks if that changes |
| `serves_goal` | This contributes to that outcome |
| `references` | Read-only pointer to a static document |
| `derived_from` | This content came from that source |
| `about` | Subject pointer to the canonical document on a topic |
| `related` | Untyped. Deprecated, kept so existing files do not break |

Values are paths from the document's own folder (`../decisions/012-x.md`), and
they stay inside the repo. At Level 2 they MUST resolve. A path written from
the repo root does not resolve, unless the document sits at the root.

Two of these carry most of the value.

**`references` closes the review loop.** Change a style guide, then
`grep -rln 'references:.*writing-style-guide'` returns everything that now needs
re-checking. This is the 'a process change affects this guideline, flag it for
review' behaviour, and it needs no tooling beyond grep.

**`about` makes noisy artefacts reachable.** A transcript pointed at the
canonical document for its subject becomes findable by topic instead of only by
date.

Keys are snake_case. Ordinary markdown links in the body are also edges for
graph purposes, but they are untyped, so they do not satisfy Level 2 on their
own.

Wikilinks (`[[like this]]`) are **not** part of this format.

### 4.1 Edges stay inside one repository

Every edge value is a path inside the repo that declares it, and at Level 2 it
must resolve. That is the whole guarantee, so an edge pointing into a different
repository cannot exist: nothing on the reading machine can check it, and a
validator that skips the ones it cannot reach has stopped promising anything.

Operations do relate to each other. One person's private operation sits above the
several businesses they run, and those relationships are real. They are declared
in `.oac/manifest.yml` (section 6.3), because they are properties of the
**repository**, not of any document inside it, and because the manifest is
already the one place a repo says what it is.

---

## 5. Transcripts and speaker attribution

Transcripts are the highest-risk documents in an operation, so they get a rule
of their own.

A transcript SHOULD carry `engagement`, `session_date` and
`speaker_attribution`:

| Value | Meaning |
|---|---|
| `labelled` | Real names are already in the body. Attribution is derivable |
| `mapped` | The body has anonymous labels. `speakers` carries the mapping |
| `anonymous` | Nobody knows who is who |

```yaml
type: transcript
speaker_attribution: mapped
speakers: ["Speaker 1=alex-tan", "Speaker 2=sam-rivera"]
```

Two rules, both hard.

**Mapping never rewrites.** The mapping lives in frontmatter. **No byte of the
body is touched.** An agent reads the frontmatter, learns that `Speaker 1` is
Alex, and greps their turns. A fix that adds a mapping is always better than a
fix that rewrites someone's words.

**`anonymous` means refuse.** When attribution is `anonymous`, an agent MUST
NOT guess who said what. Guessing is right most of the time, and the exceptions
put a fabricated quote in a real person's mouth.

---

## 6. The repository

### 6.1 Shape

```
my-operation/
├── CLAUDE.md            # operating instructions for humans and agents
├── README.md            # what this operation is
├── LICENSE              # what others may do with it
├── .oac/
│   └── manifest.yml     # which version of this format, and local extensions
├── decisions/           # decision records
├── context-core/        # the strategic layer
├── self-as-code.md      # the operator's identity, if used (section 7.1)
└── index.md             # per directory, once a directory gets large
```

Only `.oac/manifest.yml` is defined by this spec. The rest is convention, and a
repo MAY lay itself out differently.

### 6.2 `index.md`

Any directory holding more than 10 documents SHOULD carry an `index.md` listing
what is in it, one line each, using each document's `summary`.

This is progressive disclosure. It lets an agent read one small file instead of
opening 60, which is the difference between a fast answer and an expensive one.
Required at Level 2.

### 6.3 `.oac/manifest.yml`

One file at the repo root that says which standard this repo speaks and what it
has added locally.

```yaml
oac_version: 1.0

profiles: [pack]

plane: business
parent_operation: "github.com/acme/dana-okafor-ops"

types:
  property-file: "A managed property. Local to this repo."

topics: [leasing, compliance]

exempt:
  - vendor/
  - archive/

validate:
  scope: changed-files
  level: 1
```

| Key | Meaning |
|---|---|
| `oac_version` | Which version of this format the repo targets. Required |
| `profiles` | Optional conventions in use (section 7) |
| `plane` | `self` or `business`. Which kind of operation this repo is (section 7.4) |
| `parent_operation` | On a business plane, the self plane it was deployed from |
| `operations` | On a self plane, the business planes deployed from it |
| `types` | Local additions to the closed `type` list |
| `topics` | Local additions to the closed `topics` list |
| `exempt` | Paths a validator ignores. Vendored or frozen material |
| `validate` | How strictly to check, and the level being targeted |

`plane`, `parent_operation` and `operations` are the cross-repo relationships of
section 4.1. Their values name another repository, so they are **pointers, not
paths**. A consumer MUST NOT try to resolve them and MUST NOT fail a repo because
it cannot reach the other end. They exist so a person or an agent can find the
rest of an operation, and so `grep -rn '^parent_operation:'` across a fleet
answers 'whose is this?'.

They are also not an access grant. Naming a repo says it exists, nothing more.
Reading it still depends on the git host, exactly as section 3.5 says of
`audience`.

The manifest is what makes this a standard rather than a straitjacket. A repo
inherits the closed core and declares its own additions, in one place, in the
open, where a reviewer can see them.

It also makes a fleet auditable. Given a repo, `oac_version` answers 'which
version of the standard was this built against', which is otherwise
unanswerable.

---

### 6.4 What a repository does not classify

Three kinds of markdown sit inside a repository without belonging to it. None
carries this format's frontmatter, and none counts towards a conformance
level. All are declared under `exempt` in the manifest.

**Published output.** A copy made for someone else to read or download: a
static site's `public/` directory, a generated pack, a lead magnet. The source
document lives in the repository and carries frontmatter. The published copy is
an artefact of it. Frontmatter in a stranger's download is noise at best, and
if it says `audience: internal` on a free giveaway it is simply wrong.

**A nested operation.** A Context Core pack shipped to a customer is its own
OaC repository. It has its own `CLAUDE.md`, its own decisions and its own
manifest, and it is not a subdirectory of yours. Classifying its documents
means writing your metadata into someone else's operation, and `audience:
internal` means something different inside their repo than it does inside
yours.

**Another tool's schema.** A file whose frontmatter is a contract with a
different tool. A Claude Code `SKILL.md` declares `name` and `description`
because the skill loader requires exactly those; an agent definition, a CI
workflow and a static-site collection each answer to their own reader. The
frontmatter is already spoken for, and it is not speaking to us. Adding
`title`, `type` and `audience` alongside would either be ignored or, worse,
change how the owning tool behaves. A standard that edits another tool's
contract to make its own numbers look better is not a standard.

The test for all three is the same question: **when this file is read, whose
operation is it part of?** If the answer is not yours, do not classify it. For
the third kind the question sharpens slightly: **whose schema is this
frontmatter answering to?** If it is not ours, leave it alone.

**This is deliberately not a new `type` value.** Whether a document is
published, belongs to someone else, or answers to another tool, is not what the
document IS. A build
guide is a `guide` wherever it sits. Adding `lead-magnet` or `deliverable`
would cross kind with distribution, and that crossing is exactly how a type
list grows out of control. The distinction is location, and location is what
the manifest is for.

## 7. Profiles

Profiles are optional bundles of convention. Each unlocks specific behaviour. A
repo declares the ones it uses in `.oac/manifest.yml`.

### 7.1 `self-core`

The operator's strategic identity, in `self-as-code.md`.

- Frontmatter: `last_raised`, `next_raise`.
- Body: level-two headings, one per beat. Recognised case-insensitively, with
  an optional leading 'the': baseline, readme, main, rewrite, floor, cut,
  commits, refactor. The `refactor` beat is headed 'review' from 1.10;
  'refactor' is still recognised.
- Informative: the method teaches these headings as four questions in order,
  **Now** (baseline), **Why** (readme), **Who** (main) and **How** (rewrite,
  floor, cut, commits), held by the picture of a bridge from the best version
  of the person back to today; a review asks the four again. The shape is not
  grammar: a reader keys on the headings. ADR-126.
- A heading named 'Invariants'.
- An invariant line ending in `[coasting]`, which is the one machine-readable
  health signal in the profile.
- A heading named 'the split', holding one GFM table with the columns
  `Slice`, `Beat`, `Routing`, `Destination`. **`Routing` is a closed column**:
  `stays-personal`, `routes-to`, `promotable-unrouted`, as the bare value.
  `Destination` is required when `Routing` is `routes-to`, and names the unit
  as `<unit>` or `<unit>/<venture>`. A slice is a statement, not a file: what
  crosses into a business plane is the decision, never the raw session.

The split is the seam between the two planes. Anything not in the table, and
any row not routed, stays personal: a self plane fails closed. A consumer that
applies the split writes the routed statements into the named business plane's
`context-core/strategic-identity/` as a new document stamped `internal`. It
never copies a self-plane document across, and it never writes an edge back
(section 4.1), so provenance is a scalar and a commit message.

### 7.2 `live`

Execution and presence conventions. This is Level 3.

- Frontmatter: `sprint`.
- Items are GFM task list items, `- [ ]` and `- [x]`, at any indent. Lines
  inside fenced code blocks are never items.
- An item's grouping is the nearest chain of ancestor headings.
- A deviation is an indented blockquote directly under an item whose first line
  reads `> deviation (<author>, <YYYY-MM-DD>):`.

**This is the flat-file mirror for execution.** Tasks live in the markdown, so
they travel with the repo and survive any database. A task database is a
projection built from these lines, never the source of truth. That keeps design
rule 1 intact: delete the tools and the work is still there.

### 7.3 `pack`

A distributable context pack.

- Files: `CLAUDE.md`, `README.md`, `CHANGELOG.md`.
- Directories: `context-core/`, `decisions/`.
- Frontmatter: `version`, `last_updated`, `status`.
- Pack `status` values: `seeded`, `draft`, `confirmed`.

### 7.4 `self-plane`

One person's own operation, private, sitting above the businesses they run.

- Manifest: `plane: self`, and `operations` listing the business planes.
- File: `self-as-code.md` at the root, the spine. It carries the `self-core`
  profile (section 7.1).
- Directories, from 1.11, spelled **SPADE**:
  - `standards/`: ongoing, a bar you hold. Ventures live here.
  - `projects/`: has an end date.
  - `archive/`: done or dropped.
  - `decisions/`: one file per decision made, so a settled choice is never
    re-argued.
  - `evidence/`: what you look things up in and cite.
- **The old names are still read.** A reader MUST treat `history/` as
  `archive/` and `library/` as `evidence/`. A repo made before 1.11 keeps its
  folders until its owner renames them; a tool MUST NOT move them.

Evidence and Decisions are a pair: dig up the evidence, make the call, record
it. Filing by what you can act on rather than by subject is PARA, by Tiago
Forte; SPADE is the same idea with a name you can say
([ADR-126](../decisions/126-spade-the-private-repos-folders-and-the-shape-of-the-steps.md)).
How the folders relate, what a Self as Code session writes where, and the
bridge to each business repo are in the Self as Code standard
(`specs/self-as-code-standard.md`, draft).

Two fields, from 1.11:

- `venture`: the venture's slug. One slug names the venture everywhere: its
  `### ` block in the baseline, `standards/ventures/<slug>/`, the `Destination`
  in `## the split`, and the business repo in `operations`.
- `goal`: the id of a goal that crosses to a business repo, as
  `<venture>/<slug>`. Both repos carry the same id, because an edge cannot
  cross repos (4.1).

Goals link upward inside the repo with the `serves_goal` edge.

**A contact card, from 1.13.** A folder for one person, under a venture's
`partnerships/` or anywhere in `standards/`, MAY carry a contact card in its
`README.md` frontmatter. Every field is optional:

| Field | What it holds |
|---|---|
| `name` | The person's name |
| `emails` | Every address, in flow style: `[jo@example.com, jo@example.org]` |
| `phone` | With its country code and no spaces, quoted: `"+61400000000"` |
| `company` | Where they work |
| `kind` | One of `partner`, `customer`, `working-contact`, `friend`, `family` |
| `crm_person` | The business's CRM id for them, for business people only |
| `next_step` | The next thing to do with them, in one line |

The card is the record; any database is a copy built from it. A tool that
fills a card in MUST NOT overwrite a field a person has filled in. Last contact
is not a field: it is worked out from the folder's meetings and correspondence,
because a date someone has to type goes stale.

**A self plane is a private repo, so the whole thing is `owner` by default.**
This is the repo section 3.5 sends owner documents to. A consumer that reads one
is reading someone's private operation, and section 3.5's fail-closed rule
applies to every document in it.

The reason it is a separate repository and not a folder is access. A git host
grants read at the repo, so the first collaborator invited to any one business
would otherwise see the operator's identity and every other business they run.

### 7.5 `systems`

What an operation actually runs on today. The counterpart to a Context Core:
the Core holds what a business is aiming at, this holds what is true right now.

- Manifest: `plane: business`.
- File: `systems/register.md`.
- Body: up to three level-two sections, each holding one GFM table. All three are
  optional, and a missing one means that section was not captured, never an
  error.

| Section | One row per |
|---|---|
| `## Software` | A tool the operation pays for or depends on |
| `## Where the work lives` | A place files or records actually sit |
| `## Processes` | Something the operation does repeatedly |

Three columns are closed lists. A consumer finds them by header name,
case-insensitively, and ignores every column it does not recognise.

| Column | Values |
|---|---|
| `Connects via` | `api`, `mcp`, `scrape`, `none` |
| `Runs` | `manual`, `semi`, `automated` |
| `Call` | `keep`, `automate`, `build`, `replace`, `retire` |

Every other column is free text.

**A closed cell carries the bare value and nothing else.** No bold, no code
ticks, no trailing note. `| manual |`, never `| **manual** |`. The whole reason
these three columns are closed is that `grep -c` can count them, and emphasis
around the value defeats exactly that. Found by filling the first real register:
the manual rows had been bolded to make them stand out to a reader, and the
count then came back wrong.

**Rows, because the point is counting.** `Runs` is what turns 'we should automate
more' into a number an operator can watch move, and `Call` is the standing
decision about each row rather than one re-argued every quarter. Both answer to
`grep -c`, which is the only tooling this profile assumes.

**No logos, no per-app files, no frontmatter schema.** The register names `Xero`;
whatever renders it resolves the mark from the name. Thirty tools as thirty files
would lose the count that makes the register worth keeping, and structured data
in frontmatter is invisible to a scalar reader (section 3.3 exists for the same
reason).

---

## 8. Diagrams

Mermaid diagrams in fenced ```` ```mermaid ```` blocks are ordinary markdown. A
renderer SHOULD render them and MUST NOT fail on them. Every diagram SHOULD be
followed by a short text description, so the document still makes sense where
mermaid is not rendered.

A diagram node MAY link to a document anchor, which lets a generated map link
back to the step it came from. That is a Level 3 convention and is not required
below it.

Diagrams are documentation, not data. **A consumer MUST NOT treat a diagram as
the source of a repo's structure.** Structure comes from frontmatter and edges.
A diagram can go stale; an edge that does not resolve is caught by a validator.

---

## 9. Versioning

This spec uses two-part versioning, `MAJOR.MINOR`.

- **Minor** is additive. New optional fields, new profiles, new vocabulary
  values. A repo built for 1.0 keeps working under 1.1.
- **Major** is breaking. A required field changes meaning, or something is
  removed.

Rules for handling version skew:

1. A consumer meeting a **newer minor** version MUST proceed, ignoring what it
   does not recognise.
2. A consumer meeting a **newer major** version SHOULD warn, then proceed on a
   best-effort basis. It MUST NOT refuse.
3. A consumer meeting **no `oac_version`** assumes the oldest version it
   supports.
4. A field is deprecated for one full major version before removal, and is
   listed as deprecated here throughout.

Currently deprecated: `related` (use a typed edge from section 4).

Breaking changes are listed in the changelog at the end of this document.

---

## 10. What is not in the format

The **engine** is not part of this open standard: agent coaching intelligence,
persona calibration, hosted sync, certification and the paid collaboration
surface.

The format is open. The engine is the paid layer. Level 3 is where the two
meet, which is why the conformance ladder and the commercial model are the same
ladder.

Nothing here stops anyone building their own Level 3 implementation. The
standard is deliberately complete enough to allow that.

---

## 11. Relationship to the Open Knowledge Format

OaC is a **superset** of the Open Knowledge Format, not conformant to it. An
OKF-aware viewer works on an OaC repo, which is the only compatibility worth
having.

**Borrowed:** `type` as an always-required key; the per-directory `index.md`
convention; the trust fields in section 3.10; and the robustness rule in
section 2.1.

**Not adopted:** OKF's `status` semantics, because ours carries a decision-record
lifecycle theirs does not have; AI-synthesised directory descriptions, because
they need a model, send content out, and write prose nobody reviewed;
bundle-based validation, because we validate in place in the source of truth;
and wikilinks.

The main addition is `audience`, and the privacy handling around it, which OKF
does not have because it does not assume a repo full of other people's
confidential material.

OKF's specification is licensed Apache-2.0 and is credited here as the source of
the borrowed conventions above.

---

## 12. Using this spec

Licensed **CC BY 4.0**. You may copy, share, adapt and build on it, including
commercially, as long as you credit the source and say if you changed anything.

> OaC File Format by OpsCode (https://opscode.ai), used under CC BY 4.0.

Anyone may write a reader, writer or validator for this format. That is why it
is published.

'OpsCode', 'OaC' and 'Operations as Code' are trademarks. The licence grants no
right to use them. You may say your tool implements the OaC File Format. You may
not imply it is endorsed or certified.

---

## 13. Changelog

### 1.13, 20 October 2026

A contact card for a person's folder in a self plane. Additive: every field is
optional, and a repo valid under 1.12 is valid under 1.13.

- **The contact card (7.4).** `name`, `emails`, `phone`, `company`, `kind`,
  `crm_person` and `next_step` in a person's folder `README.md`, with `kind`
  from a closed list. A tool never overwrites a field a person filled in, and
  last contact is worked out, never typed. ADR-133 Rule 4.

### 1.12, 8 October 2026

Grounding. One field pairing becomes a MUST, so that what a machine writes says
where it came from. Additive: a repo valid under 1.11 that generates nothing,
or that already cites its sources, is valid under 1.12.

- **`generated: true` now requires `sources` or `derived_from` (3.10).** The
  trust fields were optional and the one that matters most was the one nobody
  filled in. A generated document that cannot name its source is the thing this
  format exists not to produce. ADR-130.
- The rest of 3.10 is unchanged. `verified` and `stale_after` stay optional.

### 1.11, 3 October 2026

The `self-plane` profile's folders get a name you can say. Additive: a repo
valid under 1.10 is valid under 1.11.

- **SPADE (7.4).** `standards/`, `projects/`, `archive/`, `decisions/`,
  `evidence/`. `history/` becomes `archive/` and `library/` becomes
  `evidence/`; readers MUST still accept the old names, and a tool MUST NOT
  move a person's folders for them. `decisions/` joins the set instead of
  sitting outside it. ADR-126.
- **Edge paths are written from the document's own folder (4).** The text said
  'repo-relative'; the validator, and every edge that resolves, has always
  read them from the document's folder. The words now match.
- **`venture` and `goal` (7.4).** The venture slug is the join key; a goal that
  crosses to a business repo carries one id on both sides. Goals link upward
  with `serves_goal`. Self as Code standard, decisions 1 to 3.
- **Now, Why, Who, How (7.1, informative).** The shape the method teaches over
  the `self-core` headings. No heading changes. ADR-126.
- The heading of this document said v1.9 through 1.10. It says the version now.

### 1.10, 3 October 2026

One spelling added to one profile. Additive only: a document valid under 1.9 is
valid under 1.10.

- **The `refactor` beat may be headed 'review' (7.1).** It is the 90-day review,
  and that is what a person calls it; 'refactor' read as hard code to the people
  the method is for. The beat key stays `refactor`, so readers map both headings
  to it, the way 'commit' maps to `commits`. New documents write `## review`.

### 1.9, 22 September 2026

One addition to one profile. Additive only: a document valid under 1.8 is valid
under 1.9.

- **`## the split` in the `self-core` profile (7.1).** The routing table the
  method has described since ADR-118 and no document had ever carried. Four
  columns, one of them closed: `Routing` is `stays-personal`, `routes-to` or
  `promotable-unrouted`, bare, so a grep can count it the way it counts the
  `systems` register. `Destination` names `<unit>` or `<unit>/<venture>`. A
  slice is a statement, not a file, which is what keeps owner material and
  cross-repo edges from ever leaving the self plane.
- The `systems` profile note that said no reader ships is corrected. One does:
  `systems-register.py`, in the reference implementation.

### 1.8, 12 September 2026

Two profiles and three manifest keys. Additive only: no change to the 26 types,
the required fields, the edge keys or the conformance levels, so a document
valid under 1.7 is valid under 1.8.

- **`self-plane` profile (7.4).** One person's own operation, private, sitting
  above the businesses they run. `self-as-code.md` as the spine, four
  actionability directories, `decisions/` outside them as the governance spine.
  This is the repo 3.5 has been sending owner documents to since 1.7; now the
  standard says what it looks like.
- **`systems` profile (7.5).** A register of what an operation runs on today:
  software, where the work lives, and processes. Three closed columns
  (`Connects via`, `Runs`, `Call`), everything else free text, GFM tables in the
  body rather than a schema in frontmatter.
- **`plane`, `parent_operation` and `operations` in the manifest (6.3).** How two
  repositories say they are halves of one operation.
- **4.1 says out loud that edges are repo-local**, which was always true and
  never written down. Cross-repo relationships are manifest pointers, and a
  consumer MUST NOT try to resolve them.

Found by asking what the name promised. A sweep of six live Context Core packs
turned up no inventory of business software anywhere, `manual` versus
`automated` as a field nowhere, and no artefact describing the operation as it
actually runs. The Context Core is half go-to-market intelligence by folder
count, so a standard for running an operation described almost everything except
the operation. The `systems` profile is the missing half, and `Runs` is the
column that makes 'automate more of it' a number instead of an intention.

### 1.7, 7 September 2026

One addition to 3.5. No change to the 26 types, the required fields, or the
conformance levels, so a document valid under 1.6 is valid under 1.7.

- **`audience: owner` gains a placement rule.** The value always meant 'the
  owner only', but the standard never said where such a document may live.
  Now it does: never in a shared repo, because a shared repo is readable by
  every collaborator and a label is not a lock. Owner documents live in a
  private repo the owner alone controls; shared repos may hold gitignored
  drop zones only if something sweeps them; commit tooling SHOULD refuse a
  staged owner document; pack and template material shipping into another
  repo is the stated exception.

Found the honest way. Six owner documents sat in a gitignored folder of a
shared repo, safe from the collaborators and invisible to version control,
which means they existed on exactly one machine. The format's own audience
field had routed them correctly and placed them nowhere.

### 1.6, 19 August 2026

One addition to Level 2.

- **`title` must be unique within a repo.** Two documents sharing a title is not
  a cosmetic problem. An index lists them identically, a reference to 'the
  pricing doc' has two answers, and an agent asked to open one opens a coin
  flip. Level 2 is where this belongs, because its promise is the relation graph
  and progressive disclosure, and a duplicate is precisely what breaks both.
  Level 1 is unchanged: it promises the three fields exist with legal values,
  which a duplicate satisfies.
- Checked repo-wide only, for the same reason as the `index.md` rule. A
  duplicate cannot be seen from a subset of changed files, and reporting
  'unique' after looking at two of them would be worse than not looking.
- Per the robustness rule in 2.1, a duplicate degrades the level and is
  reported. It is never an error and never a refusal.

Found the honest way. A commit that took nine starter packs to 187 of 187
documents typed also gave two of them the same title, and the validator
reported all green, because nothing checked that titles identify. 'Typed' and
'findable' were being treated as the same claim and they are not.

### 1.5, 19 August 2026

Four alias corrections. No change to the 26 types, the required fields, or the
conformance levels, so a document valid under 1.4 is valid under 1.5.

- **`business`, `business_knowledge` and `operations` moved from `type_aliases`
  to `type_manual_review`.** All three aliased to `engagement`, which means a
  customer or partner relationship document. None of them are that. They name a
  SUBJECT AREA, and a subject area maps to different types file by file: in one
  cohort pack `business_knowledge` covered a price list, a fabrication rule, a
  materials reference and a positioning statement, which are `offer`, `guide`,
  `reference` and `strategy`. Any single target is wrong for most of them, so
  the backfill must now stop and ask rather than guess.
- **`customers` now aliases to `audience-def`, not `engagement`.** It describes
  who we serve, which is what `audience-def` is for, and it now matches
  `customer_intelligence` and `customer-intelligence` which already pointed
  there. The three had been split across two targets.
- **`role` now aliases to `guide`, not `profile`.** `profile` means A PERSON.
  A role definition is a job description, so `team-profile` was right to point
  at `profile` and `role` was not.

Found by pointing the validator at four cohort starter packs for the first time.
All four scored Level 0, and the mis-mapped aliases were why several documents
looked typed while carrying a type that said what they were about rather than
what they were.

### 1.4, 11 August 2026

Additive, and one correction.

- **Corrected 3.3's account of how a naive reader fails.** It said the data
  'silently disappears'. Measured against the reference client, the failure is
  worse: the reader matches across the line break and returns the first list
  item with its dash attached, then drops the rest. It fabricates a value
  rather than losing one, and a fabricated value is harder to notice than an
  absent one.
- Split 3.3 into the two obligations that were previously in tension. A writer
  MUST use flow style; a consumer SHOULD parse YAML properly. The rule on
  writers was never meant as a licence for weak readers, and saying both makes
  the mapping-list carve-out coherent instead of contradictory.

### 1.3, 12 August 2026

Additive.

- Documented `audience_note`, the optional free-text companion to
  `audience`. Added after 22 documents were found with a whole sentence
  written into `audience` itself. Collapsing them to the enum would have
  discarded what they said, so the sentence moves to the note and the enum
  carries the routing.

### 1.2, 11 August 2026

Additive.

- Added section 6.4, what a repository does not classify: published output
  and nested operations. Written after a backfill stamped `audience:
  internal` into three publicly downloadable files and into 180 files of a
  customer's own pack.
- No new `type` value, on purpose. Whether a document is published, or
  belongs to someone else, is not what the document is.

### 1.1, 10 August 2026

Additive. A repo built for 1.0 keeps working unchanged.

- Added section 3.9, the extra fields a few types carry (`type_fields` in the
  vocabulary). This absorbs the last of the rival definitions ADR-098 set out
  to reconcile: five per-context schemas that lived in a separate structuring
  guide and invented `type` values this standard does not have.
- Added `field_aliases` to the vocabulary, recording `last_updated` as an
  alias of `updated` and `related_adrs` as an alias of `references`. Both were
  in wide use, and a consumer needs to read them.
- Renumbered trust fields from 3.9 to 3.10.

### 1.0, 8 August 2026

First stable version. Decision of record: ADR-098.

Replaces the v0.1 stub and closes all six of the questions it left open:

| v0.1 open question | Closed by |
|---|---|
| Flat-file mirror for execution items | Section 7.2. Markdown task lists are the source; a database is a projection |
| A manifest declaring repo type and bindings | Section 6.3. Repo type became a `profiles` list, since a repo can be more than one thing |
| Static versus dynamic classification | Section 3.6, `lifecycle`, with a third value, `record`, that the question did not anticipate |
| Dependency-link edge types | Section 4. Seven typed keys, snake_case rather than the hyphenated forms first proposed |
| RBAC and ownership metadata | Sections 3.1 and 3.5. `audience` plus `owner`, stated as routing rather than enforcement |
| The mermaid-from-docs convention | Section 8. Diagrams are documentation, never the source of structure |

Also changed from v0.1:

- Conformance became graded, levels 0 to 3, with the robustness rule.
- Required fields settled at `title`, `type`, `audience`.
- `type` values collapsed from 198 to 26, with the rule that `type` is never a
  subject.
- Lists MUST use flow style.
- The `self-core`, `live` and `pack` profiles were written down for the first
  time, from what implementations already do.
- Wikilinks removed.
- The v0.1 'a client MUST support' list is gone. Requirements now attach to
  conformance levels instead, because three of the five v0.1 requirements were
  not implemented anywhere, which made the list aspirational rather than
  normative.
