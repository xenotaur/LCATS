# LCATS experimental work

Use this directory for prototypes and investigations that may be removed or
promoted. Follow [STYLE.md's repository policy](../STYLE.md#2-repository-structure).

Document purpose, environment, command, inputs/outputs and cost/network behavior.
Retained code deserves readable structure, relevant comments and tests. When work
needs durable results, move its runner and results to a numbered repository-root
`experiments/` entry; extract reusable/product behavior into `src/lcats/` with
unit tests. Promotion may involve both destinations. Existing historical layouts
are not a reason to put new executable code into `project/`.
