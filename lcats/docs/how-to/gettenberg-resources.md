# Acquire and reuse original source bytes

Use this workflow when you already have a concrete permitted HTTP(S) file URL.
No Gutenberg metadata catalog is required. First choose a cache directory and
confirm that the source's automated-access policy permits the request. For
Gutenberg, consult its [robot policy](https://www.gutenberg.org/policy/robot_access.html)
and documented machine-access/mirror endpoints; an ebook landing page or format
alias is not itself a mirror URL. Use the [offline routing workflow](gettenberg-routing.md)
to map qualified Gutenberg aliases to configured mirror roots.

The URL below is illustrative; replace it with your actual source and allowed
origin before executing the download step.

```python
from lcats.gettenberg import resources

store = resources.ResourceStore("cache")
source = resources.SourceRequest.from_url("https://example.org/story.txt")

# Read-only: this creates no cache, requests, locks or sleeps.
plan = store.plan(source)
print(plan.action, plan.reason)  # blocked / offline cache miss on first use
```

To permit this origin explicitly, supply a policy. Keep the default limits unless
you have a concrete reason to change them.

```python
policy = resources.NetworkPolicy(
    online=True,
    allowed_origins=("https://example.org",),
)
print(store.plan(source, policy=policy).action)  # download, or reuse when cached
artifact = store.fetch(source, policy=policy)
print(artifact.path, artifact.sha256, artifact.size)
print(artifact.receipt.final_url)
```

A redirect to another origin requires that origin to be explicitly included.
Do not grant an unexpected origin merely to make a failing download succeed.
The store will not try other patterns or mirrors after denial.

On subsequent runs, omit the network policy to require offline reuse:

```python
artifact = resources.ResourceStore("cache").fetch(source)
```

The returned file contains original response-body bytes, including any server
Content-Encoding or archive container. Do not rename a legacy decoded `.txt` or
`.txt.gz` cache as an original, and do not assume the file is UTF-8 because the URL
ends in `.txt`. Use the separate [offline decoding workflow](gettenberg-decoding.md) to obtain text.

For an explicitly selected RDF archive URL, construct the request with
`kind="archive"`. Its verified body is retained in the catalog's shared archive
namespace; catalog setup is still a separate offline step. Acquisition does not
bypass the catalog's validation or count-change approval.

If a request is deferred, preserve the error's `next_eligible_at` in your scheduling
logic. Repeated immediate calls do not bypass the persisted cooldown. If cache
integrity fails, inspect/preserve the evidence; this API intentionally has no
implicit repair or destructive cleanup operation.

See [the reference](../reference/gettenberg-network.md) for exact limits, errors,
durability guarantees and conditional-refresh semantics.

## Explicitly check for a changed source

Normal fetches reuse verified bytes indefinitely. When you intend a network check,
inspect a refresh plan and then explicitly refresh with the same allowed-origin
policy. No separate catalog setup is needed:

```python
print(store.plan(source, policy=policy, refresh=True).action)
refreshed = store.refresh(source, policy=policy)
print(refreshed.receipt.status)  # 304: validated old bytes; 200: full acquisition
print(refreshed.receipt.retrieved_at, refreshed.receipt.validated_at)
```

With usable validators the server can avoid sending the body. Without them, refresh
performs a full GET. A successful refresh retains the previous body and receipt;
a failure raises an error while preserving the old entry unless a publication error
explicitly reports that replacement already happened. Use `fetch(source)` afterward
for offline access. Calling `refresh` without online authority is an error even
when bytes are cached. It never silently treats a failed refresh as success.

## Choose a catalog resource without downloading

Given an `ebook` returned by the catalog, inspect the preferred declared format:

```python
selection = resources.select_resource(ebook)
if selection.resource is None:
    print("No supported default format", selection.diagnostics)
else:
    print(selection.resource.uri, selection.matched_format)
    print(selection.diagnostics)
```

Defaults prefer declared UTF-8 plain text, then other plain text, then HTML.
You can supply ordered preferences, including formats without a text extractor:

```python
selection = resources.select_resource(
    ebook,
    preferences=(resources.ResourcePreference("application/pdf"),),
)
```

This only selects metadata. It does not establish decoder support, verify bytes,
resolve Gutenberg aliases, authorize an origin or fetch anything. All original
`ebook.resources` remain available for explicit selection. Once you have a
qualified concrete download URL, use the acquisition workflow above, or compose
selection and routing with `select_routable_resource` as described in the
[routing workflow](gettenberg-routing.md).
