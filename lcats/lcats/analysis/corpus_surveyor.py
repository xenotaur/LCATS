"""Compatibility wrapper for corpus surveyor APIs."""

from lcats.analysis.corpus import discovery
from lcats.analysis.corpus import processing
from lcats.analysis.corpus import stats

find_corpus_stories = discovery.find_corpus_stories
compute_corpus_stats = stats.compute_corpus_stats
process_corpora = processing.process_corpora
process_files = processing.process_files
process_file = processing.process_file
compute_job_dir = processing.compute_job_dir
