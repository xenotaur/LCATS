"""Offline review of immutable candidates, without acquisition or publication.

Artifact hashes establish consistency, not authenticated authorship or current
catalog validity. Gathering revalidates exported approvals against current sources.
"""

import collections
import dataclasses
import json
import pathlib

from lcats.gatherers import readiness
from lcats.gatherers import review_store
from lcats.gatherers import story_output
from lcats.utils import env

MAX_CANDIDATE_BYTES = 64 * 1024**2
MAX_DISPOSITION_BYTES = 64 * 1024
MAX_FILES = 10000
MAX_SCAN_BYTES = 1024**3
MAX_WINDOW = 16384
DEFAULT_DISPOSITIONS = pathlib.Path("logs/gather/dispositions/mass_quantities")
_ASSESSMENT_KEYS = {"policy", "status", "exclusion", "offset_basis", "findings"}
_IDENTITY_KEYS = {"source_identity_sha256", "candidate_sha256", "assessment_sha256"}
_DISPOSITION_KEYS = {
    "schema_version",
    "kind",
    "gutenberg_id",
    "candidate_record_sha256",
    "outcome",
    "reviewer",
    "rationale",
    "approval",
}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"non-finite JSON number: {value}")


def _read_json(path, limit):
    """Read a bounded regular file; reject ambiguous JSON representations."""
    path = pathlib.Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"review input must be a regular non-symlink file: {path}")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"review input exceeds {limit} bytes: {path}")
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        ), len(raw)
    except (RecursionError, UnicodeError) as exc:
        raise ValueError(f"invalid review JSON: {path}") from exc


def _positive_id(value):
    if type(value) is not int or value <= 0:
        raise ValueError("review record requires a positive integer Gutenberg ID")


def _attribution(reviewer, rationale):
    for name, value, limit in (
        ("reviewer", reviewer, 256),
        ("rationale", rationale, 4000),
    ):
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"{name} must contain 1–{limit} characters")


def _validate_candidate(record, path):
    """Validate the saved report's complete identity chain, not just its filename."""
    if (
        not isinstance(record, dict)
        or set(record) != {"schema_version", "kind", "report"}
        or type(record["schema_version"]) is not int
        or record["schema_version"] != 1
        or record["kind"] != "gettenberg_review_candidate"
    ):
        raise ValueError("unsupported candidate record schema")
    try:
        report = record["report"]
        book_id = report["gutenberg_id"]
        _positive_id(book_id)
        body = report["body"]
        provenance = report["provenance"]
        evidence = provenance["publication_readiness"]
        if (
            report["status"] != "needs_review"
            or report["rejection"] is not None
            or not isinstance(body, str)
            or not body
            or not isinstance(report["selected_span"], list)
            or any(type(v) is not int for v in report["selected_span"])
            or report["selected_span"] != [0, len(body)]
            or not isinstance(report["metadata"], dict)
            or set(evidence) != _ASSESSMENT_KEYS | _IDENTITY_KEYS
        ):
            raise ValueError("candidate must contain an unresolved, unselected report")
        assessment = {key: evidence[key] for key in _ASSESSMENT_KEYS}
        if (
            assessment["status"] != "needs_review"
            or assessment["exclusion"] is not None
            or not isinstance(assessment["policy"], str)
            or not assessment["policy"]
            or assessment["offset_basis"] != "candidate_body_unicode_characters"
            or not isinstance(assessment["findings"], list)
            or not assessment["findings"]
        ):
            raise ValueError("invalid candidate assessment")
        for finding in assessment["findings"]:
            if not isinstance(finding, dict):
                raise ValueError("invalid candidate finding")
            span = finding["span"]
            if (
                not isinstance(span, list)
                or len(span) != 2
                or any(type(v) is not int for v in span)
                or not 0 <= span[0] <= span[1] <= len(body)
                or not isinstance(finding["kind"], str)
                or not finding["kind"]
                or not isinstance(finding["message"], str)
                or not isinstance(finding["severity"], str)
                or not isinstance(finding["evidence"], dict)
            ):
                raise ValueError("invalid candidate finding/span")
        source_context = {
            "gutenberg_id": book_id,
            "metadata": report["metadata"],
            "source": {
                k: v for k, v in provenance.items() if k != "publication_readiness"
            },
        }
        if (
            evidence["candidate_sha256"] != readiness.text_sha256(body)
            or evidence["assessment_sha256"] != readiness.identity(assessment)
            or evidence["source_identity_sha256"] != readiness.identity(source_context)
        ):
            raise ValueError(
                "candidate body, assessment or derivation identity mismatch"
            )
        expected = f"{book_id}-{readiness.identity(record)}.candidate.json"
        if pathlib.Path(path).name != expected:
            raise ValueError("candidate filename/content identity mismatch")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("malformed candidate report") from exc


