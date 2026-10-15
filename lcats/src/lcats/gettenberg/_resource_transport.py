"""Private bounded urllib transport with explicit redirects and persisted pacing."""

import datetime
import email.utils
import hashlib
import functools
import io
import http.client
import math
import os
import ssl
import socket
import time
from urllib import error
from urllib import parse
from urllib import request as urllib_request

from lcats.gettenberg import _lifecycle_io
from lcats.gettenberg import _resource_io
from lcats.gettenberg import _resource_types

_TRANSIENT = {408, 429, 500, 502, 503, 504}
_REDIRECTS = {301, 302, 303, 307, 308}
_CHUNK = 128 * 1024


class _Responses(urllib_request.HTTPErrorProcessor):
    """Return every status to our loop; urllib must not retry or redirect for us."""

    def http_response(self, request, response):
        return response

    https_response = http_response


class _DeadlineReader(io.RawIOBase):
    """Bound every socket read, including reads hidden inside HTTP framing.

    A timeout on a buffered readline alone resets whenever another byte arrives.
    Checking the shared monotonic deadline underneath the buffer also bounds
    trickling status lines, headers, chunk extensions, and trailers.
    """

    def __init__(self, raw, sock, budget, io_timeout):
        self.raw, self.sock = raw, sock
        self.budget, self.io_timeout = budget, io_timeout

    def readable(self):
        return True

    def readinto(self, buffer):
        self.sock.settimeout(min(self.io_timeout, self.budget.remaining()))
        size = self.raw.readinto(buffer)
        self.budget.remaining()
        return size

    def close(self):
        try:
            self.raw.close()
        finally:
            super().close()


class _ReadSocket:
    """Supply HTTPResponse's documented socket makefile interface."""

    def __init__(self, sock, budget, io_timeout):
        self.sock, self.budget, self.io_timeout = sock, budget, io_timeout

    def makefile(self, mode):
        return io.BufferedReader(
            _DeadlineReader(
                self.sock.makefile(mode, buffering=0),
                self.sock,
                self.budget,
                self.io_timeout,
            )
        )


class _DeadlineResponse(http.client.HTTPResponse):
    """Use the normal HTTP parser over a deadline-aware raw socket reader."""

    def __init__(self, sock, *args, budget, io_timeout, **kwargs):
        super().__init__(_ReadSocket(sock, budget, io_timeout), *args, **kwargs)


class _HTTP(urllib_request.HTTPHandler):
    """Install our response reader without changing connection semantics."""

    connection_type = http.client.HTTPConnection

    def __init__(self, budget, io_timeout):
        super().__init__()
        self.budget, self.io_timeout = budget, io_timeout

    def connection(self, *args, **kwargs):
        connection = self.connection_type(*args, **kwargs)
        connection.response_class = functools.partial(
            _DeadlineResponse, budget=self.budget, io_timeout=self.io_timeout
        )
        return connection

    def http_open(self, request):
        return self.do_open(self.connection, request)


class _HTTPS(urllib_request.HTTPSHandler):
    """Retain the standard verified TLS connection before wrapping reads."""

    connection_type = http.client.HTTPSConnection

    def __init__(self, budget, io_timeout):
        super().__init__()
        self.budget, self.io_timeout = budget, io_timeout

    connection = _HTTP.connection

    def https_open(self, request):
        return self.do_open(
            self.connection, request, context=ssl.create_default_context()
        )


def opener(budget, io_timeout):
    """Build an isolated TLS-verifying opener, ignoring environment proxies."""
    return urllib_request.build_opener(
        urllib_request.ProxyHandler({}),
        _HTTP(budget, io_timeout),
        _HTTPS(budget, io_timeout),
        _Responses(),
    )


class Budget:
    """Cooperative deadline; blocking DNS/OS operations are not hard-cancellable."""

    def __init__(self, seconds):
        self.deadline = time.monotonic() + seconds

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise _resource_types.ResourceTransportError(
                "deadline", "operation time budget exhausted"
            )
        return remaining

    def wait(self, delay, next_eligible):
        if delay >= self.remaining():
            raise _resource_types.ResourceDeferredError(
                "required delay exceeds operation budget", next_eligible
            )
        if delay > 0:
            time.sleep(delay)
        self.remaining()


