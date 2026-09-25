# Comparative Visualization Contract

`lcats.visualize.comparison` defines the reusable analysis contract for
comparative lexical figures. Renderers and CLI commands consume its aligned
table rather than recalculating selection, metrics, vocabulary, or ordering.

## Specification

`ComparisonSpec` is immutable and declares:

- an explicit universe `U`;
- left and right selectors;
- genre membership mode: `candidate`, `primary`, or `selection`;
- left and right metrics;
- token preprocessing and term form;
- vocabulary policy and display ordering;
- rendering style and requested output formats.

Complements are always `U - S`, never "all stories the repository can find".
The manifest records the concrete universe story IDs, selector story IDs,
overlap, metric policy, preprocessing, vocabulary, and warnings.

## Selectors

Supported selector kinds are:

- `all`;
- `genre`;
- `manifest_genre`;
- `story_list`;
- `include_exclude`;
- `complement`.

Genre selectors are not assumed to be mutually exclusive or exhaustive. If the
left and right selectors overlap, the result records the intersection and emits
a warning.

## Metrics

Supported metrics are:

- `raw_count`;
- `per_million`;
- `document_count`;
- `document_percentage`;
- `mean_document_relative_frequency`;
- `mean_tfidf`;
- `tfidf_contrast`.

TF-IDF metrics fit once over the declared universe. `tfidf_contrast` is a
group-minus-complement mean TF-IDF difference within that shared fit. It is not
a statistical significance test.

Reference-overlay rendering requires commensurate values: identical metric
specifications and compatible preprocessing. Mirrored tables may expose
different left and right metrics because their axes can be labelled separately
by later renderers.

## Vocabulary And Ordering

One aligned vocabulary is selected before rows are ordered. Policies include
all terms, top left, top right, top signed difference, top absolute difference,
union of top lists, and intersection of top lists. Explicit include/exclude
terms and minimum document-count filters are applied deterministically.

Ordering supports left value, right value, signed difference, absolute
difference, alphabetical order, and an explicit term list. Ties are broken by
term text.

## Output Table

Each row contains:

- term and display order;
- left and right values;
- raw counts;
- document counts;
- token and document denominators;
- signed and absolute difference.

This table is the numerical source of truth for future mirrored, overlay, and
multi-panel renderers.