def load_candidate(path):
    """Load a current-format candidate and verify its recorded identity chain.

    This reads no catalog. It cannot certify literary quality or freshness against
    acquisition; the publication path independently performs those source checks.
    """
    record, _ = _read_json(path, MAX_CANDIDATE_BYTES)
    _validate_candidate(record, path)
    return record


def preview(path, *, start=0, end=None):
    """Return an exact bounded Unicode text window and overlapping findings.

    Args:
        path: Content-addressed saved candidate path.
        start: Inclusive candidate character offset.
        end: Exclusive offset; defaults to at most 4000 characters after start.

    Returns:
        JSON-compatible packet with omitted-text indicators and full identities.
    """
    record = load_candidate(path)
    report = record["report"]
    body = report["body"]
    if type(start) is not int or not 0 <= start < len(body):
        raise ValueError("start must be a candidate character offset")
    end = min(start + 4000, len(body)) if end is None else end
    if type(end) is not int or not start < end <= len(body) or end - start > MAX_WINDOW:
        raise ValueError(
            f"preview requires a nonempty window of at most {MAX_WINDOW} characters"
        )
    findings = report["provenance"]["publication_readiness"]["findings"]
    return {
        "gutenberg_id": report["gutenberg_id"],
        "candidate_record_sha256": readiness.identity(record),
        "metadata": report["metadata"],
        "candidate_characters": len(body),
        "offset_basis": "candidate_body_unicode_characters",
        "window": {"start": start, "end": end, "text": body[start:end]},
        "omitted_before": start,
        "omitted_after": len(body) - end,
        "next_start": end if end < len(body) else None,
        "finding_count": len(findings),
        "findings_in_window": [
            f for f in findings if f["span"][0] < end and f["span"][1] > start
        ],
        "validation": "saved artifact consistency; current source is revalidated during gather",
    }


def _publish_equal(path, record, limit):
    """Create complete JSON atomically, reusing only exactly equal existing data."""
    path = pathlib.Path(path)
    parent = review_store.working_root(path.parent, data_root=env.data_root())
    path = parent / path.name
    # Check output size before any directory/file mutation, including exports.
    if len(json.dumps(record, indent=4).encode("utf-8")) > limit:
        raise ValueError("review output exceeds size limit")
    parent.mkdir(parents=True, exist_ok=True)
    story_output.publish(path, record)
    existing, _ = _read_json(path, limit)
    # Python equality conflates true/1 and 1/1.0; canonical JSON keeps schema
    # types distinct so a corrupt existing artifact cannot be reported reused.
    if readiness.identity(existing) != readiness.identity(record):
        raise ValueError(f"existing review output differs; choose a new path: {path}")
    return str(path)


