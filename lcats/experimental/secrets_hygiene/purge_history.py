"""Scrub leaked secrets from git history in a fresh mirror clone.

Wraps git-filter-repo (https://github.com/newren/git-filter-repo), the tool
GitHub's own docs recommend over the deprecated BFG/`git filter-branch` for
removing sensitive data from history:
https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository

This script:
  1. creates a fresh `--mirror` clone of the target repo in a scratch dir
     (never touches your working checkout),
  2. runs `git-filter-repo --replace-text` against it, scoped to the refs
     you pass in,
  3. re-scans the rewritten refs (only the ones just rewritten, not every
     ref in the mirror - an intentionally out-of-scope ref may still
     legitimately contain the secret) to confirm no replaced secret remains,
  4. prints the `git push --force` command for you to run yourself.

It deliberately does NOT push. Force-pushing a rewritten history is a
destructive, shared-system-affecting action - see the secrets_hygiene
README's "Before you run this" section. Review the printed diff and the
verification step's output, coordinate with anyone who has a clone of an
affected branch, and only then run the printed push command by hand.

Requires:
  - `git-filter-repo` on PATH (pip install git-filter-repo, or
    brew install git-filter-repo)
  - a replacements file, one `<secret>==>PLACEHOLDER` per line, e.g. the
    replacements.txt written by find_secrets.py after human review
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import tempfile


def _check_filter_repo_available() -> None:
    if shutil.which("git-filter-repo") is None:
        print(
            "FAIL: `git-filter-repo` not found on PATH. Install it first, e.g.:\n"
            "  pip install git-filter-repo\n"
            "  # or: brew install git-filter-repo\n"
            "See https://github.com/newren/git-filter-repo#how-do-i-install-it"
        )
        raise SystemExit(1)


def _read_refs(refs_file: pathlib.Path | None) -> list[str] | None:
    if refs_file is None:
        return None
    lines = [
        line.strip()
        for line in refs_file.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        print(f"FAIL: {refs_file} has no ref lines. Refusing to run unscoped.")
        raise SystemExit(1)
    return lines


def _mirror_clone(source: str, dest: pathlib.Path) -> None:
    print(f"Cloning mirror of {source} into {dest} ...")
    subprocess.run(["git", "clone", "--mirror", source, str(dest)], check=True)


def _run_filter_repo(
    mirror_path: pathlib.Path, replacements_file: pathlib.Path, refs: list[str] | None
) -> None:
    cmd = [
        "git-filter-repo",
        "--replace-text",
        str(replacements_file.resolve()),
        "--force",
    ]
    for ref in refs or []:
        cmd += ["--refs", ref]
    print(f"Running in {mirror_path}: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=mirror_path)


def _verify_clean(
    mirror_path: pathlib.Path, replacements_file: pathlib.Path, refs: list[str]
) -> bool:
    secrets = []
    for line in replacements_file.read_text().splitlines():
        line = line.strip()
        if not line or "==>" not in line:
            continue
        secret, _, _ = line.partition("==>")
        if not secret:
            continue
        secrets.append(secret)

    all_clean = True
    for secret in secrets:
        # No --pickaxe-regex: -S takes the secret as a literal string here.
        # With --pickaxe-regex, any regex metacharacter in the secret (+, .,
        # (, etc. - common in base64-ish keys) changes what's actually being
        # searched for, which can silently produce a false "clean" verdict
        # and let a force-push go out with the secret still present.
        #
        # Checking only `refs` (not --all): verification is scoped to
        # exactly the refs this run rewrote. A secret still present on a
        # ref that was deliberately excluded from --refs-file is expected
        # and must not fail verification of the refs that WERE rewritten.
        result = subprocess.run(
            ["git", "log", *refs, "-S", secret, "--oneline"],
            check=True,
            cwd=mirror_path,
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            print("STILL PRESENT: a rewritten ref still matches a listed secret "
                  "(not printing the secret itself here - check replacements.txt "
                  "for which one, by rule/placeholder).")
            all_clean = False
    return all_clean


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Repo URL or local path to purge (e.g. origin's URL)")
    parser.add_argument(
        "replacements_file",
        type=pathlib.Path,
        help="Reviewed replacements file (see find_secrets.py)",
    )
    parser.add_argument(
        "--refs-file",
        type=pathlib.Path,
        default=None,
        help=(
            "File listing one ref per line to scope the rewrite to "
            "(e.g. refs/heads/main). Omit to rewrite every ref in the mirror - "
            "not recommended without deliberately choosing that scope first."
        ),
    )
    parser.add_argument(
        "--mirror-dir",
        type=pathlib.Path,
        default=None,
        help="Where to create the mirror clone (default: a temp directory)",
    )
    args = parser.parse_args()

    _check_filter_repo_available()

    if not args.replacements_file.exists():
        print(f"FAIL: {args.replacements_file} does not exist.")
        return 1

    refs = _read_refs(args.refs_file)
    if refs is None:
        print(
            "No --refs-file given: this will rewrite EVERY ref in the mirror.\n"
            "That is very likely too broad - re-run with --refs-file listing\n"
            "just the branches you've decided to purge."
        )
        return 1

    if args.mirror_dir is not None:
        mirror_path = args.mirror_dir
        mirror_path.mkdir(parents=True, exist_ok=True)
        _mirror_clone(args.source, mirror_path)
        _run_and_report(mirror_path, args.replacements_file, refs, args.source)
    else:
        with tempfile.TemporaryDirectory(prefix="secrets-hygiene-purge-") as tmp:
            mirror_path = pathlib.Path(tmp) / "mirror.git"
            _mirror_clone(args.source, mirror_path)
            _run_and_report(mirror_path, args.replacements_file, refs, args.source)
            print(
                f"\nNote: mirror clone was in a temp dir ({mirror_path}) and is "
                "now gone. Re-run with --mirror-dir to keep it around before "
                "you push, if you want to inspect it further first."
            )

    return 0


def _run_and_report(
    mirror_path: pathlib.Path,
    replacements_file: pathlib.Path,
    refs: list[str],
    source: str,
) -> None:
    _run_filter_repo(mirror_path, replacements_file, refs)

    print("\nVerifying no listed secret remains on the rewritten refs...")
    clean = _verify_clean(mirror_path, replacements_file, refs)
    if not clean:
        print(
            "\nFAIL: verification found at least one secret still present. "
            "Do not push this mirror. Investigate before proceeding."
        )
        raise SystemExit(1)

    print("OK: none of the listed secrets remain on any of the rewritten refs.")
    print(
        "\nMANUAL STEP REQUIRED - this script will not do this for you.\n"
        "Review the rewritten history in the mirror clone above, confirm the\n"
        "refs list is exactly what you intend, make sure every affected\n"
        "collaborator/branch-owner has been notified, then run:\n\n"
        f"  cd {mirror_path}\n"
        + "\n".join(f"  git push --force {source} {ref}" for ref in refs)
        + "\n\nEveryone with an existing local clone of these branches must "
        "discard it and re-clone - `git pull` will silently reintroduce the "
        "old history. See the secrets_hygiene README's 'Before you run this' "
        "section."
    )


if __name__ == "__main__":
    raise SystemExit(main())
