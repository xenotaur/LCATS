"""Survey and analyze a corpus of JSON story files."""

import ast
import json
import os
import pathlib
import re
import sys
import typing

from typing import Any, Dict, Iterable, List, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import tiktoken
from tqdm import tqdm


def find_corpus_stories(
    root: Union[str, pathlib.Path],
    *,
    ignore_dir_names: Iterable[str] = ("cache",),
    follow_symlinks: bool = False,
    ignore_hidden: bool = False,
    sort: bool = True,
) -> List[pathlib.Path]:
    """
    Recursively list all .json files under `root`, pruning directories
    whose *name* is in `ignore_dir_names` (e.g., 'cache') anywhere in the tree.

    Args:
        root: Corpus root directory (string or Path).
        ignore_dir_names: Directory names to prune (case-insensitive).
        follow_symlinks: Whether to descend into symlinked directories.
        ignore_hidden: If True, skip dot-directories and dot-files.
        sort: If True, return paths in sorted order (stable/deterministic).

    Returns:
        A list of pathlib.Path objects for all discovered JSON files.

    Raises:
        FileNotFoundError: if `root` does not exist.
        NotADirectoryError: if `root` is not a directory.
    """
    root_path = pathlib.Path(root).expanduser()
    if not root_path.exists():
        raise FileNotFoundError(f"Root path not found: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Root is not a directory: {root_path}")

    ignore_set = {name.casefold() for name in ignore_dir_names}
    results: typing.List[pathlib.Path] = []

    for dirpath, dirnames, filenames in os.walk(
        root_path, topdown=True, followlinks=follow_symlinks
    ):
        # Prune ignored / hidden directories in-place so os.walk won't descend into them.
        pruned = []
        for d in dirnames:
            if d.casefold() in ignore_set:
                continue
            if ignore_hidden and d.startswith("."):
                continue
            pruned.append(d)
        dirnames[:] = pruned

        # Collect JSON files (optionally skipping hidden files).
        for fname in filenames:
            if ignore_hidden and fname.startswith("."):
                continue
            if fname.lower().endswith(".json"):
                results.append(pathlib.Path(dirpath) / fname)

    if sort:
        results.sort()
    return results


_WORD_RE = re.compile(r"\S+")  # simple, robust word-ish segmentation

def _get_encoder() -> "tiktoken.Encoding":
    """Prefer GPT-4o-ish tokens; fallback to cl100k_base."""
    for name in ("o200k_base", "cl100k_base"):
        try:
            return tiktoken.get_encoding(name)
        except Exception:
            continue
    # As a last resort, use the default encoding for cl100k_base-compatible models
    try:
        return tiktoken.encoding_for_model("gpt-4")
    except Exception as e:
        raise RuntimeError("No suitable tiktoken encoding found.") from e


def _decode_possible_bytes_literal(s: str) -> str:
    """
    Safely decode strings that look like Python bytes literals: b'...'/b"...".
    Otherwise return the string unchanged.
    """
    if not isinstance(s, str):
        return str(s)
    t = s.strip()
    if len(t) >= 3 and t[0] == "b" and t[1] in ("'", '"'):
        try:
            b = ast.literal_eval(t)
            if isinstance(b, (bytes, bytearray)):
                return bytes(b).decode("utf-8", errors="replace")
        except Exception:
            pass
    return s


def _extract_title_authors_body(data: Dict[str, Any]) -> Tuple[str, List[str], str]:
    # Title
    title = (data.get("name") or data.get("metadata", {}).get("name") or "").strip()
    if not title:
        title = "<Untitled>"

    # Authors (list of strings)
    authors = data.get("author")
    if not authors:
        authors = data.get("metadata", {}).get("author", [])
    if isinstance(authors, str):
        authors = [authors]
    authors = [a.strip() for a in (authors or []) if str(a).strip()]

    # Body
    body = data.get("body", "")
    if isinstance(body, (bytes, bytearray)):
        body = bytes(body).decode("utf-8", errors="replace")
    else:
        body = _decode_possible_bytes_literal(str(body))
    return title, authors, body


