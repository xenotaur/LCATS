"""Reproducible, offline, beginning-of-narrative boundary evaluation.

Usage: python evaluate.py [--dataset training.json|testing.json] [--out results.json]

Only the narrative *start boundary* is measured. Whole-story end boundaries,
chapter filtering, metadata selection, HTTP acquisition and publisher output
are not measured by the short opening excerpts in this dataset.
"""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path

import gutenberg_extractor as parser


def reference_line(record):
    """Locate reviewed first narrative in its own original opening.

    A few human edits have dropped a quote, capitalization or whitespace.
    For these we match the opening 7 word tokens of a four-line span.
    If still ambiguous, count it as unassessable instead of fabricating truth.
    """
    original = record['original_opening'].replace('\r\n', '\n').replace('\r', '\n')
    narrative = record['first_narrative_text'].replace('\r\n', '\n').replace('\r', '\n')
    if not narrative.strip():
        return None
    for needle in (narrative[:min(70, len(narrative))], narrative[:60].strip()):
        position = original.find(needle)
        if position >= 0:
            return original[:position].count('\n')
    tokens = re.findall(r'\w+', narrative[:160].casefold())[:7]
    if not tokens:
        return None
    lines = original.split('\n')
    candidates = [i for i in range(len(lines))
                  if re.findall(r'\w+', ' '.join(lines[i:i+4]).casefold())[:len(tokens)] == tokens]
    return candidates[0] if len(candidates) == 1 else None


def estimate(record, *, guarded):
    opening = record['original_opening'].replace('\r\n', '\n').replace('\r', '\n')
    lines = opening.split('\n')
    title = record['title']
    authors = record['authors']
    lo, hi, diagnostics = parser.identify_story_boundaries(opening, title, authors, [])
    warnings = []
    lo = parser._refine_front_boundary(lines, lo, hi, title, warnings)
    lo = parser._refine_repeated_display_heading(lines, lo, hi, title, authors, [], warnings)
    if guarded:
        lo = parser._conservative_narrative_guard(lines, lo, hi, title, warnings)
        lo = parser._bracketed_marker_narrative_guard(lines, lo, hi, title, authors, [], warnings)
        lo = parser._dated_scene_opening_guard(lines, lo, hi, title, authors, [], warnings)
    return lo


def evaluate(records):
    rows = []
    for record in records:
        reference = reference_line(record)
        baseline = estimate(record, guarded=False)
        improved = estimate(record, guarded=True)
        rows.append({'gutenberg_id': record['gutenberg_id'],
                     'title': record['title'][0] if record['title'] else '',
                     'reference_start_line_1_based': None if reference is None else reference + 1,
                     'baseline_start_line_1_based': baseline + 1,
                     'modified_start_line_1_based': improved + 1,
                     'baseline_offset_lines': None if reference is None else baseline - reference,
                     'modified_offset_lines': None if reference is None else improved - reference})
    metrics = {}
    for label in ('baseline', 'modified'):
        offsets = [r[f'{label}_offset_lines'] for r in rows if r[f'{label}_offset_lines'] is not None]
        metrics[label] = {
            'assessable': len(offsets),
            'unassessable': len(rows) - len(offsets),
            'exact_boundary': sum(x == 0 for x in offsets),
            'narrative_loss_cases': sum(x > 0 for x in offsets),
            'narrative_lines_lost': sum(max(0,x) for x in offsets),
            'front_matter_retained_cases': sum(x < 0 for x in offsets),
            'front_matter_lines_retained': sum(max(0,-x) for x in offsets),
            'max_narrative_lines_lost_one_story': max((max(x,0) for x in offsets), default=0),
        }
    return {'count': len(records), 'metrics': metrics, 'per_story': rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', choices=['training.json', 'testing.json'], default='testing.json')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    folder = Path(__file__).resolve().parent
    dataset = json.loads((folder / args.dataset).read_text(encoding='utf-8'))
    output = evaluate(dataset)
    dest = folder / (args.out or args.dataset.replace('.json','_evaluation.json'))
    dest.write_text(json.dumps(output, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps(output['metrics'], indent=2))
    print(f'Full per-story evaluation: {dest}')


if __name__ == '__main__':
    main()
