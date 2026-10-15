"""Conservative MIME/HTML declarations and strict deterministic character decoding."""

import codecs
from html import parser
import re

from lcats.gettenberg import _decode_types
from lcats.gettenberg import _resource_selection

TEXT_MEDIA = {"text/plain", "text/html", "application/xhtml+xml"}
CONTAINER_MEDIA = {
    "application/gzip",
    "application/x-gzip",
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",
}


def parse_media(claim):
    """Parse the selection grammar without email's RFC 2231 normalization."""
    value = claim.strip()
    if not _resource_selection._CLAIM.fullmatch(value) or any(
        ord(char) < 32 and char != "\t" or ord(char) >= 127 for char in claim
    ):
        raise _decode_types.ResourceDecodeError(
            "invalid_metadata", "invalid MIME declaration"
        )
    media = _resource_selection._MEDIA.match(value)
    position = media.end()
    charsets = []
    while parameter := _resource_selection._PARAMETER.match(value, position):
        position = parameter.end()
        name, item = parameter.groups()
        name = name.lower()
        if name.startswith("charset*"):
            raise _decode_types.ResourceDecodeError(
                "invalid_metadata", "extended charset declarations unsupported"
            )
        if item.startswith('"'):
            item = re.sub(r"\\(.)", r"\1", item[1:-1])
        if name == "charset":
            if not re.fullmatch(_resource_selection._TOKEN, item):
                raise _decode_types.ResourceDecodeError(
                    "invalid_metadata", "invalid charset token"
                )
            charsets.append(item)
    return media.group().lower(), tuple(charsets)


