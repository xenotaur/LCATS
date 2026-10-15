"""Offline HTTP-boundary and real-filesystem tests for original-byte acquisition.

The tiny loopback server owns all network fixtures. A virtual clock keeps retry
and pacing scenarios deterministic; separate real-clock/process tests exercise
actual serialization. No Gutenberg or external service is contacted.
"""

import dataclasses
import datetime
import email.message
import hashlib
import http.server
import io
import json
import os
import pathlib
import re
import socket
import socketserver
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from urllib import error

from lcats.gettenberg import _lifecycle_io
from lcats.gettenberg import _resource_io
from lcats.gettenberg import _resource_transport
from lcats.gettenberg import resources
from lcats.utils import capture


class Clock:
    """Advance only on requested sleeps, independently of the HTTP server clock."""

    def __init__(self):
        self.now = time.time()
        self.elapsed = 0.0
        self.sleeps = []

    def time(self):
        return self.now + self.elapsed

    def monotonic(self):
        return self.elapsed

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.elapsed += seconds


@dataclasses.dataclass
class Reply:
    """A small authored response; None length exercises an EOF-delimited stream."""

    body: bytes = b"original\x00bytes\xff"
    status: int = 200
    headers: tuple = ()
    length: bool = True
    pause: float = 0


class Server:
    """Local real HTTP fixture with per-path response queues and request evidence."""

    def __init__(self):
        owner = self
        self.routes = {}
        self.requests = []
        self.guard = threading.Lock()

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def do_GET(self):
                with owner.guard:
                    owner.requests.append(
                        (self.path, dict(self.headers), time.monotonic())
                    )
                    replies = owner.routes.get(self.path, [Reply(status=404)])
                    reply = replies.pop(0) if len(replies) > 1 else replies[0]
                self.send_response(reply.status)
                if reply.length and not any(
                    key.lower() == "content-length" for key, _ in reply.headers
                ):
                    self.send_header("Content-Length", str(len(reply.body)))
                for key, value in reply.headers:
                    self.send_header(key, value)
                self.end_headers()
                if reply.pause:
                    time.sleep(reply.pause)
                try:
                    self.wfile.write(reply.body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.01},
            daemon=True,
        )
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class MemoryResponse(io.BytesIO):
    """Transport-boundary fixture for HTTPS cases without a test CA dependency."""

    def __init__(self, status=200, body=b"bytes", headers=()):
        super().__init__(body)
        self.status = status
        self.headers = email.message.Message()
        self.headers["Content-Length"] = str(len(body))
        for key, value in headers:
            self.headers[key] = value


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = pathlib.Path(self.temp.name).resolve()
        self.cache_dir = self.directory / "new" / "cache"
        self.store = resources.ResourceStore(self.cache_dir)
        self.server = Server()
        self.addCleanup(self.server.close)
        self.clock = Clock()
        self.clock_patch = mock.patch.object(_resource_transport, "time", self.clock)
        self.clock_patch.start()
        self.addCleanup(self.clock_patch.stop)
        self.policy = resources.NetworkPolicy(
            online=True, allowed_origins=(self.server.origin,)
        )

    def request(self, path="/book", **kwargs):
        return resources.SourceRequest.from_url(self.server.origin + path, **kwargs)

    def fetch(self, path="/book", **kwargs):
        return self.store.fetch(
            self.request(path), policy=dataclasses.replace(self.policy, **kwargs)
        )

    def seed(self, reply=None):
        self.server.routes["/book"] = [reply or Reply()]
        return self.fetch()

    def test_constructor_plan_offline_miss_and_denied_origin_have_no_side_effects(self):
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ):
            self.assertEqual(
                self.store.plan(self.request()).reason, "offline cache miss"
            )
            self.assertEqual(
                self.store.plan(self.request(), policy=self.policy).action, "download"
            )
            denied = dataclasses.replace(self.policy, allowed_origins=())
            self.assertEqual(
                self.store.plan(self.request(), policy=denied).reason,
                "origin not permitted",
            )
            for policy in (resources.NetworkPolicy(), denied):
                with self.assertRaises(resources.ResourcePolicyError):
                    self.store.fetch(self.request(), policy=policy)
        self.assertFalse(self.cache_dir.exists())
        self.assertEqual(self.clock.sleeps, [])

    def test_binary_original_receipt_and_offline_reuse(self):
        body = b"\x1f\x8bnot-decoded\x00\xff"
        first = self.seed(
            Reply(
                body=body,
                headers=(
                    ("Content-Encoding", "gzip"),
                    ("Content-Type", "application/pdf"),
                    ("ETag", '"one"'),
                ),
            )
        )
        self.assertEqual(first.path.read_bytes(), body)
        self.assertEqual(
            (first.sha256, first.size), (hashlib.sha256(body).hexdigest(), len(body))
        )
        self.assertEqual(dict(first.receipt.headers)["content-encoding"], "gzip")
        before = {
            p: p.stat().st_mtime_ns for p in self.cache_dir.rglob("*") if p.is_file()
        }
        with mock.patch.object(
            _resource_transport, "opener", side_effect=AssertionError("no refresh")
        ):
            self.assertEqual(self.store.fetch(self.request()), first)
            self.assertEqual(self.fetch(), first)
            self.assertEqual(self.store.plan(self.request()).artifact, first)
        self.assertEqual(
            before,
            {p: p.stat().st_mtime_ns for p in self.cache_dir.rglob("*") if p.is_file()},
        )
        self.assertEqual(len(self.server.requests), 1)
        self.assertEqual(self.server.requests[0][1]["Accept-Encoding"], "identity")
        self.assertTrue(self.server.requests[0][1]["User-Agent"].startswith("LCATS"))

    def test_request_identity_preserves_query_and_escaping_and_separates_kind(self):
        base = resources.SourceRequest.from_url(
            "HTTPS://EXAMPLE.ORG:443/a%2Fb?b=2&a=1#fragment"
        )
        same = resources.SourceRequest(
            "urn:book:1", "https://example.org/a%2Fb?b=2&a=1"
        )
        self.assertEqual(base.key, same.key)
        for url in (
            "https://example.org/a/b?b=2&a=1",
            "https://example.org/a%2Fb?a=1&b=2",
        ):
            self.assertNotEqual(base.key, resources.SourceRequest.from_url(url).key)
        self.assertNotEqual(base.key, dataclasses.replace(base, kind="archive").key)
        self.assertEqual(
            base.source_uri, "HTTPS://EXAMPLE.ORG:443/a%2Fb?b=2&a=1#fragment"
        )

    def test_invalid_urls_rejected_before_network(self):
        for url in (
            "file:///tmp/data",
            "https://u:p@example.org/x",
            "https://example.org:bad/",
            "https://example.org:0/",
            "https://example.org:/",
            "https://example.org/%xx",
            "https://example.org/a b",
            "https://example.org/a\n",
            "https://例.org/",
            "https://example.org\\evil",
            "//example.org/x",
        ):
            with self.subTest(url=url), self.assertRaises(resources.ResourceInputError):
                resources.SourceRequest.from_url(url)
        self.assertFalse(self.cache_dir.exists())

    def test_invalid_policy_values_are_not_silently_coerced(self):
        for kwargs in (
            {"online": 1},
            {"max_retries": True},
            {"max_redirects": -1},
            {"max_resource_bytes": 0},
            {"io_timeout": float("inf")},
            {"operation_seconds": float("nan")},
            {"min_interval": 1},
            {"lock_timeout": 61},
            {"allowed_origins": ["https://example.org"]},
            {"allowed_origins": ("https://example.org/path",)},
        ):
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaises(resources.ResourceInputError),
            ):
                resources.NetworkPolicy(**kwargs)

    def test_eof_delimited_stream_is_bounded(self):
        self.server.routes["/book"] = [Reply(body=b"a" * 100, length=False)]
        with self.assertRaises(resources.ResourceTransportError) as caught:
            self.fetch(max_resource_bytes=32)
        self.assertEqual(caught.exception.code, "size_limit")
        self.assertEqual(self.store.plan(self.request()).action, "blocked")
        self.assertEqual(
            list((self.cache_dir / "gettenberg/resources/tmp").iterdir()), []
        )

    def test_advertised_oversize_and_truncated_length_fail_without_cache_hit(self):
        for header, code in (
            ("1000000", "size_limit"),
            ("100", "truncated_body"),
            ("bad", "content_length"),
        ):
            with self.subTest(header=header):
                self.server.routes["/" + header] = [
                    Reply(body=b"abc", headers=(("Content-Length", header),))
                ]
                with self.assertRaises(resources.ResourceTransportError) as caught:
                    self.fetch("/" + header, max_resource_bytes=1000)
                self.assertEqual(caught.exception.code, code)
                self.assertIsNone(self.store.plan(self.request("/" + header)).artifact)

    def test_terminal_http_statuses_never_try_other_routes(self):
        for status in (401, 403, 404, 410, 304, 206):
            with self.subTest(status=status):
                path = "/" + str(status)
                self.server.routes[path] = [Reply(status=status)]
                before = len(self.server.requests)
                with self.assertRaises(resources.ResourceTransportError):
                    self.fetch(path)
                self.assertEqual(len(self.server.requests), before + 1)

    def test_retry_budget_and_success(self):
        self.server.routes["/book"] = [
            Reply(status=503),
            Reply(status=500),
            Reply(body=b"ok"),
        ]
        self.assertEqual(self.fetch().path.read_bytes(), b"ok")
        self.assertEqual(len(self.server.requests), 3)
        self.assertEqual(self.clock.sleeps, [2.0, 4.0])

    def test_exhausted_retries_remain_a_miss(self):
        self.server.routes["/book"] = [Reply(status=503)]
        with self.assertRaises(resources.ResourceTransportError):
            self.fetch(max_retries=1)
        self.assertEqual(len(self.server.requests), 2)
        self.assertIsNone(self.store.plan(self.request()).artifact)

    def test_retry_after_delay_persists_across_store_instances(self):
        self.server.routes["/book"] = [
            Reply(status=429, headers=(("Retry-After", "120"),)),
            Reply(),
        ]
        with self.assertRaises(resources.ResourceDeferredError) as caught:
            self.fetch(operation_seconds=10)
        self.assertGreaterEqual(
            caught.exception.next_eligible_at, self.clock.time() + 119
        )
        second = resources.ResourceStore(self.cache_dir)
        with self.assertRaises(resources.ResourceDeferredError):
            second.fetch(
                self.request(),
                policy=dataclasses.replace(self.policy, operation_seconds=10),
            )
        self.assertEqual(len(self.server.requests), 1)
        self.assertEqual(self.clock.sleeps, [])
        self.clock.sleep(120)
        self.assertIsNotNone(second.fetch(self.request(), policy=self.policy))

    def test_retry_after_http_date_and_malformed_fallback(self):
        from email import utils

        date = utils.formatdate(self.clock.time() + 30, usegmt=True)
        self.server.routes["/book"] = [
            Reply(status=503, headers=(("Retry-After", date),)),
            Reply(),
        ]
        self.fetch()
        self.assertTrue(29 <= self.clock.sleeps[0] <= 30)
        self.server.routes["/other"] = [
            Reply(status=503, headers=(("Retry-After", "nonsense"),)),
            Reply(),
        ]
        self.fetch("/other")
        self.assertEqual(self.clock.sleeps[-1], 2)

    def test_relative_redirect_preserves_route_and_raw_bytes(self):
        self.server.routes["/book"] = [
            Reply(status=302, headers=(("Location", "target?x=1"),))
        ]
        self.server.routes["/target?x=1"] = [Reply(body=b"target")]
        artifact = self.fetch()
        self.assertEqual(
            artifact.receipt.redirects, (self.server.origin + "/target?x=1",)
        )
        self.assertEqual(artifact.receipt.final_url, artifact.receipt.redirects[-1])
        self.assertEqual(artifact.receipt.request_url, self.request().request_url)
        self.assertEqual(self.clock.sleeps, [2])

    def test_cross_origin_redirect_needs_explicit_permission(self):
        other = Server()
        self.addCleanup(other.close)
        other.routes["/target"] = [Reply()]
        self.server.routes["/book"] = [
            Reply(status=302, headers=(("Location", other.origin + "/target"),))
        ]
        with self.assertRaises(resources.ResourcePolicyError):
            self.fetch()
        self.assertEqual(other.requests, [])
        artifact = self.fetch(allowed_origins=(self.server.origin, other.origin))
        self.assertEqual(artifact.receipt.final_url, other.origin + "/target")

    def test_redirect_retry_after_delays_new_origin(self):
        other = Server()
        self.addCleanup(other.close)
        self.server.routes["/book"] = [
            Reply(
                status=302,
                headers=(("Location", other.origin + "/target"), ("Retry-After", "20")),
            )
        ]
        other.routes["/target"] = [Reply()]
        self.fetch(allowed_origins=(self.server.origin, other.origin))
        self.assertEqual(self.clock.sleeps, [20])

    def test_redirect_loop_hop_limit_and_bad_location(self):
        self.server.routes["/book"] = [
            Reply(status=302, headers=(("Location", "/book"),))
        ]
        with self.assertRaises(resources.ResourceTransportError):
            self.fetch()
        self.server.routes["/book"] = [
            Reply(status=302, headers=(("Location", "/target"),))
        ]
        with self.assertRaises(resources.ResourceTransportError):
            self.fetch(max_redirects=0)
        self.server.routes["/book"] = [Reply(status=302)]
        with self.assertRaises(resources.ResourceTransportError):
            self.fetch()
        self.assertEqual(len(self.server.requests), 3)

    def test_https_downgrade_and_tls_errors_are_terminal(self):
        source = resources.SourceRequest.from_url("https://example.org/book")
        policy = resources.NetworkPolicy(
            online=True, allowed_origins=("https://example.org", "http://example.org")
        )
        client = mock.Mock()
        client.open.return_value = MemoryResponse(
            302, headers=(("Location", "http://example.org/book"),)
        )
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            with self.assertRaises(resources.ResourcePolicyError):
                self.store.fetch(source, policy=policy)
        self.assertEqual(client.open.call_count, 1)
        client.reset_mock()
        client.open.side_effect = error.URLError(
            ssl.SSLCertVerificationError("bad certificate")
        )
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            with self.assertRaises(resources.ResourceTransportError) as caught:
                self.store.fetch(source, policy=policy)
        self.assertEqual(caught.exception.code, "tls")
        self.assertEqual(client.open.call_count, 1)

    def test_environment_proxies_are_not_used(self):
        self.server.routes["/book"] = [Reply()]
        with mock.patch.dict(
            os.environ,
            {
                "http_proxy": "http://127.0.0.1:1",
                "HTTP_PROXY": "http://127.0.0.1:1",
                "no_proxy": "",
                "NO_PROXY": "",
            },
        ):
            self.fetch()
        self.assertEqual(len(self.server.requests), 1)

    def test_corrupt_body_is_not_a_cache_miss_or_implicit_repair(self):
        artifact = self.seed()
        artifact.path.write_bytes(b"corrupt")
        for operation in (self.store.plan, self.store.fetch):
            with self.assertRaises(resources.ResourceIntegrityError):
                operation(self.request(), policy=self.policy)
        self.assertEqual(len(self.server.requests), 1)

    def test_corrupt_and_symlinked_receipts_fail_closed(self):
        artifact = self.seed()
        path = (
            self.cache_dir
            / "gettenberg/resources/receipts"
            / (artifact.receipt_sha256 + ".json")
        )
        original = path.read_bytes()
        path.write_bytes(b"{}")
        with self.assertRaises(resources.ResourceIntegrityError):
            self.fetch()
        path.unlink()
        target = self.directory / "receipt"
        target.write_bytes(original)
        path.symlink_to(target)
        with self.assertRaises(resources.ResourceIntegrityError):
            self.fetch()
        self.assertEqual(len(self.server.requests), 1)

    def test_managed_directory_symlinks_are_rejected_without_network(self):
        self.cache_dir.mkdir(parents=True)
        (self.cache_dir / "gettenberg").symlink_to(
            self.directory, target_is_directory=True
        )
        with self.assertRaises(resources.ResourceIntegrityError):
            self.fetch()
        self.assertEqual(self.server.requests, [])

    def test_cache_hit_respects_new_smaller_byte_limit(self):
        self.seed()
        with self.assertRaises(resources.ResourceIntegrityError):
            self.fetch(max_resource_bytes=1)
        self.assertEqual(len(self.server.requests), 1)

    def test_archive_namespace_is_shared_but_not_implicitly_ingested(self):
        self.server.routes["/book"] = [Reply(body=b"archive bytes, not yet valid RDF")]
        result = self.store.fetch(self.request(kind="archive"), policy=self.policy)
        self.assertEqual(result.path.parent, self.cache_dir / "gettenberg/archives")
        self.assertEqual(result.path.name, result.sha256 + ".tar.bz2")
        self.assertFalse((self.cache_dir / "gettenberg/active.json").exists())
        self.assertIsNone(self.store.plan(self.request()).artifact)

    def test_reference_failure_leaves_no_partial_hit_and_valid_orphans_are_reusable(
        self,
    ):
        self.server.routes["/book"] = [Reply()]
        atomic = _lifecycle_io.atomic_json

        def fail_reference(path, value):
            if path.parent.name == "refs":
                raise OSError("simulated full disk")
            return atomic(path, value)

        with mock.patch.object(
            _lifecycle_io, "atomic_json", side_effect=fail_reference
        ):
            with self.assertRaises(resources.ResourceError):
                self.fetch()
        self.assertIsNone(self.store.plan(self.request()).artifact)
        self.assertEqual(
            len(list((self.cache_dir / "gettenberg/resources/objects").iterdir())), 1
        )
        self.assertIsNotNone(self.fetch())

    def test_post_reference_sync_failure_reports_publication_uncertainty(self):
        self.server.routes["/book"] = [Reply()]
        sync = _lifecycle_io.sync_directory

        def fail_after_publish(path):
            if path.name == "refs" and list(path.glob("*.json")):
                raise OSError("simulated durability failure")
            return sync(path)

        with mock.patch.object(
            _lifecycle_io, "sync_directory", side_effect=fail_after_publish
        ):
            with self.assertRaises(resources.ResourcePublicationError) as caught:
                self.fetch()
        self.assertTrue(caught.exception.published)
        self.assertIsNotNone(self.store.fetch(self.request()))

    def test_invalid_pacing_evidence_fails_without_get(self):
        self.seed()
        path = self.cache_dir / "gettenberg/resources/pacing.json"
        path.write_text('{"version":1,"next_start":-1,"origins":{}}')
        with self.assertRaises(resources.ResourceIntegrityError):
            self.fetch("/other")
        self.assertEqual(len(self.server.requests), 1)

    def test_stalled_read_is_limited_by_io_timeout(self):
        self.server.routes["/book"] = [Reply(pause=0.2)]
        started = time.monotonic()
        with self.assertRaises(resources.ResourceTransportError):
            self.fetch(io_timeout=0.03, max_retries=0)
        self.assertLess(time.monotonic() - started, 1)
        self.assertIsNone(self.store.plan(self.request()).artifact)

    def test_cooperative_deadline_stops_after_a_read_before_publication(self):
        client = mock.Mock()
        response = MemoryResponse()
        read = response.read1

        def slow_read(size):
            self.clock.elapsed += 5
            return read(size)

        response.read1 = slow_read
        client.open.return_value = response
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            with self.assertRaises(resources.ResourceTransportError) as caught:
                self.fetch(operation_seconds=4)
        self.assertEqual(caught.exception.code, "deadline")
        self.assertIsNone(self.store.plan(self.request()).artifact)

    def test_cache_environment_is_resolved_at_construction(self):
        with mock.patch.dict(os.environ, {"LCATS_CACHE_DIR": str(self.cache_dir)}):
            store = resources.ResourceStore()
        self.server.routes["/book"] = [Reply()]
        self.assertEqual(
            store.fetch(self.request(), policy=self.policy),
            self.store.fetch(self.request()),
        )

    def test_hash_valid_but_semantically_invalid_receipt_is_rejected(self):
        artifact = self.seed()
        root = self.cache_dir / "gettenberg/resources"
        original_path = root / "receipts" / (artifact.receipt_sha256 + ".json")
        original = json.loads(original_path.read_text())
        for patch in (
            {"schema_version": True},
            {"status": 206},
            {"size": True},
            {"retrieved_at": "2026-01-01"},
            {"redirects": ["file:///tmp/x"]},
            {"headers": [["authorization", "secret"]]},
            {"kind": "archive"},
        ):
            with self.subTest(patch=patch):
                value = dict(original, **patch)
                payload = json.dumps(value).encode()
                digest = hashlib.sha256(payload).hexdigest()
                (root / "receipts" / (digest + ".json")).write_bytes(payload)
                (root / "refs" / (self.request().key + ".json")).write_text(
                    json.dumps({"schema_version": 1, "receipt": digest})
                )
                with self.assertRaises(resources.ResourceIntegrityError):
                    self.fetch()
        self.assertEqual(len(self.server.requests), 1)

    def test_immutable_object_corruption_cannot_be_overwritten_by_a_new_request(self):
        artifact = self.seed()
        artifact.path.write_bytes(b"corruption")
        self.server.routes["/alias"] = [Reply()]
        with self.assertRaises(resources.ResourceIntegrityError) as caught:
            self.fetch("/alias")
        self.assertEqual(caught.exception.code, "object_collision")
        self.assertEqual(artifact.path.read_bytes(), b"corruption")
        self.assertIsNone(self.store.plan(self.request("/alias")).artifact)

    def test_symlinked_body_and_reference_are_not_followed(self):
        artifact = self.seed()
        original = artifact.path.read_bytes()
        target = self.directory / "external-body"
        target.write_bytes(original)
        artifact.path.unlink()
        artifact.path.symlink_to(target)
        with self.assertRaises(resources.ResourceIntegrityError):
            self.fetch()
        artifact.path.unlink()
        artifact.path.write_bytes(original)
        ref = (
            self.cache_dir
            / "gettenberg/resources/refs"
            / (self.request().key + ".json")
        )
        target = self.directory / "external-reference"
        target.write_bytes(ref.read_bytes())
        ref.unlink()
        ref.symlink_to(target)
        with self.assertRaises(resources.ResourceIntegrityError):
            self.fetch()
        self.assertEqual(len(self.server.requests), 1)

    def test_long_selected_header_does_not_enter_cache(self):
        self.server.routes["/book"] = [Reply(headers=(("ETag", "x" * 8193),))]
        with self.assertRaises(resources.ResourceTransportError) as caught:
            self.fetch()
        self.assertEqual(caught.exception.code, "header_limit")
        self.assertIsNone(self.store.plan(self.request()).artifact)

    def test_duplicate_headers_are_not_arbitrarily_selected(self):
        for name, values in (
            ("ETag", ("one", "two")),
            ("Retry-After", ("1", "100")),
            ("Content-Length", ("2", "3")),
        ):
            with self.subTest(name=name):
                self.server.routes["/" + name] = [
                    Reply(headers=tuple((name, value) for value in values))
                ]
                with self.assertRaises(resources.ResourceTransportError):
                    self.fetch("/" + name)
        self.assertEqual(len(self.server.requests), 3)

    def test_raw_redirect_control_characters_are_not_normalized_away(self):
        client = mock.Mock()
        client.open.return_value = MemoryResponse(
            302, headers=(("Location", "\x00https://example.org/evil"),)
        )
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            with self.assertRaises(resources.ResourceTransportError) as caught:
                self.fetch(allowed_origins=(self.server.origin, "https://example.org"))
        self.assertEqual(caught.exception.code, "redirect_location")
        self.assertEqual(client.open.call_count, 1)

    def test_timeout_retry_discards_partial_body_and_preserves_only_complete_bytes(
        self,
    ):
        class BrokenResponse(MemoryResponse):
            def read1(self, size=-1):
                if self.tell():
                    raise TimeoutError("read stalled")
                return super().read1(2)

        client = mock.Mock()
        client.open.side_effect = [
            BrokenResponse(body=b"first"),
            MemoryResponse(body=b"complete"),
        ]
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            artifact = self.fetch()
        self.assertEqual(artifact.path.read_bytes(), b"complete")
        self.assertEqual(client.open.call_count, 2)
        self.assertEqual(
            list((self.cache_dir / "gettenberg/resources/tmp").iterdir()), []
        )

    def test_connection_failure_budget_and_temporary_dns_retry(self):
        client = mock.Mock()
        client.open.side_effect = [
            error.URLError(socket.gaierror(socket.EAI_AGAIN, "temporary DNS")),
            MemoryResponse(),
        ]
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            self.fetch()
        self.assertEqual(client.open.call_count, 2)

    def test_socket_timeout_is_capped_by_remaining_operation_budget(self):
        client = mock.Mock()
        client.open.return_value = MemoryResponse()
        with mock.patch.object(_resource_transport, "opener", return_value=client):
            self.fetch(operation_seconds=0.5, io_timeout=30)
        self.assertLessEqual(client.open.call_args.kwargs["timeout"], 0.5)

    def test_zero_byte_body_is_a_valid_original(self):
        artifact = self.seed(Reply(body=b""))
        self.assertEqual(artifact.size, 0)
        self.assertEqual(self.store.fetch(self.request()), artifact)

    def test_cache_lock_wait_is_bounded_and_has_no_network_side_effect(self):
        self.seed()
        lock = self.cache_dir / "gettenberg/resources/network.lock"
        with _lifecycle_io.writer_lock(lock):
            with self.assertRaises(resources.ResourceLockError):
                self.fetch("/other", lock_timeout=0)
        self.assertEqual(len(self.server.requests), 1)

    def test_no_decode_or_catalog_dependency_on_import(self):
        # The public facade must not accidentally import the legacy gutenbergpy
        # wrapper or initialize a catalog through package-level convenience code.
        code = "from lcats.gettenberg import resources; import sys; assert 'gutenbergpy' not in sys.modules; assert 'lcats.gettenberg.lifecycle' not in sys.modules"
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_clock_jump_preserves_cooldown_and_does_not_stick_on_repeated_calls(self):
        self.server.routes["/book"] = [
            Reply(status=429, headers=(("Retry-After", "60"),)),
            Reply(),
        ]
        with self.assertRaises(resources.ResourceDeferredError):
            self.fetch(operation_seconds=5)
        self.clock.now += 3600  # Forward wall step must not erase the cooldown.
        with self.assertRaises(resources.ResourceDeferredError):
            self.fetch(operation_seconds=5)
        self.assertEqual(len(self.server.requests), 1)
        self.clock.sleep(60)
        self.assertIsNotNone(self.fetch())
        self.assertEqual(len(self.server.requests), 2)

    def test_small_wall_step_cannot_shorten_request_spacing(self):
        self.seed()
        self.clock.now += 1
        self.server.routes["/other"] = [Reply()]
        self.fetch("/other")
        self.assertGreaterEqual(self.clock.sleeps[-1], 2)

    def test_reboot_rebases_persisted_delay_once(self):
        self.clock.elapsed = 100
        self.seed()
        self.clock.now += 200
        self.clock.elapsed = 0  # New boot with a smaller monotonic clock.
        self.server.routes["/other"] = [Reply()]
        self.fetch("/other")
        self.assertEqual(self.clock.sleeps[-1], 2)

    def test_nonfinite_huge_time_limit_is_a_typed_input_error(self):
        with self.assertRaises(resources.ResourceInputError):
            resources.NetworkPolicy(io_timeout=10**400)

    def test_excessive_content_length_is_a_structured_failure(self):
        self.server.routes["/book"] = [Reply(headers=(("Content-Length", "9" * 5000),))]
        with self.assertRaises(resources.ResourceTransportError):
            self.fetch()
        self.assertEqual(len(self.server.requests), 1)

    def test_unrepresentable_pacing_timestamp_is_an_integrity_error(self):
        self.seed()
        path = self.cache_dir / "gettenberg/resources/pacing.json"
        value = json.loads(path.read_text())
        value["next_start"] = 10**1000
        path.write_text(json.dumps(value))
        with self.assertRaises(resources.ResourceIntegrityError):
            self.fetch("/other")

    def test_how_to_examples_execute_against_local_fixture(self):
        doc = (
            pathlib.Path(__file__).resolve().parents[2]
            / "docs/how-to/gettenberg-resources.md"
        )
        blocks = re.findall(r"```python\n(.*?)```", doc.read_text(), re.S)
        self.assertEqual(len(blocks), 3)
        self.server.routes["/story.txt"] = [Reply()]
        namespace = {}
        with capture.capture_output() as output:
            for block in blocks:
                code = block.replace("https://example.org", self.server.origin)
                code = code.replace('"cache"', repr(str(self.cache_dir)))
                exec(compile(code, str(doc), "exec"), namespace)
        self.assertIn("blocked offline cache miss", output.stdout.getvalue())
        self.assertEqual(namespace["artifact"].path.read_bytes(), Reply().body)
        self.assertEqual(len(self.server.requests), 1)

    def test_obsolete_http_date_retry_after_is_interpreted_in_utc(self):
        stamp = datetime.datetime.fromtimestamp(
            self.clock.time() + 60, datetime.timezone.utc
        )
        header = stamp.strftime("%a %b %d %H:%M:%S %Y")
        self.server.routes["/book"] = [
            Reply(status=429, headers=(("Retry-After", header),)),
            Reply(),
        ]
        with self.assertRaises(resources.ResourceDeferredError):
            self.fetch(operation_seconds=5)
        self.assertEqual(len(self.server.requests), 1)

    def test_transfer_framing_is_removed_or_explicitly_rejected(self):
        # Supported framing produces the original representation, not chunk lines.
        self.server.routes["/chunked"] = [
            Reply(
                body=b"3;extension=yes\r\nabc\r\n0\r\nX-Trailer: yes\r\n\r\n",
                headers=(("Transfer-Encoding", "chunked"),),
                length=False,
            )
        ]
        self.assertEqual(self.fetch("/chunked").path.read_bytes(), b"abc")
        cases = (
            (("Transfer-Encoding", "gzip, chunked"),),
            (("Transfer-Encoding", "gzip"),),
            (("Transfer-Encoding", "chunked"), ("Transfer-Encoding", "chunked")),
            (("Transfer-Encoding", "chunked"), ("Content-Length", "3")),
        )
        for index, headers in enumerate(cases):
            path = f"/unsupported-{index}"
            self.server.routes[path] = [
                Reply(body=b"3\r\nabc\r\n0\r\n\r\n", headers=headers, length=False)
            ]
            with (
                self.subTest(headers=headers),
                self.assertRaises(resources.ResourceTransportError) as caught,
            ):
                self.fetch(path)
            self.assertEqual(caught.exception.code, "transfer_encoding")
            self.assertIsNone(self.store.plan(self.request(path)).artifact)

    def test_pacing_sync_failure_does_not_claim_resource_publication(self):
        sync = _lifecycle_io.sync_directory

        def fail_pacing_sync(path):
            if path.name == "resources" and (path / "pacing.json").exists():
                raise OSError("injected pacing durability failure")
            return sync(path)

        with mock.patch.object(
            _lifecycle_io, "sync_directory", side_effect=fail_pacing_sync
        ):
            with self.assertRaises(resources.ResourceIntegrityError) as caught:
                self.fetch()
        self.assertFalse(hasattr(caught.exception, "published"))
        self.assertEqual(self.server.requests, [])
        self.assertIsNone(self.store.plan(self.request()).artifact)

    def test_platform_timeout_overflow_is_typed_without_retry(self):
        with self.assertRaises(resources.ResourceInputError) as caught:
            self.fetch(io_timeout=1e308, operation_seconds=1e308)
        self.assertEqual(caught.exception.code, "invalid_policy")
        self.assertEqual(self.server.requests, [])
        self.assertEqual(self.clock.sleeps, [])

    def test_pacing_capacity_preserves_new_and_old_cooldowns(self):
        path = self.directory / "pacing.json"
        pacing = _resource_transport.Pacing(path, 2)
        pacing.state["origins"] = {
            f"https://origin-{i}.example": self.clock.time() + 30 for i in range(256)
        }
        pacing.defer("https://new.example/book", 60)
        restored = _resource_transport.Pacing(path, 2)
        self.assertEqual(restored.state["origins"], {})
        for url in ("https://new.example/book", "https://origin-0.example/book"):
            with self.assertRaises(resources.ResourceDeferredError):
                restored.start(url, _resource_transport.Budget(5))
        self.assertLess(path.stat().st_size, 65536)

    def test_reader_can_verify_while_publisher_finishes_cleanup(self):
        # Pause a real publisher after the reference is visible. Let a reader
        # start hashing, finish publisher cleanup, then complete the reader's
        # stability check. No fake stat values hide a hard-link ctime change.
        reference_ready = threading.Event()
        hashing = threading.Event()
        publisher_done = threading.Event()
        original_publish = _resource_io.Cache.publish
        original_stable = _lifecycle_io._stable
        results = {}
        self.server.routes["/book"] = [Reply()]

        def publish(cache, *args):
            artifact = original_publish(cache, *args)
            reference_ready.set()
            if not hashing.wait(3):
                raise AssertionError("reader did not begin hashing")
            return artifact

        def stable(path, stream, before, **kwargs):
            if path.parent.name == "objects":
                hashing.set()
                if not publisher_done.wait(3):
                    raise AssertionError("publisher did not finish")
            return original_stable(path, stream, before, **kwargs)

        def acquire():
            try:
                results["publisher"] = self.fetch()
            except Exception as exc:  # Surface failures from the worker to unittest.
                results["error"] = exc
            finally:
                publisher_done.set()

        with (
            mock.patch.object(_resource_io.Cache, "publish", publish),
            mock.patch.object(_lifecycle_io, "_stable", stable),
        ):
            worker = threading.Thread(target=acquire, daemon=True)
            worker.start()
            try:
                self.assertTrue(reference_ready.wait(3), results)
                reader = self.store.fetch(self.request())
            finally:
                hashing.set()
                worker.join(3)
            self.assertFalse(worker.is_alive())
            self.assertNotIn("error", results)
            self.assertEqual(reader, results["publisher"])
        self.assertEqual(
            list((self.cache_dir / "gettenberg/resources/tmp").iterdir()), []
        )