class Pacing:
    """Atomic cooldown state, read/written only while the network lock is held.

    The lock transaction is deliberately separate from this committed JSON. A
    process killed during a response cannot roll back its recorded request start
    or the last observed Retry-After. All origins share conservative start spacing.
    """

    def __init__(self, path, interval):
        self.path = path
        self.interval = interval
        if path.exists() or path.is_symlink():
            self.state = _lifecycle_io.read_json(path)
        else:
            self.state = {
                "version": 1,
                "next_start": 0.0,
                "in_flight": False,
                "origins": {},
                "clock": {"wall": time.time(), "monotonic": time.monotonic()},
            }
        state = self.state
        valid = (
            set(state) == {"version", "next_start", "origins", "clock", "in_flight"}
            and type(state["version"]) is int
            and state["version"] == 1
            and type(state["in_flight"]) is bool
            and isinstance(state["origins"], dict)
            and len(state["origins"]) <= 256
        )
        if not valid:
            raise _resource_types.ResourceIntegrityError(
                "pacing_schema", "invalid pacing state"
            )
        if not isinstance(state["clock"], dict) or set(state["clock"]) != {
            "wall",
            "monotonic",
        }:
            raise _resource_types.ResourceIntegrityError(
                "pacing_schema", "invalid clock evidence"
            )
        for value in [
            state["next_start"],
            *state["origins"].values(),
            *state["clock"].values(),
        ]:
            try:
                valid_timestamp = (
                    type(value) in (int, float) and math.isfinite(value) and value >= 0
                )
            except OverflowError:
                valid_timestamp = False
            if not valid_timestamp:
                raise _resource_types.ResourceIntegrityError(
                    "pacing_schema", "invalid pacing timestamp"
                )
        for key in state["origins"]:
            try:
                valid_origin = _resource_types.origin(key) == key
            except _resource_types.ResourceInputError:
                valid_origin = False
            if not valid_origin:
                raise _resource_types.ResourceIntegrityError(
                    "pacing_schema", "invalid pacing origin"
                )

    def rebase_clock(self):
        """Conservatively preserve outstanding delays across clock steps/reboots.

        A shared monotonic clock protects normal same-boot coordination. When
        continuity is lost, elapsed downtime cannot be proved: reimpose at most
        the delay remaining at the last saved observation, also honoring a later
        wall deadline. The caller persists this once before waiting, avoiding a
        permanent restart/defer loop. Never sleep past the operation budget.
        """
        now, monotonic = time.time(), time.monotonic()
        old = self.state["clock"]
        elapsed = monotonic - old["monotonic"]
        changed = elapsed < 0 or abs((now - old["wall"]) - elapsed) > 5

        def remaining(deadline):
            monotonic_remaining = deadline - old["wall"] - (0 if changed else elapsed)
            return max(0.0, deadline - now, monotonic_remaining)

        self.state["next_start"] = now + remaining(self.state["next_start"])
        self.state["origins"] = {
            key: now + remaining(value) for key, value in self.state["origins"].items()
        }
        self.state["clock"] = {"wall": now, "monotonic": monotonic}
        return changed

    def save(self):
        self.rebase_clock()
        now = time.time()
        self.state["origins"] = {
            key: val for key, val in self.state["origins"].items() if val > now
        }
        if (
            len(self.state["origins"]) > 256
            or len(_resource_types.canonical_json(self.state)) > 65536
        ):
            # Preserve every outstanding cooldown without unbounded metadata.
            # At capacity, conservatively delay all origins until the latest
            # pending deadline, including the newly observed Retry-After.
            self.state["next_start"] = max(
                self.state["next_start"], *self.state["origins"].values()
            )
            self.state["origins"] = {}
        _lifecycle_io.atomic_json(self.path, self.state)

    def start(self, url, budget):
        if self.state["in_flight"]:
            # The previous holder died after recording intent. Dispatch could
            # have followed a slow fsync; its timestamp is unknown. Reestablish
            # a full conservative interval before another request.
            self.finish()
        if self.rebase_clock():
            self.save()
        now = time.time()
        target = max(
            self.state["next_start"],
            self.state["origins"].get(_resource_types.origin(url), 0),
        )
        monotonic_target = (
            self.state["clock"]["monotonic"] + target - self.state["clock"]["wall"]
        )
        budget.wait(max(0.0, target - now, monotonic_target - time.monotonic()), target)
        self.rebase_clock()
        self.state["next_start"] = time.time() + self.interval
        self.state["in_flight"] = True
        self.save()

    def finish(self):
        """Space the next attempt from completion, safely after actual dispatch."""
        self.rebase_clock()
        self.state["next_start"] = max(
            self.state["next_start"], time.time() + self.interval
        )
        self.state["in_flight"] = False
        self.save()

    def defer(self, url, delay):
        self.rebase_clock()
        key = _resource_types.origin(url)
        self.state["origins"][key] = max(
            self.state["origins"].get(key, 0), time.time() + delay
        )
        self.save()


