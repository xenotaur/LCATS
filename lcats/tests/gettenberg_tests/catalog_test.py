"""Real archive/parser/SQLite integration contracts for local catalogs."""

import bz2
import dataclasses
import doctest
import hashlib
import html
import io
import json
import pathlib
import shutil
import socket
import sqlite3
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

from lcats.gettenberg import catalog
from lcats.gettenberg import errors
from lcats.gettenberg import ingestion
from lcats.gettenberg import rdf

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def record(identifier, title="Example", extra=""):
    return (
        f'<rdf:RDF xmlns:rdf="{rdf.RDF}" xmlns:pg="{rdf.PG}" xmlns:dc="{rdf.DC}" xmlns:dcam="{rdf.DCAM}" xmlns:rel="{rdf.RELATORS}" xml:base="https://www.gutenberg.org/"><pg:ebook rdf:about="ebooks/{identifier}"><dc:title>{html.escape(title)}</dc:title>{extra}</pg:ebook></rdf:RDF>'
    ).encode()


def archive_bytes(entries):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, data, kind in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    return bz2.compress(stream.getvalue())


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.root = pathlib.Path(cls.directory.name)
        cls.archive = cls.root / "fixtures.tar.bz2"
        cls.entries = [
            (p.name, p.read_bytes(), tarfile.REGTYPE)
            for p in sorted(FIXTURES.glob("*.rdf"))
        ]
        cls.archive.write_bytes(archive_bytes(cls.entries))
        cls.path = cls.root / "catalog.sqlite"
        cls.report = ingestion.build_catalog(cls.archive, cls.path, batch_size=2)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def copy_catalog(self, root):
        path = pathlib.Path(root) / "copy.sqlite"
        shutil.copyfile(self.path, path)
        return path

    def test_documentation_example_executes(self):
        with tempfile.TemporaryDirectory() as root:
            result = doctest.testfile(
                str(
                    pathlib.Path(__file__).resolve().parents[2]
                    / "docs/reference/gettenberg-catalog.md"
                ),
                module_relative=False,
                extraglobs={
                    "archive_path": self.archive,
                    "candidate_path": pathlib.Path(root) / "docs.sqlite",
                },
            )
            self.assertEqual(result.failed, 0)
            self.assertGreater(result.attempted, 0)

    def test_all_real_records_round_trip_and_normalized_relations(self):
        with (
            catalog.Catalog(self.path) as library,
            sqlite3.connect(self.path) as connection,
        ):
            for name, data, _ in self.entries:
                expected = rdf.parse_record(data, source_name=name)
                identifier = expected.ebook.gutenberg_id
                self.assertEqual(library.get(identifier), expected)
                self.assertEqual(
                    connection.execute(
                        "SELECT value FROM titles WHERE ebook_id=? ORDER BY position",
                        (identifier,),
                    ).fetchall(),
                    [(x.value.text,) for x in expected.ebook.titles],
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT uri FROM resources WHERE ebook_id=? ORDER BY position",
                        (identifier,),
                    ).fetchall(),
                    [(x.uri,) for x in expected.ebook.resources],
                )
                for term in expected.ebook.subjects:
                    self.assertIn(
                        identifier,
                        library.find_ids(catalog.Filters(subjects=(term.value.text,))),
                    )
                for contribution in expected.ebook.contributors:
                    for alias in contribution.agent.aliases:
                        self.assertIn(
                            identifier,
                            library.find_ids(catalog.Filters(authors=(alias.text,))),
                        )
            self.assertEqual(
                connection.execute("PRAGMA foreign_key_check").fetchall(), []
            )
            self.assertEqual(
                connection.execute("PRAGMA integrity_check").fetchall(), [("ok",)]
            )

    def test_report_counts_source_identity_and_detached_info(self):
        self.assertEqual(self.report.status, "complete")
        self.assertEqual(self.report.members, len(self.entries))
        self.assertEqual(self.report.imported, len(self.entries))
        self.assertEqual((self.report.rejected, self.report.uncommitted), (0, 0))
        self.assertEqual(
            self.report.archive_sha256,
            hashlib.sha256(self.archive.read_bytes()).hexdigest(),
        )
        self.assertEqual(self.report.archive_bytes, self.archive.stat().st_size)
        self.assertGreater(
            self.report.expanded_bytes, sum(len(x[1]) for x in self.entries)
        )
        json.dumps(dataclasses.asdict(self.report))
        with catalog.Catalog(self.path) as library:
            info = library.info
            info["limits"]["max_members"] = -1
            self.assertGreater(library.info["limits"]["max_members"], 0)

    def test_batch_preserves_missing_duplicate_and_input_order(self):
        with catalog.Catalog(self.path) as library:
            items = library.get_many([84, 999999999, 84, 10000])
            self.assertEqual(
                [x.ebook.gutenberg_id if x else None for x in items],
                [84, None, 84, 10000],
            )
            self.assertEqual(library.get_many([]), ())

    def test_batch_source_budget_includes_duplicates_before_loading(self):
        size = next(len(data) for name, data, _ in self.entries if name == "pg84.rdf")
        with catalog.Catalog(self.path) as library:
            self.assertEqual(
                len(library.get_many([84, 84], max_source_bytes=2 * size)), 2
            )
            with self.assertRaises(errors.CatalogInputError):
                library.get_many([84, 84], max_source_bytes=2 * size - 1)

    def test_existing_ebook_without_source_is_corruption(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.copy_catalog(root)
            with sqlite3.connect(path) as connection:
                connection.execute("DELETE FROM sources WHERE ebook_id=84")
            with (
                catalog.Catalog(path) as library,
                self.assertRaises(errors.CatalogSchemaError),
            ):
                library.get(84)

    def test_keyset_pagination_is_bounded_complete_and_ordered(self):
        with catalog.Catalog(self.path) as library:
            expected = library.find_ids(limit=1000)
            result, after = [], 0
            while page := library.find_ids(after_id=after, limit=2):
                self.assertLessEqual(len(page), 2)
                result.extend(page)
                after = page[-1]
            self.assertEqual(tuple(result), expected)
            self.assertEqual(
                tuple(x.ebook.gutenberg_id for x in library.iter_records(limit=2)),
                expected[:2],
            )

    def test_closed_catalog_fails_explicitly(self):
        library = catalog.Catalog(self.path)
        library.close()
        library.close()
        for operation in (
            lambda: library.get(84),
            lambda: library.get_many([]),
            library.find_ids,
            lambda: library.info,
        ):
            with (
                self.subTest(operation=operation),
                self.assertRaises(errors.CatalogClosedError),
            ):
                operation()

    def test_queries_do_not_change_catalog_bytes(self):
        before = hashlib.sha256(self.path.read_bytes()).digest()
        with catalog.Catalog(self.path) as library:
            library.find_ids(catalog.Filters(languages=("en",)))
            library.search_ids(catalog.Filters(titles=("THE",)))
            library.get(84)
            with self.assertRaises(sqlite3.OperationalError):
                library._connection.execute("DELETE FROM ebooks")
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).digest(), before)

    def test_invalid_ids_filters_and_pagination(self):
        with catalog.Catalog(self.path) as library:
            for value in (True, 0, -1, "84", None, 2**63):
                with (
                    self.subTest(value=value),
                    self.assertRaises(errors.CatalogInputError),
                ):
                    library.get(value)
            for kwargs in (
                {"limit": 0},
                {"limit": 1001},
                {"limit": True},
                {"after_id": -1},
                {"after_id": "84"},
            ):
                with (
                    self.subTest(kwargs=kwargs),
                    self.assertRaises(errors.CatalogInputError),
                ):
                    library.find_ids(**kwargs)
            with self.assertRaises(errors.CatalogInputError):
                library.find_ids({"unknown": "x"})
            with self.assertRaises(errors.CatalogInputError):
                library.get_many([84] * 1001)
        for kwargs in (
            {"titles": ["x"]},
            {"titles": ("",)},
            {"ids": (True,)},
            {"languages": ("x",) * 101},
        ):
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaises(errors.CatalogInputError),
            ):
                catalog.Filters(**kwargs)
        with self.assertRaises(TypeError):
            catalog.Filters(unknown=("x",))

    def test_extreme_reader_limit_and_surrogate_filter_fail_cleanly(self):
        with self.assertRaises(errors.CatalogInputError):
            catalog.Catalog(self.path, max_record_bytes=sys.maxsize)
        with self.assertRaises(errors.CatalogInputError):
            catalog.Filters(titles=("\ud800",))

    def test_missing_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = pathlib.Path(root) / "missing.sqlite"
            with self.assertRaises(errors.CatalogMissingError):
                catalog.Catalog(path)
            self.assertFalse(path.exists())

    def test_corrupt_incompatible_and_incomplete_catalogs(self):
        edits = [
            ("PRAGMA user_version=999", (), errors.CatalogSchemaError),
            ("PRAGMA application_id=0", (), errors.CatalogSchemaError),
            ("DROP TABLE languages", (), errors.CatalogSchemaError),
            (
                "UPDATE metadata SET value=? WHERE key='status'",
                ('"building"',),
                errors.CatalogIncompleteError,
            ),
            (
                "UPDATE metadata SET value=? WHERE key='parser_version'",
                ('"future"',),
                errors.CatalogSchemaError,
            ),
        ]
        for statement, parameters, error in edits:
            with (
                self.subTest(statement=statement),
                tempfile.TemporaryDirectory() as root,
            ):
                path = self.copy_catalog(root)
                with sqlite3.connect(path) as connection:
                    connection.execute(statement, parameters)
                with self.assertRaises(error):
                    catalog.Catalog(path)
        with tempfile.TemporaryDirectory() as root:
            path = pathlib.Path(root) / "bad.sqlite"
            path.write_bytes(b"not sqlite")
            with self.assertRaises(errors.CatalogSchemaError):
                catalog.Catalog(path)

    def test_source_bounds_and_corruption_detected_before_return(self):
        with catalog.Catalog(self.path, max_record_bytes=10) as library:
            with self.assertRaises(errors.CatalogInputError):
                library.get(84)
        for statement in (
            "UPDATE sources SET sha256='wrong' WHERE ebook_id=84",
            "UPDATE sources SET data=x'00' WHERE ebook_id=84",
            "UPDATE sources SET raw_size=raw_size-1 WHERE ebook_id=84",
        ):
            with (
                self.subTest(statement=statement),
                tempfile.TemporaryDirectory() as root,
            ):
                path = self.copy_catalog(root)
                with sqlite3.connect(path) as connection:
                    connection.execute(statement)
                with (
                    catalog.Catalog(path) as library,
                    self.assertRaises(errors.CatalogSchemaError),
                ):
                    library.get(84)


class AuthoredArchiveTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        self.archive = self.root / "input.tar.bz2"
        self.output = self.root / "candidate.sqlite"

    def build(self, entries=None, **kwargs):
        if entries is None:
            entries = [("pg1.rdf", record(1), tarfile.REGTYPE)]
        self.archive.write_bytes(archive_bytes(entries))
        return ingestion.build_catalog(self.archive, self.output, **kwargs)

    def test_exact_and_text_search_and_or_semantics(self):
        extra = '<dc:alternative>Alias title</dc:alternative><dc:language><rdf:Description><rdf:value>en</rdf:value></rdf:Description></dc:language><dc:creator><pg:agent rdf:about="agents/1"><pg:name>Smith</pg:name><pg:alias>Writer</pg:alias></pg:agent></dc:creator>'
        self.build(
            [
                ("a.rdf", record(1, "Straße 100%_", extra), tarfile.REGTYPE),
                ("b.rdf", record(2, "Other"), tarfile.REGTYPE),
                ("c.rdf", record(3, "Third", extra), tarfile.REGTYPE),
            ]
        )
        with catalog.Catalog(self.output) as library:
            self.assertEqual(
                library.find_ids(catalog.Filters(titles=("Alias title",))), (1, 3)
            )
            self.assertEqual(
                library.find_ids(catalog.Filters(titles=("straße 100%_",))), ()
            )
            self.assertEqual(
                library.search_ids(catalog.Filters(titles=("STRASSE",))), (1,)
            )
            self.assertEqual(library.search_ids(catalog.Filters(titles=("%_",))), (1,))
            self.assertEqual(
                library.find_ids(catalog.Filters(ids=(1, 2), languages=("en",))), (1,)
            )
            self.assertEqual(
                library.find_ids(catalog.Filters(titles=("Other", "Third"))), (2, 3)
            )
            self.assertEqual(
                library.find_ids(
                    catalog.Filters(authors=("Writer",), languages=("en",))
                ),
                (1, 3),
            )
            self.assertEqual(
                library.search_ids(catalog.Filters(titles=("' OR 1=1 --",))), ()
            )

    def test_no_network_during_build_or_read(self):
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            self.build()
            with catalog.Catalog(self.output) as library:
                self.assertEqual(library.get(1).ebook.gutenberg_id, 1)

    def test_existing_output_is_preserved(self):
        self.output.write_bytes(b"keep me")
        with self.assertRaises(errors.CatalogBuildError):
            self.build()
        self.assertEqual(self.output.read_bytes(), b"keep me")

    def test_every_rejected_member_prevents_complete_result(self):
        bad_cases = [
            ("bad.rdf", b"bad XML", tarfile.REGTYPE),
            ("../outside.rdf", record(2), tarfile.REGTYPE),
            ("/absolute.rdf", record(2), tarfile.REGTYPE),
            ("link.rdf", b"", tarfile.SYMTYPE),
            ("note.txt", b"not RDF", tarfile.REGTYPE),
            ("second.rdf", record(1), tarfile.REGTYPE),
            ("good.rdf", record(2), tarfile.REGTYPE),
            (
                "nonbook.rdf",
                f'<rdf:RDF xmlns:rdf="{rdf.RDF}"/>'.encode(),
                tarfile.REGTYPE,
            ),
        ]
        for index, bad in enumerate(bad_cases):
            with self.subTest(bad=bad[0]):
                self.output = self.root / f"failed{index}.sqlite"
                with self.assertRaises(errors.CatalogBuildError) as caught:
                    self.build(
                        [("good.rdf", record(1), tarfile.REGTYPE), bad], batch_size=1
                    )
                result = caught.exception.report
                self.assertEqual(
                    (result.imported, result.rejected, result.members), (1, 1, 2)
                )
                self.assertEqual(result.status, "failed")
                with self.assertRaises(errors.CatalogIncompleteError):
                    catalog.Catalog(self.output)
        self.assertFalse((self.root.parent / "outside.rdf").exists())

    def test_unknown_predicate_is_preserved_and_counted(self):
        result = self.build(
            [
                (
                    "one.rdf",
                    record(1, extra="<pg:future>kept</pg:future>"),
                    tarfile.REGTYPE,
                )
            ]
        )
        self.assertEqual(result.diagnostics, 1)
        with catalog.Catalog(self.output) as library:
            self.assertEqual(library.get(1).diagnostics[0].code, "unmodeled_predicate")

    def test_empty_archive_is_not_complete(self):
        with self.assertRaises(errors.CatalogBuildError) as caught:
            self.build([])
        self.assertEqual(caught.exception.report.imported, 0)
        with self.assertRaises(errors.CatalogIncompleteError):
            catalog.Catalog(self.output)

    def test_truncated_compression_and_tar_fail(self):
        packed = archive_bytes([("one.rdf", record(1), tarfile.REGTYPE)])
        for index, data in enumerate(
            (
                packed[:-8],
                bz2.compress(bz2.decompress(packed)[:700]),
                bz2.compress(bz2.decompress(packed)[:1024]),
            )
        ):
            with self.subTest(index=index):
                path = self.root / f"truncated{index}.sqlite"
                self.archive.write_bytes(data)
                with self.assertRaises(errors.CatalogBuildError):
                    ingestion.build_catalog(self.archive, path)
                with self.assertRaises(
                    (errors.CatalogIncompleteError, errors.CatalogSchemaError)
                ):
                    catalog.Catalog(path)

    def test_record_and_accounting_roll_back_together_on_abort(self):
        small = record(1)
        with self.assertRaises(errors.CatalogBuildError) as caught:
            self.build(
                [
                    ("one.rdf", small, tarfile.REGTYPE),
                    ("two.rdf", record(2, "X" * 2000), tarfile.REGTYPE),
                ],
                limits=ingestion.BuildLimits(max_member_bytes=len(small) + 1),
            )
        result = caught.exception.report
        self.assertEqual(result.imported, 0)
        with sqlite3.connect(self.output) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM ebooks").fetchone()[0], 0
            )
            self.assertEqual(
                connection.execute("SELECT count(*) FROM archive_members").fetchone()[
                    0
                ],
                0,
            )
        self.assertEqual(result.uncommitted, result.members)

    def test_compressed_trailers_and_concatenated_streams_are_rejected(self):
        packed = archive_bytes([("one.rdf", record(1), tarfile.REGTYPE)])
        for index, trailer in enumerate(
            (b"garbage", b"BZh", bz2.compress(b""), packed)
        ):
            with self.subTest(index=index):
                self.archive.write_bytes(packed + trailer)
                with self.assertRaises(errors.CatalogBuildError):
                    ingestion.build_catalog(
                        self.archive, self.root / f"trailer{index}.sqlite"
                    )

    def test_expanded_limit_counts_tar_padding_not_only_member_payload(self):
        with self.assertRaises(errors.CatalogBuildError) as caught:
            self.build(limits=ingestion.BuildLimits(max_expanded_bytes=1024))
        self.assertEqual(caught.exception.code, "resource_limit")

    def test_member_compressed_count_and_database_limits(self):
        limits = [
            ingestion.BuildLimits(max_member_bytes=10),
            ingestion.BuildLimits(max_compressed_bytes=10),
            ingestion.BuildLimits(max_members=1),
            ingestion.BuildLimits(max_database_bytes=4096),
        ]
        for index, bound in enumerate(limits):
            with self.subTest(bound=bound):
                self.output = self.root / f"limited{index}.sqlite"
                with self.assertRaises(errors.CatalogBuildError):
                    self.build(
                        [
                            ("one.rdf", record(1), tarfile.REGTYPE),
                            ("two.rdf", record(2), tarfile.REGTYPE),
                        ],
                        limits=bound,
                        batch_size=1,
                    )

    def test_invalid_limits_are_not_assert_based(self):
        for kwargs in (
            {"max_seconds": float("nan")},
            {"max_seconds": True},
            {"max_members": 0},
            {"max_member_bytes": -1},
            {"max_compressed_bytes": "large"},
        ):
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaises(errors.CatalogInputError),
            ):
                ingestion.BuildLimits(**kwargs)
        for batch in (0, 1001, True):
            with self.subTest(batch=batch), self.assertRaises(errors.CatalogInputError):
                self.build(batch_size=batch)

    def test_elapsed_limit_uses_monotonic_checkpoints(self):
        self.archive.write_bytes(
            archive_bytes([("one.rdf", record(1), tarfile.REGTYPE)])
        )
        with (
            mock.patch.object(
                ingestion.time, "monotonic", side_effect=[0.0] + [2.0] * 100
            ),
            self.assertRaises(errors.CatalogBuildError) as caught,
        ):
            ingestion.build_catalog(
                self.archive, self.output, limits=ingestion.BuildLimits(max_seconds=1)
            )
        self.assertEqual(caught.exception.code, "resource_limit")
