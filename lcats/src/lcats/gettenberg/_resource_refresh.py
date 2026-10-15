"""Conditional-request binding and validation receipt construction.

This is an explicit archival download store, not a general HTTP freshness cache.
Validators never certify byte identity at the origin (weak ETags in particular).
They authorize reuse of the one locally hash-verified representation only at the
same canonical final URL and fixed request representation policy.
"""

import dataclasses
import datetime
import email.utils
import re

from lcats.gettenberg import _resource_types

_ETAG = re.compile(r'(?:W/)?"[\x21\x23-\x7e\x80-\xff]*"')
# HTTP-date allows these three wire forms, not arbitrary RFC5322 email dates.
_DATE = re.compile(
    r"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), [0-9]{2} [A-Z][a-z]{2} [0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT"
    r"|(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), [0-9]{2}-[A-Z][a-z]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT"
    r"|(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) [A-Z][a-z]{2} [ 0-9][0-9] [0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]{4})"
)


def _etag(value):
    """Return one sendable entity tag, never a wildcard/list/control sequence."""
    return value if value is not None and _ETAG.fullmatch(value) else None


def _date(value):
    """Return a syntactically usable HTTP date; malformed metadata is not replayed."""
    if value is None or not _DATE.fullmatch(value):
        return None
    try:
        email.utils.parsedate_to_datetime(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return value


def _date_instant(value):
    """Compare valid HTTP dates across wire forms; obsolete asctime is UTC too."""
    stamp = email.utils.parsedate_to_datetime(value)
    return (
        stamp.replace(tzinfo=datetime.timezone.utc) if stamp.tzinfo is None else stamp
    )


def validators(artifact, url):
    """Bind conditional headers to the cached final URL, never another hop."""
    if artifact is None or url != artifact.receipt.final_url:
        return {}
    headers = dict(artifact.receipt.headers)
    result = {}
    etag = _etag(headers.get("etag"))
    modified = _date(headers.get("last-modified"))
    if etag is not None:
        result["If-None-Match"] = etag
    if modified is not None:
        result["If-Modified-Since"] = modified
    return result


def validated_receipt(artifact, url, redirects, sent, headers):
    """Build a 304 receipt only when it identifies the verified cached response.

    Reject contradictory validators rather than guessing which response was
    validated. Strong returned ETags must exactly match; weak returned ETags can
    weakly match. A returned validator must identify the conditional candidate;
    RFC9111 section4.3.4's validator-less exception does not apply here.
    Preserve decoding metadata:
    a 304 is not authority to reinterpret stored bytes with a changed encoding.
    """
    if artifact is None or not sent or url != artifact.receipt.final_url:
        raise _resource_types.ResourceTransportError(
            "unexpected_304", "304 without a matching conditional cached representation"
        )
    old = dict(artifact.receipt.headers)
    new = dict(headers)
    tag = new.get("etag")
    if tag is not None or "If-None-Match" in sent:
        valid = _etag(tag)
        prior = sent.get("If-None-Match")
        matches = (
            valid is not None
            and prior is not None
            and (
                tag == prior
                if not tag.startswith("W/")
                else tag.removeprefix("W/") == prior.removeprefix("W/")
            )
        )
        if not matches:
            raise _resource_types.ResourceTransportError(
                "validator_mismatch",
                "304 ETag does not identify the cached representation",
            )
    modified = new.get("last-modified")
    if (modified is not None and _date(modified) is None) or (
        "If-None-Match" not in sent
        and (
            modified is None
            or _date(modified) is None
            or _date_instant(modified) != _date_instant(sent["If-Modified-Since"])
        )
    ):
        raise _resource_types.ResourceTransportError(
            "validator_mismatch",
            "304 Last-Modified does not identify the cached representation",
        )
    for name in ("content-type", "content-encoding"):
        if name in new and new[name] != old.get(name):
            raise _resource_types.ResourceTransportError(
                "representation_mismatch",
                f"304 changes original {name}; full acquisition needed",
            )
    old.update(new)
    return dataclasses.replace(
        artifact.receipt,
        schema_version=2,
        status=304,
        redirects=tuple(redirects),
        headers=tuple(sorted(old.items())),
        validated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        previous_receipt_sha256=artifact.receipt_sha256,
        validation_headers=headers,
    )