def record_disposition(
    candidate,
    *,
    outcome,
    reviewer,
    rationale,
    start=None,
    end=None,
    omissions=None,
    directory=DEFAULT_DISPOSITIONS,
):
    """Record one explicit, attributed disposition without changing any story.

    Approve requires a selected span or evidenced omissions (v2). Exclude/defer are audit records only: they
    neither change collection definitions nor authorize publication. Repeated
    identical records are idempotent; different records remain separate evidence.
    """
    record = load_candidate(candidate)
    _attribution(reviewer, rationale)
    if not isinstance(outcome, str) or outcome not in {"approve", "exclude", "defer"}:
        raise ValueError("outcome must be approve, exclude or defer")
    approval = None
    if outcome == "approve":
        if omissions is not None:
            if start is not None or end is not None:
                raise ValueError("choose omissions or a single span, not both")
            decision = readiness.OrderedReviewDecision.for_report(
                record["report"],
                omissions=omissions,
                reviewer=reviewer,
                rationale=rationale,
            )
        else:
            decision = readiness.ReviewDecision.for_report(
                record["report"],
                start=start,
                end=end,
                reviewer=reviewer,
                rationale=rationale,
            )
        approval = dataclasses.asdict(decision)
    elif start is not None or end is not None or omissions is not None:
        raise ValueError("only approval may select a publication span")
    disposition = {
        "schema_version": 1,
        "kind": "gettenberg_candidate_disposition",
        "gutenberg_id": record["report"]["gutenberg_id"],
        "candidate_record_sha256": readiness.identity(record),
        "outcome": outcome,
        "reviewer": reviewer,
        "rationale": rationale,
        "approval": approval,
    }
    path = (
        pathlib.Path(directory)
        / f"{disposition['gutenberg_id']}-{readiness.identity(disposition)}.disposition.json"
    )
    return _publish_equal(path, disposition, MAX_DISPOSITION_BYTES)


def _load_disposition(path):
    """Validate a disposition and retain actual input bytes for aggregate bounds."""
    record, size = _read_json(path, MAX_DISPOSITION_BYTES)
    if (
        not isinstance(record, dict)
        or set(record) != _DISPOSITION_KEYS
        or type(record["schema_version"]) is not int
        or record["schema_version"] != 1
        or record["kind"] != "gettenberg_candidate_disposition"
    ):
        raise ValueError("unsupported disposition schema")
    _positive_id(record["gutenberg_id"])
    _attribution(record["reviewer"], record["rationale"])
    digest = record["candidate_record_sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(c not in "0123456789abcdef" for c in digest)
    ):
        raise ValueError("invalid candidate record identity")
    if not isinstance(record["outcome"], str):
        raise ValueError("disposition outcome must be a string")
    if record["outcome"] == "approve":
        try:
            decision = readiness.decision_from_dict(record["approval"])
        except TypeError as exc:
            raise ValueError("invalid approval fields") from exc
        if (
            decision.gutenberg_id != record["gutenberg_id"]
            or decision.reviewer != record["reviewer"]
            or decision.rationale != record["rationale"]
        ):
            raise ValueError("disposition and approval attribution/ID differ")
    elif (
        record["outcome"] not in {"exclude", "defer"} or record["approval"] is not None
    ):
        raise ValueError("invalid non-approval disposition")
    if (
        pathlib.Path(path).name
        != f"{record['gutenberg_id']}-{readiness.identity(record)}.disposition.json"
    ):
        raise ValueError("disposition filename/content identity mismatch")
    return record, size


def load_disposition(path):
    """Validate an immutable disposition; export checks its exact candidate too."""
    return _load_disposition(path)[0]


def _match(disposition, candidate):
    """Verify the disposition names this exact candidate and selected substring."""
    report = candidate["report"]
    if (
        disposition["candidate_record_sha256"] != readiness.identity(candidate)
        or disposition["gutenberg_id"] != report["gutenberg_id"]
    ):
        raise ValueError("disposition refers to a different candidate")
    if disposition["outcome"] == "approve":
        d = readiness.decision_from_dict(disposition["approval"])
        expected = readiness.decision_for_report(d, report)
        if d != expected:
            raise ValueError(
                "approval is stale or selected text does not match candidate"
            )


def export_approvals(dispositions, *, candidates, output):
    """Export explicitly selected approvals; never infer approval from an inventory.

    Exact saved candidates must exist. Non-approvals, repeated IDs (even identical
    repeats), and unequal existing outputs fail. Gathering still checks current
    source identity and collection eligibility before publication.
    """
    approvals = []
    seen = set()
    scanned = 0
    for path in dispositions:
        if len(approvals) >= MAX_FILES:
            raise ValueError("too many approval records")
        record, size = _load_disposition(path)
        scanned += size
        if scanned > MAX_SCAN_BYTES:
            raise ValueError("review scan exceeds 1 GiB")
        if record["outcome"] != "approve":
            raise ValueError("only explicit approval dispositions can be exported")
        book_id = record["gutenberg_id"]
        if book_id in seen:
            raise ValueError(f"duplicate Gutenberg ID in export: {book_id}")
        seen.add(book_id)
        candidate_path = (
            pathlib.Path(candidates)
            / f"{book_id}-{record['candidate_record_sha256']}.candidate.json"
        )
        candidate, size = _read_json(candidate_path, MAX_CANDIDATE_BYTES)
        scanned += size
        if scanned > MAX_SCAN_BYTES:
            raise ValueError("candidate scan exceeds 1 GiB")
        _validate_candidate(candidate, candidate_path)
        _match(record, candidate)
        approvals.append(record["approval"])
    if not approvals:
        raise ValueError("select at least one explicit approval disposition")
    approvals.sort(key=lambda v: v["gutenberg_id"])
    return _publish_equal(output, approvals, 8 * 1024**2)


