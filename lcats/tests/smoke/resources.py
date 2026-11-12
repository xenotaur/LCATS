"""Offline prerequisite verification shared by smoke setup and workers.

Versions identify spaCy's installed model package. Stanza's resource manifest
and selected model bytes are checked as well, so a cache hit is not evidence of
complete or compatible provisioning. MD5 here checks upstream model identity,
not adversarial authenticity; the resource manifest itself is SHA-256 pinned.
"""

import hashlib
import importlib.metadata
import json
import os
import pathlib


MANIFEST_PATH = pathlib.Path(__file__).with_name("models.json")


def manifest():
    """Read the version-controlled smoke-only resource specification."""
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def model_dir():
    """Use an explicit smoke model directory, never a contributor's default."""
    value = os.environ.get("STANZA_RESOURCES_DIR")
    if not value:
        raise RuntimeError(
            "Set STANZA_RESOURCES_DIR to the provisioned smoke model directory"
        )
    return pathlib.Path(value).expanduser().resolve()


def digest(path, algorithm):
    """Hash model files in chunks rather than loading large weights into RAM."""
    hasher = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def check(backend):
    """Fail on absent or mismatched prerequisites without native imports."""
    spec = manifest()
    packages = (
        ("spacy", "en-core-web-sm") if backend == "spacy" else ("stanza", "torch")
    )
    versions = {}
    for name in packages:
        actual = importlib.metadata.version(name)
        expected = spec["packages"][name]
        # CPU wheels expose a +cpu suffix; the public version remains pinned.
        if actual.split("+")[0] != expected:
            raise RuntimeError(
                f"{name}: expected {expected}, found {actual}; use smoke setup"
            )
        versions[name] = actual
    if backend == "stanza":
        root = model_dir()
        if digest(root / "resources.json", "sha256") != spec["stanza_resources_sha256"]:
            raise RuntimeError(
                "Stanza resources.json differs from the pinned smoke manifest"
            )
        for relative, expected in spec["stanza_files_md5"].items():
            if digest(root / relative, "md5") != expected:
                raise RuntimeError(f"Stanza model checksum mismatch: {relative}")
        versions["stanza_resources_version"] = spec["stanza_resources_version"]
        versions["stanza_resources_sha256"] = spec["stanza_resources_sha256"]
    return versions
