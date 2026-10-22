"""Verify attributed span-role reviews without approving stories.

Labels locate inspection candidates; they cannot establish editorial authorship.
Only separately supplied reviews can propose preservation of a confirmed promotional
preface as publisher_blurb metadata. This opt-in helper currently supports historical
decoded UTF-8 cache provenance, not authenticated original HTTP representations.
It writes nothing and is not called by default extraction or batch recording.
"""

import re

from lcats.gatherers import candidate_review
from lcats.gatherers import readiness
from lcats.gatherers import review_rules

RULE = "reviewed-promotional-preface-v1"
OPENING_LIMIT = 8192
MAX_NOTE = 2048
MAX_TEXT = 4_000_000
# These delimiters identify complete inspection units, never their literary role.
# Mixed unwrapped publisher prefaces and multi-paragraph notes are out of scope.
_DELIMITED = re.compile(
    r"(?:\[(?:Publisher|Editor)['’]s note:\s+[^\[\]]+\]|"
    r"\(_Editor['’]s note:\s+[^_]+_\))",
    re.IGNORECASE,
)
_KEYS = {
    "schema_version",
    "kind",
    "gutenberg_id",
    "candidate_record_sha256",
    "candidate_span",
    "candidate_text_sha256",
    "source_span",
    "source_text_sha256",
    "decoded_utf8_sha256",
    "reviewer",
    "rationale",
}


def labeled_prefaces(body):
    """Locate bounded, delimited opening notes without assigning editorial roles.

    Returns exact Unicode ranges and text hashes for complete paragraphs ending
    within the first 8,192 characters. The remainder is not searched. A result is
    a discovery cue, including when an author uses an editor voice fictionally.
    """
    if not isinstance(body, str) or len(body) > MAX_TEXT:
        raise ValueError("preface discovery requires bounded text")
    result = []
    # One extra character lets us reject an apparent paragraph ending caused by
    # slicing the search window rather than by the actual source boundary.
    for match in review_rules._PARAGRAPH.finditer(body[: OPENING_LIMIT + 1]):
        start, end = match.span()
        text = body[start:end]
        if end > OPENING_LIMIT or len(text) > MAX_NOTE:
            continue
        if end < len(body) and re.match(r"\n[ \t]*\n|[ \t]*\Z", body[end:]) is None:
            continue
        if _DELIMITED.fullmatch(text):
            result.append({"span": [start, end], "sha256": readiness.text_sha256(text)})
    return result


def _span(text, value):
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(v) is not int for v in value)
        or not 0 <= value[0] < value[1] <= len(text)
    ):
        raise ValueError("review requires nonempty bounded Unicode spans")
    return text[value[0] : value[1]]


def reviewed_preface(path, source, review):
    """Validate one explicit role review and return a proposal-only omission.

    Args:
        path: An immutable candidate accepted by the ordinary candidate loader.
        source: Exact decoded historical cache text, including original newlines.
        review: An attributed schema-v1 gettenberg_preface_role_review packet.
            Both complete texts and the two note spans are hash-bound. The reviewer
            must positively establish a promotional role from source context.

    Returns:
        Evidence and an omission suitable for a separately reviewed v2 selection.
        Every surrounding character is retained. No disposition or approval is
        created; readiness, prior intent and history are not adjudicated here.

    Raises:
        ValueError: Invalid/stale packet, unsupported provenance, incomplete note,
            inconsistent source mapping or out-of-budget input. Attribution records
            a judgment; successful validation is not authentication or semantic proof.
    """
    record = candidate_review.load_candidate(path)
    report = record["report"]
    body, provenance = report["body"], report["provenance"]
    if not isinstance(source, str) or len(source) > MAX_TEXT:
        raise ValueError("role review requires bounded source text")
    if not isinstance(review, dict) or set(review) != _KEYS:
        raise ValueError("invalid preface role review fields")
    if (
        type(review["schema_version"]) is not int
        or review["schema_version"] != 1
        or review["kind"] != "gettenberg_preface_role_review"
        or type(review["gutenberg_id"]) is not int
        or review["gutenberg_id"] != report["gutenberg_id"]
        or review["candidate_record_sha256"] != readiness.identity(record)
    ):
        raise ValueError("stale or unsupported preface role review")
    candidate_review._attribution(review["reviewer"], review["rationale"])
    digest = readiness.text_sha256(source)
    if (
        provenance.get("input_kind") != "historical_decoded_utf8_cache"
        or provenance.get("decoded_utf8_sha256") != digest
        or review["decoded_utf8_sha256"] != digest
    ):
        raise ValueError("source identity or provenance differs")
    normalized_source = source.replace("\r\n", "\n").replace("\r", "\n")
    origin = normalized_source.find(body)
    if origin < 0 or normalized_source.find(body, origin + 1) >= 0:
        raise ValueError("candidate is not a unique unchanged source interval")
    text = _span(body, review["candidate_span"])
    raw = _span(source, review["source_span"])
    if (
        readiness.text_sha256(text) != review["candidate_text_sha256"]
        or readiness.text_sha256(raw) != review["source_text_sha256"]
        or raw.replace("\r\n", "\n").replace("\r", "\n") != text
        or any(
            len(source[:raw_offset].replace("\r\n", "\n").replace("\r", "\n"))
            != origin + candidate_offset
            for raw_offset, candidate_offset in zip(
                review["source_span"], review["candidate_span"]
            )
        )
        or {"span": review["candidate_span"], "sha256": review["candidate_text_sha256"]}
        not in labeled_prefaces(body)
    ):
        raise ValueError("note span, source mapping or complete delimiters differ")
    # Binding the full candidate also binds metadata, assessment and extraction
    # context. Delimiters validate only the reviewed unit, not a new input's role.
    start, end = review["candidate_span"]
    review_digest = readiness.identity(review)
    return {
        "rule": RULE,
        "gutenberg_id": report["gutenberg_id"],
        "candidate_record_sha256": review["candidate_record_sha256"],
        "review_sha256": review_digest,
        "review": review,
        "candidate_text": text,
        "source_text": raw,
        "omission": {
            "start": start,
            "end": end,
            "kind": "publisher_blurb",
            "reason": review["rationale"],
            "evidence": RULE + "; attributed role review SHA256 " + review_digest,
        },
        "selected_sha256": readiness.text_sha256(body[:start] + body[end:]),
        "review_binding_validated": True,
        "publication_approved": False,
    }
