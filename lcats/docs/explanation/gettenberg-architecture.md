# Why gettenberg separates metadata, original bytes and stories

Gettenberg makes the inputs to a story inspectable. A Gutenberg catalog describes
an ebook or volume; it does not establish which portion is a story, prove a
resource is downloadable, or authorize network access. Keeping these decisions
separate lets a caller query metadata offline, preserve original evidence and
repeat a transformation without silently changing its inputs.

```text
local/acquired RDF archive → candidate catalog → verified active generation
                                                   ↓ pinned metadata reader
resource metadata → explicit route → original bytes + retrieval receipt
                                            ↓ strict offline decoding
                                      decoded text + identity
                                            ↓ conservative cleanup
                                      text span + diagnostics
                                            ↓ collection extraction
                                      story.json + provenance
```

The arrows are separate operations. `ingestion` parses a bounded archive into an
inactive SQLite catalog. `lifecycle` retains the archive, verifies a candidate
and publishes its generation pointer. `CatalogPreparation` composes first-use
planning and approval. CLI commands add the published default source profile;
`CatalogPreparation` and `ResourceStore` choose no source themselves.

## A cache hit is an identity decision

A catalog generation ties an archive hash to parser/schema versions and a sealed
database. Opening a reader pins that generation. Publishing another generation
does not change an already-open reader's view. Retaining old generations also
allows deliberate rollback without guessing which files belong together.

The resource store has a different identity: a concrete request maps to original
response-body bytes and a retrieval receipt. Those bytes may still be compressed.
A verified hit is reusable offline indefinitely; it says nothing about whether a
server now offers newer bytes. `refresh` is a separate authorized network check,
while `rebuild` derives a new catalog locally. An unchanged acquired archive can
reuse its existing generation, preserving the receipt that actually built it.

The distinction is visible before any cache exists. Run this example in Python;
it only creates and removes a temporary directory:

```pycon
>>> import pathlib
>>> import tempfile
>>> from lcats.gettenberg import preparation, resources
>>> temporary = tempfile.TemporaryDirectory()
>>> cache = pathlib.Path(temporary.name) / "cache"
>>> service = preparation.CatalogPreparation(cache)
>>> service.plan().action
'blocked'
>>> service.plan(required=False).action
'not_required'
>>> store = resources.ResourceStore(cache)
>>> request = resources.SourceRequest.from_url("https://example.org/book.txt")
>>> store.plan(request).reason
'offline cache miss'
>>> policy = resources.NetworkPolicy(online=True, allowed_origins=("https://example.org",))
>>> store.plan(request, policy=policy).action
'download'
>>> cache.exists()
False
>>> temporary.cleanup()

```

Planning a download grants no permission by itself and makes no request. Network
policy governs acquisition; setup approval governs creating a missing catalog;
count-change approval governs publication of a changed catalog size. The CLI's
`--offline` overrides network authority, and `--yes` grants only missing setup.
A ready catalog bypasses unused source arguments and never refreshes implicitly.

## Derived text does not replace its evidence

Strict decoding checks bytes, container bounds and encoding claims. Its identity
records the source and interpretation choices, including an explicit encoding
override. Cleanup returns a span of the decoded text with policy version and
diagnostics; it does not normalize whitespace or overwrite originals. Ambiguous
recognized envelopes are preserved by cleanup and refused by the story-source
adapter. Marker-free text can proceed to collection extraction.

Collection extraction applies eligibility, body/chapter rules, normalization and
per-story overrides after those stages. Its provenance connects the published
story to the catalog, selected resource, acquisition, decode, cleanup and body
selection inputs. The opening-prefix body policy stops interpreting headings at
the first unknown paragraph; it favors retaining uncertain editorial text over
losing narrative when a title or author recurs later. Its contiguous span makes
that choice inspectable. Chapter assessment excludes complete book-title/byline
matches from its weak all-capital-heading heuristic while retaining explicit
section markers. Its paragraph-index evidence travels with inspection/publication
provenance; no story text is deleted to make a classification pass.
Publication readiness is a separate decision after candidate extraction. Explicit
editorial cues and ambiguous chapter evidence yield `needs_review`; originals and
candidate text remain intact outside accepted story buckets. A complete narrative
can survive extraction while still needing review because advertisements or notes
were also retained. Conversely, a long editorial note is not made a story merely
by satisfying the paragraph-count rule.

Reviewed selections bind exact source context, candidate, assessment and selected
text identities. They cannot silently survive source/policy drift, and they cannot
override definite collection exclusions. The reviewer may resolve uncertainty
without changing the extractor into a broad deletion heuristic. Batch reports
separate publication, reuse, ineligibility, review and cleanup refusal; operational
failures still abort. Download consent grants no content approval.

This policy makes uncertainty observable; it does not prove every unflagged text
is narrative. Corpus qualification and per-input material dispositions remain
necessary. The initial historical census required review for nearly all inputs;
no automatic-coverage target or corpus-wide acceptance follows from the gate.
An existing regular story output is reused without replacement or validation.
That reuse is an operational choice, not evidence of corpus equivalence.

## Failure preserves inspectable state

A failed or incomplete catalog cannot become active. A changed ebook count leaves
a recoverable candidate and the previous active generation intact. Activation
rechecks identity and integrity; a pointer-publication error can explicitly report
that publication already occurred, so status must be inspected before retrying.
Corrupt cache evidence is a failure, not an invitation to redownload silently.

Retention intentionally trades disk space for reproducibility and safe readers.
Catalog cleanup removes candidates and known publication temporary files, not
published generations or archives. The destructive cache-clean command has a
separate scope and requires other LCATS processes to be stopped. Filesystem
locking, atomic replacement and hard-link support matter to these guarantees;
see the [lifecycle reference](../reference/gettenberg-lifecycle.md).

These mechanisms provide traceable derivation and bounded operations. They do
not establish full-snapshot metadata coverage, whole-corpus equivalence, endpoint
availability or release readiness. Those require separate measured evidence on
identified inputs. Start with the [offline tutorial](../tutorials/gettenberg-first-catalog.md),
then use the [gathering contracts](../reference/gettenberg-gather.md) for the
consumer-specific behavior and defaults.