def retry_after(value):
    """Return a nonnegative server delay, or None for an absent/malformed header."""
    if value is None:
        return None
    try:
        if value.strip().isascii() and value.strip().isdigit():
            delay = float(value.strip())
        else:
            stamp = email.utils.parsedate_to_datetime(value)
            if stamp.tzinfo is None:
                # Obsolete HTTP asctime dates omit an explicit GMT token.
                # HTTP-date still defines them in UTC, not the local timezone.
                stamp = stamp.replace(tzinfo=datetime.timezone.utc)
            delay = max(0.0, stamp.timestamp() - time.time())
        if not math.isfinite(delay):
            raise _resource_types.ResourceTransportError(
                "retry_after_limit", "Retry-After is too large to represent"
            )
        return delay
    except (ValueError, TypeError, OverflowError):
        return None


def _headers(response):
    result = []
    for name in ("content-type", "content-encoding", "etag", "last-modified"):
        values = response.headers.get_all(name, [])
        if len(values) > 1:
            raise _resource_types.ResourceTransportError(
                "ambiguous_headers", f"multiple {name} headers"
            )
        if values:
            value = values[0]
            if len(value) > 8192 or any(ord(c) < 32 and c != "\t" for c in value):
                raise _resource_types.ResourceTransportError(
                    "header_limit", f"invalid {name} header"
                )
            result.append((name, value))
    return tuple(result)


def _body(response, destination, max_bytes, budget, io_timeout):
    transfers = response.headers.get_all("transfer-encoding", [])
    lengths = response.headers.get_all("content-length", [])
    # urllib only removes exactly the chunked transfer coding. Other codings
    # would leave wire framing in the artifact; conflicting length is ambiguous.
    if transfers and (
        len(transfers) != 1 or transfers[0].lower() != "chunked" or lengths
    ):
        raise _resource_types.ResourceTransportError(
            "transfer_encoding", "unsupported or ambiguous Transfer-Encoding"
        )
    if len(lengths) > 1 or (
        lengths and (not lengths[0].isascii() or not lengths[0].isdigit())
    ):
        raise _resource_types.ResourceTransportError(
            "content_length", "invalid Content-Length"
        )
    if lengths and len(lengths[0]) > 20:
        raise _resource_types.ResourceTransportError(
            "size_limit", "Content-Length exceeds supported representation size"
        )
    length = int(lengths[0]) if lengths else None
    if length is not None and length > max_bytes:
        raise _resource_types.ResourceTransportError(
            "size_limit", "advertised body exceeds limit"
        )
    digest, size = hashlib.sha256(), 0
    stream = _resource_io.local_call(destination.open, "xb")
    try:
        while True:
            budget.remaining()
            # Raw socket reads underneath HTTPResponse enforce the same budget
            # while the standard parser removes supported transfer framing.
            chunk = response.read1(min(_CHUNK, max_bytes - size + 1))
            budget.remaining()
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise _resource_types.ResourceTransportError(
                    "size_limit", "received body exceeds limit"
                )
            _resource_io.local_call(stream.write, chunk)
            digest.update(chunk)
        if length is not None and size != length:
            raise _resource_types.ResourceTransportError(
                "truncated_body", "body length differs from Content-Length"
            )
        _resource_io.local_call(stream.flush)
        _resource_io.local_call(os.fsync, stream.fileno())
    finally:
        _resource_io.local_call(stream.close)
    return digest.hexdigest(), size


