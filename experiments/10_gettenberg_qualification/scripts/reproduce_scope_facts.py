"""Recompute the derivable scope-audit facts from pinned Git and archived inputs.

Run from lcats/ with the project Python, without PYTHONPATH or gutenbergpy:
python ../experiments/10_gettenberg_qualification/scripts/reproduce_scope_facts.py /tmp/NEW_SCOPE_FACTS.json

This reads local Git objects and hash-verified archived reports only. It does not
rebuild a catalog, acquire sources, execute gather, or interpret literary content.
The investigator's unarchived temporary report cannot be reproduced here; its
parity assertion is explicitly excluded, not silently counted as verified.
Limits: 32 MiB/file, 64 MiB expanded JSON, 30s/Git call, 120s total on POSIX.
Output must be new and outside the repository. See ../scope-facts-reproduction.md.
"""

import argparse
import ast
import collections
import gzip
import hashlib
import io
import json
import pathlib
import signal
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
HEAD = "6a873b611e3958bb9ddad8e84f2ad190831a9da7"
BASE = "ed20e9c297bf5e50e1911b84722e53f5db3edee3"
ORIGINAL = "5cfd2d71caf6f3eedfdfc0b830b5c5ff1a74ba3b"
PARSER_BASE = "335855c04cd7ba936815d2635969d94fdd278c71"
PARSER = "lcats/src/lcats/gatherers/parser.py"
STORYMAP = "lcats/src/lcats/gatherers/mass_quantities/storymap.py"
NORMALIZATION = "lcats/src/lcats/gatherers/normalization.py"
RESULTS = "experiments/10_gettenberg_qualification/results/"
FACTS = RESULTS + "gettenberg-scope-audit-20261022/audit-facts.json"
FACTS_SHA = "a79dcdfff0f5d9f7814c95ce21e5527961c285aa2fb926a13345ba2d4aba08e5"
CORPUS = RESULTS + "gettenberg-qualification-20261018/corpus-after.json.gz"
INDEX = RESULTS + "gettenberg-qualification-20261018/index-counts-final.json"
MAX_BYTES = 32 * 1024**2


def sha(data):
    """Identify exact input bytes, including compressed archival bytes."""
    return hashlib.sha256(data).hexdigest()


def git(*args):
    """Read fixed local object paths; no checkout, fetch, hooks, or Git writes."""
    return subprocess.check_output(["git", "--no-pager", *args], cwd=ROOT, timeout=30)


def read_bytes(path):
    """Bound archival reads and require regular files inside this checkout."""
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(ROOT) or not resolved.is_file():
        raise ValueError("input must be a regular file inside the repository")
    with resolved.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("input exceeds 32 MiB")
    return data


def decode_json(path, data):
    """Bound gzip expansion before decoding the archived JSON payload."""
    if path.endswith(".gz"):
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            data = stream.read(2 * MAX_BYTES + 1)
        if len(data) > 2 * MAX_BYTES:
            raise ValueError("expanded input exceeds 64 MiB")
    return json.loads(data)


