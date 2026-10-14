"""Real catalog lifecycle, concurrency and publication-boundary contracts."""

import doctest
import hashlib
import json
import os
import pathlib
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

from lcats.gettenberg import _lifecycle_io
from lcats.gettenberg import errors
from lcats.gettenberg import lifecycle
from tests.gettenberg_tests import catalog_test


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = pathlib.Path(self.temporary.name).resolve()
        self.cache = self.directory / "cache"
        self.manager = lifecycle.CatalogManager(self.cache, lock_timeout=0)
        self.archive = self.make_archive("original", [(1, "Original")])

    def make_archive(self, name, books):
        path = self.directory / (name + ".tar.bz2")
        path.write_bytes(
            catalog_test.archive_bytes(
                [
                    (f"pg{i}.rdf", catalog_test.record(i, title), tarfile.REGTYPE)
                    for i, title in books
                ]
            )
        )
        return path

    def test_constructor_status_and_open_are_read_only_and_offline(self):
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            self.assertEqual(self.manager.status()["state"], "missing")
            with self.assertRaises(errors.CatalogMissingError):
                self.manager.open()
        self.assertFalse(self.cache.exists())

    def test_environment_is_resolved_at_construction(self):
        with mock.patch.dict(os.environ, {"LCATS_CACHE_DIR": str(self.cache)}):
            manager = lifecycle.CatalogManager()
        self.assertEqual(manager.cache_dir, self.cache)
        self.assertEqual(manager.root, self.cache / "gettenberg")
        self.assertFalse(self.cache.exists())

    def test_setup_reuses_without_reading_supplied_missing_archive(self):
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            first = self.manager.setup(self.archive)
            second = self.manager.setup(self.directory / "does-not-exist")
            self.assertEqual(first.generation_id, second.generation_id)
            self.assertTrue(second.reused)
            with self.manager.open() as reader:
                self.assertEqual(reader.get(1).ebook.titles[0].value.text, "Original")
        self.assertEqual(first.manifest["source"]["retrieved_at"], None)
        self.assertEqual(
            first.manifest["archive_sha256"],
            hashlib.sha256(self.archive.read_bytes()).hexdigest(),
        )
        self.assertEqual(first.archive_path.read_bytes(), self.archive.read_bytes())

    def test_setup_and_rebuild_missing_input_are_explicit(self):
        with self.assertRaises(errors.CatalogMissingError):
            self.manager.setup()
        with self.assertRaises(errors.CatalogMissingError):
            self.manager.rebuild()
        self.assertEqual(self.manager.status()["state"], "missing")

    def test_rebuild_reuses_retained_source_after_original_is_removed(self):
        first = self.manager.setup(self.archive)
        self.archive.unlink()
        second = self.manager.rebuild()
        self.assertNotEqual(first.generation_id, second.generation_id)
        self.assertEqual(first.manifest["snapshot_id"], second.manifest["snapshot_id"])
        self.assertEqual(first.archive_path, second.archive_path)
        self.assertEqual(second.previous_count, 1)

    def test_count_change_requires_approval_and_is_recoverable_without_rebuild(self):
        first = self.manager.setup(self.archive)
        bigger = self.make_archive("bigger", [(1, "One"), (2, "Two")])
        with self.assertRaises(errors.CatalogCountChangeError) as caught:
            self.manager.rebuild(bigger)
        error = caught.exception
        self.assertEqual((error.previous, error.candidate), (1, 2))
        self.assertEqual(
            self.manager.status()["active"]["generation_id"], first.generation_id
        )
        self.assertIn(error.generation_id, self.manager.status()["candidates"])
        accepted = self.manager.activate(error.generation_id, allow_count_change=True)
        self.assertEqual(accepted.previous_count, 1)
        with self.manager.open() as reader:
            self.assertEqual(reader.find_ids(), (1, 2))
        activation = self.manager.status()["active"]["activation"]
        self.assertTrue(activation["count_change_approved"])
        self.assertEqual((activation["previous_count"], activation["count"]), (1, 2))
        with self.assertRaises(errors.CatalogCountChangeError):
            self.manager.activate(first.generation_id)
        self.manager.activate(first.generation_id, allow_count_change=True)

    def test_two_readers_remain_pinned_across_activation_and_cleanup(self):
        first = self.manager.setup(self.archive)
        changed = self.make_archive("changed", [(1, "Changed")])
        with self.manager.open() as a, self.manager.open() as b:
            second = self.manager.rebuild(changed)
            self.assertEqual(self.manager.cleanup(), ())
            for reader in (a, b):
                self.assertEqual(reader.get(1).ebook.titles[0].value.text, "Original")
            with self.manager.open() as new:
                self.assertEqual(new.get(1).ebook.titles[0].value.text, "Changed")
        self.assertTrue(first.catalog_path.exists())
        self.assertTrue(second.catalog_path.exists())

    def test_legacy_artifacts_and_archives_are_preserved_by_cleanup(self):
        self.cache.mkdir()
        for name in ("gutenbergindex.db", "rdf-files.tar.bz2"):
            (self.cache / name).write_bytes(b"legacy unverified")
        (self.cache / "texts").mkdir()
        (self.cache / "texts" / "story.txt").write_text("legacy", encoding="utf-8")
        first = self.manager.setup(self.archive)
        bad = self.directory / "bad.bz2"
        bad.write_bytes(b"invalid compression")
        with self.assertRaises(errors.CatalogBuildError):
            self.manager.rebuild(bad)
        candidates = self.manager.status()["candidates"]
        self.assertEqual(len(candidates), 1)
        removed = self.manager.cleanup()
        self.assertEqual(
            removed, (str(self.manager.root / "candidates" / candidates[0]),)
        )
        self.assertTrue(first.archive_path.exists())
        self.assertTrue(first.catalog_path.exists())
        self.assertEqual(
            (self.cache / "gutenbergindex.db").read_bytes(), b"legacy unverified"
        )
        self.assertEqual(len(self.manager.status()["legacy"]), 3)
        self.assertEqual(
            len(list((self.manager.root / "archives").glob("*.tar.bz2"))), 2
        )

    def test_manifest_fingerprint_and_schema_fail_closed(self):
        first = self.manager.setup(self.archive)
        manifest = first.catalog_path.parent / "manifest.json"
        value = json.loads(manifest.read_text(encoding="utf-8"))
        value["parser_version"] = "future"
        _lifecycle_io.atomic_json(manifest, value)
        with self.assertRaises(errors.CatalogError):
            self.manager.open()
        with self.assertRaises(errors.CatalogSchemaError):
            self.manager.activate(first.generation_id)
        self.assertEqual(self.manager.status()["state"], "invalid")

    def test_implicit_rebuild_rejects_changed_retained_source_identity(self):
        first_source = self.make_archive("first", [(1, "Title000")])
        replacement = self.make_archive("replacement", [(1, "Title001")])
        self.assertEqual(first_source.stat().st_size, replacement.stat().st_size)
        first = self.manager.setup(first_source)
        first.archive_path.write_bytes(replacement.read_bytes())
        with self.assertRaises(errors.CatalogLifecycleError):
            self.manager.rebuild()
        self.assertEqual(
            self.manager.status()["active"]["generation_id"], first.generation_id
        )
        with self.manager.open() as reader:
            self.assertEqual(reader.get(1).ebook.titles[0].value.text, "Title000")

    def test_atomic_pointer_replacement_before_open_is_a_valid_snapshot(self):
        first = self.manager.setup(self.archive)
        changed = self.make_archive("changed", [(1, "Changed")])
        second = self.manager.rebuild(changed)
        pointer = self.manager.root / "active.json"
        newer = pointer.read_bytes()
        self.manager.activate(first.generation_id)
        temp = self.manager.root / "replacement.json"
        temp.write_bytes(newer)
        original_open = os.open
        armed = True

        def replace_before_open(path, *args, **kwargs):
            nonlocal armed
            if pathlib.Path(path) == pointer and armed:
                armed = False
                os.replace(temp, pointer)
            return original_open(path, *args, **kwargs)

        with mock.patch.object(os, "open", side_effect=replace_before_open):
            with self.manager.open() as reader:
                self.assertEqual(reader.get(1).ebook.titles[0].value.text, "Changed")
        self.assertEqual(
            self.manager.status()["active"]["generation_id"], second.generation_id
        )

    def test_atomic_pointer_replacement_after_open_preserves_old_snapshot(self):
        first = self.manager.setup(self.archive)
        second = self.manager.rebuild(self.make_archive("changed", [(1, "Changed")]))
        pointer = self.manager.root / "active.json"
        newer = pointer.read_bytes()
        self.manager.activate(first.generation_id)
        temp = self.manager.root / "replacement.json"
        temp.write_bytes(newer)
        original_open, original_fstat = os.open, os.fstat
        descriptor = None
        armed = True

        def capture_open(path, *args, **kwargs):
            nonlocal descriptor
            result = original_open(path, *args, **kwargs)
            if pathlib.Path(path) == pointer:
                descriptor = result
            return result

        def replace_after_stat(fd):
            nonlocal armed
            result = original_fstat(fd)
            if fd == descriptor and armed:
                armed = False
                os.replace(temp, pointer)
            return result

        with (
            mock.patch.object(os, "open", side_effect=capture_open),
            mock.patch.object(os, "fstat", side_effect=replace_after_stat),
        ):
            with self.manager.open() as reader:
                self.assertEqual(reader.get(1).ebook.titles[0].value.text, "Original")
        self.assertEqual(
            self.manager.status()["active"]["generation_id"], second.generation_id
        )

    def test_activation_rejects_same_size_archive_corruption(self):
        first = self.manager.setup(self.archive)
        original_pointer = (self.manager.root / "active.json").read_bytes()
        raw = first.archive_path.read_bytes()
        first.archive_path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
        with self.assertRaises(errors.CatalogLifecycleError):
            self.manager.activate(first.generation_id)
        self.assertEqual(
            (self.manager.root / "active.json").read_bytes(), original_pointer
        )

    def test_activation_rejects_database_content_change(self):
        first = self.manager.setup(self.archive)
        with sqlite3.connect(first.catalog_path) as connection:
            connection.execute("UPDATE titles SET value='tampered' WHERE ebook_id=1")
        with self.assertRaises(errors.CatalogLifecycleError):
            self.manager.activate(first.generation_id)

    def test_managed_symlinks_are_neither_followed_nor_deleted(self):
        self.manager.setup(self.archive)
        outside = self.directory / "outside"
        outside.mkdir()
        (outside / "keep").write_text("keep", encoding="utf-8")
        linked = self.manager.root / "candidates" / ("a" * 32)
        linked.symlink_to(outside, target_is_directory=True)
        self.manager.cleanup()
        self.assertTrue((outside / "keep").exists())
        self.assertTrue(linked.is_symlink())
        with self.assertRaises(errors.CatalogLifecycleError):
            self.manager.activate("a" * 32)

    def test_identifier_and_limit_inputs_are_validated(self):
        for value in ("../outside", "A" * 32, "x", None, 4):
            with self.subTest(value=value), self.assertRaises(errors.CatalogInputError):
                self.manager.activate(value)
        for value in (-1, float("nan"), True, 61):
            with self.subTest(value=value), self.assertRaises(errors.CatalogInputError):
                lifecycle.CatalogManager(self.cache, lock_timeout=value)
        for value in (0, float("inf"), True):
            with self.subTest(value=value), self.assertRaises(errors.CatalogInputError):
                lifecycle.CatalogManager(self.cache, validation_seconds=value)

    def test_failed_pointer_replace_retains_previous_active(self):
        first = self.manager.setup(self.archive)
        changed = self.make_archive("changed", [(1, "Changed")])
        replace = os.replace

        def fail_pointer(source, destination):
            if pathlib.Path(destination).name == "active.json":
                raise OSError("injected pointer replacement failure")
            return replace(source, destination)

        with mock.patch.object(os, "replace", side_effect=fail_pointer):
            with self.assertRaises(errors.CatalogLifecycleError):
                self.manager.rebuild(changed)
        self.assertEqual(
            self.manager.status()["active"]["generation_id"], first.generation_id
        )
        orphan = next(
            i for i in self.manager.status()["generations"] if i != first.generation_id
        )
        self.manager.activate(orphan)
        with self.manager.open() as reader:
            self.assertEqual(reader.get(1).ebook.titles[0].value.text, "Changed")

    def test_post_pointer_sync_failure_reports_possible_publication(self):
        first = self.manager.setup(self.archive)
        sync = _lifecycle_io.sync_directory

        def fail_root(path):
            if path == self.manager.root:
                raise OSError("injected durability failure")
            return sync(path)

        with mock.patch.object(_lifecycle_io, "sync_directory", side_effect=fail_root):
            with self.assertRaises(errors.CatalogPublicationError) as caught:
                self.manager.rebuild()
        self.assertTrue(caught.exception.published)
        self.assertNotEqual(
            self.manager.status()["active"]["generation_id"], first.generation_id
        )

    def test_real_process_interruption_at_publication_boundaries(self):
        code = r"""
import os, pathlib, sys
from lcats.gettenberg import lifecycle
cache, archive, phase = sys.argv[1:]
manager = lifecycle.CatalogManager(cache)
mkdir, rename, replace = os.mkdir, os.rename, os.replace

def interrupted_mkdir(path, *args, **kwargs):
    result = mkdir(path, *args, **kwargs)
    if phase == 'candidate' and pathlib.Path(path).parent.name == 'candidates':
        os._exit(77)
    return result

def interrupted_rename(source, target, *args, **kwargs):
    result = rename(source, target, *args, **kwargs)
    if phase == 'generation' and pathlib.Path(target).parent.name == 'generations':
        os._exit(77)
    return result

def interrupted_replace(source, target, *args, **kwargs):
    result = replace(source, target, *args, **kwargs)
    if (phase == 'manifest' and pathlib.Path(target).name == 'manifest.json') or (phase == 'pointer' and pathlib.Path(target).name == 'active.json'):
        os._exit(77)
    return result
os.mkdir, os.rename, os.replace = interrupted_mkdir, interrupted_rename, interrupted_replace
manager.rebuild(archive)
"""
        changed = self.make_archive("changed", [(1, "Changed")])
        for phase in ("candidate", "manifest", "generation", "pointer"):
            with self.subTest(phase=phase):
                manager = lifecycle.CatalogManager(
                    self.directory / phase, lock_timeout=0
                )
                first = manager.setup(self.archive)
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        code,
                        str(manager.cache_dir),
                        str(changed),
                        phase,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.assertEqual(result.returncode, 77, result.stderr)
                with manager.open() as reader:
                    self.assertEqual(
                        reader.get(1).ebook.titles[0].value.text,
                        "Changed" if phase == "pointer" else "Original",
                    )
                # Crash releases the writer lock; explicit recovery never rebuilds.
                state = manager.status()
                if phase == "manifest":
                    manager.activate(state["candidates"][0])
                elif phase == "generation":
                    manager.activate(
                        next(
                            i for i in state["generations"] if i != first.generation_id
                        )
                    )
                manager.cleanup()
                self.assertEqual(manager.status()["candidates"], [])

    def test_busy_writer_does_not_block_readers_or_allow_cleanup(self):
        self.manager.setup(self.archive)
        code = """import pathlib,sys
from lcats.gettenberg import _lifecycle_io
with _lifecycle_io.writer_lock(pathlib.Path(sys.argv[1]),0):
 print('locked',flush=True)
 sys.stdin.read(1)
"""
        process = subprocess.Popen(
            [sys.executable, "-c", code, str(self.manager.root / "writer.sqlite")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(process.stdout.readline().strip(), "locked")
            with self.manager.open() as reader:
                self.assertEqual(reader.find_ids(), (1,))
            with self.assertRaises(errors.CatalogLockError):
                self.manager.cleanup()
        finally:
            process.communicate("x", timeout=10)
        self.assertEqual(process.returncode, 0)
        self.manager.cleanup()

    def test_how_to_example_executes(self):
        path = (
            pathlib.Path(__file__).resolve().parents[2]
            / "docs/how-to/gettenberg-catalog.md"
        )
        result = doctest.testfile(
            str(path),
            module_relative=False,
            extraglobs={"cache_dir": self.cache, "archive_path": self.archive},
        )
        self.assertEqual(result.failed, 0)
        self.assertGreater(result.attempted, 0)