def _paths(directory, suffix):
    directory = pathlib.Path(directory)
    if not directory.is_dir():
        raise ValueError(f"review directory does not exist: {directory}")
    # Collect at most the bound before sorting; no unbounded glob materialization.
    paths = []
    for path in directory.glob("*" + suffix):
        if len(paths) >= MAX_FILES:
            raise ValueError("review directory exceeds 10000 matching files")
        paths.append(path)
    return sorted(paths)


def inventory(candidates, *, dispositions=None):
    """Summarize exact candidate generations with explicit conflict/unknown states.

    This never picks the latest generation or resolves conflicting decisions.
    Unmatched disposition identities remain visible instead of counting as reviews.
    Reads are bounded by file counts, per-file sizes and 1 GiB aggregate JSON.
    """
    by_candidate = collections.defaultdict(list)
    scanned = 0
    if dispositions is not None:
        for path in _paths(dispositions, ".disposition.json"):
            record, size = _load_disposition(path)
            scanned += size
            if scanned > MAX_SCAN_BYTES:
                raise ValueError("review scan exceeds 1 GiB")
            by_candidate[record["candidate_record_sha256"]].append((str(path), record))
    rows = []
    for path in _paths(candidates, ".candidate.json"):
        candidate, size = _read_json(path, MAX_CANDIDATE_BYTES)
        scanned += size
        if scanned > MAX_SCAN_BYTES:
            raise ValueError("candidate scan exceeds 1 GiB")
        _validate_candidate(candidate, path)
        report = candidate["report"]
        digest = readiness.identity(candidate)
        decisions = by_candidate.pop(digest, [])
        for _, d in decisions:
            _match(d, candidate)
        # Attribution differences alone do not create conflicting content intent.
        intents = {
            (
                d["outcome"],
                (
                    None
                    if d["approval"] is None
                    else readiness.decision_intent(d["approval"])
                ),
            )
            for _, d in decisions
        }
        state = (
            "unreviewed"
            if not intents
            else ("conflict" if len(intents) > 1 else next(iter(intents))[0])
        )
        rows.append(
            {
                "gutenberg_id": report["gutenberg_id"],
                "candidate": str(path),
                "candidate_record_sha256": digest,
                "titles": report["metadata"].get("titles", []),
                "candidate_characters": len(report["body"]),
                "finding_counts": dict(
                    collections.Counter(
                        f["kind"]
                        for f in report["provenance"]["publication_readiness"][
                            "findings"
                        ]
                    )
                ),
                "state": state,
                "dispositions": [p for p, _ in decisions],
            }
        )
    generations = collections.Counter(r["gutenberg_id"] for r in rows)
    return {
        "candidate_count": len(rows),
        "scanned_bytes": scanned,
        "counts": dict(collections.Counter(r["state"] for r in rows)),
        "multiple_generation_ids": sorted(k for k, v in generations.items() if v > 1),
        "unmatched_disposition_candidates": sorted(by_candidate),
        "candidates": rows,
        "meaning": "recorded reviewer intent, not publication, current-source validation or corpus acceptance",
    }


def load_omissions(path):
    """Load a bounded explicit omission list; construction validates each entry."""
    value, _ = _read_json(path, MAX_DISPOSITION_BYTES)
    if not isinstance(value, list) or not 1 <= len(value) <= 256:
        raise ValueError("omission specification must contain 1–256 entries")
    return value
