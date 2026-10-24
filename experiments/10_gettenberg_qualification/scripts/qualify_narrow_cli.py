"""Qualify installed CLI refusal continuation using authored offline fixtures.

From outside the checkout, with PYTHONPATH unset and a fresh wheel venv:
python /path/to/qualify_narrow_cli.py /tmp/NEW-cli-report.json

Requires sibling qualify_narrow_installed.py, which verifies installed origins,
forbids legacy/review imports and sockets, and seeds disposable fixture receipts.
This runner invokes the real CLI for success/refusal/success twice. Only collection
selection and fixture HTTP responses are substituted. No canonical outputs or
existing caches are touched. POSIX alarm bounds work to 120 seconds; failures
produce no completed report. Output must be fresh and outside the installed package.
"""

import argparse
import contextlib
import io
import json
import os
import pathlib
import signal
import tempfile
from unittest import mock

import qualify_narrow_installed


def main(argv=None):
    """Check real CLI exit/output semantics and preserve a JSON evidence record."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", type=lambda value: pathlib.Path(value).resolve())
    args = ap.parse_args(argv)
    require = qualify_narrow_installed.require
    require(not args.output.exists(), "output exists")
    distribution, package_root = qualify_narrow_installed.installed_environment()
    require(not args.output.is_relative_to(package_root), "output inside package")
    previous = signal.signal(signal.SIGALRM, qualify_narrow_installed.timeout)
    signal.alarm(120)
    try:
        with tempfile.TemporaryDirectory(prefix="gettenberg-cli-review-") as temporary:
            root = pathlib.Path(temporary).resolve()
            with qualify_narrow_installed.bounded_runtime():
                # Reuse the independently authored catalog/receipt fixtures, then
                # point the CLI at an empty output tree for a genuinely cold batch.
                qualify_narrow_installed.exercise(root)
                from lcats import cli
                from lcats.gatherers.mass_quantities import gatherer, storymap

                books = qualify_narrow_installed.BOOKS
                order = [books[0], books[2], books[1]]
                output_root = root / "cli-data"
                runs = []
                with (
                    contextlib.chdir(root),
                    mock.patch.dict(
                        os.environ,
                        LCATS_DATA_DIR=str(output_root),
                        LCATS_CORPORA_DIR=str(root / "cli-corpora"),
                    ),
                    mock.patch.object(storymap, "SINGLE_STORIES", order),
                ):
                    for _ in range(2):
                        stdout, stderr = io.StringIO(), io.StringIO()
                        with contextlib.redirect_stdout(
                            stdout
                        ), contextlib.redirect_stderr(stderr):
                            try:
                                cli.main(
                                    [
                                        "gather",
                                        "mass_quantities",
                                        "--offline",
                                        "--cache-dir",
                                        str(root / "cache"),
                                        "--gutenberg-main-root",
                                        qualify_narrow_installed.ORIGIN + "/main/",
                                        "--gutenberg-generated-root",
                                        qualify_narrow_installed.ORIGIN + "/generated/",
                                    ]
                                )
                            except SystemExit as exc:
                                status = exc.code
                            else:
                                raise ValueError("CLI did not exit")
                        require(status == 2, "refusal must report incomplete status 2")
                        require(
                            "Gathering incomplete" in stdout.getvalue(),
                            "missing incomplete summary",
                        )
                        files = {
                            str(
                                p.relative_to(output_root)
                            ): qualify_narrow_installed.sha(p.read_bytes())
                            for p in output_root.rglob("story.json")
                        }
                        require(
                            len(files) == 2,
                            "cold batch did not publish both safe stories",
                        )
                        runs.append(
                            {
                                "exit_status": status,
                                "stdout": stdout.getvalue(),
                                "outputs": files,
                            }
                        )
                require(
                    runs[0]["outputs"] == runs[1]["outputs"],
                    "repeat changed output bytes",
                )
                log = root / "logs/gather" / gatherer.GATHER_LOG_FILENAME
                events = [json.loads(line) for line in log.read_text().splitlines()]
                expected = [
                    "run_start",
                    "story_ready",
                    "story_cleanup_refused",
                    "story_ready",
                    "batch_summary",
                    "run_end",
                ]
                require(
                    [e["event"] for e in events] == expected * 2,
                    "batch did not continue in order",
                )
                require(
                    all(events[i]["story"] == books[2] for i in (2, 8)),
                    "wrong refused input",
                )
                origins = qualify_narrow_installed.module_origins(package_root)
        report = {
            "completed": True,
            "installed_version": distribution.version,
            "runner_sha256": qualify_narrow_installed.sha(
                pathlib.Path(__file__).read_bytes()
            ),
            "fixture_helper_sha256": qualify_narrow_installed.sha(
                pathlib.Path(qualify_narrow_installed.__file__).read_bytes()
            ),
            "network_bytes": 0,
            "configured_fixture_order": order,
            "runs": runs,
            "events": events,
            "module_origins": origins,
            "scope": "Authored three-input installed CLI; not real-corpus or original-wire qualification.",
        }
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
        print(
            json.dumps(
                {"completed": True, "statuses": [run["exit_status"] for run in runs]}
            )
        )
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


if __name__ == "__main__":
    main()
