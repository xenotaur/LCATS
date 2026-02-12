"""Plotting functions for LCATS corpus analysis."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def plot_author_stories_vs_tokens(
    author_stats: pd.DataFrame,
    *,
    log_tokens: bool = True,
    annotate_top: int = 10,
    figsize: tuple = (8, 6),
    save_path: str | None = None,
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
    bottom_pad=0.35,
):
    """Boxplot: tokens per story, grouped by author."""
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
    plt.setp(
        ax.get_xticklabels(), rotation=rotate_labels, ha=ha, rotation_mode="anchor"
    )

    fig.tight_layout()
    fig.subplots_adjust(bottom=bottom_pad)
    return fig, ax


def plot_author_stories_vs_tokens_sns(
    author_stats: pd.DataFrame,
    *,
    log_tokens: bool = True,
    annotate_top: int = 10,
    figsize: tuple = (8, 6),
):
    """Scatter: number of stories per author (x) vs tokens per author (y) using seaborn."""
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
    bottom_pad=0.35,
):
    """Violinplot: tokens per story, grouped by author, using seaborn."""
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
    sns.violinplot(
        data=df,
        x="author_label",
        y="body_tokens",
        order=label_order,
        inner=None,
        cut=0,
        ax=ax,
    )
    sns.stripplot(
        data=df,
        x="author_label",
        y="body_tokens",
        order=label_order,
        ax=ax,
        alpha=0.5,
        size=3,
        jitter=0.2,
    )

    if log_tokens:
        ax.set_yscale("log")

    ax.set_xlabel("Author (stories)")
    ax.set_ylabel("Tokens per story" + (" (log scale)" if log_tokens else ""))
    ax.set_title("Tokens per Story by Author")
    ax.grid(True, axis="y", linestyle="--", linewidth=0.5, alpha=0.6)

    ha = "right" if rotate_labels and (rotate_labels % 180) != 0 else "center"
    plt.setp(
        ax.get_xticklabels(), rotation=rotate_labels, ha=ha, rotation_mode="anchor"
    )

    fig.tight_layout()
    fig.subplots_adjust(bottom=bottom_pad)
    return fig, ax


def plot_tokens_per_story_vs_stories(
    author_stats,
    *,
    log_y=True,
    annotate_top=12,  # how many authors to label
    min_stories=1,
    jitter=0.0,  # small x jitter to de-overlap points with identical story counts
    figsize=(9, 6),
    spread_step=6,  # vertical step (in points) between adjacent labels
    max_spread=None,  # max vertical steps from point (None = no limit)
    x_spread=6,  # horizontal spread (in points) for labels
    arrow=True,  # draw faint leader line from label to point
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
    df = df.sort_values(
        ["stories", "avg_tokens_per_story"], ascending=[False, False]
    ).reset_index(drop=True)

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
            k = (i // 2) + 1
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