class FramingDeadlineTests(unittest.TestCase):
    """Real socket trickles must not reset the overall operation deadline."""

    def test_deadline_bounds_headers_chunk_extensions_and_trailers(self):
        for mode in ("headers", "chunk-extension", "trailers"):
            with self.subTest(mode=mode):
                self.check_trickle(mode)

    def check_trickle(self, mode):
        stop = threading.Event()

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.recv(8192)
                prefixes = {
                    "headers": b"HTTP/1.1 200 OK\r\nX-Test: ",
                    "chunk-extension": b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n1;",
                    "trailers": b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n0\r\nX-Trailer: ",
                }
                try:
                    self.request.sendall(prefixes[mode])
                    # Two seconds of continuous progress would defeat a plain
                    # per-socket timeout. The operation must stop much sooner.
                    for _ in range(100):
                        self.request.sendall(b"x")
                        if stop.wait(0.02):
                            break
                except (BrokenPipeError, ConnectionResetError):
                    pass

        with (
            tempfile.TemporaryDirectory() as directory,
            socketserver.TCPServer(("127.0.0.1", 0), Handler) as server,
        ):
            worker = threading.Thread(
                target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
            )
            worker.start()
            origin = f"http://127.0.0.1:{server.server_address[1]}"
            policy = resources.NetworkPolicy(
                online=True,
                allowed_origins=(origin,),
                operation_seconds=0.2,
                io_timeout=0.1,
                max_retries=0,
            )
            store = resources.ResourceStore(directory)
            request = resources.SourceRequest.from_url(origin + "/book")
            started = time.monotonic()
            try:
                with self.assertRaises(resources.ResourceTransportError):
                    store.fetch(request, policy=policy)
                self.assertLess(time.monotonic() - started, 0.8)
                self.assertIsNone(store.plan(request).artifact)
            finally:
                stop.set()
                server.shutdown()
                worker.join(3)


