"""Verify a release wheel, sdist and physical installation against a Git commit.

Run with project Python (packaging required):
python qualify_release_artifacts.py REPO REF WHEEL SDIST INSTALLED_LCATS NEW_JSON

Read-only, no imports from LCATS and no network. Compares every tracked package
file, checks wheel/sdist/installed dependency metadata, and rejects legacy or direct
URL requirements. NEW_JSON must not exist or be inside REPO. Git reads have a
30-second timeout. This verifies artifact identity, not behavior, supported-platform
coverage or permission to publish. Build/install and behavioral checks are separate.
"""

import argparse
import ast
import email.parser
import hashlib
import json
import pathlib
import subprocess
import tarfile
import zipfile

from packaging import requirements
from packaging import utils


def require(condition, message):
    """Keep qualification checks enabled even when Python uses optimization."""
    if not condition:
        raise ValueError(message)


def sha(raw):
    """Identify the exact bytes compared across each artifact boundary."""
    return hashlib.sha256(raw).hexdigest()


def dependency_metadata(raw):
    """Reject legacy names and every PEP 508 direct URL, including extras."""
    metadata = email.parser.BytesParser().parsebytes(raw)
    dependencies = metadata.get_all("Requires-Dist", [])
    for value in dependencies:
        parsed = requirements.Requirement(value)
        require(
            utils.canonicalize_name(parsed.name) != "gutenbergpy" and not parsed.url,
            f"legacy or direct URL requirement: {value}",
        )
    require(metadata["Name"] == "lcats", "unexpected distribution name")
    require(bool(metadata["Version"]), "missing distribution version")
    return {
        "name": metadata["Name"],
        "version": metadata["Version"],
        "requires_python": metadata["Requires-Python"],
        "requires_dist": sorted(dependencies),
    }


def main(argv=None):
    """Require complete equality before writing a successful evidence report."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "ref", "wheel", "sdist", "installed_lcats", "output"):
        parser.add_argument(name)
    args = parser.parse_args(argv)
    root = pathlib.Path(args.repository).resolve()
    output = pathlib.Path(args.output).resolve()
    require(not output.exists(), "output already exists")
    require(not output.is_relative_to(root), "output must be outside repository")

    def git(*parts):
        return subprocess.check_output(["git", *parts], cwd=root, timeout=30)

    commit = git("rev-parse", args.ref + "^{commit}").decode().strip()
    files = (
        git("ls-tree", "-r", "--name-only", commit, "--", "lcats/src/lcats")
        .decode()
        .splitlines()
    )
    expected = {
        name.removeprefix("lcats/src/"): git("show", f"{commit}:{name}")
        for name in files
    }
    require(bool(expected), "no package files found")
    # Inspect actual imports rather than rejecting historical explanatory prose.
    for name, raw in expected.items():
        if name.endswith(".py"):
            for node in ast.walk(ast.parse(raw)):
                imported = []
                if isinstance(node, ast.Import):
                    imported = [item.name for item in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imported = [node.module or ""]
                require(
                    not any(x.split(".")[0] == "gutenbergpy" for x in imported),
                    f"legacy import in {name}",
                )
    with zipfile.ZipFile(args.wheel) as wheel:
        require(
            len(wheel.namelist()) == len(set(wheel.namelist())), "duplicate zip member"
        )
        wheel_files = {
            name: wheel.read(name)
            for name in wheel.namelist()
            if name.startswith("lcats/") and not name.endswith("/")
        }
        (metadata_name,) = [
            x for x in wheel.namelist() if x.endswith(".dist-info/METADATA")
        ]
        wheel_metadata = dependency_metadata(wheel.read(metadata_name))
    with tarfile.open(args.sdist, "r:gz") as archive:
        members = [x for x in archive.getmembers() if x.isfile()]
        names = [x.name for x in members]
        require(len(names) == len(set(names)), "duplicate tar member")
        prefixes = {name.split("/", 1)[0] for name in names}
        require(len(prefixes) == 1, "sdist has multiple roots")
        prefix = prefixes.pop() + "/"
        contents = {
            x.name.removeprefix(prefix): archive.extractfile(x).read() for x in members
        }
        sdist_files = {
            name.removeprefix("src/"): raw
            for name, raw in contents.items()
            if name.startswith("src/lcats/")
        }
        sdist_metadata = dependency_metadata(contents["PKG-INFO"])
        for name in ("pyproject.toml", "README.md", "LICENSE"):
            require(contents[name] == git("show", f"{commit}:lcats/{name}"), name)
    installed = pathlib.Path(args.installed_lcats).resolve()
    require("site-packages" in installed.parts, "not a physical installed package")
    require(not installed.is_relative_to(root), "installation is inside checkout")
    installed_files = {
        "lcats/" + str(p.relative_to(installed)): p.read_bytes()
        for p in installed.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }
    installed_metadata = dependency_metadata(
        (installed.parent / metadata_name).read_bytes()
    )
    for label, actual in (
        ("wheel", wheel_files),
        ("sdist", sdist_files),
        ("installed", installed_files),
    ):
        require(set(actual) == set(expected), f"{label} package file set differs")
        require(
            all(actual[n] == b for n, b in expected.items()), f"{label} bytes differ"
        )
    require(wheel_metadata == sdist_metadata == installed_metadata, "metadata differs")
    report = {
        "completed": True,
        "product_commit": commit,
        "runner_sha256": sha(pathlib.Path(__file__).read_bytes()),
        "wheel": {
            "name": pathlib.Path(args.wheel).name,
            "sha256": sha(pathlib.Path(args.wheel).read_bytes()),
        },
        "sdist": {
            "name": pathlib.Path(args.sdist).name,
            "sha256": sha(pathlib.Path(args.sdist).read_bytes()),
        },
        "metadata": wheel_metadata,
        "python_files": sum(n.endswith(".py") for n in expected),
        "json_files": sum(n.endswith(".json") for n in expected),
        "other_files": sum(not n.endswith((".py", ".json")) for n in expected),
        "source_sha256": {n: sha(b) for n, b in expected.items()},
        "all_four_package_trees_equal": True,
        "legacy_static_imports": [],
        "scope": "Exact package identity and metadata; behavioral and platform qualification are separate.",
    }
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                "completed": True,
                "files": len(expected),
                "version": wheel_metadata["version"],
            }
        )
    )


if __name__ == "__main__":
    main()
