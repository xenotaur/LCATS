#!/usr/bin/env python3
"""
surveyor.py

Inventory a Python source tree and summarize "public-ish surface area" per file
to help humans or agents assess testability and plan unit tests.

Examples:
  python tools/surveyor.py lcats/lcats/utils --format md
  python tools/surveyor.py lcats/lcats/utils --format json
  python tools/surveyor.py lcats/lcats/utils --tests-root lcats/tests/utils_tests --format md
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str  # "function" | "class" | "async_function"
    lineno: int
    is_private: bool
    doc: Optional[str]


@dataclass(frozen=True)
class FileReport:
    path: str
    relpath: str
    module: str
    syntax_error: Optional[str]
    functions: list[Symbol]
    classes: list[Symbol]
    has_main_guard: bool
    top_level_imports: int
    test_file_guess: Optional[str]  # if tests-root provided, best guess name
    test_file_exists: Optional[bool]


def _is_private(name: str) -> bool:
    # Treat dunder names and leading underscore as "private-ish".
    # NOTE: you may want to consider single-underscore as "semi-public" in your project.
    return name.startswith("_")


def _first_line(doc: Optional[str]) -> Optional[str]:
    if not doc:
        return None
    line = doc.strip().splitlines()[0].strip()
    return line if line else None


def _module_name_from_path(root: pathlib.Path, path: pathlib.Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    # If root is a package dir, we can treat it as module prefix "utils.foo"
    return ".".join(rel.parts)


def _guess_test_filename(src_path: pathlib.Path) -> str:
    """
    Given names.py -> names_test.py (matching your current convention)
    """
    stem = src_path.stem
    return f"{stem}_test.py"


def _count_top_level_imports(tree: ast.AST) -> int:
    n = 0
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            n += 1
    return n


def _has_main_guard(text: str) -> bool:
    # Simple string heuristic; avoids false negatives from AST formatting
    return 'if __name__ == "__main__"' in text or "if __name__=='__main__'" in text


def analyze_file(
    root: pathlib.Path, path: pathlib.Path, tests_root: Optional[pathlib.Path]
) -> FileReport:
    relpath = str(path.relative_to(root))
    module = _module_name_from_path(root, path)

    text = path.read_text(encoding="utf-8")
    syntax_error: Optional[str] = None
    funcs: list[Symbol] = []
    clss: list[Symbol] = []
    top_level_imports = 0

    try:
        tree = ast.parse(text)
        top_level_imports = _count_top_level_imports(tree)
        for node in tree.body:  # type: ignore[attr-defined]
            if isinstance(node, ast.FunctionDef):
                funcs.append(
                    Symbol(
                        name=node.name,
                        kind="function",
                        lineno=getattr(node, "lineno", 0),
                        is_private=_is_private(node.name),
                        doc=_first_line(ast.get_docstring(node)),
                    )
                )
            elif isinstance(node, ast.AsyncFunctionDef):
                funcs.append(
                    Symbol(
                        name=node.name,
                        kind="async_function",
                        lineno=getattr(node, "lineno", 0),
                        is_private=_is_private(node.name),
                        doc=_first_line(ast.get_docstring(node)),
                    )
                )
            elif isinstance(node, ast.ClassDef):
                clss.append(
                    Symbol(
                        name=node.name,
                        kind="class",
                        lineno=getattr(node, "lineno", 0),
                        is_private=_is_private(node.name),
                        doc=_first_line(ast.get_docstring(node)),
                    )
                )
    except SyntaxError as e:
        syntax_error = f"{e.msg} (line {e.lineno}:{e.offset})"
    except UnicodeDecodeError as e:
        syntax_error = f"UnicodeDecodeError: {e}"

    test_file_guess: Optional[str] = None
    test_file_exists: Optional[bool] = None
    if tests_root is not None:
        test_file_guess = _guess_test_filename(path)
        test_path = tests_root / test_file_guess
        test_file_exists = test_path.exists()

    return FileReport(
        path=str(path),
        relpath=relpath,
        module=module,
        syntax_error=syntax_error,
        functions=sorted(funcs, key=lambda s: (s.is_private, s.name)),
        classes=sorted(clss, key=lambda s: (s.is_private, s.name)),
        has_main_guard=_has_main_guard(text),
        top_level_imports=top_level_imports,
        test_file_guess=test_file_guess,
        test_file_exists=test_file_exists,
    )


def scan_tree(
    root: pathlib.Path, tests_root: Optional[pathlib.Path]
) -> list[FileReport]:
    reports: list[FileReport] = []
    for path in sorted(root.rglob("*.py")):
        # Skip common junk dirs
        if any(
            part
            in (".venv", "venv", "__pycache__", ".git", ".mypy_cache", ".pytest_cache")
            for part in path.parts
        ):
            continue
        reports.append(analyze_file(root, path, tests_root))
    return reports


def to_markdown(
    reports: list[FileReport], root: pathlib.Path, tests_root: Optional[pathlib.Path]
) -> str:
    lines: list[str] = []
    lines.append(f"# Surface inventory: `{root}`")
    if tests_root is not None:
        lines.append(f"- Tests root: `{tests_root}`")
    lines.append(f"- Files: {len(reports)}")
    lines.append("")

    for r in reports:
        lines.append(f"## `{r.relpath}`")
        lines.append(f"- module: `{r.module}`")
        if r.syntax_error:
            lines.append(f"- ⚠️ syntax error: `{r.syntax_error}`")
            lines.append("")
            continue

        if r.test_file_guess is not None:
            status = "✅ present" if r.test_file_exists else "❌ missing"
            lines.append(f"- test file: `{r.test_file_guess}` ({status})")

        flags: list[str] = []
        if r.has_main_guard:
            flags.append("has __main__ guard")
        if r.top_level_imports > 0:
            flags.append(f"{r.top_level_imports} top-level imports")
        if flags:
            lines.append(f"- notes: {', '.join(flags)}")

        pub_funcs = [s for s in r.functions if not s.is_private]
        priv_funcs = [s for s in r.functions if s.is_private]
        pub_clss = [s for s in r.classes if not s.is_private]
        priv_clss = [s for s in r.classes if s.is_private]

        def sym_line(s: Symbol) -> str:
            doc = f" — {s.doc}" if s.doc else ""
            return f"  - `{s.name}` (line {s.lineno}){doc}"

        if pub_funcs:
            lines.append("")
            lines.append("### Public functions")
            lines.extend(sym_line(s) for s in pub_funcs)

        if pub_clss:
            lines.append("")
            lines.append("### Public classes")
            lines.extend(sym_line(s) for s in pub_clss)

        if priv_funcs or priv_clss:
            lines.append("")
            lines.append("<details><summary>Private-ish symbols</summary>")
            lines.append("")
            if priv_funcs:
                lines.append("**Functions**")
                lines.extend(sym_line(s) for s in priv_funcs)
                lines.append("")
            if priv_clss:
                lines.append("**Classes**")
                lines.extend(sym_line(s) for s in priv_clss)
                lines.append("")
            lines.append("</details>")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def to_json(reports: list[FileReport]) -> str:
    payload: list[dict[str, Any]] = []
    for r in reports:
        d = asdict(r)
        payload.append(d)
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("root", help="Root directory to scan (e.g., lcats/lcats/utils)")
    p.add_argument(
        "--tests-root",
        default=None,
        help="Optional tests dir (e.g., lcats/tests/utils_tests)",
    )
    p.add_argument("--format", choices=("md", "json"), default="md")
    p.add_argument("--out", default="-", help="Output file path, or '-' for stdout")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"ERROR: root not found or not a directory: {root}", file=sys.stderr)
        return 2

    tests_root: Optional[pathlib.Path] = None
    if args.tests_root:
        tests_root = pathlib.Path(args.tests_root).resolve()
        if not tests_root.exists() or not tests_root.is_dir():
            print(
                f"ERROR: tests-root not found or not a directory: {tests_root}",
                file=sys.stderr,
            )
            return 2

    reports = scan_tree(root, tests_root)
    if args.format == "md":
        out_txt = to_markdown(reports, root, tests_root)
    else:
        out_txt = to_json(reports)

    if args.out == "-" or args.out.strip() == "":
        sys.stdout.write(out_txt)
    else:
        out_path = pathlib.Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_txt, encoding="utf-8")
        print(f"Wrote {args.format} to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
