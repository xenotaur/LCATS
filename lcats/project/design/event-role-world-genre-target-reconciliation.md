# Event-Role-World genre targets: reconciliation and coverage plan

Date: 2026-07-26
Work item: none yet (investigation/planning only, per this document's own recommendation below)
Scope: recommendation only — implements no code, runs no large-scale annotation.

## Purpose

Three sources in this repo described the Worldcon 2026 "Shape of Science
Fiction" paper's target genre comparison set, and disagreed:

1. `VALID_GENRES` in `lcats/lcats/analysis/corpus/assess.py:8` — the genres
   the classifier tooling actually implements today — is `("science
   fiction", "horror", "western", "romance")`.
2. The governing proposal's "Resulting scientific claim" section
   (`project/design/proposals/adopted/lcats-event-role-world-extractor/00_proposal.md:288`)
   frames the comparison as SF vs. "mystery, romance, and adventure."
3. The user's own recollection going into this investigation was five
   genres: science fiction, mystery, horror, romance, and western.

This document records what was verified against the actual repo state,
the user's resolution of the discrepancy, a corpus coverage survey against
that resolved list, and the follow-up plan to close the gaps found.

## What was verified

### The three-way discrepancy is real, not a misreading

- `assess.py`'s `VALID_GENRES` is exactly `("science fiction", "horror",
  "western", "romance")` — confirmed by direct read. The four-genre framing
  is baked in beyond the tuple itself: the classifier's system prompt
  (`assess.py:149`) says "The corpus targets four genres," and the
  `detected_genre` schema description (`assess.py:66`) and the "other"
  definition (`assess.py:15`) both say "four target genres."
- The proposal's "Resulting scientific claim" section (`00_proposal.md:288`)
  states verbatim: *"Compared with mystery, romance, and adventure, public
  domain science fiction may show distinctive patterns..."* — mystery and
  adventure, not horror and western.
- `WS-EVENT-ROLE-WORLD.md` is explicitly scoped and titled **"SF
  Event-Role-World Extractor Implementation"** — its exit criteria never
  require running the annotation pipeline against non-SF genres at scale;
  non-SF material appears only as pilot comparison text.

### This exact tension was already noticed once, and quietly worked around

`WI-EVENT-0030.md` (proposed, not yet executed — see below) already
flagged the same discrepancy this investigation found, and resolved it
locally rather than escalating it: *"Mystery and adventure are not
classifiable genres in this tooling today... WI-EVENT-0028's original
comparison texts (Doyle mystery and O. Henry general-fiction) were
informally chosen for the reading-based pilot, neither a validated genre
stratum."* WI-EVENT-0028's 4-story reading pilot used Doyle (mystery) and
O. Henry (general-fiction) as informal foils to science fiction, but never
extended `VALID_GENRES` itself — WI-EVENT-0030 then pinned the entire
stratified-pilot design to the four genres the classifier actually
supports, without raising the mismatch against the proposal's own stated
claim genres for a decision. This document is that escalation.

### Annotation coverage is much thinner than the workstream's framing suggests

- WI-EVENT-0028: a 4-story **reading-based** pilot (2 Lovecraft SF/horror,
  1 Doyle mystery, 1 O. Henry general/romance-adjacent) — no pipeline code
  was run; scene/beat breaks were read and tallied by hand. Not full
  Event-Role-World annotation, and not drawn from a validated genre
  stratum for 2 of its 4 stories.
- WI-EVENT-0029: implemented the cross-segment relation pass itself
  (option A from `project/design/event-role-world-cross-segment-relations-evaluation.md`)
  and found "a clear, genre-differentiated result" — but on the same small
  pilot sample, not a corpus-scale run.
- WI-EVENT-0030: **only pilot tooling landed** (PR #158, `run_pilot.py` in
  `experiments/03_cross_segment_relation_pilot/`). The work item's own
  `status: proposed` / `resolution: null` frontmatter and the pilot's
  `results/` directory (a bare `.gitkeep`) confirm the actual 20-40-story
  stratified run (5-10 stories x 4 genres) has **not** been executed —
  only the tooling to run it exists.
- No checked-in assess output (JSONL or otherwise) anywhere in the repo
  uses the current `VALID_GENRES` 4-genre classifier at corpus scale.

### No Gutenberg bookshelf/category metadata exists in the pipeline

Grepping every gatherer (`lcats/lcats/gatherers/*/gatherer.py`) and the
ingestion library (`lcats/lcats/gatherers/gatherlib.py`,
`lcats/lcats/gatherers/parser.py`) for "genre" or "bookshelf" found
nothing. Genre is assigned exclusively by `lcats assess`'s own LLM
classifier — there is no Gutenberg-native genre/category signal anywhere
upstream of it to reconcile against.

### The one full-corpus classification that exists uses a different, older scheme

`experiments/01_classify_corpora/results/summary.tab` (dated 2025-10-19,
predates `VALID_GENRES` as it stands today) ran an older ad-hoc
`story_classifier` with a much larger, open `genre_primary` vocabulary —
not the current closed 4-genre set. Its counts (`fiction` rows only, out
of 1,815 fiction-typed rows, out of 1,879 total classified rows in that
2025-10-19 run — a different, older snapshot than the corpus's current
1,868 on-disk stories, and not directly comparable to it) are useful as a
rough compositional signal but are **not** directly comparable to what
`lcats assess` would produce today:

| genre_primary | count |
|---|---|
| science fiction | 1196 |
| literary | 215 |
| mystery/detective | 75 |
| fantasy | 69 |
| adventure | 69 |
| children's | 52 |
| horror | 37 |
| historical | 32 |
| satire | 24 |
| western | 23 |
| romance | 13 |
| thriller | 7 |
| humor | 1 |
| mystery (alt spelling) | 1 |

No comparably-scoped run of the *current* classifier exists to check
against — running one now, across ~1,868 stories, would itself be a real
LLM API cost operation, which this investigation pass deliberately did not
do (`lcats/data/`, the classifier's default target, isn't even checked out
in this worktree — it regenerates from `cache/` and is not committed).

Per-source corpus sizes (a proxy for how concentrated vs. thin coverage is
per likely genre) show one dominant, mixed-genre source and many small,
single-genre curated corpora:

| corpus | story count | likely dominant genre(s) |
|---|---|---|
| mass_quantities | 1658 | mixed (SF-heavy; source of most non-SF genres too) |
| grimm | 62 | fantasy / children's |
| ohenry-four_million | 25 | literary / mystery |
| ohenry-whirligigs | 24 | literary / mystery |
| anderson | 18 | children's / fantasy |
| lovecraft | 17 | horror / SF |
| hemingway | 14 | literary |
| wodehouse | 12 | humor |
| sherlock | 12 | mystery |
| chesterton | 12 | mystery |
| london | 8 | adventure |
| wilde_happy_prince | 5 | children's |

There is no dedicated western or romance corpus at all — both genres'
counts above come entirely from scattered stories inside the
`mass_quantities` grab-bag, which is consistent with them being the
thinnest categories in the old classifier's tally.

## Resolved target genre list

Presented with the three-way discrepancy above, the user resolved it
directly (2026-07-26), rather than picking one of the three existing
sources verbatim:

> The original list was meant to be the genres with more than ~30 stories
> in the corpus under a well-defined category: science fiction, horror,
> humor, western, and romance. Mystery, fantasy, and adventure should be
> added as well, since they are also well-defined. So the principal
> extraction-priority genre list for the Worldcon paper is: **science
> fiction, horror, humor, western, romance, mystery, fantasy, adventure**
> (8 genres). Other genres (war, medical, etc.) should still be
> representable as classificatory values in the corpus tables, but are not
> extraction priorities.

This does not match any of the three original sources exactly: it drops
neither horror nor western (unlike the proposal's framing), adds mystery
(matching the user's original recollection and the proposal's language),
and further adds humor, fantasy, and adventure (matching none of the three
sources exactly, but grounded in actual corpus composition per the table
above).

**Open flag, not re-litigated here:** the stated ">30 stories" rationale
doesn't cleanly hold under the one existing corpus-wide count — western
(23) and romance (13) fall under 30 in the old classifier's tally, and
"humor" barely registers there (1), with `wodehouse`'s stories likely
counted under `literary`/`satire` in that older scheme instead. This is
worth resolving with a **current-classifier** corpus count (see Gap 2
below) before finalizing per-genre sourcing targets — the old classifier's
category boundaries may simply not line up with how the current 8-genre
classifier will draw them.

## Gaps and follow-up plan

### Gap 1 — `VALID_GENRES` must grow from 4 to 8

`assess.py` needs:
- `VALID_GENRES` extended to `("science fiction", "horror", "humor",
  "western", "romance", "mystery", "fantasy", "adventure")`.
- `_GENRE_DEFINITIONS`, the "other" description strings, and the
  classifier's system/user prompts (`assess.py:149,153,181` — all three
  currently say "four genres"/"four target genres") rewritten for 8, with
  a definition line added for each of the 4 new genres.
- `assess_cli.py`'s `--genre` choices/help text (uses `VALID_GENRES`
  directly, so it updates automatically, but the help string's wording
  should be checked).
- Any test or `lrh validate` fixture that hardcodes "four genres" or the
  4-tuple (a repo-wide grep for `VALID_GENRES` and "four genres" found the
  hits listed above and no others outside `assess.py`/`assess_cli.py`, but
  a fresh grep should be re-run once implementation starts in case new
  references were added since this investigation).
- Every existing `detected_genre`/genre-classification consumer needs to
  tolerate the 4 new enum values (schema changes to a `tool=` structured
  output enum are additive and should not break existing callers, but this
  should be verified, not assumed).
- **A closed 8-genre enum alone is not sufficient.** `detected_genre` would
  remain `VALID_GENRES + ["other"]` — an 8-way closed enum plus a catch-all
  — which collapses every non-priority category (war, medical, etc.) into
  `other` and loses exactly the classificatory-value representation the
  user asked to keep. The existing `genre_suggestion` field does not cover
  this: its schema only populates it for `wrong`/`disputed` lens-mode
  verdicts, while a corpus-wide survey runs in detect mode
  (`genre_verdict="detected"`). Gap 1 must also add an open (non-enum)
  primary/secondary genre-tag field — populated regardless of verdict —
  before the Gap 2 survey runs, or the survey itself will silently discard
  the non-priority genre data it's meant to capture.

### Gap 2 — corpus representation needs a current-classifier survey, not just the 2025-10 one

Before sizing any real annotation work, run `lcats assess` **without**
`--genre` (once extended to 8 genres) — omitting `--genre` is what puts
the command in detect mode; passing it switches to lens mode against a
single claimed genre instead, per `lcats assess --help`'s own text — across
the full corpus to get an authoritative current per-genre count. The
2025-10 numbers above are a different classifier's output and should not be
trusted as the basis for sourcing decisions. This is itself a real
LLM-API-cost operation across ~1,868 stories and should be scoped and
estimated in its own work item (see below), not run speculatively.

Once that survey exists, the likely-thin genres flagged by the per-source
table above — **western and romance**, and possibly **humor** depending on
how the new classifier categorizes `wodehouse`/`chesterton` material —
should be checked against whatever per-genre minimum the paper's
statistical method needs. If they remain thin, further Gutenberg
sourcing/ingestion (a new gatherer, similar to the existing
per-author ones) is the likely remedy, scoped as its own follow-up rather
than folded into the survey work item.

### Gap 3 — Event-Role-World annotation coverage: only a 4-story pilot exists, for 4 of the 8 genres

Full-pipeline (stages 2-9) annotation has been run on essentially nothing
at corpus scale:
- 4 stories total, read-based only (WI-EVENT-0028) — not pipeline output.
- WI-EVENT-0030's stratified pilot (tooling only, no results) targets 4
  genres, not 8 — it will need re-scoping to cover humor, mystery, fantasy,
  and adventure once Gap 1 lands.

The paper needs a properly stratified, pipeline-run sample across all 8
resolved genres before any genre-comparison claim is publishable. Concrete
follow-up:

**Follow-up work item A — corpus-wide current-classifier genre survey.**
Run `lcats assess` **without** `--genre` (post-Gap-1) across the full
corpus (~1,868 stories) — detect mode, not lens mode, since no curation/
lens decisions are needed, just `detected_genre` + confidence. Cost
estimate: detect-only assessment is one LLM call per story with the story
body (capped at 100k chars per `assess_cli.py`'s default
`--max-body-chars`); at ~1,868 stories this is the single largest-volume
call in this reconciliation's follow-up plan and should get its own
token/cost estimate from a small timed sample (e.g. 20 stories) before
committing to the full run, per the existing cost/baseline
reporting pattern already used elsewhere in this workstream.

**Follow-up work item B — re-scope WI-EVENT-0030's stratified pilot to 8
genres.** Extend the already-landed `run_pilot.py` tooling's genre list
from 4 to 8 (mechanical, since it already parameterizes on
`lcats assess --genre`'s supported set), then actually execute the
5-10-stories-per-genre run the work item describes — 40-80 stories total
across 8 genres, each requiring a full stages-1-9 Event-Role-World
pipeline run (up to seven annotator passes per segment, per the proposal's
own cost/latency risk framing, `00_proposal.md:284`). This is
substantially larger than the original 4-genre estimate (20-40 stories)
and should get a fresh cost/latency estimate scaled from WI-EVENT-0026/9's
existing per-pass cost/baseline reporting before being run, not assumed to
be roughly double the original.

Both A and B depend on Gap 1 landing first (the classifier must support
all 8 genres before either can run against the real target list), and A
should run before B so B's per-genre sampling draws from an actual current
genre census rather than the stale 2025-10 numbers.

## Non-goals of this document

- Does not modify `assess.py`, `assess_cli.py`, or any prompt/schema code.
- Does not run `lcats assess` or the Event-Role-World pipeline at any
  scale.
- Does not create the follow-up work items sketched above as formal LRH
  work-item files — that should happen via the standard `/lrh-work-item`
  flow once this reconciliation is reviewed, so the work items can be
  scoped with full LRH frontmatter (related workstream, exit criteria,
  etc.) rather than sketched inline here.
- Does not choose the paper's final statistical method or decide whether
  "war," "medical," or other non-priority genres need their own
  classificatory support beyond being representable as free-text/secondary
  tags.
