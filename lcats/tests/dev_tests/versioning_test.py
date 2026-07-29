"""Tests for the lcats.dev.versioning release-workflow helper module."""

import subprocess
import unittest
from unittest import mock

from lcats.dev import versioning
from lcats.utils import capture


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["stub"], returncode=returncode, stdout=stdout, stderr=stderr
    )


class TestEnsureValidTag(unittest.TestCase):

    @mock.patch("lcats.dev.versioning._run_command")
    def test_raises_on_invalid_tag(self, mock_run_command):
        mock_run_command.return_value = _completed(returncode=1)
        with self.assertRaises(versioning.VersioningError):
            versioning._ensure_valid_tag("not a valid tag")

    @mock.patch("lcats.dev.versioning._run_command")
    def test_accepts_valid_tag(self, mock_run_command):
        mock_run_command.return_value = _completed(returncode=0)
        versioning._ensure_valid_tag("v1.0.0")  # should not raise


class TestEnsureCleanWorkingTree(unittest.TestCase):

    @mock.patch("lcats.dev.versioning._run_command")
    @mock.patch("lcats.dev.versioning._ensure_command_exists")
    def test_raises_when_tree_is_dirty(self, _mock_ensure_git, mock_run_command):
        mock_run_command.return_value = _completed(stdout=" M some_file.py\n")
        with self.assertRaises(versioning.VersioningError):
            versioning._ensure_clean_working_tree()

    @mock.patch("lcats.dev.versioning._run_command")
    @mock.patch("lcats.dev.versioning._ensure_command_exists")
    def test_passes_when_tree_is_clean(self, _mock_ensure_git, mock_run_command):
        mock_run_command.return_value = _completed(stdout="")
        versioning._ensure_clean_working_tree()  # should not raise


class TestVerifyRelease(unittest.TestCase):

    @mock.patch("lcats.dev.versioning._run_verification_commands")
    @mock.patch("lcats.dev.versioning._ensure_clean_working_tree")
    @mock.patch("lcats.dev.versioning._ensure_valid_tag")
    def test_validates_tag_when_given(
        self, mock_ensure_valid_tag, _mock_clean_tree, _mock_run_checks
    ):
        versioning.verify_release("v1.0.0")
        mock_ensure_valid_tag.assert_called_once_with("v1.0.0")

    @mock.patch("lcats.dev.versioning._run_verification_commands")
    @mock.patch("lcats.dev.versioning._ensure_clean_working_tree")
    @mock.patch("lcats.dev.versioning._ensure_valid_tag")
    def test_skips_tag_validation_when_absent(
        self, mock_ensure_valid_tag, _mock_clean_tree, _mock_run_checks
    ):
        versioning.verify_release("")
        mock_ensure_valid_tag.assert_not_called()

    @mock.patch("lcats.dev.versioning._run_command")
    def test_raises_when_a_check_fails(self, mock_run_command):
        # status --porcelain (clean) then scripts/lint fails.
        mock_run_command.side_effect = [
            _completed(stdout=""),
            _completed(returncode=1),
        ]
        with capture.capture_output():
            with self.assertRaises(versioning.VersioningError):
                versioning.verify_release("")


class TestCreateTag(unittest.TestCase):

    @mock.patch("lcats.dev.versioning._resolve_local_tag_commit")
    @mock.patch("lcats.dev.versioning._resolve_head_commit")
    @mock.patch("lcats.dev.versioning._ensure_valid_tag")
    def test_noop_when_tag_already_at_head(
        self, _mock_valid, mock_head, mock_local_tag
    ):
        mock_head.return_value = "abc123"
        mock_local_tag.return_value = "abc123"
        with capture.capture_output() as captured:
            versioning.create_tag("v1.0.0")
        self.assertIn("already exists at HEAD", captured.stdout.getvalue())

    @mock.patch("lcats.dev.versioning._resolve_local_tag_commit")
    @mock.patch("lcats.dev.versioning._resolve_head_commit")
    @mock.patch("lcats.dev.versioning._ensure_valid_tag")
    def test_raises_when_tag_exists_elsewhere(
        self, _mock_valid, mock_head, mock_local_tag
    ):
        mock_head.return_value = "abc123"
        mock_local_tag.return_value = "def456"
        with self.assertRaises(versioning.VersioningError):
            versioning.create_tag("v1.0.0")

    @mock.patch("lcats.dev.versioning._run_command")
    @mock.patch("lcats.dev.versioning.verify_release")
    @mock.patch("lcats.dev.versioning._resolve_local_tag_commit")
    @mock.patch("lcats.dev.versioning._resolve_head_commit")
    @mock.patch("lcats.dev.versioning._ensure_valid_tag")
    def test_creates_tag_after_verification_when_absent(
        self,
        _mock_valid,
        mock_head,
        mock_local_tag,
        mock_verify,
        mock_run_command,
    ):
        mock_head.return_value = "abc123"
        mock_local_tag.return_value = None
        mock_run_command.return_value = _completed(returncode=0)
        with capture.capture_output() as captured:
            versioning.create_tag("v1.0.0")
        mock_verify.assert_called_once_with("v1.0.0")
        mock_run_command.assert_called_once_with(["git", "tag", "v1.0.0"])
        self.assertIn("Created tag v1.0.0", captured.stdout.getvalue())


