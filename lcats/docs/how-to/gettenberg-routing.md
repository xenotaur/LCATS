# Route a Gutenberg resource before downloading

Use this workflow with an `ebook` returned by the catalog, or resolve an individual
Gutenberg file URI without opening a catalog. First choose mirror endpoints from
Gutenberg's [machine-access guidance](https://www.gutenberg.org/policy/robot_access.html)
and [mirror list](https://www.gutenberg.org/dirs/MIRRORS.ALL). Check their layouts:
main content is digit-sharded; generated content sits in ebook-ID directories.
The example hosts below are placeholders, not operational defaults.

```python
from lcats.gettenberg import resources

routes = resources.GutenbergRoutes(
    main_root="https://main.example/books/",
    generated_root="https://generated.example/epub/",
)
choice = resources.select_routable_resource(ebook, routes=routes)
for index, route in enumerate(choice.routes):
    if route.request is None:
        print(index, route.code, route.message)
print(choice.selection.matched_format, choice.selection.diagnostics)
```

Defaults prefer UTF-8 plain text, other plain text, then HTML, among qualified
routes. Pass `preferences=(resources.ResourcePreference("application/epub+zip"),)`
for EPUB bytes, for example. This does not add an EPUB text extractor. A supported
alternative is a separate resource, not proof of byte equivalence to a rejected
alias. Inspect the selected source URI and request URL before granting access:

```python
store = resources.ResourceStore("cache")
if choice.request is not None:
    print(choice.request.source_uri, choice.request.request_url)
    print(store.plan(choice.request).action)  # blocked on a cold offline cache
else:
    print("No routable resource matches the format preferences")
```

These steps perform no network access or cache creation. Unknown origins,
historical layouts and aliases have explicit rejection codes; they are never
tried as a sequence of guessed URLs. A no-match result needs your attention,
not an automatic fallback to the human-facing Gutenberg site.

Once you have chosen and authorized the real mirror origins, fetch explicitly:

```python
policy = resources.NetworkPolicy(
    online=True,
    allowed_origins=("https://main.example", "https://generated.example"),
)
if choice.request is not None:
    artifact = store.fetch(choice.request, policy=policy)
    print(artifact.path, artifact.receipt.source_uri, artifact.receipt.final_url)
```

A subsequent `store.fetch(choice.request)` reuses verified cached bytes offline.
The acquisition receipt retains its original caller's source URI even when
another catalog alias later maps to the same request URL. Keep `choice` alongside
the artifact if you also need the current selection's metadata. Decode separately
using [the decoding workflow](gettenberg-decoding.md).

For an individual URI, resolve without catalog selection:

```python
decision = routes.resolve("https://www.gutenberg.org/files/84/84-0.txt")
print(decision.code)
if decision.request is not None:
    print(decision.request.request_url)
```

For catalog acquisition, `routes.catalog_request()` describes the independently
configured archive URL (the published Gutenberg feed by default). Its origin
needs its own online permission. The existing [catalog setup workflow](gettenberg-catalog.md)
accepts the fetched artifact and independently validates it; choosing a route
cannot bypass catalog validation or count-change approval.

See [the route reference](../reference/gettenberg-network.md#qualified-offline-gutenberg-routing)
for supported aliases, roots, diagnostics and limitations. `lcats gather` has not
yet migrated to this API; these examples are library workflows.
