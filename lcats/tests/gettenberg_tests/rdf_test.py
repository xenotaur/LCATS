"""Behavioral coverage for real Gutenberg RDF and the documented parser profile."""

import base64
import dataclasses
import doctest
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from lcats.gettenberg import errors
from lcats.gettenberg import rdf

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def record(properties="", *, about="ebooks/42", extra="", attributes=""):
    """Build small authored profile fixtures; the real records live on disk."""
    return f"""<rdf:RDF xmlns:rdf="{rdf.RDF}" xmlns:pg="{rdf.PG}"
    xmlns:dc="{rdf.DC}" xmlns:dcam="{rdf.DCAM}" xmlns:role="{rdf.RELATORS}"
    xmlns:new="https://example.test/vocab/" xml:base="https://www.gutenberg.org/">
    <pg:ebook rdf:about="{about}" {attributes}>{properties}</pg:ebook>{extra}
    </rdf:RDF>""".encode()


class RealRecordTests(unittest.TestCase):
    def test_documented_examples(self):
        path = (
            pathlib.Path(__file__).resolve().parents[2]
            / "docs/reference/gettenberg-records.md"
        )
        result = doctest.testfile(str(path), module_relative=False)
        self.assertEqual(result.failed, 0)
        self.assertGreater(result.attempted, 0)

    def parse(self, filename):
        return rdf.parse_record(
            (FIXTURES / filename).read_bytes(), source_name=filename
        )

    def test_fixture_provenance_and_all_records_parse_without_diagnostics(self):
        manifest = json.loads((FIXTURES / "provenance.json").read_text())
        for entry in manifest["files"]:
            with self.subTest(file=entry["file"]):
                raw = (FIXTURES / entry["file"]).read_bytes()
                self.assertEqual(len(raw), entry["size_bytes"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry["sha256"])
                result = self.parse(entry["file"])
                self.assertEqual(result.source.data, raw)
                self.assertEqual(result.source.sha256, entry["sha256"])
                exported = result.to_dict()
                self.assertEqual(
                    base64.b64decode(exported["source"]["data"]["value"]), raw
                )
                self.assertEqual(
                    sorted({d.code for d in result.diagnostics}),
                    entry.get("expected_diagnostic_codes", []),
                )

    def test_real_in_record_agent_references_preserve_each_role(self):
        book = self.parse("pg15813.rdf").ebook
        guardini = [c for c in book.contributors if c.agent.uri.endswith("/26362")]
        self.assertEqual(
            [c.role_uri for c in guardini], [rdf.RELATORS + "edt", rdf.RELATORS + "trl"]
        )
        self.assertEqual(guardini[0].agent, guardini[1].agent)
        self.assertEqual(guardini[1].agent.aliases[0].text, "Guardini, R. (Romano)")
        book = self.parse("pg16264.rdf").ebook
        witkop = [c for c in book.contributors if c.agent.uri.endswith("/6581")]
        self.assertEqual(
            [c.role_uri for c in witkop], [rdf.RELATORS + "edt", rdf.DC + "creator"]
        )

    def test_real_resource_whitespace_is_normalized_with_evidence(self):
        result = self.parse("pg11008.rdf")
        self.assertTrue(result.diagnostics)
        self.assertTrue(all(d.code == "normalized_uri" for d in result.diagnostics))
        self.assertTrue(
            any("Antwerp%20to%20Gallipoli" in r.uri for r in result.ebook.resources)
        )
        self.assertIn(b"Antwerp to Gallipoli", result.source.data)
        self.assertTrue(all(" " not in r.uri for r in result.ebook.resources))

    def test_aliases_stay_attached_to_contributor_identity(self):
        book = self.parse("pg10000.rdf").ebook
        self.assertEqual(book.gutenberg_id, 10000)
        author = book.contributors[0]
        self.assertEqual(author.role_uri, rdf.DC + "creator")
        self.assertEqual(author.agent.uri, "http://www.gutenberg.org/2009/agents/216")
        self.assertEqual([n.text for n in author.agent.names], ["Anonymous"])
        self.assertEqual(
            [n.text for n in author.agent.aliases], ["Anonyme", "Anonymous, Anonymous"]
        )
        self.assertIn(
            "http://www.gutenberg.org/ebooks/author/49", author.agent.webpages
        )
        self.assertEqual(author.agent.birth_dates, ())

    def test_alternative_titles_multiple_languages_and_classification(self):
        book = self.parse("pg10040.rdf").ebook
        self.assertEqual([t.kind for t in book.titles], ["primary", "alternative"])
        self.assertEqual(book.titles[1].value.text, "Alaska Indian Dictionary")
        self.assertEqual([v.value.text for v in book.languages], ["en", "ale"])
        self.assertEqual(book.languages[0].value.datatype, rdf.DC + "RFC4646")
        self.assertIn(rdf.DC + "LCC", {s for t in book.subjects for s in t.schemes})
        self.assertEqual(book.issued[0].text, "2003-11-01")
        self.assertTrue(book.shelves)
        self.assertEqual(book.types[0].value.text, "Text")

    def test_noncreator_roles_and_dates(self):
        book = self.parse("pg10001.rdf").ebook
        self.assertTrue(
            any(c.role_uri.startswith(rdf.RELATORS) for c in book.contributors)
        )
        author = self.parse("pg84.rdf").ebook.contributors[0].agent
        self.assertEqual(author.birth_dates[0].text, "1797")
        self.assertEqual(author.death_dates[0].text, "1851")

    def test_resources_with_equal_formats_remain_distinct(self):
        book = self.parse("pg10000.rdf").ebook
        html = [
            r
            for r in book.resources
            if any(t.value.text == "text/html" for t in r.formats)
        ]
        self.assertGreaterEqual(len(html), 2)
        self.assertEqual(len(book.resources), 14)
        self.assertNotEqual(html[0].uri, html[1].uri)
        self.assertTrue(all(r.sizes and r.modified and r.is_format_of for r in html))
        self.assertTrue(any(len(r.formats) > 1 for r in book.resources))

    def test_source_supplied_summaries_and_rights(self):
        book = self.parse("pg10000.rdf").ebook
        summary = next(
            v for v in book.additional_metadata if v.predicate_uri == rdf.PG + "marc520"
        )
        self.assertIn("automatically generated summary", summary.value.text)
        self.assertEqual(book.rights[0].text, "Public domain in the USA.")
        self.assertEqual(book.publishers[0].text, "Project Gutenberg")
        self.assertEqual(book.downloads, 1447)
        self.assertEqual(book.licenses, ("http://www.gutenberg.org/license",))

    def test_json_export_preserves_values_and_exact_bytes(self):
        result = self.parse("pg10040.rdf")
        exported = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
        self.assertEqual(exported["schema_version"], 1)
        self.assertEqual(exported["source"]["data"]["encoding"], "base64")
        self.assertEqual(
            base64.b64decode(exported["source"]["data"]["value"]), result.source.data
        )
        self.assertEqual(
            exported["ebook"]["titles"][0]["value"]["text"],
            result.ebook.titles[0].value.text,
        )
        exported["ebook"]["titles"].clear()
        self.assertEqual(len(result.ebook.titles), 2)

    def test_records_are_frozen_and_nested_collections_are_tuples(self):
        result = self.parse("pg84.rdf")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.ebook.gutenberg_id = 99
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.ebook.contributors[0].agent.uri = "changed"
        self.assertIsInstance(result.ebook.resources, tuple)
        self.assertIsInstance(result.ebook.resources[0].formats, tuple)


class ProfileBoundaryTests(unittest.TestCase):
    def parse(self, data):
        return rdf.parse_record(data, source_name="authored.rdf")

    def assert_error(self, data, code):
        with self.assertRaises(errors.RecordParseError) as caught:
            self.parse(data)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.source_name, "authored.rdf")

    def test_literal_comment_and_processing_instruction_tails_survive(self):
        book = self.parse(
            record(
                "<dc:title>First<!--not text-->Second<?note ignored?>Third</dc:title><pg:downloads>1<!--not text-->2</pg:downloads>"
            )
        ).ebook
        self.assertEqual(book.titles[0].value.text, "FirstSecondThird")
        self.assertEqual(book.downloads, 12)

    def test_rdf_object_attributes_are_not_silently_read_as_literals_or_inline_nodes(
        self,
    ):
        for prop in (
            '<dc:title rdf:nodeID="n"/>',
            '<dc:license rdf:resource="license" rdf:nodeID="n"/>',
            '<dc:license rdf:resource="license"><!--c-->stray</dc:license>',
            '<dc:subject><rdf:Description rdf:resource="https://example.test/x"><rdf:value>X</rdf:value></rdf:Description></dc:subject>',
            '<dc:title rdf:about="ebooks/42"/>',
            '<dc:subject rdf:resource="https://example.test/x"><rdf:Description><rdf:value>X</rdf:value></rdf:Description></dc:subject>',
            '<dc:hasFormat rdf:nodeID="n"><pg:file rdf:about="files/a"/></dc:hasFormat>',
            '<dc:creator rdf:nodeID="n"><pg:agent rdf:about="2009/agents/7"/></dc:creator>',
            "<dc:subject>stray<rdf:Description><rdf:value>X</rdf:value></rdf:Description></dc:subject>",
        ):
            with self.subTest(prop=prop):
                self.assert_error(record(prop), "unsupported_shape")

    def test_conflicting_inline_agent_definitions_are_rejected(self):
        self.assert_error(
            record(
                '<dc:creator><pg:agent rdf:about="2009/agents/7"><pg:name>A</pg:name></pg:agent></dc:creator><role:trl><pg:agent rdf:about="2009/agents/7"><pg:name>B</pg:name></pg:agent></role:trl>'
            ),
            "invalid_identity",
        )

    def test_repeated_references_share_one_immutable_agent_without_amplification(self):
        aliases = "".join(f"<pg:alias>Name {n}</pg:alias>" for n in range(100))
        references = '<role:trl rdf:resource="2009/agents/7"/>' * 100
        book = self.parse(
            record(
                f'<dc:creator><pg:agent rdf:about="2009/agents/7">{aliases}</pg:agent></dc:creator>{references}'
            )
        ).ebook
        self.assertEqual(len(book.contributors), 101)
        self.assertEqual(len(book.contributors[0].agent.aliases), 100)
        self.assertTrue(
            all(c.agent is book.contributors[0].agent for c in book.contributors)
        )

    def test_missing_optional_values_do_not_fabricate_metadata(self):
        book = self.parse(record()).ebook
        self.assertIsNone(book.downloads)
        self.assertEqual(book.titles, ())
        self.assertEqual(book.resources, ())

    def test_title_order_language_inheritance_and_empty_language_reset(self):
        raw = record(
            '<dc:title xml:lang="fr">Été</dc:title><dc:alternative>Alt</dc:alternative><dc:title xml:lang="">No tag</dc:title>',
            attributes='xml:lang="en"',
        )
        titles = self.parse(raw).ebook.titles
        self.assertEqual([t.value.language for t in titles], ["fr", "en", None])
        self.assertEqual(
            [t.kind for t in titles], ["primary", "alternative", "primary"]
        )

    def test_xml_base_applies_to_agents_files_and_links(self):
        book = self.parse(
            record(
                """<role:trl xml:base="https://example.test/people/">
          <pg:agent rdf:about="a"><pg:name>A</pg:name><pg:webpage rdf:resource="bio"/></pg:agent>
        </role:trl><dc:hasFormat xml:base="https://example.test/files/">
          <pg:file rdf:about="a.txt"><dc:isFormatOf rdf:resource="https://www.gutenberg.org/ebooks/42"/></pg:file>
        </dc:hasFormat>"""
            )
        ).ebook
        self.assertEqual(
            book.contributors[0].agent.uri, "https://example.test/people/a"
        )
        self.assertEqual(
            book.contributors[0].agent.webpages, ("https://example.test/people/bio",)
        )
        self.assertEqual(book.resources[0].uri, "https://example.test/files/a.txt")

    def test_repeated_resource_claims_and_zero_downloads_are_preserved(self):
        book = self.parse(
            record(
                """<pg:downloads>0</pg:downloads><dc:hasFormat><pg:file rdf:about="files/a">
          <dc:extent>10</dc:extent><dc:extent>12</dc:extent>
          <dc:modified>old</dc:modified><dc:modified>new</dc:modified>
        </pg:file></dc:hasFormat>"""
            )
        ).ebook
        self.assertEqual(book.downloads, 0)
        self.assertEqual(book.resources[0].sizes, (10, 12))
        self.assertEqual([v.text for v in book.resources[0].modified], ["old", "new"])

    def test_unknown_properties_and_attributes_have_paths_and_original_evidence(self):
        raw = record(
            '<new:subject new:flag="yes"><new:detail>unmodeled</new:detail></new:subject>'
        )
        result = self.parse(raw)
        self.assertEqual(result.source.data, raw)
        self.assertEqual(
            {d.predicate_uri for d in result.diagnostics},
            {
                "https://example.test/vocab/subject",
                "https://example.test/vocab/detail",
                "https://example.test/vocab/flag",
            },
        )
        self.assertTrue(
            all(d.path.startswith("/rdf:RDF/pg:ebook/") for d in result.diagnostics)
        )

    def test_known_predicate_in_unmodeled_context_is_reported(self):
        result = self.parse(
            record(
                '<pg:agent rdf:about="2009/agents/1"><pg:name>A</pg:name></pg:agent>'
            )
        )
        self.assertIn(rdf.PG + "name", {d.predicate_uri for d in result.diagnostics})
        self.assertEqual(result.ebook.contributors, ())

    def test_unrecognized_marc_predicate_is_preserved_as_source_metadata(self):
        result = self.parse(record("<pg:marc999>source note</pg:marc999>"))
        self.assertEqual(
            result.ebook.additional_metadata[0].predicate_uri, rdf.PG + "marc999"
        )
        self.assertEqual(result.ebook.additional_metadata[0].value.text, "source note")

    def test_forward_agent_reference_is_resolved_only_inside_the_record(self):
        book = self.parse(
            record(
                '<role:trl rdf:resource="2009/agents/7"/><dc:creator><pg:agent rdf:about="2009/agents/7"><pg:name>A</pg:name></pg:agent></dc:creator>'
            )
        ).ebook
        self.assertEqual(book.contributors[0].agent, book.contributors[1].agent)
        self.assert_error(
            record('<role:trl rdf:resource="https://example.test/missing"/>'),
            "unsupported_shape",
        )
        self.assert_error(
            record(
                '<role:trl rdf:resource="2009/agents/7"><pg:agent rdf:about="2009/agents/7"/></role:trl>'
            ),
            "unsupported_shape",
        )

    def test_conflicting_agent_reference_is_rejected(self):
        self.assert_error(
            record(
                '<role:trl rdf:resource="2009/agents/7"/><dc:creator><pg:agent rdf:about="2009/agents/7"><pg:name>A</pg:name></pg:agent><pg:agent rdf:about="2009/agents/7"><pg:name>B</pg:name></pg:agent></dc:creator>'
            ),
            "invalid_identity",
        )

    def test_export_limits_reject_expansion_without_changing_the_record(self):
        aliases = "".join(f"<pg:alias>Name {n}</pg:alias>" for n in range(100))
        references = '<role:trl rdf:resource="2009/agents/7"/>' * 100
        result = self.parse(
            record(
                f'<dc:creator><pg:agent rdf:about="2009/agents/7">{aliases}</pg:agent></dc:creator>{references}'
            )
        )
        with self.assertRaises(errors.ExportLimitError):
            result.to_dict(max_nodes=100)
        with self.assertRaises(errors.ExportLimitError):
            result.to_dict(max_text_bytes=1000)
        exported = result.to_dict(max_nodes=1_000_000, max_text_bytes=4 * 1024**2)
        self.assertEqual(len(exported["ebook"]["contributors"]), 101)
        self.assertEqual(len(result.ebook.contributors[0].agent.aliases), 100)
        for limit in (0, -1, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                result.to_dict(max_nodes=limit)

    def test_default_export_bound_rejects_small_repeated_source_expansion(self):
        aliases = "<pg:alias>" + ("x" * 1000) + "</pg:alias>"
        raw = record(
            '<dc:creator><pg:agent rdf:about="2009/agents/7">'
            + aliases * 100
            + "</pg:agent></dc:creator>"
            + '<role:trl rdf:resource="2009/agents/7"/>' * 200
        )
        self.assertLess(len(raw), rdf.DEFAULT_MAX_BYTES)
        result = self.parse(raw)
        with self.assertRaises(errors.ExportLimitError):
            result.to_dict()

    def test_export_preserves_filesystem_surrogate_labels(self):
        for label in (
            "cache/pg42-\udcff.rdf",
            "paired-\ud83d\ude00.rdf",
            "scalar-😀.rdf",
        ):
            with self.subTest(label=repr(label)):
                result = rdf.parse_record(record(), source_name=label)
                exported = json.loads(json.dumps(result.to_dict()))
                # JSON may combine a valid escaped pair into its scalar;
                # surrogateescape/unpaired labels remain exactly preserved.
                self.assertEqual(
                    exported["source"]["source_name"], json.loads(json.dumps(label))
                )
                self.assertEqual(result.to_dict()["source"]["source_name"], label)

    def test_export_exact_limits_include_generated_wrapper_fields(self):
        result = self.parse(record())
        exported = result.to_dict()

        def measure(value):
            if isinstance(value, dict):
                parts = [measure(item) for pair in value.items() for item in pair]
            elif isinstance(value, list):
                parts = [measure(item) for item in value]
            else:
                parts = []
            size = (
                len(value.encode("utf-8", errors="backslashreplace"))
                if isinstance(value, str)
                else 0
            )
            return 1 + sum(n for n, _ in parts), size + sum(t for _, t in parts)

        nodes, text_bytes = measure(exported)
        self.assertEqual(
            result.to_dict(max_nodes=nodes, max_text_bytes=text_bytes), exported
        )
        with self.assertRaises(errors.ExportLimitError):
            result.to_dict(max_nodes=nodes - 1, max_text_bytes=text_bytes)
        with self.assertRaises(errors.ExportLimitError):
            result.to_dict(max_nodes=nodes, max_text_bytes=text_bytes - 1)

    def test_term_description_identities_are_preserved_without_graph_resolution(self):
        result = self.parse(
            record(
                '<dc:subject><rdf:Description rdf:about="terms/example"><rdf:value>X</rdf:value></rdf:Description></dc:subject><dc:language><rdf:Description rdf:nodeID="local1"><rdf:value>en</rdf:value></rdf:Description></dc:language>'
            )
        )
        self.assertEqual(
            result.ebook.subjects[0].uri, "https://www.gutenberg.org/terms/example"
        )
        self.assertIsNone(result.ebook.subjects[0].node_id)
        self.assertEqual(result.ebook.languages[0].node_id, "local1")
        self.assertIsNone(result.ebook.languages[0].uri)
        exported = result.to_dict()["ebook"]
        self.assertEqual(
            exported["subjects"][0]["uri"], "https://www.gutenberg.org/terms/example"
        )
        self.assertEqual(exported["languages"][0]["node_id"], "local1")

    def test_stray_text_and_tails_inside_structured_nodes_are_rejected(self):
        for prop in (
            "<dc:subject><rdf:Description>lost<rdf:value>X</rdf:value></rdf:Description></dc:subject>",
            "<dc:subject><rdf:Description><rdf:value>X</rdf:value>lost</rdf:Description></dc:subject>",
            "<dc:subject><rdf:Description><!--comment-->lost<rdf:value>X</rdf:value></rdf:Description></dc:subject>",
            '<dc:creator><pg:agent rdf:about="2009/agents/7">lost<pg:name>A</pg:name></pg:agent></dc:creator>',
            '<dc:hasFormat><pg:file rdf:about="files/x">lost</pg:file></dc:hasFormat>',
            "lost<dc:title>X</dc:title>",
        ):
            with self.subTest(prop=prop):
                self.assert_error(record(prop), "unsupported_shape")

    def test_input_size_limit_boundary_and_override(self):
        data = record()
        self.assertEqual(
            rdf.parse_record(
                data, source_name="s", max_bytes=len(data)
            ).ebook.gutenberg_id,
            42,
        )
        with self.assertRaises(errors.RecordParseError) as caught:
            rdf.parse_record(data, source_name="s", max_bytes=len(data) - 1)
        self.assertEqual(caught.exception.code, "record_too_large")
        for limit in (0, -1, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                rdf.parse_record(data, source_name="s", max_bytes=limit)

    def test_argument_validation_does_not_interpret_strings_as_paths(self):
        for value in (
            "/tmp/a.rdf",
            "https://example.test/a.rdf",
            bytearray(record()),
            None,
        ):
            with self.subTest(value=type(value)), self.assertRaises(TypeError):
                self.parse(value)
        with self.assertRaises(ValueError):
            rdf.parse_record(record(), source_name="")
        with self.assertRaises(TypeError):
            rdf.parse_record(record(), source_name=None)

    def test_malformed_xml(self):
        for data in (
            b"",
            b"<broken>",
            b"<a/><b/>",
            record().replace(b"</pg:ebook>", b""),
        ):
            with self.subTest(data=data[:20]):
                self.assert_error(data, "malformed_xml")

    def test_dtds_internal_external_and_utf16_are_rejected(self):
        for declaration in (
            "<!DOCTYPE rdf:RDF>",
            '<!DOCTYPE rdf:RDF SYSTEM "file:///no-such-file.dtd">',
            '<!DOCTYPE rdf:RDF SYSTEM "https://example.test/no-network.dtd">',
            '<!DOCTYPE rdf:RDF [<!ENTITY x "expanded">]>',
            '<!DOCTYPE rdf:RDF [<!ENTITY x SYSTEM "file:///etc/passwd">]>',
        ):
            for encoding in ("utf-8", "utf-16"):
                with self.subTest(declaration=declaration, encoding=encoding):
                    xml = (
                        declaration
                        + record(
                            "<dc:title>&x;</dc:title>"
                            if "<!ENTITY" in declaration
                            else ""
                        ).decode()
                    )
                    self.assert_error(xml.encode(encoding), "unsafe_xml")

    def test_xinclude_is_never_loaded(self):
        raw = record(
            '<xi:include xmlns:xi="http://www.w3.org/2001/XInclude" href="file:///etc/passwd"/>'
        )
        result = self.parse(raw)
        self.assertEqual(result.diagnostics[0].code, "unmodeled_predicate")
        self.assertNotIn(b"root:", result.source.data)

    def test_invalid_and_ambiguous_identities(self):
        for about in (
            "ebooks/0",
            "ebooks/-1",
            "ebooks/01",
            "ebooks/42?x=1",
            "https://example.test/ebooks/42",
            "ebooks/no",
            "ebooks/42/",
            "ebooks/4 2",
            "https://[broken/ebooks/42",
        ):
            with self.subTest(about=about):
                self.assert_error(record(about=about), "invalid_identity")
        self.assert_error(record(attributes='rdf:nodeID="also"'), "invalid_identity")
        self.assert_error(
            record(extra='<pg:ebook rdf:about="ebooks/43"/>'), "unsupported_record"
        )
        self.assert_error(
            record('<new:nested><pg:ebook rdf:about="ebooks/43"/></new:nested>'),
            "unsupported_record",
        )

    def test_nonbook_deletion_and_unsupported_rdf_forms_are_explicit(self):
        self.assert_error(b'<deleted id="42"/>', "unsupported_record")
        self.assert_error(
            record().replace(b'<pg:ebook rdf:about="ebooks/42" ></pg:ebook>', b""),
            "unsupported_record",
        )
        for properties in (
            '<dc:creator rdf:resource="2009/agents/1"/>',
            "<dc:language>en</dc:language>",
            "<dc:subject><rdf:Description/></dc:subject>",
            "<dc:title><new:markup>Hi</new:markup></dc:title>",
            '<dc:title rdf:parseType="Literal">Hi</dc:title>',
        ):
            with self.subTest(properties=properties):
                self.assert_error(record(properties), "unsupported_shape")

    def test_invalid_numbers_and_duplicate_download_count(self):
        for value in ("-1", "bad", "1.5", "9223372036854775808", ""):
            with self.subTest(value=value):
                self.assert_error(
                    record(f"<pg:downloads>{value}</pg:downloads>"), "invalid_value"
                )
        self.assert_error(
            record("<pg:downloads>1</pg:downloads><pg:downloads>2</pg:downloads>"),
            "unsupported_shape",
        )

    def test_fresh_import_and_parse_do_not_create_caches_or_use_network(self):
        # Deny real boundary operations in a fresh interpreter. Do not mock
        # parser internals, and do not import the legacy cache module.
        script = """import os, pathlib, socket, sys
before = set(pathlib.Path.cwd().iterdir())
def deny(*args, **kwargs): raise RuntimeError("unexpected I/O")
os.mkdir = deny
socket.socket = deny
from lcats.gettenberg import models, errors, rdf
rdf.parse_record(sys.stdin.buffer.read(), source_name="no-io")
assert set(pathlib.Path.cwd().iterdir()) == before
assert "lcats.gettenberg.cache" not in sys.modules
assert "gutenbergpy" not in sys.modules
"""
        with tempfile.TemporaryDirectory() as temp:
            env = dict(
                os.environ,
                LCATS_CACHE_DIR=str(pathlib.Path(temp) / "cache"),
                PYTHONDONTWRITEBYTECODE="1",
            )
            completed = subprocess.run(
                [sys.executable, "-B", "-c", script],
                input=record(),
                cwd=temp,
                env=env,
                capture_output=True,
                timeout=20,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            self.assertFalse((pathlib.Path(temp) / "cache").exists())


if __name__ == "__main__":
    unittest.main()
