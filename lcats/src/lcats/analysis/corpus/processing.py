"""Batch corpus processing helpers."""

from datetime import datetime
import json
import pathlib
import re

from typing import Any, Callable, Dict, Iterable, List, Optional, Union

import tqdm

from lcats import utils
from lcats.analysis.corpus import discovery


def compute_job_dir(
    output_root_path: pathlib.Path, job_label: Optional[str]
) -> pathlib.Path:
    """Compute and sanitize the job directory path."""
    if job_label:
        safe = re.sub(r"\s+", "_", job_label.strip())
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", safe)
        return output_root_path / safe
    stamp = datetime.now().strftime("job_%Y_%m_%d_%H_%M_%S")
    return output_root_path / stamp


def process_file(
    in_path: Union[str, pathlib.Path],
    *,
    corpora_root: Union[str, pathlib.Path],
    job_dir: Union[str, pathlib.Path],
    processor_function: Callable[[Any], Any],
    force: bool = False,
    encoding: str = "utf-8",
    indent: int = 2,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Process a single JSON file and write mirrored output."""
    input_path = pathlib.Path(in_path).expanduser().resolve()
    corpora_root_path = pathlib.Path(corpora_root).expanduser().resolve()
    job_dir_path = pathlib.Path(job_dir).expanduser().resolve()

    try:
        rel = input_path.relative_to(corpora_root_path)
    except ValueError:
        rel = input_path.name

    out_path = job_dir_path / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and not force:
        if verbose:
            print(f"SKIP  {rel}")
        return {
            "input": input_path,
            "output": out_path,
            "status": "skipped",
            "error": None,
        }

    try:
        print(f"Processing {rel} -> {out_path.relative_to(job_dir_path)}")
        with input_path.open("r", encoding=encoding) as input_file:
            data = json.load(input_file)

        result = processor_function(data)
        api_err = result.get("api_error")
        if api_err and api_err.get("should_abort_batch"):
            raise RuntimeError(
                f"Fatal API error: {api_err.get('category')} "
                f"{api_err.get('code')}: {api_err.get('message')}"
            )

        serializable = utils.make_serializable_extraction(result)
        with out_path.open("w", encoding=encoding, newline="\n") as output_file:
            json.dump(serializable, output_file, ensure_ascii=False, indent=indent)
            output_file.write("\n")

        if verbose:
            print(f"OK    {rel} -> {out_path.relative_to(job_dir_path)}")
        return {
            "input": input_path,
            "output": out_path,
            "status": "processed",
            "error": None,
        }

    except Exception as exception:  # noqa: BLE001
        error_message = f"{type(exception).__name__}: {exception}"
        if verbose:
            print(f"ERROR {rel} :: {error_message}")
        return {
            "input": input_path,
            "output": out_path,
            "status": "error",
            "error": error_message,
        }


def process_files(
    files: Iterable[Union[str, pathlib.Path]],
    corpora_root: Union[str, pathlib.Path],
    output_root: Union[str, pathlib.Path],
    processor_function: Callable[[Any], Any],
    *,
    job_label: Optional[str] = None,
    force: bool = False,
    sort: bool = True,
    encoding: str = "utf-8",
    indent: int = 2,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Process a list of JSON files into a mirrored output tree."""
    corpora_root_path = pathlib.Path(corpora_root).expanduser().resolve()
    output_root_path = pathlib.Path(output_root).expanduser().resolve()

    job_dir = compute_job_dir(output_root_path, job_label)
    job_dir.mkdir(parents=True, exist_ok=True)

    normalized_files: List[pathlib.Path] = [
        pathlib.Path(file_path).expanduser().resolve() for file_path in files
    ]
    if sort:
        normalized_files.sort()

    processed = 0
    skipped = 0
    errors: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []

    for input_path in tqdm.tqdm(normalized_files, desc="Processing files", unit="file"):
        result = process_file(
            input_path,
            corpora_root=corpora_root_path,
            job_dir=job_dir,
            processor_function=processor_function,
            force=force,
            encoding=encoding,
            indent=indent,
            verbose=verbose,
        )
        results.append(result)
        if result["status"] == "processed":
            processed += 1
        elif result["status"] == "skipped":
            skipped += 1
        elif result["status"] == "error":
            errors.append(
                {
                    "input": str(result["input"]),
                    "output": str(result["output"]),
                    "error": result.get("error") or "",
                }
            )

    print(f"{processed} files processed, {skipped} skipped, {len(errors)} errors")
    return {
        "job_dir": job_dir,
        "total": len(normalized_files),
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "results": results,
    }


def process_corpora(
    corpora_root: Union[str, pathlib.Path],
    output_root: Union[str, pathlib.Path],
    processor_function: Callable[[Any], Any],
    *,
    job_label: Optional[str] = None,
    force: bool = False,
    ignore_dir_names: Iterable[str] = ("cache",),
    follow_symlinks: bool = False,
    ignore_hidden: bool = False,
    sort: bool = True,
    encoding: str = "utf-8",
    indent: int = 2,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Discover and process corpus JSON files."""
    corpora_root_path = pathlib.Path(corpora_root).expanduser().resolve()
    files = discovery.find_corpus_stories(
        corpora_root_path,
        ignore_dir_names=ignore_dir_names,
        follow_symlinks=follow_symlinks,
        ignore_hidden=ignore_hidden,
        sort=sort,
    )
    return process_files(
        files,
        corpora_root=corpora_root_path,
        output_root=output_root,
        processor_function=processor_function,
        job_label=job_label,
        force=force,
        sort=False,
        encoding=encoding,
        indent=indent,
        verbose=verbose,
    )