def functions(source):
    """Compare top-level function syntax without source-position attributes."""
    return {
        node.name: node
        for node in ast.parse(source).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def configured_ids(source):
    """Read the pinned sorted literal list without importing product modules."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "SINGLE_STORIES"
            for target in node.targets
        ):
            value = node.value
            if not (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id == "sorted"
                and len(value.args) == 1
                and not value.keywords
            ):
                raise ValueError("pinned SINGLE_STORIES is not sorted(literal)")
            values = ast.literal_eval(value.args[0])
            if not isinstance(values, list) or any(type(v) is not int for v in values):
                raise ValueError("configured story IDs must be integer literals")
            return set(values)
    raise ValueError("pinned SINGLE_STORIES is missing")


def reproduce():
    """Recompute numeric/static claims, comparing each to the original record."""
    original_bytes = read_bytes(ROOT / FACTS)
    if sha(original_bytes) != FACTS_SHA:
        raise ValueError("original audit-facts.json identity differs")
    expected = json.loads(original_bytes)
    inputs = {}
    hashes = {}
    for name, expected_sha in expected["inputs_sha256"].items():
        data = read_bytes(ROOT / name)
        hashes[name] = sha(data)
        if hashes[name] != expected_sha:
            raise ValueError(f"archived input identity differs: {name}")
        inputs[name] = decode_json(name, data)

    old_functions = functions(git("show", f"{ORIGINAL}:{PARSER}"))
    migrated_functions = functions(git("show", f"{PARSER_BASE}:{PARSER}"))
    common = old_functions.keys() & migrated_functions.keys()
    changed = sorted(
        name
        for name in common
        if ast.dump(old_functions[name], include_attributes=False)
        != ast.dump(migrated_functions[name], include_attributes=False)
    )
    pinned_parser = git("show", f"{HEAD}:{PARSER}")
    # Execute only the pinned pure predicate, with set as its sole builtin.
    # This avoids importing parser and its product/runtime dependencies.
    predicate = functions(pinned_parser)["only_english"]
    namespace = {"__builtins__": {"set": set}}
    exec(
        compile(ast.Module(body=[predicate], type_ignores=[]), PARSER, "exec"),
        namespace,
    )
    only_english = namespace["only_english"]
    selected = configured_ids(git("show", f"{HEAD}:{STORYMAP}"))
    rows = inputs[CORPUS]["rows"]
    compared = [row for row in rows if row["status"] == "compared"]
    additions = inputs[INDEX]["english"]["new_only"]
    languages = inputs[INDEX]["english"]["new_only_languages_in_source_order"]
    computed = {
        "pinned_head": HEAD,
        "qualification_base": BASE,
        "source_baseline": ORIGINAL,
        "product_diff": git(
            "diff", "--name-status", BASE, HEAD, "--", "lcats/src/lcats"
        )
        .decode()
        .splitlines(),
        "gettenberg_diff": git(
            "diff", "--name-status", BASE, HEAD, "--", "lcats/src/lcats/gettenberg"
        )
        .decode()
        .splitlines(),
        "baseline_common_parser_functions": len(common),
        "baseline_changed_common_parser_functions": changed,
        "population": dict(collections.Counter(row["status"] for row in rows)),
        "old_new_equal": sum(
            row["normalized_before_sha256"] == row["normalized_after_sha256"]
            for row in compared
        ),
        "old_new_changed": sum(
            row["normalized_before_sha256"] != row["normalized_after_sha256"]
            for row in compared
        ),
        "matches_retained_corpus": sum(
            row["normalized_after_sha256"] == row["retained_corpus_body_sha256"]
            for row in compared
        ),
        "metadata_rejections": sum(bool(row.get("metadata_rejection")) for row in rows),
        "english_query_additions": len(additions),
        "english_additions_in_comparison": sorted(
            set(additions) & {r["id"] for r in rows}
        ),
        "english_additions_in_configured_list": sorted(set(additions) & selected),
        "english_additions_passing_only_english": sorted(
            book_id
            for book_id in additions
            if only_english(
                [value for group in languages[str(book_id)] for value in group]
            )
        ),
        "inputs_sha256": hashes,
        "unchanged_normalization_storymap": not git(
            "diff", "--name-only", ORIGINAL, HEAD, "--", NORMALIZATION, STORYMAP
        ).strip(),
    }
    mismatches = [key for key, value in computed.items() if expected[key] != value]
    if mismatches:
        raise ValueError("original fact mismatch: " + ", ".join(mismatches))
    # These fields report a historical observation, not a computation from the
    # preserved inputs. Explicitly exclude them from reproduced claims.
    excluded = {
        key: expected[key]
        for key in (
            "coordinator_replay_matches_investigator_rows",
            "investigator_report_sha256",
            "note",
        )
    }
    if set(expected) != set(computed) | set(excluded):
        raise ValueError("original facts contain an unclassified field")
    return {
        "scope": "Pinned static/count reproduction; not source, corpus, or delivery acceptance",
        "original_facts_sha256": FACTS_SHA,
        "reproduced_fields": computed,
        "all_reproduced_fields_match": True,
        "not_reproduced": {
            "reason": "The temporary investigator report is not an archived input; parity is historical testimony.",
            "original_observations": excluded,
        },
    }


def timeout_handler(_signum, _frame):
    """Stop even a blocked diagnostic under the documented POSIX ceiling."""
    raise TimeoutError("120-second reproduction ceiling")


def main(argv=None):
    """Validate output authority before reads and publish only complete results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output", type=pathlib.Path, help="New JSON path outside repository"
    )
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("output already exists; never overwrite evidence")
    output = args.output.resolve()
    if output.is_relative_to(ROOT) or not output.parent.is_dir():
        raise ValueError("output requires an existing parent outside repository")
    if not hasattr(signal, "SIGALRM"):
        raise RuntimeError("POSIX SIGALRM required")
    previous = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(120)
    try:
        payload = json.dumps(reproduce(), indent=2) + "\n"
        # Exclusive creation also rejects a racing writer. Only our own partial
        # file is removed on a write failure; existing evidence is never touched.
        with output.open("x", encoding="utf-8") as stream:
            try:
                stream.write(payload)
            except BaseException:
                output.unlink()
                raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
    print(
        f"Reproduced 18 fact fields; historical investigator parity excluded: {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
