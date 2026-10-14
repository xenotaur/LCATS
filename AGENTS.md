# LCATS repository guidance

The canonical engineering and repository-placement policy is
[lcats/STYLE.md](lcats/STYLE.md), especially Repository Structure. Read it before
changing code or moving evidence. Package-specific instructions also apply under
[lcats/AGENTS.md](lcats/AGENTS.md).

- `lcats/project/` contains documentation and non-executable control-plane data.
- Prototypes belong in `lcats/experimental/`; durable experiment runners and
  results belong together under `experiments/NN_name/`.
- Reusable/product logic belongs in `lcats/src/lcats/` with unit tests.
- Preserve historical outputs and source identities; document relocations.
- Run package commands from `lcats/` in the project environment. Explicitly pass
  changed experiment paths to format/lint and run their documented smoke tests.
  A green default package check does not establish experiment coverage.