def _normalize_title(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _token_count(text: str, enc: "tiktoken.Encoding") -> int:
    # Note: tiktoken expects bytes/str; do not pre-split.
    return len(enc.encode(text, disallowed_special=()))


# ---------- main API ----------

def compute_corpus_stats(
    json_paths: Iterable[Union[str, pathlib.Path]],
    *,
    dedupe: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Given an iterable of JSON file paths, produce:
      - story_stats: one row per unique story
      - author_stats: one row per author, aggregated across their stories

    Uniqueness key (if dedupe=True): (normalized_title, tuple(sorted(lowercased_authors)))

    Columns in story_stats:
        path, story_id, title, authors, n_authors,
        title_words, title_chars, title_tokens,
        body_words, body_chars, body_tokens

    Columns in author_stats:
        author, stories, body_words, body_chars, body_tokens
    """
    enc = _get_encoder()
    seen_keys = set()

    story_rows: List[Dict[str, Any]] = []

    for p in tqdm(json_paths):
        path = pathlib.Path(p)
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"warn: skipping unreadable JSON {path}: {e}", file=sys.stderr)
            continue

        title, authors, body = _extract_title_authors_body(data)

        # Uniqueness key
        key = (_normalize_title(title), tuple(sorted(a.lower() for a in authors)))
        if dedupe and key in seen_keys:
            continue
        seen_keys.add(key)

        # Metrics
        title_chars = len(title)
        title_words = _word_count(title)
        title_tokens = _token_count(title, enc)

        body_chars = len(body)
        body_words = _word_count(body)
        body_tokens = _token_count(body, enc)

        story_rows.append(
            {
                "path": str(path),
                "story_id": f"{key[0]}::{';'.join(key[1])}" if key[1] else key[0],
                "title": title,
                "authors": authors,
                "n_authors": len(authors),

                "title_words": title_words,
                "title_chars": title_chars,
                "title_tokens": title_tokens,

                "body_words": body_words,
                "body_chars": body_chars,
                "body_tokens": body_tokens,
            }
        )

    story_stats = pd.DataFrame(story_rows)

    if story_stats.empty:
        # Return empty frames with expected columns
        story_cols = [
            "path","story_id","title","authors","n_authors",
            "title_words","title_chars","title_tokens",
            "body_words","body_chars","body_tokens",
        ]
        author_cols = ["author","stories","body_words","body_chars","body_tokens"]
        return pd.DataFrame(columns=story_cols), pd.DataFrame(columns=author_cols)

    # Build author_stats by exploding authors and aggregating body metrics.
    # (We aggregate body metrics, as requested; titles are usually small and not counted here.)
    exploded = story_stats.explode("authors", ignore_index=True)
    exploded["authors"] = exploded["authors"].fillna("")

    # Drop rows with no author string (optional; comment out to keep)
    exploded = exploded[exploded["authors"].str.len() > 0].copy()

    grp = exploded.groupby("authors", as_index=False).agg(
        stories=("story_id", "nunique"),
        body_words=("body_words", "sum"),
        body_chars=("body_chars", "sum"),
        body_tokens=("body_tokens", "sum"),
    )
    grp = grp.rename(columns={"authors": "author"}).sort_values(
        ["stories", "body_words"], ascending=[False, False]
    )

    author_stats = grp.reset_index(drop=True)

    return story_stats, author_stats


def plot_author_stories_vs_tokens(
    author_stats: pd.DataFrame,
    *,
    log_tokens: bool = True,
    annotate_top: int = 10,
    figsize: tuple = (8, 6),
    save_path: str | None = None
):
    """
    Scatter: number of stories per author (x) vs tokens per author (y).

    Args:
        author_stats: DataFrame with columns ['author', 'stories', 'body_tokens'].
        log_tokens: If True, use log scale on y-axis (helps with heavy tails).
        annotate_top: Label the top-N authors by tokens (0 to disable).
        figsize: Matplotlib figure size.
        save_path: If provided, saves the figure to this path.

    Returns:
        (fig, ax)
    """
    df = author_stats.copy()
    df = df.sort_values("body_tokens", ascending=False)

    x = df["stories"].to_numpy()
    y = df["body_tokens"].to_numpy()

    fig, ax = plt.subplots(figsize=figsize)
    ax.scatter(x, y, marker="o", alpha=0.8)

    if log_tokens:
        ax.set_yscale("log")

    ax.set_xlabel("Stories per author")
    ax.set_ylabel("Tokens per author" + (" (log scale)" if log_tokens else ""))
    ax.set_title("Stories vs. Tokens per Author")
    ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)

    # Annotate top-N by tokens
    if annotate_top and annotate_top > 0:
        top = df.head(annotate_top)
        for _, row in top.iterrows():
            ax.annotate(
                row["author"],
                xy=(row["stories"], row["body_tokens"]),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=9,
            )

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig, ax


def tokens_per_story_by_author_frame(story_stats):
    """
    Return per-(author, story) rows with tokens.
    Expects columns: ['story_id','title','authors','body_tokens'].
    """
    df = story_stats[["story_id", "title", "authors", "body_tokens"]].copy()
    df = df.explode("authors", ignore_index=True)
    df = df[df["authors"].notna() & (df["authors"].str.len() > 0)]
    df = df.rename(columns={"authors": "author"})
    return df[["author", "story_id", "title", "body_tokens"]]

def plot_tokens_per_story_by_author(
    story_stats,
    *,
    top_n=12,
    min_stories=2,
    log_tokens=True,
    figsize=(10, 6),
    rotate_labels=45,
    bottom_pad=0.35
):
    df = tokens_per_story_by_author_frame(story_stats)

    counts = df.groupby("author")["story_id"].nunique().sort_values(ascending=False)
    keep_authors = counts[counts >= min_stories].head(top_n).index.tolist()
    df = df[df["author"].isin(keep_authors)].copy()

    # Sort strictly by number of stories (desc). Build display labels "Author (N)".
    order = counts.loc[keep_authors].sort_values(ascending=False).index.tolist()
    label_map = {a: f"{a} ({counts[a]})" for a in order}
    label_order = [label_map[a] for a in order]

    # Prepare data for boxplot in the same order
    grouped = [g["body_tokens"].to_numpy() for _, g in df.groupby("author")]
    # Ensure grouping follows 'order'
    grouped = [df[df["author"] == a]["body_tokens"].to_numpy() for a in order]

    fig, ax = plt.subplots(figsize=figsize)
    ax.boxplot(grouped, showfliers=False, labels=label_order, vert=True)

    if log_tokens:
        ax.set_yscale("log")

    # jittered points overlay aligned to positions 1..len(order)
    for i, a in enumerate(order, start=1):
        y = df.loc[df["author"] == a, "body_tokens"].to_numpy()
        x = np.random.normal(loc=i, scale=0.06, size=len(y))
        ax.plot(x, y, linestyle="none", marker="o", alpha=0.5, markersize=3)

    ax.set_xlabel("Author (stories)")
    ax.set_ylabel("Tokens per story" + (" (log scale)" if log_tokens else ""))
    ax.set_title("Tokens per Story by Author")
    ax.grid(True, axis="y", linestyle="--", linewidth=0.5, alpha=0.6)

    ha = "right" if rotate_labels and (rotate_labels % 180) != 0 else "center"
    plt.setp(ax.get_xticklabels(), rotation=rotate_labels, ha=ha, rotation_mode="anchor")

    fig.tight_layout()
    fig.subplots_adjust(bottom=bottom_pad)
    return fig, ax

def plot_author_stories_vs_tokens_sns(
    author_stats: pd.DataFrame,
    *,
    log_tokens: bool = True,
    annotate_top: int = 10,
    figsize: tuple = (8, 6)
):
    df = author_stats.sort_values("body_tokens", ascending=False).copy()

    fig, ax = plt.subplots(figsize=figsize)
    sns.scatterplot(data=df, x="stories", y="body_tokens", ax=ax)

    if log_tokens:
        ax.set_yscale("log")

    ax.set_xlabel("Stories per author")
    ax.set_ylabel("Tokens per author" + (" (log scale)" if log_tokens else ""))
    ax.set_title("Stories vs. Tokens per Author")
    ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)

    if annotate_top and annotate_top > 0:
        top = df.head(annotate_top)
        for _, row in top.iterrows():
            ax.annotate(
                row["author"],
                xy=(row["stories"], row["body_tokens"]),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=9,
            )

    fig.tight_layout()
    return fig, ax

def plot_tokens_per_story_by_author_sns(
    story_stats,
    *,
    top_n=12,
    min_stories=2,
    log_tokens=True,
    figsize=(10, 6),
    rotate_labels=45,
    bottom_pad=0.35
):
    df = tokens_per_story_by_author_frame(story_stats)

    counts = df.groupby("author")["story_id"].nunique().sort_values(ascending=False)
    keep_authors = counts[counts >= min_stories].head(top_n).index.tolist()
    df = df[df["author"].isin(keep_authors)].copy()

    # Sort strictly by number of stories (desc) and build labels
    order = counts.loc[keep_authors].sort_values(ascending=False).index.tolist()
    label_map = {a: f"{a} ({counts[a]})" for a in order}
    df["author_label"] = df["author"].map(label_map)
    label_order = [label_map[a] for a in order]

    fig, ax = plt.subplots(figsize=figsize)
    sns.violinplot(data=df, x="author_label", y="body_tokens", order=label_order, inner=None, cut=0, ax=ax)
    sns.stripplot(data=df, x="author_label", y="body_tokens", order=label_order, ax=ax, alpha=0.5, size=3, jitter=0.2)

    if log_tokens:
        ax.set_yscale("log")

    ax.set_xlabel("Author (stories)")
    ax.set_ylabel("Tokens per story" + (" (log scale)" if log_tokens else ""))
    ax.set_title("Tokens per Story by Author")
    ax.grid(True, axis="y", linestyle="--", linewidth=0.5, alpha=0.6)

    ha = "right" if rotate_labels and (rotate_labels % 180) != 0 else "center"
    plt.setp(ax.get_xticklabels(), rotation=rotate_labels, ha=ha, rotation_mode="anchor")

    fig.tight_layout()
    fig.subplots_adjust(bottom=bottom_pad)
    return fig, ax


def plot_tokens_per_story_vs_stories(
    author_stats,
    *,
    log_y=True,
    annotate_top=12,      # how many authors to label
    min_stories=1,
    jitter=0.0,           # small x jitter to de-overlap points with identical story counts
    figsize=(9, 6),
    spread_step=6,        # vertical step (in points) between adjacent labels
    max_spread=None,      # max vertical steps from point (None = no limit)
    x_spread=6,           # horizontal spread (in points) for labels
    arrow=True            # draw faint leader line from label to point
):
    """
    Scatter of average tokens per story (y) vs stories per author (x),
    with 'spread' label placement to reduce overlaps (no external deps).

    Expects author_stats with: ['author', 'stories', 'body_tokens'].
    """
    df = author_stats.copy()
    df = df[df["stories"] >= min_stories].copy()
    df = df[df["stories"] > 0].copy()

    df["avg_tokens_per_story"] = df["body_tokens"] / df["stories"]
    if log_y:
        df = df[df["avg_tokens_per_story"] > 0].copy()

    # Order by stories desc (annotation priority), then avg tokens
    df = df.sort_values(["stories", "avg_tokens_per_story"], ascending=[False, False]).reset_index(drop=True)

    x = df["stories"].to_numpy()
    y = df["avg_tokens_per_story"].to_numpy()
    if jitter and jitter > 0:
        x = x + np.random.normal(0.0, jitter, size=len(x))

    fig, ax = plt.subplots(figsize=figsize)
    ax.scatter(x, y, alpha=0.85)

    if log_y:
        ax.set_yscale("log")

    ax.set_xlabel("Stories per author")
    ax.set_ylabel("Average tokens per story" + (" (log scale)" if log_y else ""))
    ax.set_title("Average Tokens per Story vs Stories per Author")
    ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)

    # ---- Spread labels for top-N authors ----
    if annotate_top and annotate_top > 0:
        top = df.head(annotate_top).copy()

        # Alternate vertical offsets: +step, -step, +2*step, -2*step, ...
        offsets_y = []
        offsets_x = []
        for i in range(len(top)):
            k = ((i // 2) + 1)
            sign = +1 if i % 2 == 0 else -1
            spread = k * spread_step
            if max_spread:
                spread = min(spread, max_spread * spread_step)
            offsets_y.append(sign * spread)
            offsets_x.append(x_spread)

        # Place labels; align left/right based on whether point is right/left of median x
        x_med = np.median(df["stories"])
        for (i, row), dy, dx in zip(top.iterrows(), offsets_y, offsets_x):
            xi = row["stories"]
            yi = row["avg_tokens_per_story"]
            label = f"{row['author']} ({row['stories']})"

            ha = "left" if xi >= x_med else "right"
            if ha == "left":
                dx = -dx
            # dx = x_spread if ha == "left" else -x_spread

            arrowprops = dict(arrowstyle="-", lw=0.5, alpha=0.5) if arrow else None
            ax.annotate(
                label,
                xy=(xi, yi),
                xytext=(dx, dy),
                textcoords="offset points",
                ha=ha,
                va="center",
                fontsize=9,
                arrowprops=arrowprops,
            )

    fig.tight_layout()
    return fig, ax

