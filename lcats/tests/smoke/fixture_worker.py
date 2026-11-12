"""Controlled child outcomes for harness tests; never discovered as smoke tests.

This small protocol peer exercises the real process, log and receipt boundary
without importing NLP packages. It is not exposed by the smoke CLI.
"""

import argparse
import json
import os
import pathlib
import signal
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker")
    parser.add_argument("--backend")
    parser.add_argument("--worker-dir", type=pathlib.Path)
    args = parser.parse_args()
    mode = args.worker
    print("fixture stdout", flush=True)
    print("fixture native stderr", file=sys.stderr, flush=True)
    if mode == "signal":
        os.kill(os.getpid(), signal.SIGTERM)
    if mode == "timeout":
        time.sleep(30)
    if mode == "failure":
        return 1
    if mode == "no-receipt":
        return 0
    receipt = {
        "ok": True,
        "kind": "test",
        "case": mode,
        "tests_run": 0 if mode == "zero" else 1,
        "skipped": 1 if mode == "skip" else 0,
    }
    (args.worker_dir / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
