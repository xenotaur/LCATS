"""Guard historical figure regeneration against changed source inputs."""

from __future__ import annotations

import hashlib
import json
import pathlib


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _story_content_revision(rows: list[dict], corpora_root: pathlib.Path) -> str:
    file_hashes = []
    for row in rows:
        story_path = corpora_root / row["story_path"]
        file_hashes.append(f"{row['story_id']}:{_sha256(story_path)}")
    return hashlib.sha256("\n".join(sorted(file_hashes)).encode("utf-8")).hexdigest()


def verify_inputs(
    *,
    preservation_root: pathlib.Path,
    corpora_root: pathlib.Path,
    selection_manifest: pathlib.Path,
    tokenizer_source: pathlib.Path,
) -> None:
    """Refuse to overwrite preserved outputs when recorded inputs changed."""
    preservation_manifest = json.loads(
        (preservation_root / "preservation_manifest.json").read_text(encoding="utf-8")
    )
    manifest_bytes = selection_manifest.read_bytes()
    rows = [
        json.loads(line)
        for line in manifest_bytes.decode("utf-8").splitlines()
        if line.strip()
    ]

    expected = {
        "selection manifest": preservation_manifest["universe"]["manifest_sha256"],
        "story content": preservation_manifest["universe"]["story_content_revision"],
        "tokenizer source": preservation_manifest["preprocessing"][
            "tokenization_source_sha256"
        ],
    }
    actual = {
        "selection manifest": hashlib.sha256(manifest_bytes).hexdigest(),
        "story content": _story_content_revision(rows, corpora_root),
        "tokenizer source": _sha256(tokenizer_source),
    }
    mismatches = [
        f"{name}: expected {expected[name]}, found {actual[name]}"
        for name in expected
        if actual[name] != expected[name]
    ]
    if mismatches:
        details = "\n- ".join(mismatches)
        raise RuntimeError(
            "Refusing to overwrite preserved Worldcon figures because their "
            f"recorded inputs changed:\n- {details}\n"
            "Regenerate into a separate output directory and review the new "
            "artifacts before updating this preservation bundle."
        )
