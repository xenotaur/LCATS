# Strict offline text decoding

`resources.decode_text(source, *, options=DecodeOptions(), catalog_formats=())`
is separate from acquisition, selection, boilerplate removal and story extraction.
It accepts immutable `bytes` or a `SourceArtifact`, returns immutable `DecodedText`,
and performs no network requests, filesystem writes, extraction or catalog setup.
The existing gather command has not yet migrated to this API.

For artifacts, the decoder validates the receipt schema/hash and its binding to
body hash/size, then reads a bounded regular nonsymlink file and checks for mutation.
Bare bytes carry no invented HTTP provenance. The trusted-local-cache boundary is
the same as acquisition; parent directories controlled by a hostile writer are
not a security isolation boundary.

## Options and limits

| DecodeOptions field | Default | Meaning |
|---|---|---|
| `encoding_override` | `None` | Explicit character encoding, with strict errors. |
| `container` | `"auto"` | `auto`, `none`, `gzip` or `zip`; explicit choice must match bytes. |
| `zip_member` | `None` | Exact safe text-member name; never an extraction destination. |
| `max_source_bytes` | 32 MiB | Original bytes read before any decompression. |
| `max_decoded_bytes` | 64 MiB | Output limit for each inflation stage and final encoded payload. |
| `max_zip_entries` | 1000 | Actual central directory records, counted before ZipFile indexes them. |
| `max_metadata_bytes` | 65536 | Combined declaration bytes plus one byte per field. |
| `html_scan_bytes` | 8192 | Prefix inspected for complete HTML encoding declarations. |

Integer bounds must be in 1..2147483647, excluding booleans. Bounds prevent
unbounded inflation; they are not a process memory or wall-clock quota. The
implementation holds original/intermediate bytes, decoded text and hashing/index
buffers in memory. Peak memory can exceed the per-stage bound, and Python strings
may use multiple bytes per character. No persisted derived cache is created.

## Format and container contract

Supported text media are `text/plain`, `text/html`, and `application/xhtml+xml`.
Catalog declarations are an immutable tuple of original MIME strings. HTTP
Content-Type comes only from an artifact's validated receipt. Malformed MIME and
extended charset parameters error; source filenames do not imply character encoding.
Conflicting text media error, except a selected ZIP member identifies its inner
media type by `.txt`, `.html`, `.htm` or `.xhtml` suffix. Missing text media defaults
to plain text with `default_media` diagnostic. This is an explicit interpretation
of untyped input, not proof that arbitrary binary input is a story.

One identity/gzip HTTP Content-Encoding is supported, followed by at most one
gzip or ZIP container. Every recognized container MIME declaration must match the
container signature after HTTP decoding; contradictory claims error. Inflation is bounded before output accumulates. Gzip CRC,
trailer and complete termination are checked; concatenated streams, trailing data
and further nested containers error. Recognized unsupported containers error too.

ZIP supports stored/deflated members only. The actual central directory count
and bounds are checked before allocating the member index. All names must be safe,
unique and free of traversal, absolute paths, backslashes, colons or control
characters. Encrypted, special-file, ZIP64, multidisk and unsupported-compression
entries are refused, including unselected entries. Selected local headers/overlap,
full inflated length and CRC are checked independently of declared output length.
Archives with unsupported layout/trailing data are refused. No member is extracted.

A ZIP needs exactly one text candidate or an explicit matching text-member name.
Assets are never decoded. EPUB (including its container manifest), PDF and audio
remain byte-retrieval only. Gzip/ZIP support is not a general archive extractor.

## Encoding decisions

Authority order is explicit override, Unicode BOM, HTTP charset, catalog charset,
HTML declaration, then UTF-8. Compatible codec aliases agree. Generic UTF-16/32
requires a matching BOM; otherwise specify the byte order explicitly, avoiding platform
endianness. Compatible BOM bytes are removed; an incompatible override preserves
them as input to the explicitly chosen decoder. Generic overrides are resolved to
the matching BOM's byte order before conflict detection. Exactly one leading BOM
is consumed; a following U+FEFF content character remains, including with utf-8-sig.

Without override/BOM, conflicting declarations raise `ambiguous_encoding` rather
than guessing. With override/BOM, conflicts and superseded unknown declarations
are diagnosed. Selected unknown codecs and invalid encoded bytes error. Python
character codecs are supported; binary and escape/IDNA/punycode transformations
are excluded. There is no guessed Latin-1 fallback or replacement decoding.

For HTML/XHTML, complete meta charset and http-equiv Content-Type declarations are
read from a bounded prefix. Comments, script/style text, inert/text contexts and
content after the head/body boundary do not supply declarations. Latin-1 is used
only to inspect ASCII-compatible declaration bytes when no Unicode/override codec
is known; it is never used as a content-decoding fallback. XML declarations and
browser error-repair semantics are not implemented. Malformed-markup acceptance
can vary with the Python HTML parser version; accepted markup stays intact and
parser failures become `invalid_html`, never raw parser exceptions. Larger HTML payloads receive
`html_scan_limit`; declarations beyond that prefix are not assumed to be known.
HTML markup, whitespace and line endings are otherwise preserved, without assets.

## Results and identity

`DecodedText` contains `text`, `media_type`, `encoding`, `encoding_source`,
`source_sha256`, `source_size`, `payload_sha256`, `identity`, `transformations`,
`zip_member`, `diagnostics`, and `decoder_version="strict-text-v1"`.
The source hash is over original bytes before HTTP/container decoding; payload
hash is over the inner encoded bytes before character decoding and BOM removal.
Identity hashes decoder version, source hash, receipt headers, catalog claims and
all options. Equal text alone does not imply equal derivation identity.

`DecodeDiagnostic` contains stable `code`, `source` and `message` fields. Codes:
`default_media`, `html_scan_limit`, `ignored_encoding`, `encoding_conflict`, and
`encoding_selected`, and `invalid_html`. The encoding source is `override`, `bom`, `http`, `catalog`,
`html` or `default`. Conflict diagnostics preserve the competing normalized codec.

## Errors

Invalid caller argument shapes/options raise `ResourceInputError`. Changed
artifact bytes, receipt inconsistencies or unsafe file reads raise
`ResourceIntegrityError`. `ResourceDecodeError` derives from `ResourceError` and
includes `code`, immutable `diagnostics`, and `source_sha256` when a bounded source
read succeeded. A source-limit rejection occurs before hashing and leaves that
field None. Originals remain intact on every outcome.

| ResourceDecodeError code | Meaning / action |
|---|---|
| `source_limit`, `decoded_limit`, `metadata_limit`, `zip_entries_limit` | Inspect expected size and explicitly choose a suitable bound. |
| `invalid_html` | Malformed HTML prevents bounded declaration inspection; repair the source. |
| `invalid_metadata` | Repair malformed MIME/charset metadata; no guessing occurred. |
| `unknown_encoding`, `missing_bom` | Supply a supported encoding and explicit byte order where needed. |
| `ambiguous_encoding`, `ambiguous_media` | Resolve conflicting source evidence; encoding override is available. |
| `invalid_bytes` | Bytes are invalid under the selected strict decoder. |
| `unsupported_media`, `unsupported_container`, `unsupported_content_encoding` | Preserve original bytes; this decoder does not support that representation. |
| `container_mismatch`, `container_chain`, `invalid_container` | Inspect declared format, wrapping and container integrity. |
| `unsafe_member`, `encrypted_member` | The ZIP cannot safely be handled under this contract. |
| `ambiguous_member`, `invalid_member` | Choose an existing safe text member in a ZIP. |
