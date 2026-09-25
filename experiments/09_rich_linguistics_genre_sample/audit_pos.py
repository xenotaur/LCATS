"""Resumable, experiment-local review helper for the POS audit packet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lcats" / "src"))
SAMPLE_PATH = pathlib.Path(__file__).parent / "results" / "pos_audit_sample.csv"
LEDGER_PATH = pathlib.Path(__file__).parent / "results" / "pos_audit_ledger.json"
SCORED_PATH = pathlib.Path(__file__).parent / "results" / "pos_audit_scored.json"
SCHEMA_VERSION = "rich-linguistics-pos-audit-ledger-v1"
SCORED_SCHEMA_VERSION = "rich-linguistics-pos-audit-scored-v1"
PACKET_SCHEMA_VERSION = "rich-linguistics-pos-audit-v1"
SCORING_CONTRACT_VERSION = "rich-linguistics-pos-audit-scoring-v1"
DISPOSITIONS = {"pending", "reviewed", "uncertain", "blocked"}
LABELS = {"NOUN", "PROPN", "OTHER"}
ISSUE_CODES = {"segmentation", "tokenization", "context", "pos_ambiguity", "other"}
IMMUTABLE_FIELDS = (
    "story_id",
    "selection_genre",
    "audit_bucket",
    "audit_features",
    "token_key",
    "sentence_index",
    "token_index",
    "global_token_index",
    "text",
    "lemma",
    "machine_upos",
    "context",
)
PACKET_FIELDS = IMMUTABLE_FIELDS + ("gold_upos", "notes")


def _pilot_module() -> Any:
    path = pathlib.Path(__file__).parent / "run_rich_linguistics_sample.py"
    spec = importlib.util.spec_from_file_location("rich_linguistics_pilot", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load pilot scorer from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_packet(path: pathlib.Path = SAMPLE_PATH) -> list[dict[str, str]]:
    """Load the generated packet and reject duplicate or missing token keys."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"{path}: audit packet is empty")
    if rows and list(rows[0]) != list(PACKET_FIELDS):
        raise ValueError(f"{path}: expected fields in canonical order: {PACKET_FIELDS}")
    if any(
        None in row or any(row.get(field) is None for field in PACKET_FIELDS)
        for row in rows
    ):
        raise ValueError(f"{path}: every row must contain the canonical packet fields")
    keys = [row.get("token_key", "") for row in rows]
    if any(not key for key in keys):
        raise ValueError(f"{path}: every row must have a token_key")
    if len(set(keys)) != len(keys):
        raise ValueError(f"{path}: duplicate token_key")
    return rows


def row_fingerprint(row: dict[str, str]) -> str:
    payload = {field: row.get(field, "") for field in IMMUTABLE_FIELDS}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def packet_fingerprint(rows: list[dict[str, str]]) -> str:
    joined = "\n".join(row_fingerprint(row) for row in rows)
    return hashlib.sha256(joined.encode("ascii")).hexdigest()


def new_ledger(
    rows: list[dict[str, str]], sample_path: pathlib.Path = SAMPLE_PATH
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "packet_schema_version": PACKET_SCHEMA_VERSION,
        "sample_path": _relative(sample_path),
        "packet_fingerprint": packet_fingerprint(rows),
        "row_count": len(rows),
        "entries": {
            row["token_key"]: {
                "token_key": row["token_key"],
                "row_fingerprint": row_fingerprint(row),
                "disposition": "pending",
                "gold_upos": None,
                "issue_codes": [],
                "notes": "not yet reviewed",
                "reviewer": None,
            }
            for row in rows
        },
    }


