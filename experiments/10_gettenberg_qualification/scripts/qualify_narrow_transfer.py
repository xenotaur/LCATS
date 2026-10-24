"""Verify a narrow candidate wheel and transfer dated catalog evidence.

Run with the LCATS project Python, supplying repository, full product commit,
wheel and a new output JSON outside the repository. This reads immutable Git and
prior experiment records; it does not import product code or access the network.

The expected four-module delta deliberately pins this experiment to the narrow
candidate. A changed product or historical ledger fails instead of silently
transferring evidence. Static local import closure supports the catalog transfer;
it is not a proof about arbitrary dynamic imports or dependency-version behavior.
"""

import argparse
import ast
import hashlib
import json
import pathlib
import subprocess
import zipfile


def sha(raw):
    """Return the byte identity used by the existing experiment ledgers."""
    return hashlib.sha256(raw).hexdigest()


def main(argv=None):
    """Compare complete wheel bytes and measured component source identities."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=lambda value: pathlib.Path(value).resolve())
    parser.add_argument("product_ref")
    parser.add_argument("wheel", type=lambda value: pathlib.Path(value).resolve())
    parser.add_argument("output", type=lambda value: pathlib.Path(value).resolve())
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_relative_to(args.repository):
        parser.error("output must be fresh and outside the repository")
    root = args.repository
    ref = args.product_ref

    def git_bytes(path):
        """Read the reviewed tree, never a staged or dirty substitute."""
        return subprocess.check_output(
            ["git", "show", f"{ref}:{path}"], cwd=root, timeout=30
        )

    # Pin all product Python and data files, including modules not imported by smoke.
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", ref, "--", "lcats/src/lcats"],
        text=True,
        cwd=root,
        timeout=30,
    ).splitlines()
    expected = {
        name.removeprefix("lcats/src/"): git_bytes(name)
        for name in paths
        if name.endswith((".py", ".json"))
    }
    for name, raw in expected.items():
        assert (root / "lcats/src" / name).read_bytes() == raw, name
    wheel_path = args.wheel
    with zipfile.ZipFile(wheel_path) as wheel:
        actual = {
            name: wheel.read(name)
            for name in wheel.namelist()
            if name.startswith("lcats/") and not name.endswith("/")
        }
        assert set(actual) == set(expected), (
            set(actual) - set(expected),
            set(expected) - set(actual),
        )
        assert all(actual[name] == raw for name, raw in expected.items())
        (metadata_name,) = [
            name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")
        ]
        metadata = wheel.read(metadata_name).decode()
        requires = [
            line for line in metadata.splitlines() if line.startswith("Requires-Dist:")
        ]
        assert not any(
            "gutenbergpy" in line.lower() or "git+" in line for line in requires
        )

    # Reuse earlier measurements only for byte-identical components. These are not
    # rerun timings, and the revised cleanup outcomes must use the newer corpus evidence.
    prior_root = (
        root
        / "experiments/10_gettenberg_qualification/results/gettenberg-qualification-20261018"
    )
    old = json.loads((prior_root / "source-ledger.json").read_text())
    changed = []
    for name, digest in old["product_sha256"].items():
        if sha((root / "lcats" / name).read_bytes()) != digest:
            changed.append(name)
    assert set(changed) == {
        "src/lcats/gettenberg/cleanup.py",
        "src/lcats/gatherers/gutenberg_source.py",
        "src/lcats/gatherers/main.py",
        "src/lcats/gatherers/mass_quantities/gatherer.py",
    }
    transfers = {}
    for label in ("snapshot", "lifecycle"):
        report_path = prior_root / f"{label}.json"
        report = json.loads(report_path.read_text())
        matches, differences = [], []
        for name, digest in report["source_sha256"].items():
            target = (
                matches
                if sha((root / "lcats" / name).read_bytes()) == digest
                else differences
            )
            target.append(name)
        assert differences == ["src/lcats/gettenberg/cleanup.py"]
        assert report["qualified"]
        transfers[label] = {
            "report_sha256": sha(report_path.read_bytes()),
            "matching_modules": matches,
            "changed_modules": differences,
        }

    # Check static LCATS import closure from the measured catalog entry points. This
    # establishes that the changed cleanup/gather modules are outside that closure;
    # it is not a general proof about arbitrary future dynamic/plugin imports.
    modules = {}
    for name, raw in expected.items():
        if name.endswith(".py"):
            module = name[:-3].replace("/", ".").removesuffix(".__init__")
            modules[module] = raw
    edges = {}
    for module, raw in modules.items():
        imported = set()
        for node in ast.walk(ast.parse(raw)):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.update(node.module + "." + alias.name for alias in node.names)
        edges[module] = imported & modules.keys()
    seen, pending = set(), [
        "lcats.gettenberg.catalog",
        "lcats.gettenberg.lifecycle",
        "lcats.gettenberg.ingestion",
        "lcats.gettenberg.rdf",
    ]
    while pending:
        name = pending.pop()
        if name not in seen:
            seen.add(name)
            pending.extend(edges[name] - seen)
    assert not seen.intersection(
        {
            "lcats.gettenberg.cleanup",
            "lcats.gatherers.gutenberg_source",
            "lcats.gatherers.main",
            "lcats.gatherers.mass_quantities.gatherer",
        }
    )
    result = {
        "reviewed_ref": ref,
        "runner_sha256": sha(pathlib.Path(__file__).read_bytes()),
        "wheel_filename": wheel_path.name,
        "wheel_sha256": sha(wheel_path.read_bytes()),
        "qualification_version_only": True,
        "exact_wheel_source_and_data_match": True,
        "python_files": sum(name.endswith(".py") for name in expected),
        "json_files": sum(name.endswith(".json") for name in expected),
        "source_sha256": {name: sha(raw) for name, raw in expected.items()},
        "requirements": requires,
        "prior_product_modules": len(old["product_sha256"]),
        "changed_since_prior_product_ledger": changed,
        "transfers": transfers,
        "catalog_static_import_closure": sorted(seen),
        "historical_environment": old["environment"],
        "limits": [
            "Historical performance figures are not rerun benchmarks.",
            "Revised cleanup/gather outcomes use 2026-10-23 census and current independent replay.",
            "Fresh wheel dependencies/smoke are separately recorded; not a full-snapshot run on every supported dependency version.",
        ],
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "reviewed_ref",
                    "python_files",
                    "json_files",
                    "exact_wheel_source_and_data_match",
                    "changed_since_prior_product_ledger",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
