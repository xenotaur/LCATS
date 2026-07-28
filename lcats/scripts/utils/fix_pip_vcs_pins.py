#!/usr/bin/env python
"""Restore VCS pins that `conda env export` silently drops.

`conda env export`'s pip section renders any pip-installed package as a
bare `name==version` line, even when it was actually installed from a VCS
URL (e.g. `gutenbergpy @ git+https://.../@<commit>`). `pip freeze` renders
these correctly. This script splices the accurate `pip freeze` line back
into an `environment.yml` produced by `conda env export`, so regenerating
the file doesn't silently regress a commit-pinned dependency to a bare
version number.
"""

import re
import subprocess
import sys

BARE_LINE = re.compile(r"^(\s*-\s*)([A-Za-z0-9._-]+)==")
# Match only genuine VCS URLs (git+/hg+/bzr+/svn+), not `pip freeze`'s
# other direct-reference forms like `file:///...` local build-artifact
# paths, which conda-forge-built packages can report and which are not
# portable to another machine.
VCS_LINE = re.compile(r"^([A-Za-z0-9._-]+) @ (?:git|hg|bzr|svn)\+")


def vcs_pins_by_name(python):
    freeze = subprocess.run(
        [python, "-m", "pip", "freeze"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    pins = {}
    for line in freeze:
        match = VCS_LINE.match(line)
        if match:
            pins[match.group(1).lower()] = line
    return pins


def main(path, python=sys.executable):
    pins = vcs_pins_by_name(python)
    if not pins:
        return

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    changed = False
    for i, line in enumerate(lines):
        match = BARE_LINE.match(line)
        if match and match.group(2).lower() in pins:
            lines[i] = f"{match.group(1)}{pins[match.group(2).lower()]}\n"
            changed = True

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)


if __name__ == "__main__":
    main(sys.argv[1])
