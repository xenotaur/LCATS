#!/usr/bin/env python3
"""
Create a filled-out PR request from a template.

Usage:
    tools/create_request.py improve_coverage lcats/analysis/llm_extractor.py

Templates live in:
    tools/templates/<template_name>.md

Interpolation variables use the form:
    {{VARIABLE_NAME}}
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Tuple


_TEMPLATE_VAR_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _templates_dir() -> Path:
    return _script_dir() / "templates"


def _load_template(template_name: str) -> Tuple[Path, str]:
    template_path = _templates_dir() / f"{template_name}.md"
    if not template_path.exists():
        raise FileNotFoundError(
            f"Template not found: {template_path}\n"
            f"Expected: tools/templates/{template_name}.md"
        )
    return template_path, template_path.read_text(encoding="utf-8")


def _normalize_target_for_gha(target_input: str) -> str:
    """
    Normalize an input path into repo-root style module path:
        lcats/lcats/<...>.py

    Accepts inputs like:
        lcats/analysis/foo.py         -> lcats/lcats/analysis/foo.py
        lcats/lcats/analysis/foo.py   -> lcats/lcats/analysis/foo.py
        analysis/foo.py               -> lcats/lcats/analysis/foo.py  (assumed relative to lcats/)
    """
    s = target_input.strip().replace("\\", "/")
    s = s.lstrip("./")

    # If user passes a path relative to the lcats/ dir (common local usage)
    if not s.startswith("lcats/"):
        s = f"lcats/{s}"

    # If already includes lcats/lcats, keep as-is
    if s.startswith("lcats/lcats/"):
        return s

    # If starts with lcats/ but not lcats/lcats/, insert the second lcats/
    if s.startswith("lcats/"):
        return "lcats/lcats/" + s[len("lcats/") :]

    # Should be unreachable, but keep safe
    return s


def _compute_suggested_test_path(target_module_gha: str) -> str:
    """
    Given:
        lcats/lcats/<subdir>/<...>/<name>.py
    Suggest:
        lcats/tests/<subdir>_tests/<...>/<name>_test.py

    Example:
        lcats/lcats/analysis/llm_extractor.py
            -> lcats/tests/analysis_tests/llm_extractor_test.py

        lcats/lcats/analysis/nlp/foo.py
            -> lcats/tests/analysis_tests/nlp/foo_test.py
    """
    p = Path(target_module_gha)

    # Expect: lcats / lcats / <subdir> / ... / <file>
    parts = p.parts
    if len(parts) < 4 or parts[0] != "lcats" or parts[1] != "lcats":
        # Fall back: place in lcats/tests/misc_tests/
        stem = p.stem
        return str(Path("lcats/tests/misc_tests") / f"{stem}_test.py").replace("\\", "/")

    subdir = parts[2]
    rest_dirs = parts[3:-1]  # dirs after subdir, before file
    stem = p.stem

    test_dir = Path("lcats/tests") / f"{subdir}_tests"
    if rest_dirs:
        test_dir = test_dir.joinpath(*rest_dirs)

    return str(test_dir / f"{stem}_test.py").replace("\\", "/")


def _render_template(template_text: str, variables: Dict[str, str]) -> str:
    """
    Simple, deterministic interpolation:
      - Replaces {{VARNAME}} with variables[VARNAME] if present.
      - Leaves unknown placeholders intact (so you can notice missing vars).
    """

    def repl(match: re.Match) -> str:
        key = match.group(1)
        return variables.get(key, match.group(0))

    return _TEMPLATE_VAR_RE.sub(repl, template_text)


def _build_variables(template_name: str, target_input: str) -> Dict[str, str]:
    target_module_gha = _normalize_target_for_gha(target_input)
    module_name = Path(target_module_gha).stem
    suggested_test_path = _compute_suggested_test_path(target_module_gha)

    # Keep names stable and ALL CAPS to match {{...}} usage
    return {
        "TEMPLATE_NAME": template_name,
        "TARGET_INPUT": target_input,
        "TARGET_MODULE_GHA": target_module_gha,
        "MODULE_NAME": module_name,
        "SUGGESTED_TEST_PATH": suggested_test_path,
    }


def _parse_args(argv) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="create_request.py",
        description="Fill a PR request template with computed variables.",
    )
    parser.add_argument(
        "template_name",
        help="Template base name (e.g. improve_coverage) corresponding to tools/templates/<name>.md",
    )
    parser.add_argument(
        "target",
        help="Target module path (e.g. lcats/analysis/llm_extractor.py or lcats/lcats/analysis/llm_extractor.py)",
    )
    parser.add_argument(
        "--show-vars",
        action="store_true",
        help="Print computed variables to stderr (debugging).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    # print('hello from create_request.py with template "%s" and target "%s"' % (args.template_name, args.target), file=sys.stderr)
    try:
        _, template_text = _load_template(args.template_name)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2

    variables = _build_variables(args.template_name, args.target)

    if args.show_vars:
        for k in sorted(variables.keys()):
            print(f"{k}={variables[k]}", file=sys.stderr)

    rendered = _render_template(template_text, variables)
    sys.stdout.write(rendered)
    if not rendered.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())