# Experiment 01_classify_corpora: Classify Stories in the Corpora
This experiment attempts to identify what classes 

* Source: TaurDev / 06138667510934ac57ebc076a40ed6d15eac58b6
* Code: $PROJECT_ROOT/lcats/notebooks/03_clean_corpus.ipynb
* Data: $PROJECT_ROOT/corpora
* Results: ./results/survey.tab

Raw data files were produced by the cell:

```
more_summary = corpus_surveyor.process_files(
    json_stories,
    corpora_root=CORPORA_ROOT,
    output_root=DEV_OUTPUT,
    processor_function=story_classifier,
    job_label="story_classes",
    verbose=True,
)
```

The summary.tab was extracted from these raw data files using:

```
find output/story_classes -name '*.json' -exec jq -r 'def F: ["type","integrity","completeness","series","genre_primary","genre_secondary"];
      ([F[] as $k | .extracted_output[$k] // ""]
       + [(input_filename|split("/")[-2]),
          (input_filename|split("/")[-1]|rtrimstr(".json"))]) | @tsv' {} + | sort > output/story_classes/summary.tab
```

The key summary of the results is:
```
$ cat results/summary.tab | egrep -v "^fiction" | cut -f1 | sort | uniq -c | sort -nr
  57 nonfiction
   3 poetry
   2 drama
   1 other
   1 mixed
```