class ProcessResourceTests(unittest.TestCase):
    """Real processes prove duplicate suppression without shared Python locks."""

    def test_two_processes_download_one_missing_resource(self):
        with tempfile.TemporaryDirectory() as directory:
            server = Server()
            self.addCleanup(server.close)
            server.routes["/book"] = [Reply(pause=0.15)]
            code = """from lcats.gettenberg import resources
import sys
store = resources.ResourceStore(sys.argv[1])
request = resources.SourceRequest.from_url(sys.argv[2] + '/book')
policy = resources.NetworkPolicy(online=True, allowed_origins=(sys.argv[2],))
print(store.fetch(request, policy=policy).sha256)
"""
            processes = [
                subprocess.Popen(
                    [sys.executable, "-c", code, directory, server.origin],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for _ in range(2)
            ]
            try:
                results = [p.communicate(timeout=15) for p in processes]
                self.assertEqual([p.returncode for p in processes], [0, 0], results)
                self.assertEqual(results[0][0], results[1][0])
                self.assertEqual(len(server.requests), 1)
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                        process.wait()

    def test_killed_lock_holder_does_not_leave_a_stale_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            server = Server()
            self.addCleanup(server.close)
            server.routes["/book"] = [Reply()]
            code = """from lcats.gettenberg import _resource_io, _lifecycle_io
import pathlib, sys, time
cache = _resource_io.Cache(sys.argv[1])
cache.directories(create=True)
with _lifecycle_io.writer_lock(cache.root / 'network.lock'):
    pathlib.Path(sys.argv[2]).write_text('locked')
    time.sleep(30)
"""
            marker = root / "locked"
            child = subprocess.Popen(
                [sys.executable, "-c", code, directory, str(marker)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                deadline = time.monotonic() + 5
                while (
                    not marker.exists()
                    and child.poll() is None
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.01)
                self.assertTrue(marker.exists(), "child did not acquire lock")
                child.kill()
                child.communicate(timeout=5)
                policy = resources.NetworkPolicy(
                    online=True, allowed_origins=(server.origin,), lock_timeout=0
                )
                result = resources.ResourceStore(directory).fetch(
                    resources.SourceRequest.from_url(server.origin + "/book"),
                    policy=policy,
                )
                self.assertEqual(result.path.read_bytes(), Reply().body)
                self.assertTrue((root / "gettenberg/resources/network.lock").is_file())
            finally:
                if child.poll() is None:
                    child.kill()
                    child.communicate(timeout=5)

    def test_real_request_spacing_across_fresh_store_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            server = Server()
            self.addCleanup(server.close)
            server.routes["/one"] = server.routes["/two"] = [Reply()]
            policy = resources.NetworkPolicy(
                online=True, allowed_origins=(server.origin,)
            )
            for path in ("/one", "/two"):
                resources.ResourceStore(directory).fetch(
                    resources.SourceRequest.from_url(server.origin + path),
                    policy=policy,
                )
            self.assertGreaterEqual(server.requests[1][2] - server.requests[0][2], 1.9)
