"""Refresh acceptance over local HTTP, immutable files and real shared locks.

No external service is used. Shared acquisition fixtures provide response queues
and a virtual pacing clock; concurrent tests synchronize before the actual lock
rather than relying on scheduler timing. Faults are injected only at HTTP or
filesystem boundaries to verify observable failure preservation.
"""

import dataclasses
import hashlib
import json
import pathlib
import socket
import tempfile
import threading
import unittest
from unittest import mock

from lcats.gettenberg import _lifecycle_io
from lcats.gettenberg import _resource_io
from lcats.gettenberg import _resource_transport
from lcats.gettenberg import _resource_types
from lcats.gettenberg import resources
from tests.gettenberg_tests import resources_test

_DATE = "Wed, 21 Oct 2015 07:28:00 GMT"


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache_dir = pathlib.Path(self.temp.name) / "cache"
        self.store = resources.ResourceStore(self.cache_dir)
        self.server = resources_test.Server()
        self.addCleanup(self.server.close)
        self.clock = resources_test.Clock()
        patch = mock.patch.object(_resource_transport, "time", self.clock)
        patch.start()
        self.addCleanup(patch.stop)
        self.policy = resources.NetworkPolicy(
            online=True, allowed_origins=(self.server.origin,)
        )
        self.request = resources.SourceRequest.from_url(self.server.origin + "/book")

    def seed(self, headers=(("ETag", '"v1"'),), body=b"A story.", request=None):
        self.server.routes["/book"] = [resources_test.Reply(body=body, headers=headers)]
        return self.store.fetch(request or self.request, policy=self.policy)

    def refresh(self, reply=None, **policy):
        self.server.routes["/book"] = [
            reply
            or resources_test.Reply(status=304, body=b"", headers=(("ETag", 'W/"v1"'),))
        ]
        return self.store.refresh(
            self.request, policy=dataclasses.replace(self.policy, **policy)
        )

    def sent(self, server=None, index=-1):
        return {
            key.lower(): value
            for key, value in (server or self.server).requests[index][1].items()
        }

    def evidence(self, artifact):
        return (
            self.cache_dir
            / "gettenberg/resources/receipts"
            / (artifact.receipt_sha256 + ".json")
        )

    def assert_current(self, artifact):
        self.assertEqual(self.store.fetch(self.request), artifact)
        self.assertEqual(
            hashlib.sha256(artifact.path.read_bytes()).hexdigest(), artifact.sha256
        )

    def test_304_preserves_original_time_bytes_inode_and_receipt_history(self):
        original = self.seed(
            headers=(
                ("ETag", '"v1"'),
                ("Last-Modified", _DATE),
                ("Content-Type", "text/plain"),
            )
        )
        stat = original.path.stat()
        original_receipt = self.evidence(original).read_bytes()
        validated = self.refresh(
            resources_test.Reply(status=304, body=b"", headers=(("ETag", 'W/"v1"'),))
        )
        self.assertEqual(validated.path, original.path)
        self.assertEqual(
            (validated.sha256, validated.size), (original.sha256, original.size)
        )
        self.assertEqual(validated.receipt.retrieved_at, original.receipt.retrieved_at)
        self.assertIsNotNone(validated.receipt.validated_at)
        self.assertEqual(validated.receipt.status, 304)
        self.assertEqual(validated.receipt.validation_headers, (("etag", 'W/"v1"'),))
        self.assertEqual(
            validated.receipt.previous_receipt_sha256, original.receipt_sha256
        )
        self.assertEqual(original_receipt, self.evidence(original).read_bytes())
        self.assertEqual(original.path.stat().st_ctime_ns, stat.st_ctime_ns)
        self.assertEqual(original.path.stat().st_mtime_ns, stat.st_mtime_ns)
        self.assertEqual(self.sent()["if-none-match"], '"v1"')
        self.assertEqual(self.sent()["if-modified-since"], _DATE)
        # A second explicit refresh uses the newly recorded weaker validator.
        again = self.refresh()
        self.assertEqual(self.sent()["if-none-match"], 'W/"v1"')
        self.assertEqual(
            again.receipt.previous_receipt_sha256, validated.receipt_sha256
        )
        self.assertEqual(again.receipt.retrieved_at, original.receipt.retrieved_at)
        self.assertEqual(resources.decode_text(original).text, "A story.")
        self.assertEqual(resources.decode_text(again).text, "A story.")
        self.assert_current(again)
        self.assertEqual(len(self.server.requests), 3)

    def test_last_modified_only_and_obsolete_http_dates(self):
        for date in (
            _DATE,
            "Wednesday, 21-Oct-15 07:28:00 GMT",
            "Wed Oct 21 07:28:00 2015",
        ):
            with self.subTest(date=date):
                request = resources.SourceRequest.from_url(
                    self.server.origin + "/" + str(len(self.server.requests))
                )
                self.server.routes[
                    request.request_url.removeprefix(self.server.origin)
                ] = [
                    resources_test.Reply(headers=(("Last-Modified", date),)),
                    resources_test.Reply(
                        status=304, body=b"", headers=(("Last-Modified", date),)
                    ),
                ]
                old = self.store.fetch(request, policy=self.policy)
                new = self.store.refresh(request, policy=self.policy)
                self.assertNotIn("if-none-match", self.sent())
                self.assertEqual(self.sent()["if-modified-since"], date)
                self.assertEqual(new.sha256, old.sha256)

    def test_changed_200_preserves_history_and_resets_validation_time(self):
        old = self.seed()
        validated = self.refresh()
        new = self.refresh(
            resources_test.Reply(body=b"New story.", headers=(("ETag", '"v2"'),))
        )
        self.assertNotEqual(new.sha256, old.sha256)
        self.assertEqual(new.receipt.status, 200)
        self.assertIsNone(new.receipt.validated_at)
        self.assertEqual(new.receipt.previous_receipt_sha256, validated.receipt_sha256)
        self.assertNotEqual(new.receipt.retrieved_at, old.receipt.retrieved_at)
        self.assertEqual(old.path.read_bytes(), b"A story.")
        self.assertTrue(
            self.evidence(old).is_file() and self.evidence(validated).is_file()
        )
        self.assert_current(new)
        self.assertEqual(resources.decode_text(old).text, "A story.")

    def test_missing_and_malformed_validators_use_unconditional_get(self):
        for headers in (
            (),
            (("ETag", "*"),),
            (("ETag", '"one", "two"'),),
            (("ETag", '"bad\x7f"'),),
            (("Last-Modified", "yesterday"),),
            (("Last-Modified", "Foo, 21 Oct 2015 07:28:00 GMT"),),
        ):
            with self.subTest(headers=headers):
                path = "/case" + str(len(self.server.requests))
                request = resources.SourceRequest.from_url(self.server.origin + path)
                self.server.routes[path] = [
                    resources_test.Reply(headers=headers),
                    resources_test.Reply(body=b"replacement"),
                ]
                self.store.fetch(request, policy=self.policy)
                plan = self.store.plan(request, policy=self.policy, refresh=True)
                self.assertIn("unconditional", plan.reason)
                refreshed = self.store.refresh(request, policy=self.policy)
                self.assertNotIn("if-none-match", self.sent())
                self.assertNotIn("if-modified-since", self.sent())
                self.assertEqual(refreshed.path.read_bytes(), b"replacement")

    def test_offline_denial_and_plans_have_no_network_or_writes(self):
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            self.assertEqual(
                self.store.plan(self.request, refresh=True).action, "blocked"
            )
            self.assertEqual(
                self.store.plan(self.request, policy=self.policy, refresh=True).action,
                "download",
            )
            with self.assertRaises(resources.ResourcePolicyError):
                self.store.refresh(self.request)
            self.assertFalse(self.cache_dir.exists())
        old = self.seed()
        before = {p: p.stat().st_mtime_ns for p in self.cache_dir.rglob("*")}
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            self.assertEqual(self.store.plan(self.request, refresh=True).artifact, old)
            for policy in (
                resources.NetworkPolicy(),
                dataclasses.replace(self.policy, allowed_origins=()),
            ):
                with self.assertRaises(resources.ResourcePolicyError):
                    self.store.refresh(self.request, policy=policy)
            self.assertEqual(
                self.store.plan(self.request, policy=self.policy, refresh=True).action,
                "refresh",
            )
            self.assert_current(old)
            with self.assertRaises(resources.ResourceInputError):
                self.store.plan(self.request, refresh=1)
        self.assertEqual(
            before, {p: p.stat().st_mtime_ns for p in self.cache_dir.rglob("*")}
        )

    def test_cold_refresh_downloads_and_unsolicited_304_fails(self):
        self.server.routes["/book"] = [
            resources_test.Reply(status=304, body=b"", headers=(("ETag", 'W/"v1"'),))
        ]
        with self.assertRaises(resources.ResourceTransportError):
            self.store.refresh(self.request, policy=self.policy)
        self.assertIsNone(self.store.plan(self.request).artifact)
        new = self.refresh(resources_test.Reply(body=b"cold download"))
        self.assertIsNone(new.receipt.previous_receipt_sha256)
        self.assertNotIn("if-none-match", self.sent())
        with self.assertRaises(resources.ResourceTransportError) as caught:
            self.refresh()
        self.assertEqual(caught.exception.code, "unexpected_304")
        self.assert_current(new)

    def test_contradictory_304_headers_are_refused_without_replacement(self):
        old = self.seed(headers=(("ETag", '"v1"'), ("Content-Type", "text/plain")))
        for headers, code in (
            ((("ETag", '"v2"'),), "validator_mismatch"),
            ((("ETag", "*"),), "validator_mismatch"),
            ((("ETag", '"v1"'), ("ETag", '"v1"')), "ambiguous_headers"),
            ((("ETag", '"v1"'), ("Last-Modified", "bad")), "validator_mismatch"),
            (
                (("ETag", '"v1"'), ("Content-Type", "text/html")),
                "representation_mismatch",
            ),
            (
                (("ETag", '"v1"'), ("Content-Encoding", "gzip")),
                "representation_mismatch",
            ),
        ):
            with (
                self.subTest(headers=headers),
                self.assertRaises(resources.ResourceTransportError) as caught,
            ):
                self.refresh(
                    resources_test.Reply(status=304, body=b"", headers=headers)
                )
            self.assertEqual(caught.exception.code, code)
            self.assert_current(old)
        self.assertEqual(len(self.server.requests), 7)

    def test_missing_returned_validator_cannot_select_cached_response(self):
        old = self.seed()
        for headers in ((), (("Last-Modified", _DATE),)):
            with (
                self.subTest(headers=headers),
                self.assertRaises(resources.ResourceTransportError) as caught,
            ):
                self.refresh(
                    resources_test.Reply(status=304, body=b"", headers=headers)
                )
            self.assertEqual(caught.exception.code, "validator_mismatch")
            self.assert_current(old)
        # Last-Modified-only candidates also need a returned matching validator.
        path = "/date"
        request = resources.SourceRequest.from_url(self.server.origin + path)
        self.server.routes[path] = [
            resources_test.Reply(headers=(("Last-Modified", _DATE),)),
            resources_test.Reply(status=304, body=b""),
        ]
        date_old = self.store.fetch(request, policy=self.policy)
        with self.assertRaises(resources.ResourceTransportError):
            self.store.refresh(request, policy=self.policy)
        self.assertEqual(self.store.fetch(request), date_old)

    def test_equivalent_last_modified_wire_forms_compare_as_utc_instants(self):
        old = self.seed(headers=(("Last-Modified", "Wed Oct 21 07:28:00 2015"),))
        new = self.refresh(
            resources_test.Reply(
                status=304, body=b"", headers=(("Last-Modified", _DATE),)
            )
        )
        self.assertEqual(new.sha256, old.sha256)
        self.assertEqual(dict(new.receipt.headers)["last-modified"], _DATE)

    def test_last_modified_conflict_and_unmatched_strong_validator_fail(self):
        old = self.seed(headers=(("Last-Modified", _DATE),))
        for headers in (
            (("Last-Modified", "Thu, 22 Oct 2015 07:28:00 GMT"),),
            (("ETag", '"new"'),),
        ):
            with (
                self.subTest(headers=headers),
                self.assertRaises(resources.ResourceTransportError),
            ):
                self.refresh(
                    resources_test.Reply(status=304, body=b"", headers=headers)
                )
            self.assert_current(old)

    def test_redirect_validators_are_bound_to_final_url_not_origin_or_alias(self):
        other = resources_test.Server()
        self.addCleanup(other.close)
        policy = dataclasses.replace(
            self.policy, allowed_origins=(self.server.origin, other.origin)
        )
        self.server.routes["/book"] = [
            resources_test.Reply(
                status=302, headers=(("Location", other.origin + "/target"),)
            )
        ]
        other.routes["/target"] = [
            resources_test.Reply(headers=(("ETag", '"target"'),)),
            resources_test.Reply(
                status=304, body=b"", headers=(("ETag", 'W/"target"'),)
            ),
        ]
        old = self.store.fetch(self.request, policy=policy)
        result = self.store.refresh(self.request, policy=policy)
        self.assertNotIn("if-none-match", self.sent())
        self.assertEqual(self.sent(other)["if-none-match"], '"target"')
        self.assertEqual(result.sha256, old.sha256)
        # The formerly final URL now redirects, so its validator must be stripped
        # even when the new target is on the same origin.
        other.routes["/target"] = [
            resources_test.Reply(status=302, headers=(("Location", "/new"),))
        ]
        other.routes["/new"] = [resources_test.Reply(body=b"new location")]
        replacement = self.store.refresh(self.request, policy=policy)
        self.assertEqual(self.sent(other, -2)["if-none-match"], 'W/"target"')
        self.assertNotIn("if-none-match", self.sent(other))
        self.assertEqual(replacement.path.read_bytes(), b"new location")

    def test_304_on_redirect_alias_does_not_match_cached_final_resource(self):
        self.server.routes["/book"] = [
            resources_test.Reply(status=302, headers=(("Location", "/final"),))
        ]
        self.server.routes["/final"] = [
            resources_test.Reply(headers=(("ETag", '"final"'),))
        ]
        old = self.store.fetch(self.request, policy=self.policy)
        with self.assertRaises(resources.ResourceTransportError) as caught:
            self.refresh()
        self.assertEqual(caught.exception.code, "unexpected_304")
        self.assert_current(old)
        self.assertNotIn("if-none-match", self.sent())

    def test_network_failures_leave_old_entry_and_honor_retry_budget(self):
        old = self.seed()
        before = len(self.server.requests)
        with self.assertRaises(resources.ResourceTransportError):
            self.refresh(resources_test.Reply(status=503), max_retries=1)
        self.assertEqual(len(self.server.requests), before + 2)
        self.assert_current(old)
        self.server.routes["/book"] = [
            resources_test.Reply(status=503),
            resources_test.Reply(status=304, body=b"", headers=(("ETag", 'W/"v1"'),)),
        ]
        result = self.store.refresh(self.request, policy=self.policy)
        self.assertEqual(result.sha256, old.sha256)
        for index in (-1, -2):
            self.assertEqual(self.sent(index=index)["if-none-match"], '"v1"')

    def test_corrupt_cached_body_is_never_used_for_a_conditional_request(self):
        old = self.seed()
        old.path.write_bytes(b"tampering")
        with self.assertRaises(resources.ResourceIntegrityError):
            self.refresh()
        self.assertEqual(len(self.server.requests), 1)

    def test_body_is_reverified_after_304_before_receipt_publication(self):
        old = self.seed()
        response = resources_test.MemoryResponse(
            status=304, body=b"", headers=(("ETag", 'W/"v1"'),)
        )
        client = mock.Mock()

        def mutate_during_request(*args, **kwargs):
            old.path.write_bytes(b"corrupt while waiting")
            return response

        client.open.side_effect = mutate_during_request
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            with self.assertRaises(resources.ResourceIntegrityError):
                self.refresh()
        reference = json.loads(
            (
                self.cache_dir
                / "gettenberg/resources/refs"
                / (self.request.key + ".json")
            ).read_text()
        )
        self.assertEqual(reference["receipt"], old.receipt_sha256)

    def test_publication_faults_preserve_old_reference_before_replace(self):
        old = self.seed()
        atomic, immutable = _lifecycle_io.atomic_json, _resource_io.Cache._immutable
        for status in (200, 304):
            for stage in ("receipt", "reference"):

                def fail_ref(path, value):
                    if stage == "reference" and path.parent.name == "refs":
                        raise OSError("injected reference failure")
                    return atomic(path, value)

                def fail_receipt(cache, temporary, target, expected, limit):
                    if stage == "receipt" and target.parent.name == "receipts":
                        raise OSError("injected receipt failure")
                    return immutable(cache, temporary, target, expected, limit)

                with (
                    self.subTest(status=status, stage=stage),
                    mock.patch.object(_lifecycle_io, "atomic_json", fail_ref),
                    mock.patch.object(_resource_io.Cache, "_immutable", fail_receipt),
                ):
                    with self.assertRaises(resources.ResourceIntegrityError):
                        self.refresh(
                            resources_test.Reply(
                                status=status,
                                body=b"changed" if status == 200 else b"",
                                headers=(("ETag", 'W/"v1"'),),
                            )
                        )
                self.assert_current(old)
        self.assertEqual(len(self.server.requests), 5)

    def test_post_replace_failure_reports_published_validation(self):
        old = self.seed()
        sync = _lifecycle_io.sync_directory
        reference = (
            self.cache_dir / "gettenberg/resources/refs" / (self.request.key + ".json")
        )

        def fail_sync(path):
            if (
                path.name == "refs"
                and json.loads(reference.read_text())["receipt"] != old.receipt_sha256
            ):
                raise OSError("injected durability failure after replace")
            return sync(path)

        with mock.patch.object(_lifecycle_io, "sync_directory", fail_sync):
            with self.assertRaises(resources.ResourcePublicationError) as caught:
                self.refresh()
        self.assertTrue(caught.exception.published)
        self.assertEqual(self.store.fetch(self.request).receipt.status, 304)

    def test_concurrent_refreshes_coalesce_after_actual_network_lock(self):
        old = self.seed()
        self.server.routes["/book"] = [
            resources_test.Reply(status=304, body=b"", headers=(("ETag", 'W/"v1"'),))
        ]
        barrier = threading.Barrier(2)
        plan = self.store.plan
        results, failures = [], []

        def synchronized_plan(*args, **kwargs):
            result = plan(*args, **kwargs)
            barrier.wait(3)
            return result

        def refresh():
            try:
                results.append(self.store.refresh(self.request, policy=self.policy))
            except Exception as exc:
                failures.append(exc)

        with mock.patch.object(self.store, "plan", synchronized_plan):
            threads = [threading.Thread(target=refresh, daemon=True) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(5)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(failures, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])
        self.assertNotEqual(results[0].receipt_sha256, old.receipt_sha256)
        self.assertEqual(len(self.server.requests), 2)

    def test_archive_validation_reuses_shared_bytes_without_catalog_mutation(self):
        request = resources.SourceRequest.from_url(
            self.request.request_url, kind="archive"
        )
        old = self.seed(request=request)
        stat = old.path.stat()
        self.server.routes["/book"] = [
            resources_test.Reply(status=304, body=b"", headers=(("ETag", 'W/"v1"'),))
        ]
        new = self.store.refresh(request, policy=self.policy)
        self.assertEqual(new.path, old.path)
        self.assertEqual(old.path.stat().st_ctime_ns, stat.st_ctime_ns)
        self.assertFalse((self.cache_dir / "gettenberg/active.json").exists())

    def test_schema1_receipt_hash_and_decoding_survive_refresh(self):
        old = self.seed()
        value = dataclasses.asdict(old.receipt)
        value["schema_version"] = 1
        del (
            value["validated_at"],
            value["previous_receipt_sha256"],
            value["validation_headers"],
        )
        payload = _resource_types.canonical_json(value)
        digest = hashlib.sha256(payload).hexdigest()
        root = self.cache_dir / "gettenberg/resources"
        (root / "receipts" / (digest + ".json")).write_bytes(payload)
        (root / "refs" / (self.request.key + ".json")).write_text(
            json.dumps({"schema_version": 1, "receipt": digest})
        )
        legacy = self.store.fetch(self.request)
        self.assertEqual(legacy.receipt_sha256, digest)
        self.assertEqual(resources.decode_text(legacy).text, "A story.")
        new = self.refresh()
        self.assertEqual(new.receipt.previous_receipt_sha256, digest)
        self.assertEqual(new.receipt.retrieved_at, legacy.receipt.retrieved_at)
        self.assertEqual(
            resources.decode_text(legacy).text, resources.decode_text(new).text
        )
        self.assertEqual(payload, (root / "receipts" / (digest + ".json")).read_bytes())

    def test_oversized_receipt_cannot_publish_unreachable_body_objects(self):
        # Each URL/header is individually allowed, but their receipt exceeds the
        # aggregate bound. Reject it before linking an otherwise complete body.
        origin = "https://example.org"
        policy = resources.NetworkPolicy(online=True, allowed_origins=(origin,))
        for kind in ("resource", "archive"):
            request = resources.SourceRequest.from_url(origin + "/start", kind=kind)
            for attempt in range(2):
                replies = [
                    resources_test.MemoryResponse(
                        status=302,
                        headers=(("Location", origin + "/" + str(i) + "x" * 8100),),
                    )
                    for i in range(4)
                ]
                replies.append(
                    resources_test.MemoryResponse(
                        body=f"unique {kind} {attempt}".encode(),
                        headers=tuple(
                            (name, "x" * 8192)
                            for name in (
                                "Content-Type",
                                "Content-Encoding",
                                "ETag",
                                "Last-Modified",
                            )
                        ),
                    )
                )
                client = mock.Mock()
                client.open.side_effect = replies
                with (
                    self.subTest(kind=kind, attempt=attempt),
                    mock.patch.object(
                        _resource_transport, "opener", return_value=client
                    ),
                ):
                    with self.assertRaises(resources.ResourceIntegrityError) as caught:
                        self.store.fetch(request, policy=policy)
                    self.assertEqual(caught.exception.code, "metadata_limit")
                    self.assertIsNone(self.store.plan(request).artifact)
                    self.assertEqual(
                        list(
                            (self.cache_dir / "gettenberg/resources/objects").iterdir()
                        ),
                        [],
                    )
                    self.assertEqual(
                        list(
                            (self.cache_dir / "gettenberg/archives").glob("*.tar.bz2")
                        ),
                        [],
                    )
                    self.assertEqual(
                        list((self.cache_dir / "gettenberg/resources/tmp").iterdir()),
                        [],
                    )

    def test_persisted_304_requires_actual_valid_response_validator(self):
        self.seed()
        good = self.refresh()
        original = json.loads(self.evidence(good).read_bytes())
        for headers in (
            [],
            [["content-type", "text/plain"]],
            [["etag", "*"]],
            [["last-modified", "bad"]],
        ):
            value = dict(original, validation_headers=headers)
            effective = dict(original["headers"])
            effective.update(headers)
            value["headers"] = [list(pair) for pair in effective.items()]
            payload = _resource_types.canonical_json(value)
            digest = hashlib.sha256(payload).hexdigest()
            root = self.cache_dir / "gettenberg/resources"
            (root / "receipts" / (digest + ".json")).write_bytes(payload)
            (root / "refs" / (self.request.key + ".json")).write_text(
                json.dumps({"schema_version": 1, "receipt": digest})
            )
            with (
                self.subTest(headers=headers),
                self.assertRaises(resources.ResourceIntegrityError),
            ):
                self.store.fetch(self.request)

    def test_invalid_validation_schema_fails_even_with_matching_receipt_hash(self):
        self.seed()
        good = self.refresh()
        original = json.loads(self.evidence(good).read_bytes())
        for patch in (
            {"validated_at": None},
            {"validated_at": "2026-10-15"},
            {"previous_receipt_sha256": None},
            {"previous_receipt_sha256": "bad"},
            {"schema_version": 1},
            {"status": 200},
        ):
            with self.subTest(patch=patch):
                value = dict(original, **patch)
                payload = _resource_types.canonical_json(value)
                digest = hashlib.sha256(payload).hexdigest()
                root = self.cache_dir / "gettenberg/resources"
                (root / "receipts" / (digest + ".json")).write_bytes(payload)
                (root / "refs" / (self.request.key + ".json")).write_text(
                    json.dumps({"schema_version": 1, "receipt": digest})
                )
                with self.assertRaises(resources.ResourceIntegrityError):
                    self.store.fetch(self.request)


if __name__ == "__main__":
    unittest.main()
