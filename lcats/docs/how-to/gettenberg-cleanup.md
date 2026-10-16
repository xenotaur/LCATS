# Remove a verified Gutenberg envelope without losing the source

Use this workflow for decoded plain text from Gutenberg. Keep the acquired
artifact and decoding result for provenance; cleanup returns an in-memory view
of the text and does not overwrite either. This example is entirely local:

```python
from lcats.gettenberg import cleanup
from lcats.gettenberg import resources

raw = (
    "*** START OF THE PROJECT GUTENBERG EBOOK A LANTERN ***\r\n"
    "\r\nA café kept its lamp lit.\r\n\r\n"
    "*** END OF THE PROJECT GUTENBERG EBOOK A LANTERN ***\r\n"
).encode("utf-8")
decoded = resources.decode_text(raw)
result = cleanup.strip_boilerplate(decoded.text)
assert result.changed
assert result.text == "\r\nA café kept its lamp lit.\r\n\r\n"
assert result.original == decoded.text
print(result.policy_version, result.content_start, result.content_end)
```

Passing bytes directly raises `CleanupInputError`; decoding is always explicit.
HTML returned by the decoder is still markup and needs separate extraction.
Cleanup performs no whitespace or story normalization; those belong to your
story-processing workflow.

Inspect the evidence before consuming a transformed text:

```python
for marker in result.markers:
    print(marker.kind, marker.line, repr(result.original[marker.start:marker.end]))
for diagnostic in result.diagnostics:
    print(diagnostic.code, diagnostic.message, diagnostic.line)
assert (
    result.original[:result.content_start]
    + result.text
    + result.original[result.content_end:]
) == decoded.text
```

If markers are absent, incomplete, repeated or contradictory—or surrounding
text does not look like a Gutenberg header/footer—the entire input is retained.
Do not treat `changed=False` as proof that the text contains no boilerplate:

```python
uncertain = "A story that mentions Gutenberg.\nTHE END\n"
preserved = cleanup.strip_boilerplate(uncertain)
assert not preserved.changed
assert preserved.text == uncertain
print([diagnostic.code for diagnostic in preserved.diagnostics])
```

Review a refusal against the source and decide whether it needs a new qualified
rule. Do not add a broad substring fallback to force a successful extraction.
The [reference](../reference/gettenberg-cleanup.md) lists supported modern and
historical forms, context checks, limits and diagnostic codes.

For a compact record, save boundaries and policy alongside your existing source
identity instead of copying the source into every downstream artifact:

```python
record = {
    "decoded_identity": decoded.identity,
    "cleanup_policy": result.policy_version,
    "content_start": result.content_start,
    "content_end": result.content_end,
    "diagnostics": [diagnostic.code for diagnostic in result.diagnostics],
}
assert result.original[record["content_start"]:record["content_end"]] == result.text
```

For complete in-memory evidence, `dataclasses.asdict(result)` is JSON-compatible
and includes the original text. This library does not write that record for you.
Legacy `headers.strip_headers` and `lcats gather` still use their existing path;
consumer migration is a separate planned step.
