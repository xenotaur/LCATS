# Gatherer Reconciliation Audit

`WI-GATHER-0101`. Audits `mass_quantities`, `sherlock`, and
`lovecraft`'s own separate `gather()`/`gather_stories()` implementations
against `gatherlib.gather()`'s real signature and behavior
(`lcats/src/lcats/gatherers/gatherlib.py:89-159`), to determine which (if
any) can be reconciled onto the shared function. Follows the
`WI-SEGMENT-0069`/`WI-EVENT-0028` precedent for investigation-type work
items: real file:line citations, a per-site classification, and an
explicit recommendation.

## `gatherlib.gather()`'s actual contract

Reading `gatherlib.py:89-159` directly (not from memory or prior
descriptions):

- **Signature:** `gather(corpus, target_directory, description,
  license_text, author, year, headings, gutenberg_url,
  paragraph_finder=find_paragraphs, verbose=True,
  log_dir=DEFAULT_GATHER_LOG_DIR)`.
- **Shape assumed:** one `gutenberg_url` shared by every entry in
  `headings`; each `headings` entry is `(raw_filename, heading_text,
  title)`; per-entry text is located by searching for `heading_text`
  inside one shared document (`find_paragraphs`, `gatherlib.py:20-49`) —
  not fetched from a per-entry URL.
- **Callback:** `create_download_callback` (`gatherlib.py:52-86`) builds
  a `story_data` dict from `author`/`year` (function-level, shared
  across every entry) plus a `paragraph_finder` callable, defaulting to
  `find_paragraphs`.
- **Error handling:** no per-story exception isolation.
  `gatherer.download()` (`downloaders.py:239-279`) has no internal
  `try`/`except`, and `gather()`'s own loop (`gatherlib.py:129-156`) has
  none either — an unhandled `download()` failure aborts the whole call.
  This was a deliberate Non-Goal of `WI-RUNLOG-0082` (not something this
  audit should try to change without explicit sign-off, per this WI's
  own Non-Goals).
- **Logging:** wraps the loop in a `run_log.RunLog` scope
  (`gatherlib.py:123-156`, delivered by `WI-RUNLOG-0082`/`WI-RUNLOG-0083`
  and the direct motivation for this audit).

## Site 1: `sherlock/gatherer.py` — **Full reconciliation**

`lcats/src/lcats/gatherers/sherlock/gatherer.py:123-141`'s `gather()`
reproduces `gatherlib.gather()`'s own loop 1:1: same `DataGatherer`
construction, same per-heading `.download()` call, same
`ADVENTURES_HEADINGS` tuple shape `(filename, heading, title)` as
`gatherlib.gather()`'s `headings` parameter expects. The only
differences are values that would become call-site arguments:
`author="Arthur Conan Doyle"` and `year=1891` are hardcoded inside
`sherlock.create_download_callback` (`sherlock/gatherer.py:111-116`)
instead of being threaded through as `gatherlib.gather()`'s own
`author`/`year` parameters.

**One real behavioral divergence found**, not just a naming difference:
`sherlock.find_paragraphs_adventures` (`sherlock/gatherer.py:71-92`)
only collects `<p>` tags (`current_element.name == "p"`,
`sherlock/gatherer.py:88`), while `gatherlib.find_paragraphs`
(`gatherlib.py:45`) also collects `<pre>` tags
(`current_element.name == "p" or current_element.name == "pre"`).
Reconciling onto `gatherlib.find_paragraphs` directly would widen
Sherlock's extraction to include any `<pre>` blocks between the heading
and the next division tag — a behavior change, even if a likely-benign
one for this specific Gutenberg HTML source (Sherlock's source page has
no `<pre>` blocks in the relevant sections, based on the story text
already gathered successfully under the narrower version). This is the
kind of "unambiguous, low-risk" case the WI's own Non-Goals name as
eligible for in-run sign-off — but it is not fully unambiguous without
someone confirming the source HTML has no `<pre>` content in scope,
so this audit does not resolve it unilaterally; see Recommendation
below.

**Design sketch:** replace `sherlock/gatherer.py:123-141`'s `gather()`
body with a direct call:

