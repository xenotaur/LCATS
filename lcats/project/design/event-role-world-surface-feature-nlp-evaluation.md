# NLP library evaluation for Event-Role-World surface-feature extraction

Date: 2026-07-23
Work item: WI-EVENT-0025 (investigation)
Scope: recommendation only — adds no dependency, implements no integration.

## Purpose

`WI-EVENT-0024` plans to implement the Event-Role-World extractor's stage 2
(surface-feature pass) as a lightweight, dependency-free lexical/structural
pass (word/sentence counts, average word/sentence length, punctuation
density), since this repo has no NLP/parsing dependency today
(`lcats/pyproject.toml`). This document surveys candidate NLP libraries that could
provide real syntactic/morphological features instead, and recommends
whether to adopt one now or defer.

This is a design recommendation only — it adds no dependency and implements
no integration, per `WI-EVENT-0025`'s non-goals.

## LCATS-specific constraints

- **License:** LCATS is distributed under the MIT license
  (`lcats/pyproject.toml:32`). Any dependency, including its pretrained models,
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
  packages. The smallest English model, `en_core_web_sm`, is approximately
  11-13MB; larger models with word vectors or transformer weights run to
  500MB+. Installable offline from a downloaded `.whl`/`.tar.gz` once
  fetched. [spaCy models](https://github.com/explosion/spacy-models),
  [en_core_web_sm size](https://huggingface.co/spacy/en_core_web_sm)
- **Fit:** provides tokenization, POS tagging, dependency parsing, and
  lemmatization out of the box — covers exactly the "syntactic and
  morphological" gap in stage 2. No heavy ML framework dependency for the
  small models (no PyTorch requirement for `en_core_web_sm`). Its ~12MB
  small-model footprint is in the same range as NLTK's tagger data and
  UDPipe's model below, not categorically smaller — see the footprint
  comparison in the Recommendation section.
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
  prose than a general web-trained model. The `averaged_perceptron_tagger`
  data package is approximately 2.4MB — smaller than spaCy's small model —
  despite the older training domain.
  [NLTK tagging](https://www.nltk.org/api/nltk.tag.html),
  [tagger file size](https://huggingface.co/spaces/pritamdeka/pubmed-abstract-retriever/blame/main/nltkmodule.py)
- **Fit:** offline use is well-supported (download once, copy the
  `nltk_data` directory), but NLTK's API and maintenance cadence are
  older-generation compared to spaCy's, and the Penn Treebank training
  domain is a specific concern for this corpus.

### Stanza (Stanford NLP)

- **License:** Apache 2.0. [Stanza on GitHub](https://github.com/stanfordnlp/stanza)
- **Dependency weight:** requires PyTorch 1.3.0 or above. PyTorch's CPU-only
  pip wheel alone has ranged roughly 200MB to over 1GB across recent
  releases — one to two orders of magnitude larger than spaCy's, NLTK's, or
  UDPipe's model footprints below, before even counting Stanza's
  per-language model files.
  [PyTorch wheel size discussion](https://github.com/pytorch/pytorch/issues/17621)
- **Fit:** supports 80 languages via Universal Dependencies treebanks,
  actively maintained by Stanford NLP. The multilingual breadth is not a
  requirement for LCATS's English-only corpus, and the PyTorch dependency
  is a disproportionate cost for a single-language surface-feature pass.
  [Stanza available models](https://stanfordnlp.github.io/stanza/available_models.html)

### UDPipe

- **License:** the library itself is MPL 2.0. The official pretrained
  models (e.g. `english-ud-2.1-20180111.udpipe`, ~15.6MB) are distributed
  under CC BY-NC-SA, which restricts non-commercial reuse and
  redistribution of the model files themselves.
  [UDPipe](https://ufal.mff.cuni.cz/udpipe),
  [UD 2.1 model size](https://github.com/bnosac/udpipe.models.ud). Whether
  annotations *produced by running* a CC BY-NC-SA model are themselves
  bound by that restriction is not established by UDPipe's own
  documentation — model-use restrictions and output copyright are
  different questions, and this evaluation does not assert that outputs
  inherit the model's license. What is established is a real, unresolved
  legal ambiguity: LCATS would need to confirm its intended use is
  covered, or use an alternative model distribution such as
  `bnosac/udpipe.models.ud` (CC BY-SA, no non-commercial restriction),
  before relying on UDPipe's official models for redistributable research
  artifacts.
- **Fit:** fast, lightweight (C++ core with Python bindings, ~15.6MB model
  — comparable to spaCy's and NLTK's footprints, far below Stanza's), good
  offline support. The official model's license terms are a real
  complication to resolve, not a settled disqualifier, given the
  CC BY-SA alternative distribution above.

## Footprint comparison

| Candidate | Model/data footprint | Framework dependency | Source |
|---|---|---|---|
| spaCy (`en_core_web_sm`) | ~11-13MB | None (small models) | [HF model card](https://huggingface.co/spacy/en_core_web_sm) |
| NLTK (`averaged_perceptron_tagger`) | ~2.4MB | None | [tagger file size](https://huggingface.co/spaces/pritamdeka/pubmed-abstract-retriever/blame/main/nltkmodule.py) |
| UDPipe (English UD 2.1) | ~15.6MB | None (C++ core) | [bnosac model repo](https://github.com/bnosac/udpipe.models.ud) |
| Stanza | tens-to-hundreds MB per language | PyTorch, ~200MB-1GB+ | [PyTorch wheel size](https://github.com/pytorch/pytorch/issues/17621) |

spaCy, NLTK, and UDPipe are all in the same rough size class (single-digit
to ~15MB) and require no heavy ML framework. Stanza is the clear outlier,
driven entirely by its PyTorch dependency rather than its model files.

## Recommendation

**Defer adoption for now.** None of the four candidates has a demonstrated
accuracy advantage on LCATS's specific corpus (1880s–1930s public-domain
and translated literary prose) — all are trained on modern text, and no
candidate's documentation includes benchmarks on comparable material. Given
that, the cost side of the tradeoff dominates: Stanza's PyTorch dependency
is disproportionate, UDPipe's official pretrained-model license carries an
unresolved non-commercial restriction (mitigated by the CC BY-SA
alternative distribution, but not eliminated as a decision to make), and
NLTK's standard tagger is trained on a narrow, dated news corpus with no
demonstrated advantage over the alternatives for this project's text.

**If adoption becomes justified later, spaCy is the best-positioned
candidate under an English-only assumption**: MIT-licensed (matches
LCATS), a footprint comparable to NLTK's and UDPipe's — not categorically
smaller, per the table above — no heavy ML framework requirement, and the
most actively maintained, feature-rich API of the three lightweight
options (tokenization, POS tagging, dependency parsing, and lemmatization
in one package). Adoption should not proceed, however, without first
running a small stratified accuracy sample against this corpus's actual
prose — the governing proposal's own validation principle (span-grounded,
evidence-backed claims) applies as much to a tooling decision as to an
extraction result. **This "best-positioned" judgment assumes the corpus
stays English-only — see the follow-up discussion below, which reopens
that assumption.**

## Follow-up discussion: multilingual direction and dependency cost

After this document's initial recommendation, the team discussed it
further and raised two points that revise — without overturning — the
analysis above.

**Multilingual direction.** The original Stanza assessment reasoned that
"the multilingual breadth is not a requirement for LCATS's English-only
corpus" (Candidates surveyed, above) and weighed its PyTorch dependency as
a disproportionate cost on that basis. If a multilingual corpus is an
actual near-term direction for LCATS rather than a distant possibility,
that premise no longer holds: Stanza is the only one of the four
candidates built around genuine multilingual support (80 languages via a
uniform Universal Dependencies interface), while spaCy, NLTK, and UDPipe
would each need separate per-language integration work. This is a
legitimate reason to revisit which candidate is "best positioned" — the
spaCy conclusion above was reasoned specifically for an English-only
future.

**PyTorch cost reconsideration.** The team's view is that the PyTorch
dependency may be less disqualifying than this document originally
treated it, on the expectation that LCATS may need something like PyTorch
for other future work regardless of this decision. Checking the repo for
supporting evidence: `lcats/lcats/datasets/torchdata.py:5` already
imports `from torch.utils.data import Dataset`, but `torch` is not
declared in `lcats/pyproject.toml`'s dependencies, and no other file in
the codebase imports this module (`torchdata`) or anything from
`lcats.datasets`. This is real evidence that PyTorch was reached for once
in this project's history, but it is an unused, undeclared import today —
not a currently active or working dependency. The "we'll need it anyway"
argument is directionally supported by this precedent but remains a
forecast, not something the repo currently demonstrates.

**Team familiarity.** Separately, the team has more hands-on experience
with NLTK than with spaCy. This does not change the factual concerns
raised above about NLTK's tagger (Penn Treebank training domain, dated
API) but is a legitimate practical factor — implementation speed and
risk — that the original evaluation did not weigh at all.

**What this changes:** the core recommendation is unchanged — defer
adoption until a stratified accuracy sample is run against LCATS's actual
prose, since no candidate (including Stanza) has demonstrated accuracy on
comparable text, and a multilingual direction raises the bar for that
validation rather than lowering it. What changes is the "if adoption is
justified later, spaCy is best" sub-recommendation: it now depends on
whether the multilingual direction is near-term (favors reconsidering
Stanza, with its dependency cost weighed against the team's other
anticipated PyTorch needs) or remains a longer-term possibility (favors
the original English-only reasoning, in which case NLTK's team familiarity
is a legitimate tie-breaking factor against spaCy alongside the
accuracy question). This document does not resolve which branch applies —
that is a corpus-roadmap decision for the team to make, not one this
evaluation is positioned to make on its own.

## Tension with WI-EVENT-0024's acceptance criteria

`WI-EVENT-0024`'s acceptance criteria require the extractor to produce
"surface-feature (lexical, syntactic, morphological) ... annotations per
segment" and state explicitly that "an implementation that skips stage 2
(surface features) does not satisfy this item." The lightweight,
dependency-free heuristic approach it currently plans (word/sentence
counts, average word/sentence length, punctuation density) produces
**lexical and structural** features only — it cannot produce real POS
tags, dependency parses, or morphological analysis, which require exactly
the kind of library this document evaluates.

Deferring library adoption therefore does not fully satisfy
`WI-EVENT-0024`'s stage-2 acceptance criterion as currently written. This
document does not resolve that gap — it flags it for `WI-EVENT-0024`'s
implementer to resolve one of two ways before that work item is considered
complete:

1. **Narrow `WI-EVENT-0024`'s stage-2 acceptance criterion** to the lexical
   and structural features the heuristic approach actually produces,
   explicitly deferring "syntactic, morphological" to a future work item
   contingent on this document's adoption conditions being met; or
2. **Adopt a lightweight library now** (spaCy, per the recommendation
   above) rather than deferring, accepting the unverified-accuracy risk on
   this corpus in exchange for satisfying the literal acceptance criterion
   today.

This document's own recommendation (defer) implies option 1 is the
consistent path, but that is `WI-EVENT-0024`'s decision to make, not one
this investigation is authorized to make on its behalf.

**Rationale in one line:** the lightweight heuristic approach already
planned in `WI-EVENT-0024` produces lexical/structural features only, not
syntactic/morphological ones as its own acceptance criteria require; every
evaluated alternative has a real cost (dependency weight, license
ambiguity, or unverified domain fit), so the tradeoff is between accepting
a scope gap now (option 1 above) or paying one of those costs today
(option 2).

## Sketch if adoption is later approved

Not applicable — adoption is not recommended at this time. If a future
work item revisits this with a stratified accuracy sample favoring
adoption, the affected surface-feature fields would be *new* additions —
POS-tag distribution, dependency-parse depth, and morphological features —
none of which the current heuristic approach produces today (see the
"Tension with WI-EVENT-0024's acceptance criteria" section above). The
existing word/sentence-count and punctuation-density fields would remain
unchanged since they do not require a parser.
