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

**A behavioral divergence exists between `sherlock.find_paragraphs_adventures`
(`sherlock/gatherer.py:71-92`) and `gatherlib.find_paragraphs`
(`gatherlib.py:20-49`)** — the former only collects `<p>` tags
(`current_element.name == "p"`, `sherlock/gatherer.py:88`), the latter
also collects `<pre>` tags (`gatherlib.py:45`) — **but this divergence
does not need to be resolved to reconcile Sherlock, and the first draft
of this design sketch was wrong to route through it** (review finding,
PR #414). `gatherlib.gather()` already accepts a `paragraph_finder`
callable parameter (`gatherlib.py:98`, defaulting to
`gatherlib.find_paragraphs` but freely substitutable) specifically so a
caller can supply its own extraction function. Since
`find_paragraphs_adventures(soup, start_heading_text)` already matches
the exact call shape `gatherlib.create_download_callback` invokes
(`paragraph_finder(story_soup, start_heading_text)`, `gatherlib.py:71`),
passing it in directly — unchanged, not replaced — reconciles Sherlock
with **zero behavior change and no `<pre>`-tag risk at all**. No
remote-HTML confirmation is needed; the divergence is simply never
exercised.

**Design sketch:** replace `sherlock/gatherer.py:123-141`'s `gather()`
body with a direct call, passing the existing
`find_paragraphs_adventures` through unchanged:

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
        paragraph_finder=find_paragraphs_adventures,
    )
```

Only `create_download_callback` becomes dead code, removable — not
`find_paragraphs_adventures`, which stays and is passed through as-is.
This also closes the run-log gap for this site as a side effect — no
separate `WI-RUNLOG-*` follow-up needed for Sherlock specifically once
reconciled.

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

**A third incompatibility, found on review** (PR #414): even the two
extensions below are not sufficient to preserve Lovecraft's exact
behavior. `gatherlib.create_download_callback` stores the *normalized
filename* as `story_data["name"]`
(`story_name`, threaded from `gatherlib.gather()`'s own loop variable
`filename`, `gatherlib.py:77-82`, `gatherlib.py:130,138`), while
`lovecraft.create_download_callback` stores the *display title*,
`extractor.title`, as `story_data["name"]`
(`lovecraft/gatherer.py:111-116`). Routing Lovecraft through
`gatherlib.create_download_callback` unchanged would silently rewrite
every story's stored `name` field from a human-readable title (e.g.
`"The Call of Cthulhu"`) to a filename slug — a real data change, not
cosmetic. Any reconciliation design needs a third extension: either a
pluggable per-entry metadata-name source, or `gatherlib.gather()`
accepting a `create_download_callback` override entirely rather than
composing its own internally.

**Design sketch, if pursued as a follow-up (not this audit's job to
implement):** `gatherlib.gather()` would need at least three signature
extensions — accepting a per-entry URL (e.g. `headings` entries carrying
`(filename, url_or_heading, title)` with a mode flag, or a parallel
`gather_by_id()` sibling function), accepting a pluggable full
extraction-strategy callable (not just a `paragraph_finder`), and either
a pluggable metadata-`name` source or a way to substitute the whole
callback. This is a
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
exists — but **a follow-up review on PR #414 correctly flagged that the
correction above itself overcorrected.** `mass_quantities` is *not*
identical to `gatherlib.gather()`'s error-handling behavior: the one
`try`/`except` that does exist (`parser.py:1402-1405`, around
`api.load_etext()`) means that when *that specific* call fails,
`gather_story()` returns an error tuple rather than raising, and
`gather_stories()`'s loop (`mass_quantities/gatherer.py:49-56`) records
it in `failed_stories` and continues to the next Gutenberg ID —
`load_etext()` failing on one story does not abort the whole run. This
is a real, narrower per-story exception contract that `gatherlib.gather()`
does not have at all today: an unhandled `download()` failure there
always aborts the whole call, with no equivalent single-call-type
carve-out. So the accurate statement is neither "general isolation"
(the original overstatement) nor "no isolation at all, identical to
`gatherlib.gather()`" (this doc's own first-draft overcorrection):
`mass_quantities` has *narrow* per-story recovery, scoped to exactly one
failure mode (`load_etext()`), while every other exception path
(metadata access, parsing, filename construction, normalization,
directory creation, the JSON write) remains unprotected and would still
abort the whole `gather_stories()` call, same as `gatherlib.gather()`
today. Any hypothetical reconciliation would need to either preserve
this narrow carve-out (e.g. `gatherlib.gather()` gaining an optional,
explicitly-opted-into per-story-recoverable-exception-type parameter) or
explicitly decide to drop it — not silently assume no error-handling
change is needed at all.

## Recommendation

| Site | Classification | Follow-up warranted? |
|---|---|---|
| `sherlock` | Full reconciliation, zero behavior change | Yes — small, mechanical, and now unambiguous: recommend a new deliverable work item to replace `gather()`'s body with the `gatherlib.gather()` call sketched above, passing the existing `find_paragraphs_adventures` through unchanged, and delete the now-dead `create_download_callback`. No `<pre>`-tag confirmation needed. This closes the run-log gap for Sherlock as a side effect. |
| `lovecraft` | No reconciliation without extending `gatherlib.gather()` first (3 incompatibilities: per-entry URL, extraction mechanism, metadata-name source) | Only if `gatherlib.gather()` itself is deliberately widened as its own separate, explicitly-scoped deliverable work item — not a byproduct of reconciling Lovecraft. Until then, Lovecraft stays separate and would need its own dedicated run-log work item (a small, scoped addition mirroring `WI-RUNLOG-0080`'s pattern) if run-log coverage is wanted for it specifically. |
| `mass_quantities` | No reconciliation | No — structurally a different kind of gatherer (bulk ID scan + metadata filter, not corpus-with-headings), with a narrow `load_etext()`-only per-story recovery `gatherlib.gather()` doesn't share. If run-log coverage is wanted for `mass_quantities` specifically, it needs its own dedicated work item wrapping `gather_stories()`'s own loop, not a `gatherlib.gather()` change. |

Sherlock's reconciliation is now unambiguous enough (zero behavior
change, confirmed on review) that it would have qualified for the WI's
own Non-Goals sign-off clause allowing in-run implementation — it is not
implemented here regardless, since the finding only reached this
clarity during this same PR's review-response, after the investigation
itself was otherwise complete; it is reported as a ready-to-implement
recommendation instead, for a human to act on via a new, separately
tracked work item. `lovecraft` and `mass_quantities` both require new,
separately-scoped work before any reconciliation decision can even be
made (a `gatherlib.gather()` extension design for Lovecraft; an explicit
decision on the `mass_quantities` `load_etext()` recovery carve-out).
All three are reported here as findings for a human to act on, per the
WI's own acceptance criterion — none implemented by this WI.
