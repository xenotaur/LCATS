"""QA orchestration for corpus survey checks."""

from typing import Any, Mapping, Optional, Sequence

from lcats.analysis.corpus import models
from lcats.analysis.corpus.detectors import boundary
from lcats.analysis.corpus.detectors import structural
from lcats.analysis.corpus.detectors import unicode

DEFAULT_CHECKS = ["special-characters", "boundary-contamination"]


def build_default_detectors() -> list[models.Detector]:
    """Build the default detector list."""
    return [
        unicode.SpecialCharactersDetector(
            safe_excluded_chars=unicode.SAFE_EXCLUDED_CHARS,
            rare_review_chars=unicode.RARE_REVIEW_CHARS,
            mojibake_trigger_chars=unicode.MOJIBAKE_TRIGGER_CHARS,
        ),
        boundary.StartDetector(),
        boundary.EndDetector(),
        structural.ChapterHeadingDetector(),
        structural.TocRemnantsDetector(),
        structural.SectionBreakDetector(),
        structural.IllustrationCaptionDetector(),
    ]


def run_detectors(
    text: str,
    config: Optional[Mapping[str, Any]] = None,
) -> list[models.Finding]:
    """Run configured detectors and return findings in deterministic order."""
    resolved = dict(config or {})
    detectors: Optional[Sequence[models.Detector]] = resolved.get("detectors")
    active_detectors = detectors or build_default_detectors()

    findings = []
    for detector in active_detectors:
        findings.extend(detector.run(text))

    return findings
