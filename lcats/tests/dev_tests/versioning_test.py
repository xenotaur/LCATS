"""Tests for the lcats.dev.versioning release-workflow helper module."""

import contextlib
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from lcats.dev import versioning
from lcats.utils import capture


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["stub"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _git(repo_path, *args):
    subprocess.run(["git", *args], cwd=repo_path, check=True, capture_output=True)


@contextlib.contextmanager
def _temporary_git_repo(with_remote=False):
    """A throwaway git repo (with one commit) that versioning._repo_root points at.

    Used to exercise create_tag()/push_tag() against real git rather than
    mocking every collaborator -- see AGENTS.md's mocking/test philosophy
    ("avoid heavy mocking... validate behavior, not that mocks were
    called") and the review finding on WI-RELEASE-0038's original tests,
    which mocked git entirely and so never actually proved a tag could be
    created (missing the "--annotate"-style option-like-name bug).
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = pathlib.Path(tmp_dir) / "repo"
        repo_path.mkdir()
        _git(repo_path, "init", "-q")
        _git(repo_path, "config", "user.email", "test@example.com")
        _git(repo_path, "config", "user.name", "Test")
        (repo_path / "README.md").write_text("test\n")
        _git(repo_path, "add", "README.md")
        _git(repo_path, "commit", "-q", "-m", "initial commit")

        if with_remote:
            remote_path = pathlib.Path(tmp_dir) / "origin.git"
            subprocess.run(
                ["git", "init", "-q", "--bare", str(remote_path)], check=True
            )
            _git(repo_path, "remote", "add", "origin", str(remote_path))

        with mock.patch("lcats.dev.versioning._repo_root", return_value=repo_path):
            yield repo_path


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

    def test_rejects_option_like_tag_name(self):
        # git check-ref-format accepts "--annotate" as a syntactically
        # valid ref name, but "git tag --annotate" would then be
        # interpreted as a CLI option and fail -- reject it up front,
        # with no subprocess call needed since this short-circuits first.
        with self.assertRaises(versioning.VersioningError):
            versioning._ensure_valid_tag("--annotate")


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
    """Exercises create_tag() against a real temporary git repo.

    Only verify_release() is mocked -- it has its own dedicated test
    class above, and running the real scripts/lint|format|test suite
    against a throwaway repo with no scripts/ directory doesn't make
    sense. Everything else (tag validation, HEAD/tag resolution, and
    the actual "git tag" invocation) runs for real.
    """

    def test_noop_when_tag_already_at_head(self):
        with _temporary_git_repo() as repo_path:
            _git(repo_path, "tag", "v1.0.0")
            with capture.capture_output() as captured:
                versioning.create_tag("v1.0.0")
        self.assertIn("already exists at HEAD", captured.stdout.getvalue())

    def test_raises_when_tag_exists_elsewhere(self):
        with _temporary_git_repo() as repo_path:
            _git(repo_path, "tag", "v1.0.0")
            (repo_path / "second.txt").write_text("more\n")
            _git(repo_path, "add", "second.txt")
            _git(repo_path, "commit", "-q", "-m", "second commit")
            with self.assertRaises(versioning.VersioningError):
                versioning.create_tag("v1.0.0")

    @mock.patch("lcats.dev.versioning.verify_release")
    def test_creates_tag_after_verification_when_absent(self, mock_verify):
        with _temporary_git_repo() as repo_path:
            with capture.capture_output() as captured:
                versioning.create_tag("v1.0.0")
            tag_exists = subprocess.run(
                ["git", "rev-parse", "--verify", "refs/tags/v1.0.0"],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )
        mock_verify.assert_called_once_with("v1.0.0")
        self.assertEqual(0, tag_exists.returncode, "git tag was not actually created")
        self.assertIn("Created tag v1.0.0", captured.stdout.getvalue())

    @mock.patch("lcats.dev.versioning.verify_release")
    def test_rejects_option_like_tag_name_before_verification(self, mock_verify):
        with _temporary_git_repo():
            with self.assertRaises(versioning.VersioningError):
                versioning.create_tag("--annotate")
        mock_verify.assert_not_called()


class TestPushTag(unittest.TestCase):
    """Exercises push_tag() against a real local git repo and remote.

    The "remote" is a local bare repo, so there is no genuine network
    boundary to mock here -- push_tag runs against real git end to end.
    """

    def test_raises_when_local_tag_missing(self):
        with _temporary_git_repo(with_remote=True):
            with self.assertRaises(versioning.VersioningError):
                versioning.push_tag("v1.0.0")

    def test_pushes_when_absent_on_remote(self):
        with _temporary_git_repo(with_remote=True) as repo_path:
            _git(repo_path, "tag", "v1.0.0")
            with capture.capture_output() as captured:
                versioning.push_tag("v1.0.0")
            remote_check = subprocess.run(
                ["git", "ls-remote", "--tags", "origin", "v1.0.0"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertIn("v1.0.0", remote_check.stdout, "tag was not actually pushed")
        self.assertIn("Pushed tag v1.0.0", captured.stdout.getvalue())

    def test_noop_when_remote_matches_local(self):
        with _temporary_git_repo(with_remote=True) as repo_path:
            _git(repo_path, "tag", "v1.0.0")
            _git(repo_path, "push", "origin", "refs/tags/v1.0.0")
            with capture.capture_output() as captured:
                versioning.push_tag("v1.0.0")
        self.assertIn("already exists on origin", captured.stdout.getvalue())

    def test_raises_when_remote_diverges(self):
        with _temporary_git_repo(with_remote=True) as repo_path:
            _git(repo_path, "tag", "v1.0.0")
            _git(repo_path, "push", "origin", "refs/tags/v1.0.0")
            # Move the local tag to point at a different commit than
            # what's already on origin, simulating a diverged remote.
            _git(repo_path, "tag", "-d", "v1.0.0")
            (repo_path / "second.txt").write_text("more\n")
            _git(repo_path, "add", "second.txt")
            _git(repo_path, "commit", "-q", "-m", "second commit")
            _git(repo_path, "tag", "v1.0.0")
            with self.assertRaises(versioning.VersioningError):
                versioning.push_tag("v1.0.0")


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