def load_ledger(path: pathlib.Path = LEDGER_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        try:
            ledger = json.load(handle, object_pairs_hook=_reject_duplicate_keys)
        except ValueError as error:
            raise ValueError(f"{path}: {error}") from error
    if not isinstance(ledger, dict):
        raise TypeError(f"{path}: ledger must be a JSON object")
    if ledger.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported ledger schema")
    return ledger


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def ledger_fingerprint(ledger: dict[str, Any]) -> str:
    """Return a stable fingerprint for the editable ledger contents."""
    encoded = json.dumps(
        ledger["entries"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_ledger(
    rows: list[dict[str, str]],
    ledger: dict[str, Any],
    sample_path: pathlib.Path | None = None,
) -> list[str]:
    errors: list[str] = []
    if ledger.get("schema_version") != SCHEMA_VERSION:
        errors.append("ledger schema version mismatch")
    expected = {row["token_key"]: row for row in rows}
    entries = ledger.get("entries")
    if not isinstance(entries, dict):
        return ["ledger entries must be an object"]
    if ledger.get("packet_schema_version") != PACKET_SCHEMA_VERSION:
        errors.append("packet schema version mismatch")
    if ledger.get("row_count") != len(rows):
        errors.append("ledger row count mismatch")
    if sample_path is not None and ledger.get("sample_path") != _relative(sample_path):
        errors.append("ledger sample path mismatch")
    if ledger.get("packet_fingerprint") != packet_fingerprint(rows):
        errors.append("packet fingerprint mismatch")
    if set(entries) != set(expected):
        errors.append("ledger keys do not exactly match packet keys")
    for key, entry in entries.items():
        if key not in expected:
            continue
        if not isinstance(entry, dict):
            errors.append(f"ledger entry for {key} must be an object")
            continue
        if entry.get("token_key") != key:
            errors.append(f"ledger token_key mismatch for {key}")
        if entry.get("row_fingerprint") != row_fingerprint(expected[key]):
            errors.append(f"row fingerprint mismatch for {key}")
        disposition = entry.get("disposition")
        if not isinstance(disposition, str) or disposition not in DISPOSITIONS:
            errors.append(f"invalid disposition for {key}: {disposition}")
            continue
        label = entry.get("gold_upos")
        if disposition == "reviewed" and label not in LABELS:
            errors.append(f"reviewed row {key} needs NOUN, PROPN, or OTHER")
        if disposition != "reviewed" and label is not None:
            errors.append(f"unreviewed row {key} cannot carry a scoring label")
        if (
            disposition in {"pending", "uncertain", "blocked"}
            and not str(entry.get("notes", "")).strip()
        ):
            errors.append(f"unresolved row {key} needs an explanatory note")
        issues = entry.get("issue_codes", [])
        if not isinstance(issues, list) or any(
            not isinstance(issue, str) or issue not in ISSUE_CODES for issue in issues
        ):
            errors.append(f"invalid issue code for {key}")
    return errors


def unresolved(entries: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in entries.values()
        if entry.get("disposition") in {"pending", "uncertain", "blocked"}
    ]


def audit_guidance(row: dict[str, str]) -> list[str]:
    """Return concise, deterministic guidance for reviewing one row."""
    guidance = [
        "Check the token in its sentence context before choosing a label.",
        "Use NOUN for a common noun, PROPN for a named entity, and OTHER otherwise.",
    ]
    features = set(str(row.get("audit_features", "")).split(","))
    if "proper_name_candidate" in features:
        guidance.append(
            "Check capitalization and whether the token names a specific entity."
        )
    if "noun_verb_ambiguous" in features:
        guidance.append(
            "Check the token's syntactic role rather than its spelling alone."
        )
    if "hyphenated" in features or "contraction_or_possessive" in features:
        guidance.append(
            "Record a tokenization or segmentation issue when the boundary is defective."
        )
    return guidance


def score(rows: list[dict[str, str]], ledger: dict[str, Any]) -> dict[str, Any]:
    errors = validate_ledger(rows, ledger)
    if errors:
        raise ValueError("cannot score audit: " + "; ".join(errors))
    unresolved_keys = [
        entry["token_key"]
        for entry in ledger["entries"].values()
        if entry["disposition"] in {"pending", "uncertain", "blocked"}
    ]
    if unresolved_keys:
        raise ValueError(
            "cannot score audit: unresolved rows remain; first: " + unresolved_keys[0]
        )
    labels = {key: entry["gold_upos"] for key, entry in ledger["entries"].items()}
    pilot = _pilot_module()
    scoring = pilot.score_audit(rows, labels)
    scored_rows = []
    for row in rows:
        entry = ledger["entries"][row["token_key"]]
        scored_rows.append(
            {
                "token_key": row["token_key"],
                "gold_upos": entry["gold_upos"],
                "machine_upos": row["machine_upos"],
                "issue_codes": entry["issue_codes"],
                "notes": entry["notes"],
                "reviewer": entry["reviewer"],
            }
        )
    return {
        "schema_version": SCORED_SCHEMA_VERSION,
        "packet_schema_version": PACKET_SCHEMA_VERSION,
        "packet_fingerprint": ledger["packet_fingerprint"],
        "ledger_schema_version": ledger["schema_version"],
        "ledger_fingerprint": ledger_fingerprint(ledger),
        "row_count": len(rows),
        "rows": scored_rows,
        "scoring": scoring,
        "decisions": pilot.scored_decisions(scoring),
        "scorer_source": "experiments/09_rich_linguistics_genre_sample/run_rich_linguistics_sample.py",
        "scoring_contract_version": SCORING_CONTRACT_VERSION,
        "repository_commit": _repository_commit(),
        "thresholds": {
            "overall": pilot.OVERALL_GATE,
            "severe_genre_slice": pilot.SEVERE_GENRE_GATE,
        },
    }


def _repository_commit() -> str | None:
    try:
        import subprocess

        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _relative(path: pathlib.Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _reject_protected_output(path: pathlib.Path, *protected: pathlib.Path) -> None:
    resolved = path.resolve()
    if any(resolved == candidate.resolve() for candidate in protected):
        raise ValueError(f"refusing to overwrite protected input: {path}")


def write_json(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temporary_path: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = pathlib.Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def command_start(args: argparse.Namespace) -> None:
    rows = load_packet(args.sample)
    _reject_protected_output(args.ledger, args.sample)
    if args.ledger.exists() and not args.force:
        raise FileExistsError(f"{args.ledger} exists; use --force or resume it")
    write_json(args.ledger, new_ledger(rows, args.sample))
    print(f"started {len(rows)} audit rows: {args.ledger}")


def command_status(args: argparse.Namespace) -> None:
    rows = load_packet(args.sample)
    ledger = load_ledger(args.ledger)
    errors = validate_ledger(rows, ledger, args.sample)
    if not isinstance(ledger.get("entries"), dict):
        print(json.dumps({"counts": {}, "valid": False, "errors": errors}))
        return
    counts = {disposition: 0 for disposition in sorted(DISPOSITIONS)}
    for entry in ledger["entries"].values():
        if not isinstance(entry, dict):
            counts["invalid"] = counts.get("invalid", 0) + 1
            continue
        counts[entry.get("disposition", "invalid")] = (
            counts.get(entry.get("disposition", "invalid"), 0) + 1
        )
    print(json.dumps({"counts": counts, "valid": not errors, "errors": errors}))


def command_next(args: argparse.Namespace) -> None:
    rows = load_packet(args.sample)
    ledger = load_ledger(args.ledger)
    errors = validate_ledger(rows, ledger, args.sample)
    if errors:
        raise ValueError("cannot select next row: " + "; ".join(errors))
    for row in rows:
        entry = ledger["entries"][row["token_key"]]
        if entry["disposition"] in {"pending", "uncertain", "blocked"}:
            print(
                json.dumps(
                    {"row": row, "review": entry, "guidance": audit_guidance(row)},
                    ensure_ascii=False,
                )
            )
            return
    print("no unresolved rows")


def command_record(args: argparse.Namespace) -> None:
    rows = load_packet(args.sample)
    ledger = load_ledger(args.ledger)
    errors = validate_ledger(rows, ledger, args.sample)
    if errors:
        raise ValueError("cannot record against invalid ledger: " + "; ".join(errors))
    if args.token_key not in ledger["entries"]:
        raise ValueError(f"unknown token_key: {args.token_key}")
    if args.disposition == "reviewed" and args.label not in LABELS:
        raise ValueError("reviewed requires --label NOUN, PROPN, or OTHER")
    if args.disposition != "reviewed" and args.label:
        raise ValueError("only reviewed rows may carry --label")
    if args.disposition != "reviewed" and (
        args.notes is None or not args.notes.strip()
    ):
        raise ValueError("unresolved dispositions require --notes")
    issue_codes = args.issue_code or []
    issues = [item for item in issue_codes if item not in ISSUE_CODES]
    if issues:
        raise ValueError("invalid issue code: " + ", ".join(issues))
    entry = ledger["entries"][args.token_key]
    notes = args.notes if args.notes is not None else entry.get("notes", "")
    issue_codes = issue_codes or entry.get("issue_codes", [])
    reviewer = args.reviewer if args.reviewer is not None else entry.get("reviewer")
    entry.update(
        {
            "disposition": args.disposition,
            "gold_upos": args.label or None,
            "issue_codes": list(dict.fromkeys(issue_codes)),
            "notes": notes,
            "reviewer": reviewer,
        }
    )
    errors = validate_ledger(rows, ledger)
    if errors:
        raise ValueError("record would invalidate ledger: " + "; ".join(errors))
    write_json(args.ledger, ledger)
    print(f"recorded {args.token_key}: {args.disposition}")


def command_validate(args: argparse.Namespace) -> None:
    rows = load_packet(args.sample)
    ledger = load_ledger(args.ledger)
    errors = validate_ledger(rows, ledger, args.sample)
    if errors:
        raise ValueError("; ".join(errors))
    print(f"valid ledger: {len(rows)} rows")


def command_score(args: argparse.Namespace) -> None:
    rows = load_packet(args.sample)
    ledger = load_ledger(args.ledger)
    _reject_protected_output(args.output, args.sample, args.ledger)
    errors = validate_ledger(rows, ledger, args.sample)
    if errors:
        raise ValueError("cannot score audit: " + "; ".join(errors))
    result = score(rows, ledger)
    write_json(args.output, result)
    print(f"scored {len(rows)} rows: {args.output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=pathlib.Path, default=SAMPLE_PATH)
    parser.add_argument("--ledger", type=pathlib.Path, default=LEDGER_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start")
    start.add_argument("--force", action="store_true")
    start.set_defaults(function=command_start)
    for name, function in (
        ("status", command_status),
        ("next", command_next),
        ("validate", command_validate),
    ):
        subparsers.add_parser(name).set_defaults(function=function)
    record = subparsers.add_parser("record")
    record.add_argument("--token-key", required=True)
    record.add_argument("--disposition", choices=sorted(DISPOSITIONS), required=True)
    record.add_argument("--label", choices=sorted(LABELS))
    record.add_argument("--issue-code", action="append")
    record.add_argument("--notes")
    record.add_argument("--reviewer")
    record.set_defaults(function=command_record)
    scoring = subparsers.add_parser("score")
    scoring.add_argument("--output", type=pathlib.Path, default=SCORED_PATH)
    scoring.set_defaults(function=command_score)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.function(args)
    except (FileNotFoundError, OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
