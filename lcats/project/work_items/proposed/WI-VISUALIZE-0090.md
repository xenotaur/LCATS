---
resolution: null
blocked_reason: null
blocked: false
id: WI-VISUALIZE-0090
title: "TF-IDF distinguishing-terms contrast metric: lcats visualize tfidf --contrast"
type: deliverable
status: proposed
owner: unassigned
contributors: []
assigned_agents: []
related_focus:
  - FOCUS-WORLDCON-2026
related_roadmap: []
related_workstreams:
  - WS-CORPUS-TEXT-VISUALIZATION
related_design:
  - project/design/proposals/adopted/corpus-text-visualization/00_proposal.md
  - lcats/src/lcats/visualize/analysis.py
depends_on:
  - WI-VISUALIZE-0073
  - WI-VISUALIZE-0085
  - WI-VISUALIZE-0086
  - WI-VISUALIZE-0089
blocked_by: []
expected_actions:
  - create_file
  - edit_file
  - run_tests
  - create_pr
  - write_docs
forbidden_actions:
  - force_push
  - delete_branch
  - implement_new_architecture
  - promote_sidecars
  - modify_lcats_annotate
  - modify_lcats_promote
acceptance:
  - "`lcats visualize tfidf` gains a new, additive `--contrast` mode -- not a change to existing behavior: with `--contrast`, `tfidf_top_terms` (or a new sibling function) computes both the selected group's mean TF-IDF and the complement group's (every corpus story not in `group_indices`) mean TF-IDF, over the same corpus-wide-IDF matrix, and ranks terms by `group_mean - complement_mean` (a simple, robust baseline metric -- not a statistical significance test; log-odds/chi-square-style weighting is explicitly deferred, following the same 'baseline first' choice `WI-VISUALIZE-0087` made for `topics`)"
  - "The **default** (no `--contrast`) computation and every existing manifest field are unchanged -- every existing `tfidf_top_terms`/`run_tfidf` test continues to pass unmodified, confirming this is additive, not a breaking change. A new `mode` field disclosing `salience` (default) vs `contrast` is an explicitly allowed additive manifest extension, not a violation of this criterion -- only removing or changing the meaning of an existing field, or changing the default ranking itself, would be. The existing within-group-mean-salience mode (and its own accurate documentation, delivered by `WI-VISUALIZE-0089`) remains available and correct"
  - "`--contrast` requires `--genre` (or another comparison-group selector) to be set -- a whole-corpus run has no complement to contrast against, so `--contrast` with no selector raises a clear, documented error rather than silently producing an undefined or degenerate result"
  - "The contrast-ranking function is unit-tested independently of rendering, on tiny fixtures: a term common only within the selected group must rank above a term equally common in the group and its complement, and above a term more common in the complement than the group"
  - "The manifest discloses which mode (`salience` default vs `contrast`) produced the figure, alongside the existing input-revision/content-identity disclosure convention (`corpus_source_revision`, `candidates_source_revision`) already established by `WI-VISUALIZE-0086`"
  - "Rendering reuses the existing `plot_bar_chart`/`plot_tfidf_bar_chart` primitives (or a thin wrapper over them) -- no new parallel plotting API"
  - "At least one real contrast figure (e.g. a genre-vs-rest-of-corpus run) is dogfooded against the real, checked-in corpus and committed -- most naturally as a documented addendum to the existing `experiments/08_visualize_dogfood/` location (updating its README) rather than a new numbered experiment directory, since it extends the same dogfooding effort `WI-VISUALIZE-0088` already delivered"
  - "`docs/how-to/run-visualize.md` and `docs/reference/cli-commands.md` are updated to document `--contrast` accurately, reconciling with the within-group-salience-mode caveats `WI-VISUALIZE-0089` added -- the two modes' descriptions must not contradict each other"
  - "scripts/test passes with no new failures"
  - "lrh validate introduces no new errors: the pre-existing repo-wide error count at this WI's start is a known, out-of-scope baseline (documented in its own execution record), not a blocker this item must fix; this item's own new/changed files parse and validate cleanly"
required_evidence:
  - test_output
  - lrh_validate
  - manual_review
artifacts_expected:
  - "lcats/src/lcats/visualize/analysis.py (extended: contrast-ranking function)"
  - "lcats/src/lcats/visualize/cli.py (extended: --contrast option on the tfidf subcommand)"
  - lcats/tests/visualize_tests/ (new tests)
  - "experiments/08_visualize_dogfood/ (extended: at least one real contrast figure, README updated)"
  - lcats/docs/how-to/run-visualize.md (updated)
  - lcats/docs/reference/cli-commands.md (updated)
---

# Work Item: WI-VISUALIZE-0090

## Summary

