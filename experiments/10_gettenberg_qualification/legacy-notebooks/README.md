# Historical upstream diagnostics (unsupported)

These notebooks are retained byte-for-byte as research history, not maintained
LCATS examples. The manifest records their original paths, revision and hashes.
They require that historical checkout and its pinned gutenbergpy environment.
They inspect old SQL, monkeypatch upstream internals and may download/rebuild a
large catalog or change global settings; do not run them against a current/live
cache. Existing outputs were not changed and no notebook was executed to archive it.

Supported replacements are LCATS catalog/lifecycle status and query APIs, and
`gatherers.parser.inspect_story(id, source=...)` for structured extraction evidence.
Regression coverage lives in catalog_test.py, lifecycle_test.py, migration_test.py
and live_gather_test.py under lcats/tests. IDs 24927/3115 in the notebooks remain
unverified historical leads; authored tests using those IDs are not assertions
about their actual Gutenberg content.

The obsolete print-only parser helpers are recoverable at the source revision in
`lcats/src/lcats/gatherers/parser.py`; their duplicated extraction/CSV behavior
is replaced by inspect_story and analysis.corpus.reconciliation. No duplicate
copy of executable library code is retained here.
