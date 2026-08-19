"""Scan full git history for leaked secrets and draft a filter-repo replacements file.

Runs gitleaks (https://github.com/gitleaks/gitleaks) with `--log-opts=--all`
against a repository's entire git history (every commit, every ref) rather
than just the working tree, so it catches secrets that were later deleted
but still live in old commits. Emits two files for human review:

  findings.json     - raw gitleaks report (rule, file, commit, line, secret)
  replacements.txt  - draft `git-filter-repo --replace-text` input, one
                       `<secret>==>***REMOVED-<RuleID>***` line per unique
                       secret found

Nothing here rewrites history or touches the repository under scan -
this script only reads and reports. Review both output files before
handing replacements.txt to purge_history.py; see the secrets_hygiene
README's "Manual steps" section for what to check before that handoff.

Requires the `gitleaks` binary on PATH:
https://github.com/gitleaks/gitleaks#installing
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess


def _check_gitleaks_available() -> None:
    if shutil.which("gitleaks") is None:
        print(
            "FAIL: `gitleaks` not found on PATH. Install it first, e.g.:\n"
            "  brew install gitleaks\n"
            "See https://github.com/gitleaks/gitleaks#installing for other platforms."
        )
        raise SystemExit(1)


def _run_gitleaks(repo_path: pathlib.Path, report_path: pathlib.Path) -> None:
    cmd = [
        "gitleaks",
        "detect",
        "--source",
        str(repo_path),
        "--log-opts=--all",
        "--report-format",
        "json",
        "--report-path",
        str(report_path),
        "--no-banner",
        "--exit-code",
        "0",
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def _load_findings(report_path: pathlib.Path) -> list[dict]:
    if not report_path.exists() or report_path.stat().st_size == 0:
        return []
    with report_path.open() as f:
        return json.load(f)


def _draft_replacements(findings: list[dict]) -> list[tuple[str, str]]:
    """Dedupe findings by secret value, return [(secret, placeholder), ...]."""
    by_secret: dict[str, str] = {}
    for finding in findings:
        secret = finding.get("Secret", "")
        rule_id = finding.get("RuleID", "unknown-rule")
        if not secret or secret in by_secret:
            continue
        by_secret[secret] = f"***REMOVED-{rule_id}***"
    return sorted(by_secret.items())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "repo_path",
        type=pathlib.Path,
        help="Path to the git repository (or mirror clone) to scan",
    )
    parser.add_argument(
        "--out-dir",
        type=pathlib.Path,
        required=True,
        help=(
            "Directory to write findings.json and replacements.txt into. "
            "Required (no cwd default): these files contain real secret "
            "values, so pick a location that is actually gitignored (e.g. "
            "lcats/experimental/secrets_hygiene/scratch/) rather than "
            "risking them landing somewhere a later `git add .` would pick "
            "up."
        ),
    )
    args = parser.parse_args()

    _check_gitleaks_available()

    repo_path = args.repo_path.resolve()
    if not (repo_path / ".git").exists() and not (repo_path / "HEAD").exists():
        print(f"FAIL: {repo_path} does not look like a git repo or mirror clone.")
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.out_dir / "findings.json"
    replacements_path = args.out_dir / "replacements.txt"

    _run_gitleaks(repo_path, report_path)
    findings = _load_findings(report_path)

    print(f"\ngitleaks found {len(findings)} finding(s) across all history.")
    if not findings:
        print("Nothing to purge. Not writing replacements.txt.")
        return 0

    replacements = _draft_replacements(findings)
    with replacements_path.open("w") as f:
        for secret, placeholder in replacements:
            f.write(f"{secret}==>{placeholder}\n")

    print(f"Wrote {len(findings)} raw finding(s) to {report_path}")
    print(f"Wrote {len(replacements)} unique secret(s) to {replacements_path}")
    print(
        "\nSTOP: do not hand replacements.txt to purge_history.py yet.\n"
        "Review findings.json for false positives (test fixtures, hashes,\n"
        "placeholder examples in docs) and confirm every line in\n"
        "replacements.txt is a real secret before proceeding. See the\n"
        "secrets_hygiene README's 'Manual steps' section."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
