# Publication readiness contract — 2026-10-20

Implements the human-approved [milestone](gettenberg-editorial-milestone.md) under
WI-GETTENBERG-0010. This is the bounded run's implementation specification, not
corpus acceptance. Approval permits an explicit review outcome; no human has
approved any individual source annotation by approving the direction.

## Decisions

- Keep pure gettenberg envelope cleanup and conservative contiguous candidate
  extraction unchanged. Readiness belongs in gatherers, where collection rules
  already live. Reuse corpus Finding span/evidence structure, not broad detectors
  as deletion rules. No machine-learning classifier or new dependency.
- Inspection returns `ready`, `needs_review`, or `ineligible`, with candidate text,
  pre-normalization character offsets and deterministic policy/findings. `ready`
  means no unresolved cues under this policy, not proof of literary purity.
  Metadata ineligibility causes no acquisition. Known short bodies remain ineligible.
- A chapter heuristic's all-caps/prefix cues do not prove chapters. Corroborated
  multi-work contents and multiple distinct standalone numbered section headings
  support exclusion; ambiguous structural evidence requires review. Editorial
  evidence prevents treating even numbered advertisement entries as certain
  structure. Existing chapter evidence remains inspectable. Genuine named sections
  may require review; they must never be silently promoted by weakening a boolean.
- Detect narrow explicit editorial labels anywhere, editorial publication/credit
  cues near boundaries, and uncertain opening labels. Do not flag ordinary words
  such as 'transcriber' inside a narrative sentence just for their presence.
  Record exact spans; do not delete anything in response to a warning.
- `gather_story` returns a structured result: published, reused, ineligible,
  needs_review. Cleanup refusal remains a structured source exception; batch
  gathering records it distinctly and continues, while operational failure aborts.
  Reused existing outputs are not requalified, overwritten, or labeled newly ready.
- Save review reports/candidates outside data and corpora under logs/gather/review,
  with content-derived names and a non-story filename. Reports contain provenance,
  candidate text, findings and identities. Preserve different generations and fail
  visibly on corrupt/colliding existing evidence; no automatic deletion.
- Batch API retains all outcome categories. CLI summarizes counts/paths, exits 3
  when review/cleanup refusals remain, 0 on completed eligible/ineligible/reuse-only
  runs, 2 on operational error. No per-story prompts. `--yes` remains setup approval
  only. Unrelated collections have no new Gutenberg dependency or gate.
- Explicit reviewed decisions use JSON records with ebook ID, source-context hash,
  candidate hash, assessment hash, selected contiguous span/hash, reviewer and
  rationale. Unknown/duplicate fields, wrong types, changed source/context/policy,
  mismatched selection or stale findings fail visibly. Source context also binds
  extraction and chapter policy/evidence even when the candidate text is unchanged. No blanket approve flag.
  Reviewer identifies the actual person/agent; it never implies a human signature.
  Decisions may resolve uncertain findings but cannot override metadata, too-short
  or corroborated multi-work exclusions. Reassess selected text before publication;
  all exclusions and retained findings remain in provenance. Exact candidate/source
  identities are anchors; separate text snippets are not needed for replay safety.
- Review selections happen before existing normalization; provenance distinguishes
  candidate, selected text and normalized output. Existing normalization/overrides
  remain a separate recorded transformation, not readiness approvals.

## Measurement and activation

Build the pure assessment and run an immutable 1,659-input census before wiring the
default gate. Record per-input identities/status/reasons and distinguish automatic
assessment from reviewed decisions. Inspect known cases plus common cue groups;
report volume and limitations without an invented automatic-coverage target. Then
wire the gate with offline end-to-end fixtures and source-bound positive recipes.
No canonical corpus regeneration. Material findings remain unresolved unless an
explicit per-input disposition covers them; repeated pattern alone is not acceptance.

## Validation

Authored positive/negative and stale-decision tests; real eight-anchor preservation
and reviewed temporary publication; five ambiguous chapter sources and genuine
multi-work negative; batch partial-run/reuse/cleanup/CLI outcomes; full corpus census;
canonical scripts and explicit experiment checks; fresh installed wheel; independent
review and bounded fixes. Historical output bytes and source identities remain intact.