class TestPushTag(unittest.TestCase):

    @mock.patch("lcats.dev.versioning._resolve_local_tag_commit")
    @mock.patch("lcats.dev.versioning._ensure_valid_tag")
    def test_raises_when_local_tag_missing(self, _mock_valid, mock_local_tag):
        mock_local_tag.return_value = None
        with self.assertRaises(versioning.VersioningError):
            versioning.push_tag("v1.0.0")

    @mock.patch("lcats.dev.versioning._resolve_remote_tag_commit")
    @mock.patch("lcats.dev.versioning._resolve_local_tag_commit")
    @mock.patch("lcats.dev.versioning._ensure_valid_tag")
    def test_noop_when_remote_matches_local(
        self, _mock_valid, mock_local_tag, mock_remote_tag
    ):
        mock_local_tag.return_value = "abc123"
        mock_remote_tag.return_value = "abc123"
        with capture.capture_output() as captured:
            versioning.push_tag("v1.0.0")
        self.assertIn("already exists on origin", captured.stdout.getvalue())

    @mock.patch("lcats.dev.versioning._resolve_remote_tag_commit")
    @mock.patch("lcats.dev.versioning._resolve_local_tag_commit")
    @mock.patch("lcats.dev.versioning._ensure_valid_tag")
    def test_raises_when_remote_diverges(
        self, _mock_valid, mock_local_tag, mock_remote_tag
    ):
        mock_local_tag.return_value = "abc123"
        mock_remote_tag.return_value = "def456"
        with self.assertRaises(versioning.VersioningError):
            versioning.push_tag("v1.0.0")

    @mock.patch("lcats.dev.versioning._run_command")
    @mock.patch("lcats.dev.versioning._resolve_remote_tag_commit")
    @mock.patch("lcats.dev.versioning._resolve_local_tag_commit")
    @mock.patch("lcats.dev.versioning._ensure_valid_tag")
    def test_pushes_when_absent_on_remote(
        self,
        _mock_valid,
        mock_local_tag,
        mock_remote_tag,
        mock_run_command,
    ):
        mock_local_tag.return_value = "abc123"
        mock_remote_tag.return_value = None
        mock_run_command.return_value = _completed(returncode=0)
        with capture.capture_output() as captured:
            versioning.push_tag("v1.0.0")
        mock_run_command.assert_called_once_with(
            ["git", "push", "origin", "refs/tags/v1.0.0"]
        )
        self.assertIn("Pushed tag v1.0.0", captured.stdout.getvalue())


class TestPrintToolVersions(unittest.TestCase):

    @mock.patch("lcats.dev.versioning._run_command")
    def test_prints_package_cli_and_toolchain_versions(self, mock_run_command):
        mock_run_command.return_value = _completed(stdout="stub version output")
        with mock.patch("lcats.version.get_installed_version", return_value="1.2.3"):
            with capture.capture_output() as captured:
                versioning.print_tool_versions()
        output = captured.stdout.getvalue()
        self.assertIn("LCATS package metadata", output)
        self.assertIn("lcats 1.2.3", output)
        self.assertIn("lcats CLI", output)
        self.assertIn("Python", output)
        self.assertIn("Ruff", output)
        self.assertIn("Black", output)
        self.assertIn("pip", output)
        # Toolchain scoped to LCATS's actual dev extras, not LRH's list.
        self.assertNotIn("Pylint", output)
        self.assertNotIn("Pyright", output)


class TestMainDispatch(unittest.TestCase):

    @mock.patch("lcats.dev.versioning.print_lcats_version")
    def test_no_command_prints_version(self, mock_print_version):
        result = versioning.main([])
        self.assertEqual(0, result)
        mock_print_version.assert_called_once()

    @mock.patch("lcats.dev.versioning.print_tool_versions")
    def test_tools_command(self, mock_print_tools):
        result = versioning.main(["tools"])
        self.assertEqual(0, result)
        mock_print_tools.assert_called_once()

    @mock.patch("lcats.dev.versioning.verify_release")
    def test_verify_command(self, mock_verify):
        result = versioning.main(["verify", "v1.0.0"])
        self.assertEqual(0, result)
        mock_verify.assert_called_once_with("v1.0.0")

    @mock.patch("lcats.dev.versioning.create_tag")
    def test_tag_command(self, mock_create_tag):
        result = versioning.main(["tag", "v1.0.0"])
        self.assertEqual(0, result)
        mock_create_tag.assert_called_once_with("v1.0.0")

    @mock.patch("lcats.dev.versioning.push_tag")
    def test_push_command(self, mock_push_tag):
        result = versioning.main(["push", "v1.0.0"])
        self.assertEqual(0, result)
        mock_push_tag.assert_called_once_with("v1.0.0")

    @mock.patch("lcats.dev.versioning.verify_release")
    def test_versioning_error_returns_exit_code_one(self, mock_verify):
        mock_verify.side_effect = versioning.VersioningError("boom")
        with capture.capture_output():
            result = versioning.main(["verify"])
        self.assertEqual(1, result)


if __name__ == "__main__":
    unittest.main()
