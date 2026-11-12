"""Bounded, offline subprocess runner for the explicit NLP smoke suite.

The parent imports only discovery-safe modules. Every check gets a fresh
interpreter and durable logs; a receipt is required in addition to exit zero.
This is test infrastructure, not a production NLP runner.
"""

import argparse
import faulthandler
import json
import math
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest


PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[2]


def child_environment():
    """Return child-only CPU/offline settings without changing the parent."""
    env = os.environ.copy()
    env.update(
        CUDA_VISIBLE_DEVICES="-1",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        PYTHONUNBUFFERED="1",
        PYTHONFAULTHANDLER="1",
    )
    return env


def block_network(event, _args):
    """Reject Python socket connections even if an NLP library tries to fetch."""
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("Smoke execution is offline; provision models separately")


def flatten(suite):
    """Yield individual unittest cases, including discovery errors."""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def discover(backend=None):
    """Discover only *_smoke.py; module import must never initialize models."""
    loader = unittest.TestLoader()
    suite = loader.discover(
        str(PACKAGE_ROOT / "tests" / "smoke"),
        pattern="*_smoke.py",
        top_level_dir=str(PACKAGE_ROOT),
    )
    if loader.errors:
        raise RuntimeError("\n".join(loader.errors))
    cases = list(flatten(suite))
    return [c for c in cases if backend is None or c.backend_name == backend]


def run_child(command, directory, timeout):
    """Run one worker, preserving output even on abort, timeout or interrupt.

    POSIX workers get their own process group so timeout kills descendants too.
    On Windows the worker itself is terminated; the supported NLP checks do not
    launch external worker processes.
    """
    directory.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    with (
        (directory / "stdout.log").open("wb") as out,
        (directory / "stderr.log").open("wb") as err,
    ):
        process = subprocess.Popen(
            command,
            cwd=PACKAGE_ROOT,
            env=child_environment(),
            stdout=out,
            stderr=err,
            start_new_session=os.name == "posix",
        )
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            if process.poll() is None:
                if os.name == "posix":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # The child exited between poll() and killpg().
                else:
                    process.kill()
                process.wait()
    code = process.returncode
    if timed_out:
        reason = "timeout"
    elif code < 0:
        reason = f"signal {signal.Signals(-code).name} ({-code})"
    else:
        reason = f"exit {code}"
    return {
        "returncode": code,
        "reason": reason,
        "timed_out": timed_out,
        "seconds": round(time.monotonic() - start, 3),
    }


def worker(case_id, backend, directory, check_only=False):
    """Execute a single case and publish a receipt only after unittest returns."""
    from tests.smoke import resources

    sys.addaudithook(block_network)
    # Use a dedicated descriptor: code suppressing stdout/stderr cannot hide
    # faulthandler's native crash traceback in this file.
    with (directory / "fault.log").open("w", encoding="utf-8") as fault:
        faulthandler.enable(file=fault, all_threads=True)
        try:
            versions = resources.check(backend)
            print(json.dumps({"backend": backend, "versions": versions}), flush=True)
            if check_only:
                receipt = {"ok": True, "kind": "prerequisites", "versions": versions}
            else:
                suite = unittest.defaultTestLoader.loadTestsFromName(case_id)
                result = unittest.TextTestRunner(verbosity=2).run(suite)
                ok = (
                    result.wasSuccessful()
                    and result.testsRun == 1
                    and not result.skipped
                    and not result.expectedFailures
                )
                receipt = {
                    "ok": ok,
                    "kind": "test",
                    "case": case_id,
                    "tests_run": result.testsRun,
                    "skipped": len(result.skipped),
                    "versions": versions,
                }
            (directory / "receipt.json").write_text(
                json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
            )
            return 0 if receipt["ok"] else 1
        finally:
            faulthandler.disable()


def run_cases(
    cases, log_dir, timeout, check_only=False, *, worker_module="tests.smoke.run"
):
    """Continue after individual failures, returning a nonzero aggregate."""
    if not cases:
        raise ValueError("No smoke checks selected")
    log_dir.mkdir(parents=True, exist_ok=True)
    run_dir = pathlib.Path(tempfile.mkdtemp(prefix="run-", dir=log_dir)).resolve()
    results = []
    for index, case in enumerate(cases):
        directory = run_dir / f"{index + 1:02d}-{case.backend_name}"
        command = [
            sys.executable,
            "-m",
            worker_module,
            "--worker",
            case.id(),
            "--backend",
            case.backend_name,
            "--worker-dir",
            str(directory),
        ]
        if check_only:
            command.append("--check")
        outcome = run_child(command, directory, timeout)
        outcome.update(case=case.id(), backend=case.backend_name, logs=str(directory))
        try:
            receipt = json.loads(
                (directory / "receipt.json").read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            receipt = {}
        expected_kind = "prerequisites" if check_only else "test"
        valid = receipt.get("ok") is True and receipt.get("kind") == expected_kind
        if not check_only:
            valid = (
                valid
                and receipt.get("case") == case.id()
                and receipt.get("tests_run") == 1
                and receipt.get("skipped") == 0
            )
        outcome["ok"] = (
            outcome["returncode"] == 0 and not outcome["timed_out"] and valid
        )
        outcome["receipt"] = receipt
        if outcome["returncode"] == 0 and not valid:
            outcome["reason"] = "missing or invalid completion receipt"
        results.append(outcome)
        print(
            f"{'PASS' if outcome['ok'] else 'FAIL'} {case.id()}: {outcome['reason']}",
            flush=True,
        )
        # Persist after each child so earlier results survive interruption.
        (run_dir / "summary.json").write_text(
            json.dumps(results, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"{sum(r['ok'] for r in results)}/{len(results)} {'prerequisite checks' if check_only else 'smoke tests'} passed; logs: {run_dir}"
    )
    return 0 if all(r["ok"] for r in results) else 1


def main(argv=None):
    """CLI used by scripts/smoke; provision resources in a separate command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("spacy", "stanza"))
    parser.add_argument(
        "--timeout", type=float, default=120, help="seconds per child (default: 120)"
    )
    parser.add_argument(
        "--log-dir", type=pathlib.Path, default=pathlib.Path("tmp/logs/smoke")
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--dry-run",
        action="store_true",
        help="list checks without imports of native packages",
    )
    modes.add_argument(
        "--check",
        action="store_true",
        help="verify pinned packages and model files only; does not certify inference",
    )
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    parser.add_argument("--worker-dir", type=pathlib.Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")
    if args.worker:
        if args.worker_dir is None or args.backend is None:
            parser.error("worker requires directory and backend")
        return worker(args.worker, args.backend, args.worker_dir, args.check)
    try:
        cases = discover(args.backend)
        if not cases:
            raise ValueError("No smoke checks selected")
        if args.dry_run:
            for case in cases:
                print(f"{case.backend_name}: {case.id()}")
            return 0
        return run_cases(cases, args.log_dir, args.timeout, args.check)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Smoke failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
