"""Persist immutable review candidates separately from accepted story buckets."""

import json
import pathlib

from lcats.gatherers import readiness
from lcats.gatherers import story_output
from lcats.utils import env

DEFAULT_DIRECTORY = pathlib.Path("logs") / "gather" / "review" / "mass_quantities"


def working_root(path, *, data_root):
    """Validate a runtime working directory outside all known collection roots.

    Unlike source-checkout discovery this also works in an installed wheel. Use
    the same runtime data/corpora roots as gathering, plus the caller's explicit
    output root. Resolving paths catches symlink aliases into protected trees.
    """
    root = pathlib.Path(path).resolve()
    for value in (data_root, env.data_root(), env.corpora_root()):
        protected = pathlib.Path(value).resolve()
        if root == protected or protected in root.parents:
            raise ValueError(
                f"review/log directory must be outside data/corpora: {root}"
            )
    return root


def save(report, *, directory=DEFAULT_DIRECTORY, data_root):
    """Save one exact candidate/report without overwriting any earlier evidence.

    The name binds the full report, including source identities and policy. A
    repeated report reuses equal JSON only; corruption or a conflicting writer
    fails visibly. The filename is never story.json and there is no promotion.
    """
    if report.get("status") != "needs_review":
        raise ValueError("only needs_review reports belong in the candidate store")
    root = working_root(directory, data_root=data_root)
    record = {
        "schema_version": 1,
        "kind": "gettenberg_review_candidate",
        "report": report,
    }
    digest = readiness.identity(record)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{report['gutenberg_id']}-{digest}.candidate.json"
    story_output.publish(path, record)
    if json.loads(path.read_text(encoding="utf-8")) != json.loads(json.dumps(record)):
        raise ValueError(f"review candidate identity collision/corruption: {path}")
    return str(path)