class _HTMLDeclarations(parser.HTMLParser):
    """Inspect complete meta tags only; scripts/comments cannot declare encoding."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.charsets = []
        self.ended_head = False
        self.suppressed = []

    def handle_starttag(self, tag, attrs):
        if tag in (
            "template",
            "noscript",
            "textarea",
            "title",
            "xmp",
            "iframe",
            "noembed",
            "noframes",
            "plaintext",
        ):
            self.suppressed.append(tag)
        if self.suppressed:
            return
        if tag == "body":
            self.ended_head = True
        if tag != "meta" or self.ended_head:
            return
        # Preserve duplicates so conflicting attributes are not silently lost.
        for name, value in attrs:
            if name == "charset" and value is not None:
                self.charsets.append(value)
        if any(
            name == "http-equiv" and value and value.lower() == "content-type"
            for name, value in attrs
        ):
            for name, value in attrs:
                if name == "content" and value is not None:
                    _, charsets = parse_media(value)
                    self.charsets.extend(charsets)

    def handle_endtag(self, tag):
        if self.suppressed:
            if tag == self.suppressed[-1]:
                self.suppressed.pop()
            return
        if tag == "head":
            self.ended_head = True


def _codec(label):
    if not re.fullmatch(_resource_selection._TOKEN, label):
        raise _decode_types.ResourceDecodeError(
            "unknown_encoding", "invalid character encoding label"
        )
    try:
        codec = codecs.lookup(label)
        # bytes.decode disallows binary transform codecs; exclude text-to-text
        # transformations too, which are not character-set declarations.
        if not codec._is_text_encoding or codec.name in (
            "unicode-escape",
            "raw-unicode-escape",
            "punycode",
            "idna",
        ):
            raise LookupError("not a character encoding")
        b"".decode(codec.name, errors="strict")
        return codec.name
    except (LookupError, UnicodeError, ValueError) as exc:
        raise _decode_types.ResourceDecodeError(
            "unknown_encoding", f"unsupported character encoding: {label}"
        ) from exc


def _compatible(left, right):
    if left == right or {left, right} <= {"utf-8", "utf-8-sig"}:
        return True
    return any(
        generic in (left, right) and (right if left == generic else left) in variants
        for generic, variants in (
            ("utf-16", {"utf-16-le", "utf-16-be"}),
            ("utf-32", {"utf-32-le", "utf-32-be"}),
        )
    )


def decode(payload, media_type, declarations, options, diagnostics):
    """Resolve all declarations, retaining conflicts and the winning authority."""
    bom = None
    for marker, codec in (
        (codecs.BOM_UTF32_LE, "utf-32-le"),
        (codecs.BOM_UTF32_BE, "utf-32-be"),
        (codecs.BOM_UTF8, "utf-8"),
        (codecs.BOM_UTF16_LE, "utf-16-le"),
        (codecs.BOM_UTF16_BE, "utf-16-be"),
    ):
        if payload.startswith(marker):
            bom = (marker, codec)
            break
    claims = list(declarations)
    if media_type in ("text/html", "application/xhtml+xml"):
        # Without a BOM, HTML declarations must be ASCII-compatible. With a BOM,
        # decode just the bounded prefix in its proven Unicode byte order. A
        # partial final code unit is held by the incremental decoder, not replaced.
        prefix = payload[: options.html_scan_bytes]
        scan_codec = (
            _codec(options.encoding_override)
            if options.encoding_override is not None
            else bom[1] if bom else None
        )
        if scan_codec:
            reader = codecs.getincrementaldecoder(scan_codec)(errors="strict")
            skip = (
                len(bom[0])
                if bom
                and _compatible(scan_codec, bom[1])
                and scan_codec not in ("utf-16", "utf-32")
                else 0
            )
            try:
                markup = reader.decode(prefix[skip:], final=False)
            except UnicodeError as exc:
                raise _decode_types.ResourceDecodeError(
                    "invalid_bytes", "invalid BOM-encoded HTML prefix"
                ) from exc
        else:
            markup = prefix.decode("latin-1")  # Byte-preserving tag inspection only.
        html = _HTMLDeclarations()
        try:
            html.feed(markup)
        except (ValueError, AssertionError) as exc:
            # HTMLParser rejects some marked sections and oversized numeric
            # entities with implementation exceptions, even in a bounded prefix.
            # Keep malformed source within the public structured-error boundary.
            diagnostic = _decode_types.DecodeDiagnostic(
                "invalid_html", "html", "cannot inspect HTML encoding declarations"
            )
            raise _decode_types.ResourceDecodeError(
                "invalid_html",
                diagnostic.message,
                diagnostics=(*diagnostics, diagnostic),
            ) from exc
        claims.extend(("html", label) for label in html.charsets)
        if len(payload) > options.html_scan_bytes:
            diagnostics.append(
                _decode_types.DecodeDiagnostic(
                    "html_scan_limit",
                    "html",
                    "only the bounded prefix was inspected for declarations",
                )
            )
    strong = options.encoding_override is not None or bom is not None
    if options.encoding_override is not None:
        chosen, authority = _codec(options.encoding_override), "override"
    elif bom:
        chosen, authority = bom[1], "bom"
    else:
        chosen, authority = None, None
    resolved = []
    if bom:
        resolved.append(("bom", bom[1]))
    for source, label in claims:
        try:
            resolved.append((source, _codec(label)))
        except _decode_types.ResourceDecodeError:
            if not strong:
                raise
            diagnostics.append(
                _decode_types.DecodeDiagnostic(
                    "ignored_encoding",
                    source,
                    f"unsupported declaration superseded: {label}",
                )
            )
    if chosen is None:
        authority, chosen = resolved[0] if resolved else ("default", "utf-8")
    conflicts = [
        (source, codec) for source, codec in resolved if not _compatible(chosen, codec)
    ]
    for source, codec in conflicts:
        diagnostics.append(
            _decode_types.DecodeDiagnostic(
                "encoding_conflict",
                source,
                f"{codec} conflicts with chosen {chosen} ({authority})",
            )
        )
    if conflicts and not strong:
        raise _decode_types.ResourceDecodeError(
            "ambiguous_encoding",
            "encoding declarations conflict",
            diagnostics=diagnostics,
        )
    if chosen in ("utf-16", "utf-32") and bom is None:
        raise _decode_types.ResourceDecodeError(
            "missing_bom",
            "use a BOM or explicit Unicode byte order",
            diagnostics=diagnostics,
        )
    data = payload
    if bom and _compatible(chosen, bom[1]):
        data = payload[len(bom[0]) :]
        if chosen in ("utf-16", "utf-32"):
            chosen = bom[1]
    try:
        text = data.decode(chosen, errors="strict")
    except (UnicodeError, LookupError, ValueError) as exc:
        raise _decode_types.ResourceDecodeError(
            "invalid_bytes", f"payload is not valid {chosen}", diagnostics=diagnostics
        ) from exc
    diagnostics.append(
        _decode_types.DecodeDiagnostic("encoding_selected", authority, chosen)
    )
    return text, chosen, authority
