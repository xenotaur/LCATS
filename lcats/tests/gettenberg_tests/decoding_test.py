"""Strict offline decoding with authored compressed files and real artifact paths."""

import codecs
import dataclasses
import gzip
import hashlib
import io
import pathlib
import re
import stat
import struct
import tempfile
import unittest
import warnings
import zipfile
import zlib

from lcats.gettenberg import resources
from lcats.utils import capture
from lcats.gettenberg import _resource_types


def zip_bytes(members, compression=zipfile.ZIP_DEFLATED):
    """Create tiny deterministic ZIP fixtures entirely in memory."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=compression) as archive:
        for name, data in members:
            info = name if isinstance(name, zipfile.ZipInfo) else zipfile.ZipInfo(name)
            info.compress_type = compression
            archive.writestr(info, data)
    return stream.getvalue()


class DecodingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)

    def artifact(self, data, headers=()):
        """Represent a real saved acquisition without contacting an HTTP service."""
        digest = hashlib.sha256(data).hexdigest()
        request = resources.SourceRequest.from_url("https://example.org/book")
        receipt = resources.RetrievalReceipt(
            2,
            request.key,
            request.source_uri,
            request.request_url,
            "resource",
            request.route_policy,
            request.request_url,
            (),
            digest,
            len(data),
            "2026-10-15T00:00:00+00:00",
            headers,
        )
        receipt_hash = hashlib.sha256(
            _resource_types.canonical_json(dataclasses.asdict(receipt))
        ).hexdigest()
        path = self.root / digest
        path.write_bytes(data)
        return resources.SourceArtifact(path, digest, len(data), receipt_hash, receipt)

    def assert_decode_error(self, code, data, **kwargs):
        with self.assertRaises(resources.ResourceDecodeError) as caught:
            resources.decode_text(data, **kwargs)
        self.assertEqual(caught.exception.code, code)
        if isinstance(data, bytes) and code != "source_limit":
            self.assertEqual(
                caught.exception.source_sha256, hashlib.sha256(data).hexdigest()
            )
        return caught.exception

    def test_malformed_html_parser_errors_are_structured(self):
        # Numeric entities fit the declaration scan bound but exceed Python's
        # integer-conversion limit in both direct and http-equiv attributes.
        for payload in (
            b'<meta charset="&#' + b"1" * 5000 + b';">',
            b'<meta http-equiv="Content-Type" content="text/html; charset=&#'
            + b"1" * 5000
            + b';">',
        ):
            with self.subTest(payload_prefix=payload[:50]):
                error = self.assert_decode_error(
                    "invalid_html", payload, catalog_formats=("text/html",)
                )
                self.assertEqual(error.diagnostics[-1].code, "invalid_html")
                self.assertEqual(error.diagnostics[-1].source, "html")
                self.assertIsInstance(error.__cause__, (ValueError, AssertionError))

    def test_unknown_marked_section_never_leaks_parser_exception(self):
        # Python 3.11.9 raises AssertionError for this section; 3.11.17 accepts
        # it. Either preserve all markup or return our typed parse error. Never
        # expose the stdlib exception or silently rewrite the caller's source.
        payload = b"<![bogus]><p>story</p>"
        try:
            result = resources.decode_text(payload, catalog_formats=("text/html",))
        except resources.ResourceDecodeError as error:
            self.assertEqual(error.code, "invalid_html")
            self.assertEqual(error.source_sha256, hashlib.sha256(payload).hexdigest())
            self.assertEqual(error.diagnostics[-1].code, "invalid_html")
            self.assertIsInstance(error.__cause__, AssertionError)
        else:
            self.assertEqual(result.text, payload.decode("utf-8"))
            self.assertEqual(result.source_sha256, hashlib.sha256(payload).hexdigest())
            self.assertEqual(result.encoding_source, "default")

    def test_zip_comment_signatures_are_not_directory_records(self):
        # Valid archive comments may contain short signatures, a full misleading
        # EOCD-shaped record, repeated signatures, or the maximum comment length.
        for comment in (
            b"comment PK\x05\x06 suffix",
            b"PK\x05\x06" + b"\x00" * 18,
            b"PK\x05\x06" * 1000,
            b"x" * 65531 + b"PK\x05\x06",
        ):
            with self.subTest(comment_length=len(comment)):
                stream = io.BytesIO()
                with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr("story.txt", "A story")
                    archive.comment = comment
                data = stream.getvalue()
                artifact = self.artifact(data)
                result = resources.decode_text(artifact)
                self.assertEqual(result.text, "A story")
                self.assertEqual(result.zip_member, "story.txt")
                self.assertEqual(result.source_sha256, hashlib.sha256(data).hexdigest())
                self.assertEqual(artifact.path.read_bytes(), data)

    def test_plausible_zip_end_records_in_comment_do_not_mask_directory(self):
        for count, size_from_position, offset_from_position in (
            (0, False, True),
            (1, True, False),
        ):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as archive:
                archive.writestr("story.txt", "A story")
            fake_position = len(stream.getvalue())
            # Both fake records satisfy EOF/directory arithmetic. One pretends
            # the archive is empty; the other points at an invalid directory.
            comment = struct.pack(
                "<4s4H2LH",
                b"PK\x05\x06",
                0,
                0,
                count,
                count,
                fake_position if size_from_position else 0,
                fake_position if offset_from_position else 0,
                0,
            )
            with zipfile.ZipFile(stream, "a") as archive:
                archive.comment = comment
            data = stream.getvalue()
            with self.subTest(count=count):
                result = resources.decode_text(data)
                self.assertEqual(result.text, "A story")
                self.assertEqual(result.source_sha256, hashlib.sha256(data).hexdigest())

    def test_end_record_candidates_inside_member_data_are_ignored(self):
        # Fake indexes can satisfy directory arithmetic yet point inside their
        # own member, or forge a zero size to hide that overlap. Local headers
        # are independent evidence that the complete original text must survive.
        reference = zip_bytes((("story.txt", b"x" * 78),), zipfile.ZIP_STORED)
        for zero_sizes in (False, True):
            central = bytearray(reference[117:172])
            if zero_sizes:
                struct.pack_into("<3L", central, 16, 0, 0, 0)
            payload = (
                b"x"
                + central
                + struct.pack("<4s4H2LH", b"PK\x05\x06", 0, 0, 1, 1, 55, 40, 77)
            )
            data = zip_bytes((("story.txt", payload),), zipfile.ZIP_STORED)
            with self.subTest(zero_sizes=zero_sizes):
                result = resources.decode_text(
                    data, options=resources.DecodeOptions(encoding_override="latin1")
                )
                self.assertEqual(result.text, payload.decode("latin1"))
        payload = b"x" + struct.pack("<4s4H2LH", b"PK\x05\x06", 1, 0, 1, 1, 40, 0, 77)
        result = resources.decode_text(
            zip_bytes((("story.txt", payload),), zipfile.ZIP_STORED)
        )
        self.assertEqual(result.text, payload.decode("utf-8"))

    def test_unsupported_looking_fake_local_header_does_not_mask_real_zip(self):
        reference = zip_bytes((("story.txt", b"x" * 117),), zipfile.ZIP_STORED)
        local = bytearray(reference[:39])
        struct.pack_into("<2L", local, 18, 0xFFFFFFFF, 0xFFFFFFFF)
        central = bytearray(reference[156:211])
        struct.pack_into("<L", central, 42, 40)
        payload = (
            b"x"
            + local
            + central
            + struct.pack("<4s4H2LH", b"PK\x05\x06", 0, 0, 1, 1, 55, 79, 77)
        )
        data = zip_bytes((("story.txt", payload),), zipfile.ZIP_STORED)
        result = resources.decode_text(
            data, options=resources.DecodeOptions(encoding_override="latin1")
        )
        self.assertEqual(result.text, payload.decode("latin1"))

    def test_streaming_zip_data_descriptor(self):
        class StreamingBuffer(io.BytesIO):
            def seekable(self):
                return False

            def seek(self, *args):
                raise io.UnsupportedOperation("stream cannot seek")

        for method in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            stream = StreamingBuffer()
            with zipfile.ZipFile(stream, "w", method) as archive:
                archive.writestr("story.txt", "A streaming story")
            self.assertEqual(
                resources.decode_text(stream.getvalue()).text, "A streaming story"
            )

    def test_container_declarations_must_match_after_http_decoding(self):
        gzip_data = gzip.compress(b"story")
        zip_data = zip_bytes((("story.txt", b"story"),))
        for data, good, bad in (
            (gzip_data, "application/gzip", "application/zip"),
            (zip_data, "application/zip", "application/gzip"),
        ):
            for claims in ((bad,), (good, bad)):
                with self.subTest(claims=claims, signature=data[:4]):
                    self.assert_decode_error(
                        "container_mismatch", data, catalog_formats=claims
                    )
            artifact = self.artifact(
                gzip.compress(data),
                (("content-encoding", "gzip"), ("content-type", good)),
            )
            self.assertEqual(resources.decode_text(artifact).text, "story")
            self.assert_decode_error(
                "container_mismatch", artifact, catalog_formats=(bad,)
            )

    def test_generic_override_reports_opposite_bom_order(self):
        for family in ("utf-16", "utf-32"):
            for order, other in (("be", "le"), ("le", "be")):
                codec = family + "-" + order
                bom = getattr(
                    codecs,
                    "BOM_" + family.replace("-", "").upper() + "_" + order.upper(),
                )
                for media in ("text/plain", "text/html"):
                    with self.subTest(codec=codec, media=media):
                        result = resources.decode_text(
                            bom + "<p>story</p>".encode(codec),
                            options=resources.DecodeOptions(encoding_override=family),
                            catalog_formats=(
                                media + "; charset=" + family + "-" + other,
                            ),
                        )
                        self.assertEqual(result.text, "<p>story</p>")
                        self.assertEqual(result.encoding, codec)
                        conflicts = [
                            d
                            for d in result.diagnostics
                            if d.code == "encoding_conflict"
                        ]
                        self.assertEqual(len(conflicts), 1)
                        self.assertEqual(conflicts[0].source, "catalog")
                        self.assertIn(family + "-" + other, conflicts[0].message)

    def test_generic_override_requires_compatible_bom(self):
        for family in ("utf-16", "utf-32"):
            for data in (
                codecs.BOM_UTF8 + b"x",
                b"x",
                (
                    codecs.BOM_UTF16_BE + b"\x00x"
                    if family == "utf-32"
                    else codecs.BOM_UTF32_BE + b"\x00\x00\x00x"
                ),
            ):
                for media in ("text/plain", "text/html"):
                    with self.subTest(family=family, data=data, media=media):
                        self.assert_decode_error(
                            "missing_bom",
                            data,
                            options=resources.DecodeOptions(encoding_override=family),
                            catalog_formats=(media,),
                        )

    def test_signature_override_preserves_content_feff(self):
        for text in ("\ufeffstory", "\ufeff<meta charset='utf-8'><p>story</p>"):
            for media in ("text/plain", "text/html"):
                data = codecs.BOM_UTF8 + text.encode("utf-8")
                with self.subTest(text=text, media=media):
                    result = resources.decode_text(
                        data,
                        catalog_formats=(media,),
                        options=resources.DecodeOptions(encoding_override="utf-8-sig"),
                    )
                    self.assertEqual(result.text, text)
                    self.assertEqual(
                        result.source_sha256, hashlib.sha256(data).hexdigest()
                    )
                    self.assertEqual(result.encoding, "utf-8")
                    self.assertEqual(result.encoding_source, "override")

    def test_plain_utf8_and_empty_payload(self):
        for data in (b"", "A café\r\n".encode()):
            result = resources.decode_text(data)
            self.assertEqual(result.text, data.decode())
            self.assertEqual(
                (result.encoding, result.encoding_source), ("utf-8", "default")
            )
            self.assertEqual(result.source_sha256, hashlib.sha256(data).hexdigest())
            self.assertEqual(result.source_size, len(data))
            self.assertEqual(result.payload_sha256, result.source_sha256)

    def test_result_immutable_and_deterministic(self):
        result = resources.decode_text(b"story")
        self.assertEqual(result, resources.decode_text(b"story"))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.text = "changed"

    def test_identity_captures_options_and_claims(self):
        first = resources.decode_text(b"story")
        for other in (
            resources.decode_text(
                b"story", options=resources.DecodeOptions(encoding_override="ascii")
            ),
            resources.decode_text(b"story", catalog_formats=("text/plain",)),
            resources.decode_text(
                b"story", options=resources.DecodeOptions(max_decoded_bytes=100)
            ),
        ):
            self.assertEqual(other.text, first.text)
            self.assertNotEqual(other.identity, first.identity)

    def test_http_and_catalog_encoding_sources(self):
        data = b"caf\xe9"
        result = resources.decode_text(
            self.artifact(data, (("content-type", "text/plain; charset=iso-8859-1"),))
        )
        self.assertEqual((result.text, result.encoding_source), ("café", "http"))
        result = resources.decode_text(
            data, catalog_formats=("text/plain; charset=windows-1252",)
        )
        self.assertEqual((result.text, result.encoding_source), ("café", "catalog"))

    def test_conflicting_http_catalog_is_ambiguous(self):
        artifact = self.artifact(
            b"story", (("content-type", "text/plain; charset=utf-8"),)
        )
        error = self.assert_decode_error(
            "ambiguous_encoding",
            artifact,
            catalog_formats=("text/plain; charset=latin1",),
        )
        self.assertIn("encoding_conflict", [d.code for d in error.diagnostics])

    def test_conflicting_catalog_parameters_are_ambiguous(self):
        self.assert_decode_error(
            "ambiguous_encoding",
            b"story",
            catalog_formats=("text/plain; charset=utf8; charset=ascii",),
        )

    def test_equivalent_charset_aliases_agree(self):
        result = resources.decode_text(
            b"story",
            catalog_formats=("text/plain; charset=utf8", "text/plain; charset=UTF_8"),
        )
        self.assertEqual(result.encoding, "utf-8")

    def test_override_wins_and_reports_conflicts(self):
        result = resources.decode_text(
            b"caf\xe9",
            catalog_formats=("text/plain; charset=utf8",),
            options=resources.DecodeOptions(encoding_override="latin1"),
        )
        self.assertEqual((result.text, result.encoding_source), ("café", "override"))
        self.assertIn("encoding_conflict", [d.code for d in result.diagnostics])

    def test_unknown_codec_is_structured(self):
        self.assert_decode_error(
            "unknown_encoding",
            b"x",
            catalog_formats=("text/plain; charset=x-no-such-codec",),
        )
        self.assert_decode_error(
            "unknown_encoding",
            b"x",
            options=resources.DecodeOptions(encoding_override="x-no-such-codec"),
        )

    def test_override_can_supersede_unknown_claim(self):
        result = resources.decode_text(
            b"story",
            catalog_formats=("text/plain; charset=x-no-such-codec",),
            options=resources.DecodeOptions(encoding_override="utf8"),
        )
        self.assertIn("ignored_encoding", [d.code for d in result.diagnostics])

    def test_transform_codecs_are_not_character_sets(self):
        for encoding in (
            "base64",
            "hex",
            "zlib",
            "unicode_escape",
            "raw_unicode_escape",
            "idna",
            "punycode",
        ):
            with self.subTest(encoding=encoding):
                self.assert_decode_error(
                    "unknown_encoding",
                    b"story",
                    options=resources.DecodeOptions(encoding_override=encoding),
                )

    def test_invalid_bytes_are_never_replaced(self):
        self.assert_decode_error("invalid_bytes", b"caf\xe9")
        self.assert_decode_error("invalid_bytes", b"\xc0\xaf")
        self.assert_decode_error("invalid_bytes", b"\xed\xa0\x80")

    def test_all_unicode_boms(self):
        for encoding, bom in (
            ("utf-8", codecs.BOM_UTF8),
            ("utf-16-le", codecs.BOM_UTF16_LE),
            ("utf-16-be", codecs.BOM_UTF16_BE),
            ("utf-32-le", codecs.BOM_UTF32_LE),
            ("utf-32-be", codecs.BOM_UTF32_BE),
        ):
            with self.subTest(encoding=encoding):
                result = resources.decode_text(
                    bom + "café".encode(encoding),
                    catalog_formats=("text/plain; charset=ascii",),
                )
                self.assertEqual(result.text, "café")
                self.assertEqual(result.encoding_source, "bom")
                self.assertIn("encoding_conflict", [d.code for d in result.diagnostics])

    def test_generic_unicode_requires_bom_or_explicit_byte_order(self):
        for encoding in ("utf-16", "utf-32"):
            self.assert_decode_error(
                "missing_bom",
                b"x\x00\x00\x00",
                options=resources.DecodeOptions(encoding_override=encoding),
            )
        result = resources.decode_text(
            b"x\x00", options=resources.DecodeOptions(encoding_override="utf-16-le")
        )
        self.assertEqual(result.text, "x")

    def test_matching_generic_override_uses_bom_order(self):
        result = resources.decode_text(
            codecs.BOM_UTF16_BE + "story".encode("utf-16-be"),
            options=resources.DecodeOptions(encoding_override="utf-16"),
        )
        self.assertEqual((result.text, result.encoding), ("story", "utf-16-be"))

    def test_mismatched_override_does_not_discard_bom_bytes(self):
        data = codecs.BOM_UTF8 + b"story"
        result = resources.decode_text(
            data, options=resources.DecodeOptions(encoding_override="latin1")
        )
        self.assertEqual(result.text, data.decode("latin1"))

    def test_html_meta_charset_and_markup_preserved(self):
        data = b'<html><head><meta charset="windows-1252"></head><body>caf\xe9<img src="https://never.invalid/x"></body></html>'
        result = resources.decode_text(data, catalog_formats=("text/html",))
        self.assertEqual(result.text, data.decode("cp1252"))
        self.assertEqual(result.encoding_source, "html")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_html_http_equiv(self):
        data = b'<meta http-equiv="Content-Type" content="text/html; charset=latin1">caf\xe9'
        self.assertEqual(
            resources.decode_text(data, catalog_formats=("text/html",)).encoding,
            "iso8859-1",
        )

    def test_html_conflict_with_catalog_and_duplicate_attributes(self):
        data = b'<meta charset="latin1">story'
        self.assert_decode_error(
            "ambiguous_encoding", data, catalog_formats=("text/html; charset=utf8",)
        )
        self.assert_decode_error(
            "ambiguous_encoding",
            b'<meta charset="latin1" charset="utf8">story',
            catalog_formats=("text/html",),
        )

    def test_html_comment_script_and_body_declarations_are_ignored(self):
        data = b'<!-- <meta charset="latin1"> --><script>"<meta charset=latin1>"</script><body><meta charset="latin1">story'
        result = resources.decode_text(data, catalog_formats=("text/html",))
        self.assertEqual(result.encoding_source, "default")

    def test_html_inert_and_text_contexts_do_not_declare_encoding(self):
        for tag in ("template", "noscript", "textarea", "title", "iframe"):
            markup = f'<{tag}><meta charset="latin1"></{tag}><meta charset="utf8">story'
            result = resources.decode_text(
                markup.encode(), catalog_formats=("text/html",)
            )
            self.assertEqual(result.encoding, "utf-8")

    def test_html_scan_limit_is_explicit(self):
        data = b" " * 40 + b'<meta charset="latin1">caf\xe9'
        self.assert_decode_error(
            "invalid_bytes",
            data,
            catalog_formats=("text/html",),
            options=resources.DecodeOptions(html_scan_bytes=20),
        )
        result = resources.decode_text(
            b" " * 40,
            catalog_formats=("text/html",),
            options=resources.DecodeOptions(html_scan_bytes=20),
        )
        self.assertIn("html_scan_limit", [d.code for d in result.diagnostics])

    def test_html_bom_and_override_scan(self):
        text = '<meta charset="latin1">story'
        data = codecs.BOM_UTF16_LE + text.encode("utf-16-le")
        result = resources.decode_text(data, catalog_formats=("text/html",))
        self.assertEqual(result.text, text)
        result = resources.decode_text(
            data,
            catalog_formats=("text/html",),
            options=resources.DecodeOptions(encoding_override="latin1"),
        )
        self.assertEqual(result.text, data.decode("latin1"))

    def test_xhtml_markup(self):
        result = resources.decode_text(
            b"<html>story</html>", catalog_formats=("application/xhtml+xml",)
        )
        self.assertEqual(result.media_type, "application/xhtml+xml")

    def test_unknown_and_conflicting_media(self):
        for media in (
            "application/pdf",
            "audio/mpeg",
            "application/epub+zip",
            "image/png",
        ):
            self.assert_decode_error(
                "unsupported_media", b"abc", catalog_formats=(media,)
            )
        self.assert_decode_error("unsupported_media", b"%PDF-1.4\n")
        self.assert_decode_error(
            "ambiguous_media", b"story", catalog_formats=("text/plain", "text/html")
        )

    def test_malformed_mime_and_extended_charset(self):
        for claim in (
            "text/plain;",
            "text/plain; charset*=utf-8''utf-8",
            "text/plain; charset*1=utf8",
            "text/plain\n",
            'text/plain; charset="utf8\x00"',
        ):
            with self.subTest(claim=claim):
                self.assert_decode_error(
                    "invalid_metadata", b"story", catalog_formats=(claim,)
                )

    def test_metadata_limits_and_unicode_error(self):
        self.assert_decode_error(
            "metadata_limit",
            b"x",
            catalog_formats=("text/plain",),
            options=resources.DecodeOptions(max_metadata_bytes=3),
        )
        self.assert_decode_error(
            "invalid_metadata", b"x", catalog_formats=("text/plain; x=\ud800",)
        )

    def test_gzip_container_roundtrip(self):
        original = gzip.compress("café".encode(), mtime=0)
        result = resources.decode_text(
            original, catalog_formats=("application/gzip", "text/plain")
        )
        self.assertEqual(result.text, "café")
        self.assertEqual(result.transformations, ("container:gzip",))
        self.assertEqual(result.source_sha256, hashlib.sha256(original).hexdigest())

    def test_http_gzip_then_zip(self):
        original = gzip.compress(zip_bytes((("story.txt", b"hello"),)), mtime=0)
        result = resources.decode_text(
            self.artifact(
                original,
                (("content-encoding", "gzip"), ("content-type", "application/zip")),
            )
        )
        self.assertEqual(result.text, "hello")
        self.assertEqual(result.transformations, ("http:gzip", "container:zip"))

    def test_http_gzip_alone(self):
        result = resources.decode_text(
            self.artifact(
                gzip.compress(b"hello", mtime=0),
                (("content-encoding", "gzip"), ("content-type", "text/plain")),
            )
        )
        self.assertEqual(result.transformations, ("http:gzip",))

    def test_gzip_inflation_limit(self):
        packed = gzip.compress(b"a" * 10000, mtime=0)
        self.assert_decode_error(
            "decoded_limit",
            packed,
            options=resources.DecodeOptions(max_decoded_bytes=100),
        )
        self.assertEqual(
            len(
                resources.decode_text(
                    packed, options=resources.DecodeOptions(max_decoded_bytes=10000)
                ).text
            ),
            10000,
        )

    def test_corrupt_truncated_and_concatenated_gzip(self):
        packed = gzip.compress(b"hello", mtime=0)
        self.assert_decode_error("invalid_container", packed[:-1])
        corrupt = bytearray(packed)
        corrupt[-8] ^= 1
        self.assert_decode_error("invalid_container", bytes(corrupt))
        self.assert_decode_error("container_chain", packed + packed)
        self.assert_decode_error("container_chain", packed + b"trailing")

    def test_nested_containers_refused(self):
        self.assert_decode_error(
            "container_chain", gzip.compress(gzip.compress(b"hello", mtime=0), mtime=0)
        )
        self.assert_decode_error(
            "container_chain",
            zip_bytes((("story.txt", gzip.compress(b"hello", mtime=0)),)),
        )

    def test_container_policy_and_content_encoding(self):
        packed = gzip.compress(b"hello", mtime=0)
        self.assert_decode_error(
            "container_mismatch",
            packed,
            options=resources.DecodeOptions(container="none"),
        )
        self.assert_decode_error(
            "container_mismatch",
            b"hello",
            options=resources.DecodeOptions(container="zip"),
        )
        self.assert_decode_error(
            "container_mismatch", b"hello", catalog_formats=("application/zip",)
        )
        for value in ("br", "gzip, gzip", "deflate"):
            self.assert_decode_error(
                "unsupported_content_encoding",
                self.artifact(packed, (("content-encoding", value),)),
            )

    def test_single_zip_text_member_with_assets(self):
        packed = zip_bytes(
            (("story.html", b"<p>hello</p>"), ("images/a.png", b"asset"))
        )
        result = resources.decode_text(packed)
        self.assertEqual(
            (result.text, result.zip_member, result.media_type),
            ("<p>hello</p>", "story.html", "text/html"),
        )
        self.assertEqual(list(self.root.iterdir()), [])

    def test_stored_zip_member(self):
        self.assertEqual(
            resources.decode_text(
                zip_bytes((("story.txt", b"hello"),), zipfile.ZIP_STORED)
            ).text,
            "hello",
        )

    def test_ambiguous_and_explicit_zip_member(self):
        packed = zip_bytes((("a.txt", b"one"), ("b.txt", b"two")))
        self.assert_decode_error("ambiguous_member", packed)
        result = resources.decode_text(
            packed, options=resources.DecodeOptions(zip_member="b.txt")
        )
        self.assertEqual(result.text, "two")
        self.assert_decode_error(
            "ambiguous_member",
            packed,
            options=resources.DecodeOptions(zip_member="missing.txt"),
        )
        self.assert_decode_error(
            "invalid_member",
            b"hello",
            options=resources.DecodeOptions(zip_member="a.txt"),
        )

    def test_unsafe_zip_names_even_unselected(self):
        for name in (
            "../bad.txt",
            "/bad.txt",
            "a/../bad.txt",
            "C:bad.txt",
            "a\\b.txt",
            "a//b.txt",
        ):
            with self.subTest(name=name):
                self.assert_decode_error(
                    "unsafe_member",
                    zip_bytes((("story.txt", b"good"), (name, b"bad"))),
                    options=resources.DecodeOptions(zip_member="story.txt"),
                )

    def test_zip_symlink_and_encryption(self):
        info = zipfile.ZipInfo("link.txt")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.assert_decode_error("unsafe_member", zip_bytes(((info, b"target"),)))
        packed = bytearray(zip_bytes((("story.txt", b"hello"),)))
        center = packed.index(b"PK\x01\x02")
        struct.pack_into("<H", packed, center + 8, 1)
        struct.pack_into("<H", packed, 6, 1)  # Consistent encrypted local/index flags.
        self.assert_decode_error("encrypted_member", bytes(packed))

    def test_zip_entry_limit_and_forged_count(self):
        packed = zip_bytes((("one.txt", b"one"), ("two.txt", b"two")))
        self.assert_decode_error(
            "zip_entries_limit",
            packed,
            options=resources.DecodeOptions(max_zip_entries=1),
        )
        forged = bytearray(packed)
        end = forged.rfind(b"PK\x05\x06")
        struct.pack_into("<HH", forged, end + 8, 0, 0)
        self.assert_decode_error(
            "zip_entries_limit",
            bytes(forged),
            options=resources.DecodeOptions(max_zip_entries=1),
        )

    def test_zip_output_limit_and_forged_short_size(self):
        packed = zip_bytes((("story.txt", b"a" * 10000),))
        self.assert_decode_error(
            "decoded_limit",
            packed,
            options=resources.DecodeOptions(max_decoded_bytes=100),
        )
        forged = bytearray(packed)
        center = forged.index(b"PK\x01\x02")
        struct.pack_into("<L", forged, center + 24, 1)
        struct.pack_into("<L", forged, center + 16, zlib.crc32(b"a"))
        # Contradictory local/index metadata is now refused before inflation,
        # even when an output limit would also reject the true expanded bytes.
        self.assert_decode_error(
            "invalid_container",
            bytes(forged),
            options=resources.DecodeOptions(max_decoded_bytes=100),
        )
        self.assert_decode_error("invalid_container", bytes(forged))
        # If both headers lie consistently, structural agreement is insufficient.
        # Independent inflation must still count all bytes and validate full CRC.
        struct.pack_into("<L", forged, 22, 1)
        struct.pack_into("<L", forged, 14, zlib.crc32(b"a"))
        self.assert_decode_error(
            "decoded_limit",
            bytes(forged),
            options=resources.DecodeOptions(max_decoded_bytes=100),
        )
        self.assert_decode_error("invalid_container", bytes(forged))

    def test_zip_corruption_and_trailing_data(self):
        packed = zip_bytes((("story.txt", b"hello"),))
        self.assert_decode_error("invalid_container", packed[:-4])
        self.assert_decode_error("invalid_container", packed + b"trailing")
        forged = bytearray(packed)
        center = forged.index(b"PK\x01\x02")
        struct.pack_into("<L", forged, center + 16, 0)
        self.assert_decode_error("invalid_container", bytes(forged))

    def test_zip_duplicate_and_empty_members(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            packed = zip_bytes((("a.txt", b"one"), ("a.txt", b"two")))
        self.assert_decode_error("ambiguous_member", packed)
        self.assert_decode_error("ambiguous_member", zip_bytes(()))
        self.assertEqual(resources.decode_text(zip_bytes((("a.txt", b""),))).text, "")

    def test_epub_and_unsupported_zip_compression(self):
        self.assert_decode_error(
            "unsupported_media",
            zip_bytes((("META-INF/container.xml", b"xml"), ("a.xhtml", b"story"))),
        )
        self.assert_decode_error(
            "unsupported_container",
            zip_bytes((("a.txt", b"hello"),), zipfile.ZIP_BZIP2),
        )

    def test_known_unsupported_containers_are_not_text(self):
        for data in (b"BZh1data", b"Rar!data", b"x" * 257 + b"ustar\x00"):
            self.assert_decode_error("unsupported_container", data)

    def test_zip_multidisk_and_directory_mode_are_refused(self):
        packed = bytearray(zip_bytes((("story.txt", b"hello"),)))
        center = packed.index(b"PK\x01\x02")
        struct.pack_into("<H", packed, center + 34, 1)
        self.assert_decode_error("unsupported_container", bytes(packed))
        info = zipfile.ZipInfo("story.txt")
        info.external_attr = (stat.S_IFDIR | 0o755) << 16
        self.assert_decode_error("unsafe_member", zip_bytes(((info, b"hello"),)))

    def test_zip64_refused(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            with archive.open("a.txt", "w", force_zip64=True) as member:
                member.write(b"hello")
        self.assert_decode_error("unsupported_container", stream.getvalue())

    def test_source_and_payload_bounds(self):
        self.assert_decode_error(
            "source_limit",
            b"hello",
            options=resources.DecodeOptions(max_source_bytes=4),
        )
        self.assert_decode_error(
            "decoded_limit",
            b"hello",
            options=resources.DecodeOptions(max_decoded_bytes=4),
        )
        artifact = self.artifact(b"hello")
        with self.assertRaises(resources.ResourceDecodeError) as caught:
            resources.decode_text(
                artifact, options=resources.DecodeOptions(max_source_bytes=4)
            )
        self.assertEqual(caught.exception.code, "source_limit")

    def test_artifact_original_unchanged_on_success_and_failure(self):
        artifact = self.artifact(b"hello")
        before = artifact.path.stat()
        resources.decode_text(artifact)
        self.assert_decode_error(
            "decoded_limit",
            artifact,
            options=resources.DecodeOptions(max_decoded_bytes=1),
        )
        after = artifact.path.stat()
        self.assertEqual(
            (before.st_ino, before.st_size, before.st_mtime_ns),
            (after.st_ino, after.st_size, after.st_mtime_ns),
        )
        self.assertEqual(artifact.path.read_bytes(), b"hello")
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_artifact_changed_or_symlink_is_integrity_error(self):
        artifact = self.artifact(b"hello")
        artifact.path.write_bytes(b"other")
        with self.assertRaises(resources.ResourceIntegrityError):
            resources.decode_text(artifact)
        target = self.root / "target"
        target.write_bytes(b"hello")
        artifact.path.unlink()
        artifact.path.symlink_to(target)
        with self.assertRaises(resources.ResourceIntegrityError):
            resources.decode_text(artifact)

    def test_artifact_receipt_binding(self):
        artifact = self.artifact(b"hello")
        changed_receipt = dataclasses.replace(
            artifact.receipt, headers=(("content-type", "text/plain; charset=latin1"),)
        )
        for changed in (
            dataclasses.replace(artifact, sha256="a" * 64),
            dataclasses.replace(artifact, receipt=changed_receipt),
            dataclasses.replace(artifact, receipt_sha256="0" * 64),
        ):
            with self.assertRaises(resources.ResourceIntegrityError):
                resources.decode_text(changed)

    def test_how_to_examples_execute_offline(self):
        doc = (
            pathlib.Path(__file__).resolve().parents[2]
            / "docs/how-to/gettenberg-decoding.md"
        )
        blocks = re.findall(r"```python\n(.*?)```", doc.read_text(), re.S)
        self.assertEqual(len(blocks), 4)
        namespace = {"artifact": self.artifact(b"A cached story")}
        before = set(self.root.iterdir())
        with capture.capture_output():
            for block in blocks:
                exec(compile(block, str(doc), "exec"), namespace)
        self.assertEqual(namespace["result"].text, "Second story")
        self.assertEqual(set(self.root.iterdir()), before)

    def test_invalid_options_and_argument_shapes(self):
        for field in (
            "max_source_bytes",
            "max_decoded_bytes",
            "max_zip_entries",
            "max_metadata_bytes",
            "html_scan_bytes",
        ):
            for value in (0, -1, True, 1.5, 2**80):
                with self.assertRaises(resources.ResourceInputError):
                    resources.DecodeOptions(**{field: value})
        for kwargs in (
            {"container": "tar"},
            {"encoding_override": ""},
            {"zip_member": ""},
        ):
            with self.assertRaises(resources.ResourceInputError):
                resources.DecodeOptions(**kwargs)
        for data, kwargs in (
            (bytearray(b"x"), {}),
            (b"x", {"options": None}),
            (b"x", {"catalog_formats": ["text/plain"]}),
        ):
            with self.assertRaises(resources.ResourceInputError):
                resources.decode_text(data, **kwargs)


if __name__ == "__main__":
    unittest.main()
