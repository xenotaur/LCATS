"""Compatibility wrapper for corpus survey APIs."""

from lcats.analysis.corpus import cli
from lcats.analysis.corpus import discovery
from lcats.analysis.corpus import output
from lcats.analysis.corpus import qa
from lcats.analysis.corpus.detectors import boundary
from lcats.analysis.corpus.detectors import structural
from lcats.analysis.corpus.detectors import unicode
from lcats.analysis.corpus import models

SMART_ALLOWED = unicode.SMART_ALLOWED
ASCII_PUNCT = unicode.ASCII_PUNCT
DEFAULT_EXCLUDED_CODEPOINTS = unicode.DEFAULT_EXCLUDED_CODEPOINTS
SAFE_EXCLUDED_CHARS = unicode.SAFE_EXCLUDED_CHARS
RARE_REVIEW_CHARS = unicode.RARE_REVIEW_CHARS
MOJIBAKE_TRIGGER_CHARS = unicode.MOJIBAKE_TRIGGER_CHARS
DEFAULT_EXCLUDED_CHARS = unicode.DEFAULT_EXCLUDED_CHARS
DEFAULT_CHECKS = qa.DEFAULT_CHECKS
DEFAULT_OUTPUT_FORMAT = output.DEFAULT_OUTPUT_FORMAT
TSV_COLUMNS = output.TSV_COLUMNS
BOUNDARY_WINDOW_LINES = boundary.BOUNDARY_WINDOW_LINES
STRUCTURAL_WINDOW_LINES = structural.STRUCTURAL_WINDOW_LINES

Finding = models.Finding

SpecialCharactersDetector = unicode.SpecialCharactersDetector
StartDetector = boundary.StartDetector
EndDetector = boundary.EndDetector
ChapterHeadingDetector = structural.ChapterHeadingDetector
TocRemnantsDetector = structural.TocRemnantsDetector
SectionBreakDetector = structural.SectionBreakDetector
IllustrationCaptionDetector = structural.IllustrationCaptionDetector

run_detectors = qa.run_detectors
find_json_files = discovery.find_json_files
run_lcats_display = cli.run_lcats_display
run_special_characters_check = cli.run_special_characters_check
parse_special_character_rows = output.parse_special_character_rows
survey_file = cli.survey_file
parse_csv_args = cli.parse_csv_args
build_parser = cli.build_survey_parser
subprocess = cli.subprocess
lcats = cli.lcats


def main(argv=None):
    """Run survey CLI via compatibility wrapper."""
    original_find_json_files = cli.discovery.find_json_files
    original_survey_file = cli.survey_file
    original_tqdm = cli.tqdm
    original_sys = cli.sys
    try:
        cli.discovery.find_json_files = find_json_files
        cli.survey_file = survey_file
        cli.tqdm = tqdm
        cli.sys = sys
        return cli.run_survey(argv)
    finally:
        cli.discovery.find_json_files = original_find_json_files
        cli.survey_file = original_survey_file
        cli.tqdm = original_tqdm
        cli.sys = original_sys


_clean_row = output.clean_row
_show_progress = cli._show_progress
sys = cli.sys
tqdm = cli.tqdm
