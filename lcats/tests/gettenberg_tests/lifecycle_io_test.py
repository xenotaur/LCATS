"""Filesystem and independent-process contracts for lifecycle I/O."""

import hashlib
import json
import os
import pathlib
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from lcats.gettenberg import _lifecycle_io
from lcats.gettenberg import errors


class LifecycleIOTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        self.path = self.root / "active.json"
        self.archives = self.root / "archives"
        self.archives.mkdir()
        self.source = self.root / "source.tar.bz2"
        self.source.write_bytes(b"archive payload")

    def test_json_canonical_round_trip(self):
        value = {"z": "café", "a": [1, True, None]}
        _lifecycle_io.atomic_json(self.path, value)
        self.assertEqual(
            self.path.read_bytes(), b'{"a":[1,true,null],"z":"caf\xc3\xa9"}'
        )
        self.assertEqual(_lifecycle_io.read_json(self.path), value)
        _lifecycle_io.atomic_json(self.path, {"replacement": True})
        self.assertEqual(_lifecycle_io.read_json(self.path), {"replacement": True})
        self.assertEqual(list(self.root.glob(".active.json.*.tmp")), [])

    def test_json_rejects_bad_encoding_syntax_shape_and_nonfinite(self):
        for payload in (b"\xff", b"{", b"[]", b"null", b'{"n":NaN}', b'{"n":Infinity}'):
            with self.subTest(payload=payload):
                self.path.write_bytes(payload)
                with self.assertRaises(errors.CatalogLifecycleError):
                    _lifecycle_io.read_json(self.path)

    def test_json_read_is_bounded(self):
        self.path.write_bytes(b'{"long":"' + b"x" * 100 + b'"}')
        with self.assertRaises(errors.CatalogLifecycleError):
            _lifecycle_io.read_json(self.path, max_bytes=20)
        self.assertEqual(
            _lifecycle_io.read_json(self.path, self.path.stat().st_size),
            {"long": "x" * 100},
        )

    def test_invalid_json_values_preserve_previous_publication(self):
        self.path.write_bytes(b'{"old":true}')
        for value in (float("nan"), {"bad": object()}, {"bad": "\ud800"}):
            with self.subTest(value=value):
                with self.assertRaises(errors.CatalogInputError):
                    _lifecycle_io.atomic_json(self.path, value)
                self.assertEqual(self.path.read_bytes(), b'{"old":true}')
        self.assertEqual(list(self.root.glob(".active.json.*.tmp")), [])

    def test_prepublication_replace_failure_preserves_pointer(self):
        self.path.write_bytes(b'{"old":true}')
        with mock.patch.object(
            os, "replace", side_effect=OSError("injected replace failure")
        ):
            with self.assertRaises(errors.CatalogLifecycleError) as caught:
                _lifecycle_io.atomic_json(self.path, {"new": True})
        self.assertNotIsInstance(caught.exception, errors.CatalogPublicationError)
        self.assertEqual(self.path.read_bytes(), b'{"old":true}')
        self.assertEqual(list(self.root.glob(".active.json.*.tmp")), [])

    @unittest.skipIf(os.name == "nt", "POSIX directory durability boundary")
    def test_postpublication_directory_sync_failure_reports_published(self):
        real_fsync = os.fsync

        def fail_directory(descriptor):
            if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise OSError("injected directory fsync failure")
            real_fsync(descriptor)

        with mock.patch.object(os, "fsync", side_effect=fail_directory):
            with self.assertRaises(errors.CatalogPublicationError) as caught:
                _lifecycle_io.atomic_json(self.path, {"new": True})
        self.assertTrue(caught.exception.published)
        self.assertEqual(_lifecycle_io.read_json(self.path), {"new": True})
        self.assertEqual(list(self.root.glob(".active.json.*.tmp")), [])

    def test_prepublication_file_sync_failure_preserves_pointer(self):
        self.path.write_bytes(b'{"old":true}')
        with mock.patch.object(
            os, "fsync", side_effect=OSError("injected fsync failure")
        ):
            with self.assertRaises(errors.CatalogLifecycleError) as caught:
                _lifecycle_io.atomic_json(self.path, {"new": True})
        self.assertNotIsInstance(caught.exception, errors.CatalogPublicationError)
        self.assertEqual(_lifecycle_io.read_json(self.path), {"old": True})
        self.assertEqual(list(self.root.glob(".active.json.*.tmp")), [])

    def test_missing_files_and_parent_are_typed(self):
        with self.assertRaises(errors.CatalogLifecycleError):
            _lifecycle_io.read_json(self.path)
        with self.assertRaises(errors.CatalogLifecycleError):
            _lifecycle_io.hash_file(self.path, 100)
        with self.assertRaises(errors.CatalogLifecycleError):
            _lifecycle_io.atomic_json(self.root / "missing" / "value.json", {})
        with self.assertRaises(errors.CatalogLifecycleError):
            with _lifecycle_io.writer_lock(self.root / "missing" / "writer.sqlite"):
                self.fail("Missing parent must fail")

    def test_rejects_symlinks_and_directories(self):
        self.path.symlink_to(self.source)
        for path in (self.path, self.archives):
            with self.subTest(path=path):
                with self.assertRaises(errors.CatalogLifecycleError):
                    _lifecycle_io.hash_file(path, 100)
                with self.assertRaises(errors.CatalogLifecycleError):
                    _lifecycle_io.read_json(path)
                with self.assertRaises(errors.CatalogLifecycleError):
                    _lifecycle_io.atomic_json(path, {})
                with self.assertRaises(errors.CatalogLifecycleError):
                    with _lifecycle_io.writer_lock(path, 0):
                        self.fail("Nonregular lock must fail")
        self.assertEqual(self.source.read_bytes(), b"archive payload")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO requires POSIX")
    def test_fifo_is_rejected_without_opening(self):
        os.mkfifo(self.path)
        with self.assertRaises(errors.CatalogLifecycleError):
            _lifecycle_io.hash_file(self.path, 100)
        with self.assertRaises(errors.CatalogLifecycleError):
            _lifecycle_io.read_json(self.path)

    def test_invalid_size_bounds(self):
        for limit in (True, -1, 1.5, None):
            for operation in (
                lambda: _lifecycle_io.hash_file(self.source, limit),
                lambda: _lifecycle_io.read_json(self.source, limit),
                lambda: _lifecycle_io.retain_archive(self.source, self.archives, limit),
            ):
                with self.subTest(limit=limit, operation=operation):
                    with self.assertRaises(errors.CatalogInputError):
                        operation()

    def test_streamed_hash_and_chunk_cancellation_checks(self):
        data = b"x" * (128 * 1024 * 2 + 3)
        self.source.write_bytes(data)
        checks = []
        result = _lifecycle_io.hash_file(
            self.source, len(data), lambda: checks.append(True)
        )
        self.assertEqual(result, (hashlib.sha256(data).hexdigest(), len(data)))
        self.assertGreaterEqual(len(checks), 3)
        with self.assertRaises(errors.CatalogLifecycleError):
            _lifecycle_io.hash_file(self.source, len(data) - 1)
        self.source.write_bytes(b"")
        self.assertEqual(
            _lifecycle_io.hash_file(self.source, 0),
            (hashlib.sha256(b"").hexdigest(), 0),
        )

    def test_source_mutation_is_rejected_for_hash_and_retention(self):
        for operation in (
            lambda check: _lifecycle_io.hash_file(self.source, 100, check),
            lambda check: _lifecycle_io.retain_archive(
                self.source, self.archives, 100, check
            ),
        ):
            with self.subTest(operation=operation):
                self.source.write_bytes(b"original")
                changed = False

                def change_once():
                    nonlocal changed
                    if not changed:
                        changed = True
                        self.source.write_bytes(b"changed contents")

                with self.assertRaises(errors.CatalogLifecycleError):
                    operation(change_once)
                self.assertEqual(list(self.archives.iterdir()), [])

    def test_source_replacement_is_rejected(self):
        replacement = self.root / "replacement"
        replacement.write_bytes(self.source.read_bytes())

        def replace_once():
            if replacement.exists():
                os.replace(replacement, self.source)

        with self.assertRaises(errors.CatalogLifecycleError):
            _lifecycle_io.hash_file(self.source, 100, replace_once)

    def test_cancellation_preserves_source_and_removes_archive_temp(self):
        def cancel():
            raise errors.CatalogLifecycleError("deadline exceeded")

        with self.assertRaisesRegex(errors.CatalogLifecycleError, "deadline exceeded"):
            _lifecycle_io.retain_archive(self.source, self.archives, 100, cancel)
        self.assertEqual(self.source.read_bytes(), b"archive payload")
        self.assertEqual(list(self.archives.iterdir()), [])

    def test_archive_retention_and_reuse_preserve_inode_and_source(self):
        result = _lifecycle_io.retain_archive(self.source, self.archives, 100)
        target, digest, size = result
        identity = target.stat().st_ino
        self.assertEqual(digest, hashlib.sha256(b"archive payload").hexdigest())
        self.assertEqual(size, len(b"archive payload"))
        self.assertEqual(target, self.archives / f"{digest}.tar.bz2")
        self.assertEqual(target.read_bytes(), self.source.read_bytes())
        self.assertEqual(
            _lifecycle_io.retain_archive(self.source, self.archives, 100), result
        )
        self.assertEqual(target.stat().st_ino, identity)
        self.assertEqual(list(self.archives.iterdir()), [target])

    def test_corrupt_retained_archive_is_preserved_and_rejected(self):
        target, _, _ = _lifecycle_io.retain_archive(self.source, self.archives, 100)
        target.write_bytes(b"corrupt")
        identity = target.stat().st_ino
        with self.assertRaisesRegex(errors.CatalogLifecycleError, "corrupt"):
            _lifecycle_io.retain_archive(self.source, self.archives, 100)
        self.assertEqual(target.read_bytes(), b"corrupt")
        self.assertEqual(target.stat().st_ino, identity)
        self.assertEqual(self.source.read_bytes(), b"archive payload")
        self.assertEqual(list(self.archives.iterdir()), [target])

    def test_retention_rejects_symlink_source_and_destination(self):
        link = self.root / "source-link"
        link.symlink_to(self.source)
        with self.assertRaises(errors.CatalogLifecycleError):
            _lifecycle_io.retain_archive(link, self.archives, 100)
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        target = self.archives / f"{digest}.tar.bz2"
        target.symlink_to(self.source)
        with self.assertRaises(errors.CatalogLifecycleError):
            _lifecycle_io.retain_archive(self.source, self.archives, 100)
        self.assertTrue(target.is_symlink())
        self.assertEqual(list(self.archives.iterdir()), [target])

    def test_archive_oversize_and_publication_failure_leave_no_temp(self):
        with self.assertRaises(errors.CatalogLifecycleError):
            _lifecycle_io.retain_archive(self.source, self.archives, 1)
        with mock.patch.object(
            os, "link", side_effect=OSError("hard links unavailable")
        ):
            with self.assertRaisesRegex(
                errors.CatalogLifecycleError, "hard links unavailable"
            ):
                _lifecycle_io.retain_archive(self.source, self.archives, 100)
        self.assertEqual(list(self.archives.iterdir()), [])
        self.assertEqual(self.source.read_bytes(), b"archive payload")

    def test_lock_timeout_validation(self):
        for timeout in (True, -1, 61, float("inf"), float("nan"), "1", None):
            with self.subTest(timeout=timeout):
                with self.assertRaises(errors.CatalogInputError):
                    with _lifecycle_io.writer_lock(self.path, timeout):
                        self.fail("Invalid timeout must fail")
        self.assertFalse(self.path.exists())

    def test_lock_persistent_inode_and_release_on_body_error(self):
        with self.assertRaisesRegex(RuntimeError, "body error"):
            with _lifecycle_io.writer_lock(self.path, 0):
                identity = self.path.stat().st_ino
                with sqlite3.connect(self.path, timeout=0) as competitor:
                    with self.assertRaises(sqlite3.OperationalError):
                        competitor.execute("BEGIN IMMEDIATE")
                raise RuntimeError("body error")
        with _lifecycle_io.writer_lock(self.path, 0):
            self.assertEqual(self.path.stat().st_ino, identity)
        self.assertTrue(self.path.exists())

    def test_invalid_sqlite_lock_is_typed(self):
        self.path.write_bytes(b"this is not SQLite")
        with self.assertRaises(errors.CatalogLifecycleError):
            with _lifecycle_io.writer_lock(self.path, 0):
                self.fail("Corrupt lock must fail")

    def _holder(self):
        ready = self.root / "ready"
        code = """
import pathlib
import sys
from lcats.gettenberg import _lifecycle_io
with _lifecycle_io.writer_lock(pathlib.Path(sys.argv[1]), 0):
    pathlib.Path(sys.argv[2]).write_text('ready', encoding='utf-8')
    sys.stdin.read()
"""
        process = subprocess.Popen(
            [sys.executable, "-c", code, str(self.path), str(ready)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        def finish():
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

        self.addCleanup(finish)
        deadline = time.monotonic() + 8
        while not ready.exists():
            if process.poll() is not None:
                self.fail(f"Lock subprocess failed: {process.communicate(timeout=5)}")
            if time.monotonic() >= deadline:
                self.fail("Lock subprocess did not become ready")
            time.sleep(0.01)
        return process

    def test_independent_writer_process_contention_and_normal_release(self):
        process = self._holder()
        code = """
import pathlib
import sys
from lcats.gettenberg import _lifecycle_io, errors
try:
    with _lifecycle_io.writer_lock(pathlib.Path(sys.argv[1]), 0.05):
        raise RuntimeError('unexpectedly acquired busy lock')
except errors.CatalogLockError:
    print('busy')
"""
        competitor = subprocess.run(
            [sys.executable, "-c", code, str(self.path)],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        self.assertEqual(competitor.returncode, 0, competitor.stderr)
        self.assertEqual(competitor.stdout.strip(), "busy")
        started = time.monotonic()
        with self.assertRaises(errors.CatalogLockError):
            with _lifecycle_io.writer_lock(self.path, 0.05):
                self.fail("Busy writer lock must time out")
        self.assertLess(time.monotonic() - started, 3)
        process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0)
        with _lifecycle_io.writer_lock(self.path, 0):
            self.assertTrue(self.path.exists())

    def test_process_death_releases_lock_without_deleting_inode(self):
        process = self._holder()
        identity = self.path.stat().st_ino
        process.kill()
        process.communicate(timeout=5)
        self.assertNotEqual(process.returncode, 0)
        with _lifecycle_io.writer_lock(self.path, 0.5):
            self.assertEqual(self.path.stat().st_ino, identity)

    def test_json_hash_is_hash_of_actual_canonical_bytes(self):
        _lifecycle_io.atomic_json(self.path, {"é": 2, "b": 1})
        expected = hashlib.sha256(self.path.read_bytes()).hexdigest()
        actual, size = _lifecycle_io.hash_file(self.path, 65536)
        self.assertEqual(actual, expected)
        self.assertEqual(size, len(self.path.read_bytes()))
        self.assertEqual(json.loads(self.path.read_bytes()), {"é": 2, "b": 1})