def acquire(source, policy, cache, budget):
    """Stream one original representation, without alternate URL/format fallback."""
    pacing = Pacing(cache.root / "pacing.json", policy.min_interval)
    client = opener(budget, policy.io_timeout)
    url = source.request_url
    redirects, visited, retries = [], {url}, 0
    while True:
        if not policy.permits(url):
            raise _resource_types.ResourcePolicyError(
                "origin_denied", f"origin not permitted: {_resource_types.origin(url)}"
            )
        pacing.start(url, budget)
        temporary = cache.temporary()
        published = False
        try:
            request = urllib_request.Request(
                url,
                headers={
                    "Accept-Encoding": "identity",
                    "User-Agent": "LCATS-gettenberg/1",
                },
                method="GET",
            )
            with client.open(
                request, timeout=min(policy.io_timeout, budget.remaining())
            ) as response:
                status = response.status
                retry_headers = response.headers.get_all("retry-after", [])
                if len(retry_headers) > 1:
                    raise _resource_types.ResourceTransportError(
                        "ambiguous_headers", "multiple Retry-After headers"
                    )
                server_delay = retry_after(retry_headers[0] if retry_headers else None)
                if server_delay is not None:
                    pacing.defer(url, server_delay)
                if status in _REDIRECTS:
                    locations = response.headers.get_all("location", [])
                    if len(locations) != 1 or not locations[0]:
                        raise _resource_types.ResourceTransportError(
                            "redirect_location", "redirect needs one Location"
                        )
                    location = locations[0]
                    # urljoin/urlsplit strip some leading control characters.
                    # Validate the raw header first, before normalizing anything.
                    if len(location) > 8192 or any(
                        ord(c) <= 32 or ord(c) >= 127 for c in location
                    ):
                        raise _resource_types.ResourceTransportError(
                            "redirect_location", "invalid Location text"
                        )
                    try:
                        target = _resource_types.canonical_url(
                            parse.urljoin(url, location)
                        )
                    except _resource_types.ResourceInputError as exc:
                        raise _resource_types.ResourceTransportError(
                            "redirect_location", str(exc)
                        ) from exc
                    if (
                        parse.urlsplit(url).scheme == "https"
                        and parse.urlsplit(target).scheme != "https"
                    ):
                        raise _resource_types.ResourcePolicyError(
                            "https_downgrade", "HTTPS downgrade refused"
                        )
                    if not policy.permits(target):
                        raise _resource_types.ResourcePolicyError(
                            "origin_denied", "redirect origin not permitted"
                        )
                    if (
                        target in visited
                        or len(redirects) >= policy.max_redirects
                        or len(redirects) >= 256
                    ):
                        raise _resource_types.ResourceTransportError(
                            "redirect_limit", "redirect loop/hop limit"
                        )
                    # A redirect's Retry-After delays following it, including when
                    # the target is on another allowed origin.
                    if server_delay is not None:
                        pacing.defer(target, server_delay)
                    visited.add(target)
                    redirects.append(target)
                    url = target
                    continue
                if status in _TRANSIENT and retries < policy.max_retries:
                    pacing.defer(url, max(2.0 * 2**retries, server_delay or 0))
                    retries += 1
                    continue
                if status != 200:
                    raise _resource_types.ResourceTransportError(
                        "http_status",
                        f"HTTP status {status}; no representation published",
                    )
                headers = _headers(response)
                digest, size = _body(
                    response,
                    temporary,
                    policy.byte_limit(source),
                    budget,
                    policy.io_timeout,
                )
                receipt = _resource_types.RetrievalReceipt(
                    1,
                    source.key,
                    source.source_uri,
                    source.request_url,
                    source.kind,
                    source.route_policy,
                    url,
                    tuple(redirects),
                    digest,
                    size,
                    datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    headers,
                )
                budget.remaining()
                artifact = _resource_io.local_call(
                    cache.publish,
                    temporary,
                    receipt,
                    policy.byte_limit(source),
                    min(policy.lock_timeout, budget.remaining()),
                )
                published = True
                return artifact
        except _resource_types.ResourcePublicationError:
            published = True
            raise
        except (error.URLError, OSError, http.client.HTTPException) as exc:
            reason = exc.reason if isinstance(exc, error.URLError) else exc
            if isinstance(reason, ssl.SSLError):
                raise _resource_types.ResourceTransportError(
                    "tls", str(reason)
                ) from exc
            # Only network failures are retryable. Local file errors must not
            # trigger another GET or hide a full disk/permission problem.
            transient = isinstance(
                reason, (TimeoutError, ConnectionError, http.client.IncompleteRead)
            ) or (
                isinstance(reason, socket.gaierror) and reason.errno == socket.EAI_AGAIN
            )
            if not transient or retries >= policy.max_retries:
                raise _resource_types.ResourceTransportError(
                    (
                        "protocol"
                        if isinstance(reason, http.client.HTTPException)
                        and not transient
                        else "connection"
                    ),
                    str(exc),
                ) from exc
            pacing.defer(url, 2.0 * 2**retries)
            retries += 1
        finally:
            # Preserve crash-safe intent before dispatch, then conservatively
            # renew spacing after every attempt. A slow pre-request save cannot
            # consume the spacing owed to the next actual GET.
            try:
                try:
                    _resource_io.local_call(pacing.finish)
                except _resource_types.ResourceError as exc:
                    if published:
                        raise _resource_types.ResourcePublicationError(
                            "coordination_uncertain",
                            "resource published but completion pacing could not be confirmed",
                        ) from exc
                    raise
            finally:
                _discard_temporary(
                    temporary,
                    cache,
                    source.kind,
                    min(
                        policy.lock_timeout,
                        max(0.0, budget.deadline - time.monotonic()),
                    ),
                )


def _discard_temporary(temporary, cache, kind, lock_timeout):
    """Clean a failed partial body without replacing the primary error."""
    cache.discard(temporary, kind, lock_timeout)
