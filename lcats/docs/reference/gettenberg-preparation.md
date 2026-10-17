# Collection planning and catalog preparation

`lcats.gatherers.planning.CollectionRequirement(name, source_type, catalog_use="none")`
is an immutable description, not a plugin registration. Source types are `local`,
`fixed_url`, and `gutenberg`; catalog uses are `none`, `discovery`, and `enrichment`.
`needs_catalog` depends only on explicit use, not source identity. `select(names)`
validates all built-in names, preserves order and duplicates, and defaults an empty
selection to all built-ins. It imports no gatherer modules. The `GATHERERS` registry
now maps names to import paths; modules are loaded only during actual execution.

`lcats.gettenberg.preparation.CatalogPreparation(cache_dir=None, *, archive=None,
request=None, policy=NetworkPolicy(), offline=False)` resolves one cache root for
both `CatalogManager` and `ResourceStore`. Local archive and archive-kind
`SourceRequest` are mutually exclusive. Construction performs no writes. There
is no default network source, global client or implicit refresh.

| Operation | Result / authority |
|---|---|
| `plan(required=False)` | `not_required`; catalog not inspected |
| `plan()` on ready state | `reuse`; supplied source ignored |
| `plan()` on invalid state | `blocked`; no repair inferred |
| Missing catalog, local archive or permitted/cached request | `setup`; approval required |
| Missing catalog, absent/blocked source | `blocked`; reason retained |
| `prepare(dry_run=True, ...)` | Read-only plan, even if blocked; no approval prompt |
| `prepare(approved=False)` | Reuse is allowed; missing setup raises `PreparationError` |
| `prepare(approved=True)` | Rechecks state, acquires if necessary, calls lifecycle setup |

`PreparationPlan` contains `action`, `reason`, `catalog_state`, `acquisition`, and
an `approval_required` property. `dataclasses.asdict(plan)` is JSON-compatible;
the property is not included by `asdict`. A saved plan is not permission to act.
`prepare` rechecks it; invalid cache evidence raises a structured resource error.
Offline overrides online policy but permits verified cache reads. Setup never
uses the refresh API, passes count-change approval, or touches story output.
Returned generations and errors retain the existing lifecycle contracts.

The catalog CLI exposes `status`, `setup`, `refresh`, and `rebuild` through these
same APIs. All return JSON and exit 0 for success, 2 for operational/input failure
or blocked plans. `status` with missing state is a successful observation (0);
invalid state is 2. `--dry-run` is supported for all three mutating commands.
Only actionable missing setup prompts, only on an interactive input stream;
`--yes` supplies that approval explicitly. Prompts go to stderr, JSON to stdout.
CLI setup defaults to the published Gutenberg RDF archive unless a local archive
or URL overrides it. Refresh still requires an explicit URL; refresh/rebuild
require an active catalog. The library itself still selects no source.
See the [command guide](../how-to/gettenberg-preparation.md) for flags and examples.

Gather dry-run and live execution both use collection requirements. Live
metadata-dependent gathering composes this setup policy with the new source API;
see [gather contracts](gettenberg-gather.md) for CLI defaults and overrides.

## Composing collection requirements with setup policy

```python
from lcats.gatherers import planning
from lcats.gettenberg import preparation

collections = planning.select(["sherlock"])
service = preparation.CatalogPreparation(cache_dir="cache")
plan = service.prepare(
    required=any(item.needs_catalog for item in collections),
    dry_run=True,
)
assert plan.action == "not_required"
```

For a metadata-dependent workflow, configure an explicit archive/request, show
`service.plan()` to the user, then call `prepare(approved=True)` only after setup
approval. Live `mass_quantities` execution uses this same preparation contract.
