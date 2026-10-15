# Decode cached text without network access

Use `resources.decode_text` after acquiring original bytes, or with a small local
byte string. It returns text and provenance in memory; it creates no cache files
and never fetches URLs, linked images or stylesheets.

```python
from lcats.gettenberg import resources

result = resources.decode_text("A café story.\n".encode("utf-8"))
print(result.text)
print(result.source_sha256, result.encoding, result.encoding_source)
```

For an existing `SourceArtifact` called `artifact`, decoding rechecks the original
file and receipt. Supply the selected resource's catalog format claims when known:

```python
result = resources.decode_text(artifact, catalog_formats=("text/plain",))
print(result.identity, result.diagnostics)
```

In a catalog workflow, build that tuple with
`tuple(term.value.text for term in selection.resource.formats)`, after checking
that selection returned a resource. A selected format is still only metadata;
the decoder validates the actual bytes and rejects unsupported extractors.

If declarations conflict, inspect `ResourceDecodeError.code` and `.diagnostics`.
Resolve the source evidence before deliberately overriding an encoding:

```python
result = resources.decode_text(
    b"caf\xe9",
    options=resources.DecodeOptions(encoding_override="windows-1252"),
)
assert result.text == "café"
```

The override is recorded in the result's identity and encoding source. Invalid
bytes never become replacement characters, and failed decoding leaves originals
intact. HTML returns markup for the separate extraction layer; it does not remove
Gutenberg headers or segment stories.

Gzip and ZIP are recognized from their signatures. ZIPs with multiple text
members require an exact member name. This example needs no filesystem or network:

```python
import io
import zipfile

archive_bytes = io.BytesIO()
with zipfile.ZipFile(archive_bytes, "w") as archive:
    archive.writestr("one.txt", "First story")
    archive.writestr("two.txt", "Second story")
result = resources.decode_text(
    archive_bytes.getvalue(),
    options=resources.DecodeOptions(zip_member="two.txt"),
)
assert result.text == "Second story"
assert result.zip_member == "two.txt"
```

Limits default to 32 MiB original bytes, 64 MiB inflated bytes per stage and 1000
ZIP entries. Increase a bound explicitly only when the input is expected to need
it. Unknown codecs, ambiguous declarations, unsafe containers and unsupported
formats produce actionable errors; they do not trigger fallback downloads.

See the [reference](../reference/gettenberg-decoding.md) for exact precedence,
container support, limits, error codes and memory guarantees, and the
[acquisition guide](gettenberg-resources.md) for obtaining original bytes.
