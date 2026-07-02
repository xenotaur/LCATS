"""Tests for lcats.utils.secrets.load_secrets."""

import os
import pathlib
import tempfile
import unittest

from lcats.utils import secrets


class TestLoadSecretsFromFile(unittest.TestCase):
    """Keys not in the environment are loaded from .env files."""

    def test_loads_key_from_env_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = pathlib.Path(tmpdir) / "test_api_keys.env"
            env_file.write_text("TEST_LCATS_KEY=sentinel-value\n")
            os.environ.pop("TEST_LCATS_KEY", None)
            try:
                secrets.load_secrets(secrets_dir=pathlib.Path(tmpdir))
                self.assertEqual(os.environ.get("TEST_LCATS_KEY"), "sentinel-value")
            finally:
                os.environ.pop("TEST_LCATS_KEY", None)


class TestLoadSecretsNoOverride(unittest.TestCase):
    """Already-exported variables are not overridden."""

    def test_does_not_override_existing_env_var(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = pathlib.Path(tmpdir) / "test_api_keys.env"
            env_file.write_text("TEST_LCATS_KEY=from-file\n")
            os.environ["TEST_LCATS_KEY"] = "from-shell"
            try:
                secrets.load_secrets(secrets_dir=pathlib.Path(tmpdir))
                self.assertEqual(os.environ.get("TEST_LCATS_KEY"), "from-shell")
            finally:
                os.environ.pop("TEST_LCATS_KEY", None)


class TestLoadSecretsMissingDir(unittest.TestCase):
    """Missing secrets_dir is a silent no-op."""

    def test_missing_dir_does_not_raise(self):
        nonexistent = pathlib.Path("/tmp/lcats_test_no_such_dir_xyz")
        try:
            secrets.load_secrets(secrets_dir=nonexistent)
        except Exception as exc:  # pragma: no cover
            self.fail(f"load_secrets raised unexpectedly: {exc}")


class TestLoadSecretsMultipleFiles(unittest.TestCase):
    """All .env files in secrets_dir are loaded."""

    def test_loads_from_multiple_env_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (pathlib.Path(tmpdir) / "a_keys.env").write_text("TEST_LCATS_A=val-a\n")
            (pathlib.Path(tmpdir) / "b_keys.env").write_text("TEST_LCATS_B=val-b\n")
            for key in ("TEST_LCATS_A", "TEST_LCATS_B"):
                os.environ.pop(key, None)
            try:
                secrets.load_secrets(secrets_dir=pathlib.Path(tmpdir))
                self.assertEqual(os.environ.get("TEST_LCATS_A"), "val-a")
                self.assertEqual(os.environ.get("TEST_LCATS_B"), "val-b")
            finally:
                for key in ("TEST_LCATS_A", "TEST_LCATS_B"):
                    os.environ.pop(key, None)


class TestLoadSecretsExplicitDir(unittest.TestCase):
    """Explicit secrets_dir argument is respected over the default."""

    def test_explicit_dir_overrides_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = pathlib.Path(tmpdir) / "explicit.env"
            env_file.write_text("TEST_LCATS_EXPLICIT=explicit-val\n")
            os.environ.pop("TEST_LCATS_EXPLICIT", None)
            try:
                secrets.load_secrets(secrets_dir=pathlib.Path(tmpdir))
                self.assertEqual(os.environ.get("TEST_LCATS_EXPLICIT"), "explicit-val")
            finally:
                os.environ.pop("TEST_LCATS_EXPLICIT", None)


if __name__ == "__main__":
    unittest.main()
