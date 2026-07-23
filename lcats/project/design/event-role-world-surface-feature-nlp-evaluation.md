# NLP library evaluation for Event-Role-World surface-feature extraction

Date: 2026-07-23
Work item: WI-EVENT-0025 (investigation)
Scope: recommendation only — adds no dependency, implements no integration.

## Purpose

`WI-EVENT-0024` plans to implement the Event-Role-World extractor's stage 2
(surface-feature pass) as a lightweight, dependency-free lexical/structural
pass (word/sentence counts, average word/sentence length, punctuation
density), since this repo has no NLP/parsing dependency today
(`pyproject.toml`). This document surveys candidate NLP libraries that could
provide real syntactic/morphological features instead, and recommends
whether to adopt one now or defer.

This is a design recommendation only — it adds no dependency and implements
no integration, per `WI-EVENT-0025`'s non-goals.

## LCATS-specific constraints

- **License:** LCATS is distributed under the MIT license
  (`pyproject.toml:32`). Any dependency, including its pretrained models,
  should be compatible with permissive redistribution of derived research
  artifacts.
- **Corpus era and provenance:** the corpus spans Andersen and Grimm (19th-
  century fairy tales, translated from Danish/German), Chesterton, Doyle
  (`sherlock/`), Wilde, O. Henry, London, Lovecraft, Hemingway, and
  Wodehouse — public-domain English prose from roughly the 1880s–1930s,
  including in-translation material. Off-the-shelf taggers are trained on
  modern text (news, web); accuracy on this corpus is not guaranteed by any
  candidate's benchmark numbers.
- **Offline/no-network CI:** the extraction pipeline should not require a
  network fetch at run time in CI. Any library requiring a separate
  pretrained-model download must support a one-time offline install.
- **Dependency weight:** LCATS's current dependency list
  (`unidecode`, `beautifulsoup4`, `PyYAML`, `tiktoken`, `pandas`, `tqdm`,
  `matplotlib`, `seaborn`, `gutenbergpy`, `anthropic`, `openai`,
  `python-dotenv`) has no ML/NLP framework. Adding one is a real footprint
  increase, not an incremental addition.

## Candidates surveyed

### spaCy

- **License:** MIT (commercial open-source) — compatible with LCATS's MIT
  license. [spaCy on PyPI](https://pypi.org/project/spacy/)
- **Models:** distributed separately from the library as installable
  packages (e.g. `en_core_web_sm`), sized from small (tens of MB) to large
  (500MB+ with word vectors / transformer weights). Installable offline
  from a downloaded `.whl`/`.tar.gz` once fetched once.
  [spaCy models](https://github.com/explosion/spacy-models)
- **Fit:** provides tokenization, POS tagging, dependency parsing, and
  lemmatization out of the box — covers exactly the "syntactic and
  morphological" gap in stage 2. Smallest and most inspectable of the
  candidates evaluated; no heavy ML framework dependency for the small
  models (no PyTorch requirement for `en_core_web_sm`).
- **Risk:** trained on modern web/news text; accuracy on 19th-century
  translated fairy-tale prose or archaic punctuation is unverified without
  a sampled evaluation.

### NLTK

- **License:** Apache 2.0 for the library. Individual corpora/model
  packages (fetched via `nltk.download()`) carry their own licenses that
  are not uniformly documented on the NLTK data page — this needs
  per-package verification before use, not an assumption of Apache 2.0
  coverage. [NLTK data](https://www.nltk.org/nltk_data/)
- **Models:** the standard English POS tagger
  (`averaged_perceptron_tagger_eng`) is trained on the Penn Treebank (Wall
  Street Journal financial news, 1989) — a specific, dated, and
  narrow-domain training corpus, further from LCATS's 1880s–1930s literary
  prose than a general web-trained model.
  [NLTK tagging](https://www.nltk.org/api/nltk.tag.html)
- **Fit:** offline use is well-supported (download once, copy the
  `nltk_data` directory), but NLTK's API and maintenance cadence are
  older-generation compared to spaCy's, and the Penn Treebank training
  domain is a specific concern for this corpus.

### Stanza (Stanford NLP)

- **License:** Apache 2.0. [Stanza on GitHub](https://github.com/stanfordnlp/stanza)
- **Dependency weight:** requires PyTorch 1.3.0 or above — a substantial
  ML framework dependency, heavier than anything else in this evaluation
  or in LCATS's current dependency list.
- **Fit:** supports 80 languages via Universal Dependencies treebanks,
  actively maintained by Stanford NLP. The multilingual breadth is not a
  requirement for LCATS's English-only corpus, and the PyTorch dependency
  is a disproportionate cost for a single-language surface-feature pass.
  [Stanza available models](https://stanfordnlp.github.io/stanza/available_models.html)

### UDPipe

- **License:** the library itself is MPL 2.0, but **pretrained models are
  CC BY-NC-SA — non-commercial use only**.
  [UDPipe](https://ufal.mff.cuni.cz/udpipe) This is a real conflict with
  redistributing MIT-licensed, permissively-reusable research artifacts:
  any annotation produced using UDPipe's official pretrained models would
  inherit a non-commercial restriction, which is a poor fit for an
  academic corpus project that otherwise keeps its outputs permissively
  licensed.
- **Fit:** fast, lightweight (C++ core with Python bindings), good offline
  support — otherwise a reasonable technical fit, but the model license is
  a disqualifying constraint as currently distributed.

## Recommendation

**Defer adoption for now.** None of the four candidates has a demonstrated
accuracy advantage on LCATS's specific corpus (1880s–1930s public-domain
and translated literary prose) — all are trained on modern text, and no
candidate's documentation includes benchmarks on comparable material. Given
that, the cost side of the tradeoff dominates: Stanza's PyTorch dependency
is disproportionate, UDPipe's pretrained-model license conflicts with
LCATS's MIT license, and NLTK's standard tagger is trained on a narrow,
dated news corpus that is arguably no closer to this project's text than
the lightweight heuristics `WI-EVENT-0024` already implements.

**If adoption becomes justified later, spaCy is the best-positioned
candidate**: MIT-licensed (matches LCATS), smallest model footprint,
supports one-time offline install, and does not require a heavy ML
framework for its small models. Adoption should not proceed, however,
without first running a small stratified accuracy sample against this
corpus's actual prose — the governing proposal's own validation principle
(span-grounded, evidence-backed claims) applies as much to a tooling
decision as to an extraction result.

**Rationale in one line:** the lightweight heuristic approach already
planned in `WI-EVENT-0024` is not clearly worse than any evaluated
alternative for this specific corpus, and every alternative has a real
cost (dependency weight, license, or unverified domain fit) that a
one-line "add spaCy" decision would gloss over.

## Sketch if adoption is later approved

Not applicable — adoption is not recommended at this time. If a future
work item revisits this with a stratified accuracy sample favoring
adoption, the affected `WI-EVENT-0024` surface-feature fields would be the
POS-tag distribution, dependency-parse depth, and morphological-feature
fields currently produced heuristically; the existing word/sentence-count
fields would remain unchanged since they do not require a parser.