```python
def gather():
    return gatherlib.gather(
        corpus="Sherlock Holmes",
        target_directory=TARGET_DIRECTORY,
        description="Sherlock Holmes stories from the Gutenberg Project.",
        license_text="Public domain, from Project Gutenberg.",
        author="Arthur Conan Doyle",
        year=1891,
        headings=ADVENTURES_HEADINGS,
        gutenberg_url=ADVENTURES_GUTENBERG,
        paragraph_finder=gatherlib.find_paragraphs,
    )
```

`find_paragraphs_adventures` and `create_download_callback` would then
be dead code, removable. This also closes the run-log gap for this site
as a side effect — no separate `WI-RUNLOG-*` follow-up needed for
Sherlock specifically once reconciled.

## Site 2: `lovecraft/gatherer.py` — **No reconciliation** (real structural incompatibility, corrected from the WI's own initial premise)

`lcats/src/lcats/gatherers/lovecraft/gatherer.py:123-134` shares
`gatherlib.gather()`'s outer loop shape (a `DataGatherer`, one
`.download()` call per entry), but two real incompatibilities with
`gatherlib.gather()`'s actual signature make direct reconciliation
unsafe as a same-signature swap:

1. **Per-entry URL, not one shared `gutenberg_url`.** Each story is its
   own `extractors.Extractor` object (`lovecraft/gatherer.py:11-13`,
   `make_extractor(title, url, author=...)`), each carrying its own
   `url` (`extractors.py:15-30`). `gatherlib.gather()`'s signature has
   exactly one `gutenberg_url` parameter shared by every `headings`
   entry — there is no way to pass a distinct URL per entry today.
2. **ID-based extraction, not heading-text search.**
   `lovecraft.create_download_callback` (`lovecraft/gatherer.py:95-120`)
   calls `extractors.extract_text_between_ids(story_soup)`
   (`lovecraft/gatherer.py:105`, defined at `extractors.py:189-206` —
   locates content between two HTML element IDs), never taking a
   `start_heading_text` argument at all. `gatherlib.gather()`'s
   `paragraph_finder` callable contract
   (`create_download_callback(..., paragraph_finder=find_paragraphs)`,
   `gatherlib.py:52-86`) is heading-text search only; `extract_text_between_ids`
   has a fundamentally different signature (`soup, start_id, end_id,
   content_tags, separator` — `extractors.py:189-194`) that doesn't fit
   the `paragraph_finder(soup, start_heading_text)` call shape
   `gatherlib.create_download_callback` invokes at `gatherlib.py:71`.

**Design sketch, if pursued as a follow-up (not this audit's job to
implement):** `gatherlib.gather()` would need two signature extensions —
accepting a per-entry URL (e.g. `headings` entries carrying
`(filename, url_or_heading, title)` with a mode flag, or a parallel
`gather_by_id()` sibling function) and accepting a pluggable full
extraction-strategy callable, not just a `paragraph_finder`. This is a
non-trivial widening of `gatherlib.gather()`'s own contract, not a small
scoped patch — the kind of change this audit's own Non-Goals require
explicit sign-off for, and given its size, better scoped as its own
deliverable work item than done inside this investigation.

**Correction to this WI's own initial premise:** the WI's first draft
characterized Lovecraft as "near-identical" to `gatherlib.gather()` —
that was wrong (caught by a Codex review on PR #412 before this WI was
even executed) and is not repeated here; the loop shape is shared, but
the extraction mechanism is not.

## Site 3: `mass_quantities/gatherer.py` — **No reconciliation**

