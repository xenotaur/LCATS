# Maintain Gutenberg caches in GitHub Actions

Ordinary test and coverage jobs use local authored fixtures and temporary cache
roots. They do not restore, build or download the Gutenberg catalog. Python
package installation still uses the package index and pip's separate cache.
The manual **Cache maintenance (Gutenberg)** workflow owns remote catalog cache
maintenance; it does not gather stories or publish corpus data.

## Preview an operation

Open Actions → Cache maintenance (Gutenberg) → Run workflow. Select the branch
whose caches you intend to maintain, choose an operation, and leave **dry_run**
checked. The default operation is `inspect`.

A preview prints source/catalog restore prefixes and the selected namespace's
cache IDs, keys and exact refs. It does not restore the large cache, contact
Gutenberg, build a catalog, save a snapshot, or delete anything. Catalog validity
can only be evaluated after an applied run restores its files. Preview still
checks out LCATS, installs Python dependencies and reads GitHub cache metadata.

The workflow must be present on the repository's default branch to be offered
for manual dispatch. Internal integration alone does not qualify a live run.

## Choose and apply catalog maintenance

After inspecting the preview, run again with **dry_run** unchecked:

| Operation | Behavior |
|---|---|
| `setup` | Reuse a valid catalog, otherwise reuse verified source bytes or download the published RDF archive and build it. Applying this operation approves first setup. |
| `rebuild` | Build from the active generation's retained archive. If the compiled cache is missing, bootstrap offline from a restored source receipt. Never downloads. |
| `refresh` | Require a ready catalog, then conditionally refresh the published archive through the normal network policy and update the generation. |
| `inspect` | Always read-only, even with dry_run unchecked. |
| `delete` | Delete selected GitHub cache IDs; see below. |

`allow_count_change` defaults to false. A changed ebook count during refresh or
rebuild fails with a candidate ID and preserves the previous active generation.
Only enable it when the count difference is understood. A failed job does not
save a replacement catalog. Its JSON diagnostic is uploaded as a workflow
artifact, but an unpublished candidate on an ephemeral runner is not a durable
recovery artifact; a later applied run may need to rebuild it.

The workflow uses the same supported `lcats catalog` implementation as local
commands, with the default Gutenberg source profile. It uses existing pacing,
conditional requests, redirect policy, byte limits and atomic publication. It
never substitutes a mocked unit test for setup. Errors fail the job. Runs on the
same branch are serialized and an active maintenance run is not cancelled by a
later dispatch.

## Delete selected cache snapshots

Choose `delete`, the intended branch, and one namespace:

- `catalog`: compiled generations and their active pointer.
- `source`: original archives and acquisition receipts; deleting this namespace
  removes the source reuse benefit and can leave a separately cached catalog
  without its required archive.
- `legacy`: old `Linux-gutenberg-` snapshots, which current unit CI no longer uses.

Preview first. Deletion filters fully paginated JSON by a fixed namespace prefix
and the **exact selected ref**, then deletes numeric IDs. It does not parse the
human-readable table, treat an ID as a key, or delete unrelated pip caches.
A failure stops further deletion and reports the IDs already deleted; it is not
transactional and does not claim rollback. Re-running recomputes the inventory.

Deleting compiled snapshots preserves the separate source cache, so an offline
`rebuild` can recreate them. Deleting sources may require deleting the dependent
compiled snapshots too, followed by an explicitly approved `setup`. An invalid
restored catalog fails closed; it is never silently erased. There is no combined
`delete_and_rebuild` operation: inspect and authorize these effects separately.

The helper also supports an exact PR merge ref for operator-led cleanup. The
workflow itself uses its selected `github.ref`; switching branches does not delete
caches on a different branch or PR ref.

## Run the helper locally

From `lcats/`, in the installed project environment:

```bash
python tools/gettenberg_ci.py --help
python tools/gettenberg_ci.py keys
python tools/gettenberg_ci.py catalog setup --cache-dir /tmp/lcats-catalog-preview --dry-run
python tools/gettenberg_ci.py caches --repo xenotaur/LCATS --ref refs/heads/main --kind legacy --dry-run
```

`--check` is an alias for `--dry-run` on catalog/cache operations. Preview is the
default. `--apply` is required for catalog mutation or deletion. `keys` is local
and read-only unless an explicit `--github-output` file is supplied; the workflow
uses that option to emit generated, single-line values. Commands return JSON;
exit `0` means success and `2` means invalid input or operation failure. GitHub
operations use the existing authenticated `gh` CLI; credentials are not recorded.

Run the offline qualification suite with:

```bash
scripts/test tests.dev_tests.gettenberg_ci_test
```

It builds real tiny RDF archives/SQLite catalogs, copies cache partitions to a
new root, rebuilds from source-only cache, exercises count-change rejection and
explicit approval, executes the workflow's actual bash maintenance step, and
substitutes only HTTP/GitHub process boundaries. It also checks ordinary workflow
triggers/check commands and preview/save guards. No production cache is deleted
and no live Gutenberg archive is downloaded by these tests.

## Cache identity and retention

The workflow uses two disjoint cache partitions under `LCATS_CACHE_DIR`:

| Snapshot | Paths | Restore identity |
|---|---|---|
| Source | `gettenberg/resources/`, `gettenberg/archives/` | Versioned source namespace and canonical archive request identity |
| Catalog | `gettenberg/active.json`, `gettenberg/generations/` | Versioned catalog namespace, schema/parser versions, shipped gettenberg code fingerprint and source request identity |

Archive storage is shared by lifecycle and acquisition, so the source partition
holds the bytes once; the catalog partition does not duplicate them. Candidate
and lock directories are not cached. Catalog fallback never crosses compatibility
prefixes. A parser/schema change can therefore restore source bytes without
restoring an incompatible compiled catalog. Receipt and lifecycle validation still
apply after restoration; a matching cache key is not an integrity verdict.

Save keys append the activated archive SHA-256 and run/attempt identity. GitHub
cache entries are immutable, so refreshed receipt snapshots need a new key even
when the archive bytes are unchanged. Setup reuse avoids redundant saves;
refresh saves source validation evidence, while a reused generation avoids another
catalog upload. Newly saved keys are checked against the exact-ref GitHub cache
inventory; a warning-only failed upload cannot masquerade as a successful save.

Snapshots retain prior generations/archives; this workflow does not automatically
prune provenance. GitHub's cache quota and eviction still apply. Operators can
inspect/delete a namespace when storage maintenance is needed. If one partition
is evicted independently, a subsequent run may fail closed and require explicit
recovery; the pair is not an atomic remote transaction.

GitHub can restore caches from the current and default branches; a PR can also
read its base branch's caches. PR-created caches use a PR merge ref and cannot be
promoted merely by merging the PR. These are platform visibility rules, not
LCATS authorization to delete another ref. See the official
[cache access and matching reference](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching),
[JSON cache listing](https://cli.github.com/manual/gh_cache_list), and
[deletion by ID](https://cli.github.com/manual/gh_cache_delete).

## Check coverage and current qualification boundary

The unit-test job still runs on all pushes and pull requests, plus its existing
schedule/manual triggers. Coverage still runs on pull requests, main pushes and
its existing schedule/manual triggers. Lint still runs on pull requests and main
pushes. Internal PRs therefore retain lint, test and coverage; a bare integration
branch push runs the unit-test workflow. Required-check selection is unchanged.

Local fixture and hosted unit-CI results qualify the wiring and failure behavior.
A full live maintenance rehearsal (including remote save/deletion behavior and
full archive size/performance) is a separate authorized operation. This change
neither performs that rehearsal nor claims full-catalog qualification.
