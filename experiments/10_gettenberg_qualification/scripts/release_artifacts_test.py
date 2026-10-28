"""Offline checks for the release evidence gate, including false-success defenses.

From the scripts directory: python -m unittest release_artifacts_test -v
Uses tiny synthetic Git/zip/tar/install trees under temporary directories; no LCATS
imports, external downloads, shared caches or configured Git identity are needed.
"""

import contextlib
import io
import json
import pathlib
import subprocess
import tarfile
import tempfile
import unittest
import zipfile

import qualify_release_artifacts


class ReleaseArtifactTest(unittest.TestCase):
    """Reject dependency and byte-identity failures before reporting completion."""

    def metadata(self, dependency="PyYAML>=6"):
        return f"Name: lcats\nVersion: 1.0\nRequires-Python: >=3.10\nRequires-Dist: {dependency}\n\n".encode()

    def test_ordinary_requirement(self):
        result = qualify_release_artifacts.dependency_metadata(self.metadata())
        self.assertEqual(result["requires_dist"], ["PyYAML>=6"])

    def test_legacy_requirement_is_rejected_even_when_extra_is_inactive(self):
        with self.assertRaisesRegex(ValueError, "legacy or direct URL"):
            qualify_release_artifacts.dependency_metadata(
                self.metadata('GutenbergPy; extra == "optional"')
            )

    def test_all_direct_url_schemes_are_rejected(self):
        for url in (
            "https://example.invalid/a.whl",
            "file:///tmp/a.whl",
            "git+https://example.invalid/a.git",
        ):
            with self.subTest(url=url), self.assertRaisesRegex(
                ValueError, "direct URL"
            ):
                qualify_release_artifacts.dependency_metadata(
                    self.metadata(f"thing @ {url}")
                )

    def exercise(
        self, *, changed_asset=False, missing_file=False, installed_extra=False
    ):
        """Use real containers and Git to test the gate, not mocked file comparisons."""
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            package = {
                "lcats/__init__.py": b'"""Fixture."""\n',
                "lcats/data.txt": b"retained data\n",
            }
            for name, raw in package.items():
                p = repo / "lcats/src" / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(raw)
            for name in ("pyproject.toml", "README.md", "LICENSE"):
                (repo / "lcats" / name).write_text("fixture\n")
            for args in (
                ["init", "-q"],
                ["add", "."],
                [
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    "-c",
                    "commit.gpgsign=false",
                    "commit",
                    "-qm",
                    "fixture",
                ],
            ):
                subprocess.run(
                    ["git", *args], cwd=repo, check=True, capture_output=True
                )
            wheel = root / "fixture.whl"
            metadata_name = "lcats-1.0.dist-info/METADATA"
            with zipfile.ZipFile(wheel, "w") as archive:
                for name, raw in package.items():
                    if missing_file and name.endswith(".txt"):
                        continue
                    archive.writestr(
                        name,
                        b"changed" if changed_asset and name.endswith(".txt") else raw,
                    )
                archive.writestr(metadata_name, self.metadata())
            sdist = root / "fixture.tar.gz"
            with tarfile.open(sdist, "w:gz") as archive:
                contents = {"src/" + n: b for n, b in package.items()}
                contents.update(
                    {
                        n: b"fixture\n"
                        for n in ("pyproject.toml", "README.md", "LICENSE")
                    }
                )
                contents["PKG-INFO"] = self.metadata()
                for name, raw in contents.items():
                    member = tarfile.TarInfo("lcats-1.0/" + name)
                    member.size = len(raw)
                    archive.addfile(member, io.BytesIO(raw))
            installed = root / "site-packages"
            for name, raw in {**package, metadata_name: self.metadata()}.items():
                p = installed / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(raw)
            if installed_extra:
                (installed / "lcats/extra.py").write_text("# stale installation\n")
            output = root / "report.json"
            args = [
                str(repo),
                "HEAD",
                str(wheel),
                str(sdist),
                str(installed / "lcats"),
                str(output),
            ]
            if changed_asset or missing_file or installed_extra:
                with self.assertRaises(ValueError):
                    qualify_release_artifacts.main(args)
                self.assertFalse(output.exists())
            else:
                with contextlib.redirect_stdout(io.StringIO()):
                    qualify_release_artifacts.main(args)
                self.assertTrue(
                    json.loads(output.read_text())["all_four_package_trees_equal"]
                )
                with self.assertRaisesRegex(ValueError, "output already exists"):
                    qualify_release_artifacts.main(args)

    def test_complete_package_including_non_python_asset(self):
        self.exercise()

    def test_changed_wheel_asset_cannot_pass(self):
        self.exercise(changed_asset=True)

    def test_missing_wheel_file_cannot_pass(self):
        self.exercise(missing_file=True)

    def test_extra_installed_module_cannot_pass(self):
        self.exercise(installed_extra=True)


if __name__ == "__main__":
    unittest.main()