`lcats/src/lcats/gatherers/mass_quantities/gatherer.py:26-58`'s
`gather_stories()` is not a corpus-with-known-headings gatherer at all —
it is a bulk scanner over raw Gutenberg story IDs
(`storymap.py:99`'s `SINGLE_STORIES` list), filtered by metadata
criteria (`parser.gather_story`, `parser.py:1365-1483`: subject/language/
title/author checks at `parser.py:1381-1395`, an exclusion list at
`parser.py:1397-1399`, chapter detection at `parser.py:1415-1416`, a
minimum-length filter at `parser.py:1418-1424`) that has no equivalent
concept anywhere in `gatherlib.gather()`. There is no `headings` list to
search a single document against; each Gutenberg ID is its own
independent fetch-and-classify operation with no shared source document
at all. Reconciling this onto `gatherlib.gather()` would mean building
an entirely different function, not extending the existing one — this
audit classifies it as no reconciliation, full stop, not merely "not
attempted."

**Error-handling correction (the WI's own acceptance criterion,
verified directly against the code, not assumed):**
`gather_stories()` (`mass_quantities/gatherer.py:26-58`) returns a
`failed_stories` dict rather than propagating every failure, but this is
**not** general per-story exception isolation. Reading
`parser.gather_story()` in full (`parser.py:1365-1483`):

- Only `api.load_etext(story)` is wrapped in `try`/`except`
  (`parser.py:1402-1405`).
- Everything before it (`api.get_metadata` calls, `parser.py:1377-1388`)
  and everything after it — `headers.strip_headers`/`.decode()`
  (`parser.py:1407-1408`), `body_of_text()` (`parser.py:1413`),
  `chaptered()` (`parser.py:1415`), `names.title_and_author_to_filename()`
  (`parser.py:1430-1432`), `normalization.normalize_story_dict()`
  (`parser.py:1466-1470`), `gatherer.ensure()` (`parser.py:1477`), and
  the final `json.dump()` write (`parser.py:1480-1481`) — are all
  **unprotected**. Any exception raised in any of these would propagate
  straight out of `gather_story()`, then straight out of
  `gather_stories()`'s own loop (`mass_quantities/gatherer.py:49-56`,
  which has no `try`/`except` of its own either), aborting the whole
  `gather_stories()` call exactly the same way an unhandled `download()`
  failure aborts `gatherlib.gather()` today.
- `failed_stories` mostly records **explicit rejection values**
  `gather_story()` itself returns on purpose (bad metadata, excluded
  story, chaptered, too short — each an early `return story, None,
  "<reason>"`, not a caught exception) — i.e. expected filtering
  outcomes, not crash recovery.

This confirms the review finding on PR #412: the original premise that
`mass_quantities` "already does its own per-story error collection ...
unlike `gatherlib.gather()`'s current behavior" overstated what actually
exists. In the one dimension that matters for the run-log
question — does an unhandled exception mid-run abort everything or not —
`mass_quantities` and `gatherlib.gather()` behave the same way today: no
isolation, whole-call abort. There is no error-handling contract change
that reconciling `mass_quantities` would require `gatherlib.gather()` to
absorb, because `mass_quantities` does not actually have one beyond what
`gatherlib.gather()` already has.

## Recommendation

| Site | Classification | Follow-up warranted? |
|---|---|---|
| `sherlock` | Full reconciliation | Yes — small, mechanical; recommend a new deliverable work item to (a) confirm the source HTML has no in-scope `<pre>` content (or accept the widened extraction as harmless), then (b) replace `gather()`'s body with the `gatherlib.gather()` call sketched above and delete the now-dead `find_paragraphs_adventures`/`create_download_callback`. This closes the run-log gap for Sherlock as a side effect. |
| `lovecraft` | No reconciliation without extending `gatherlib.gather()` first | Only if `gatherlib.gather()` itself is deliberately widened (per-entry URL + pluggable extraction strategy) as its own separate, explicitly-scoped deliverable work item — not a byproduct of reconciling Lovecraft. Until then, Lovecraft stays separate and would need its own dedicated run-log work item (a small, scoped addition mirroring `WI-RUNLOG-0080`'s pattern) if run-log coverage is wanted for it specifically. |
| `mass_quantities` | No reconciliation | No — structurally a different kind of gatherer (bulk ID scan + metadata filter, not corpus-with-headings). If run-log coverage is wanted for `mass_quantities` specifically, it needs its own dedicated work item wrapping `gather_stories()`'s own loop, not a `gatherlib.gather()` change. |

No implementation was made in this audit — per this WI's own Non-Goals,
none of the three findings above is unambiguous enough to act on without
a live human decision (Sherlock's `<pre>`-tag question is close, but not
fully resolved by this pass alone; Lovecraft and `mass_quantities` both
require new, separately-scoped work first). All three are reported here
as findings for a human to act on via new work items, per the WI's own
acceptance criterion.