Add a genuine group-vs-complement contrast metric to `lcats visualize
tfidf`, as a new, additive `--contrast` mode. This closes a real gap
between `WS-CORPUS-TEXT-VISUALIZATION`'s own exit criterion ("`lcats
visualize tfidf` produces TF-IDF *comparison* visualizations") and what
`WI-VISUALIZE-0086` actually delivered: `tfidf_top_terms` computes only
the selected group's own mean TF-IDF, never a background/complement
mean, so it ranks within-group *salience*, not a true
distinguishing/contrast measure -- a distinction `WI-VISUALIZE-0089`'s
own review round surfaced and corrected in the documentation, without
changing the underlying algorithm.

## Problem / Context

During `WI-VISUALIZE-0089` (usage documentation), a review-bot finding
(independently re-verified against the real `tfidf_top_terms`
implementation) established that the command's `--help` text and this
project's own prior documentation both described `--genre`-filtered
`tfidf` runs as ranking terms that "distinguish" the subset from the
rest of the corpus -- but the actual computation
(`matrix[group_indices].mean(axis=0)`) never touches the complement
group at all. A majority genre's terms therefore rank almost identically
to the whole-corpus run, and a globally common term can outrank a term
genuinely more characteristic of the subset, simply because it also
appears frequently within the subset.

This work item was scoped, in conversation with the workstream owner,
as a deliberately **additive** follow-up rather than a change to
`WI-VISUALIZE-0086`'s existing behavior: the already-dogfooded
`tfidf_fantasy`/`tfidf_science_fiction` figures under
`experiments/08_visualize_dogfood/` remain valid, accurate examples of
the existing within-group-salience metric (now correctly documented as
such); this item adds a second, genuinely comparative metric alongside
it, not in place of it.

### Prior Art Check

- In-repo: no existing `complement`/`contrast` computation exists
  anywhere in `lcats/src/lcats/visualize/` or `lcats/src/lcats/analysis/`
  (confirmed via `grep -rn "complement\|contrast"` across both
  directories -- no hits). `tfidf_top_terms`'s existing
  `TfidfVectorizer` fit and `group_indices` selection machinery should
  be reused directly (the new mode needs only an additional
  complement-indices computation and a different ranking formula, not a
  parallel vectorization pipeline).
- Sibling repos / external libraries: none required beyond what's
  already a core dependency (scikit-learn).
- Demand: originates directly from this workstream's own exit-criteria
  review at `WI-VISUALIZE-0089`'s closeout, not an external request;
  `WS-CORPUS-TEXT-VISUALIZATION`'s WS closeout is explicitly held open
  pending this item, per the workstream owner's direction.

## Scope

- A new `--contrast` CLI flag on `lcats visualize tfidf`, requiring
  `--genre` (or another future comparison-group selector).
- A group-vs-complement mean-TF-IDF-difference ranking function.
- Manifest disclosure of which mode produced a given figure.
- At least one real, dogfooded contrast figure committed to the existing
  `experiments/08_visualize_dogfood/` location.
- Documentation updates reconciling both `tfidf` modes.

## Out of Scope

- Changing the default (no `--contrast`) behavior, output schema, or
  existing tests of `tfidf_top_terms`/`run_tfidf` -- this item is
  additive only.
- A statistically rigorous contrast measure (log-odds ratio,
  chi-square, keyness) -- the simple mean-difference baseline is
  sufficient for this tranche; a future item may revisit this if the
  baseline proves inadequate for the paper's actual needs.
- Extending `--contrast` (or an equivalent) to `words`, `genres`, or
  `topics` -- out of scope unless a concrete need surfaces.
- A new numbered `experiments/` directory for the contrast figures --
  reuses and extends `experiments/08_visualize_dogfood/`.

## Required Changes

1. Extend `lcats/src/lcats/visualize/analysis.py` with a
   complement-aware contrast-ranking function (or a `contrast: bool`
   parameter on the existing `tfidf_top_terms`, whichever keeps the
   default path's behavior most clearly unchanged).
2. Extend `lcats/src/lcats/visualize/cli.py`'s `tfidf` subcommand with
   `--contrast`, validated to require `--genre`, and thread the mode
   through to the manifest.
3. Add tests covering the contrast-ranking correctness (group-only term
   ranks above group-and-complement term ranks above complement-only
   term), the `--contrast`-without-`--genre` error path, and that all
   existing `tfidf` tests still pass unmodified.
4. Dogfood at least one real contrast figure against the checked-in
   corpus; commit it under `experiments/08_visualize_dogfood/`, updating
   that experiment's README to document the new figure and its
   provenance.
5. Update `docs/how-to/run-visualize.md` and
   `docs/reference/cli-commands.md` to document `--contrast` accurately
   and reconcile with the existing salience-mode caveats.

## Likely Files

- `lcats/src/lcats/visualize/analysis.py`
- `lcats/src/lcats/visualize/cli.py`
- `lcats/tests/visualize_tests/`
- `experiments/08_visualize_dogfood/`
- `lcats/docs/how-to/run-visualize.md`
- `lcats/docs/reference/cli-commands.md`

## Validation

- `scripts/format --check --diff`
- `scripts/lint`
- `scripts/test`
- `lrh validate`
- `lcats visualize tfidf --genre fantasy --contrast --output-dir /tmp/tfidf_contrast_fantasy`, confirming a real, non-empty result whose ranking visibly differs from the existing salience-mode output for the same genre
- `lcats visualize tfidf --contrast --output-dir /tmp/tfidf_contrast_bad` (no `--genre`), confirming a clear, documented error rather than a crash or silent degenerate output

## Risk Notes

- **Ranking-formula choice is a baseline, not a final answer.** A simple
  mean-difference is easy to reason about and implement correctly but
  may prove too crude once real paper figures are reviewed (e.g. it has
  no notion of statistical significance or sample-size sensitivity).
  Document this explicitly as a deliberate, documented baseline choice,
  the same way `WI-VISUALIZE-0087` framed its NMF topic model.
- **Two `tfidf` modes must stay clearly distinguished in every surface**
  (CLI help, manifest, docs) -- a reader conflating "salience" and
  "contrast" results would be exactly the kind of misinterpretation this
  work item exists to prevent. Keep the mode explicit everywhere the
  metric's meaning matters, not just in the CLI flag name.
