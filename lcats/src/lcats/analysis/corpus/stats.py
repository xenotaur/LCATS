"""Corpus statistics helpers."""

import json
import pathlib
import sys

from typing import Any, Dict, Iterable, List, Tuple, Union

import pandas as pd
import tqdm

from lcats.analysis import story_analysis


def compute_corpus_stats(
    json_paths: Iterable[Union[str, pathlib.Path]],
    *,
    dedupe: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Compute story-level and author-level aggregate corpus stats."""
    encoder = story_analysis.get_encoder()
    seen_keys = set()
    story_rows: List[Dict[str, Any]] = []

    for path_value in tqdm.tqdm(json_paths):
        path = pathlib.Path(path_value)
        try:
            with path.open("r", encoding="utf-8") as input_file:
                data = json.load(input_file)
        except Exception as exception:  # noqa: BLE001
            print(
                f"warn: skipping unreadable JSON {path}: {exception}", file=sys.stderr
            )
            continue

        title, authors, body = story_analysis.extract_title_authors_body(data)
        key = (
            story_analysis.normalize_title(title),
            tuple(sorted(author.lower() for author in authors)),
        )
        if dedupe and key in seen_keys:
            continue
        seen_keys.add(key)

        story_rows.append(
            {
                "path": str(path),
                "story_id": f"{key[0]}::{';'.join(key[1])}" if key[1] else key[0],
                "title": title,
                "authors": authors,
                "n_authors": len(authors),
                "title_words": story_analysis.word_count(title),
                "title_chars": len(title),
                "title_tokens": story_analysis.token_count(title, encoder),
                "body_words": story_analysis.word_count(body),
                "body_chars": len(body),
                "body_tokens": story_analysis.token_count(body, encoder),
            }
        )

    story_stats = pd.DataFrame(story_rows)
    if story_stats.empty:
        story_cols = [
            "path",
            "story_id",
            "title",
            "authors",
            "n_authors",
            "title_words",
            "title_chars",
            "title_tokens",
            "body_words",
            "body_chars",
            "body_tokens",
        ]
        author_cols = ["author", "stories", "body_words", "body_chars", "body_tokens"]
        return pd.DataFrame(columns=story_cols), pd.DataFrame(columns=author_cols)

    exploded = story_stats.explode("authors", ignore_index=True)
    exploded["authors"] = exploded["authors"].fillna("")
    exploded = exploded[exploded["authors"].str.len() > 0].copy()

    author_stats = exploded.groupby("authors", as_index=False).agg(
        stories=("story_id", "nunique"),
        body_words=("body_words", "sum"),
        body_chars=("body_chars", "sum"),
        body_tokens=("body_tokens", "sum"),
    )
    author_stats = author_stats.rename(columns={"authors": "author"}).sort_values(
        ["stories", "body_words"], ascending=[False, False]
    )

    return story_stats, author_stats.reset_index(drop=True)
