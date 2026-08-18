# secrets_hygiene

Tooling for finding leaked secrets in git history and, when you decide it's
worth doing, scrubbing them out. Written after a live OpenAI key was found
committed in `lcats/notebooks/04_rag_expt.ipynb` (see
[`lcats/docs/how-to/secrets-hygiene.md`](../../docs/how-to/secrets-hygiene.md)
for the incident background and the revoke/confirm/enable-scanning runbooks
this tooling complements).

Two scripts, meant to run in sequence with a human checkpoint between them:

```
find_secrets.py   → findings.json, replacements.txt   (read-only, safe to run anytime)
                     |
                     |  <-- you review these files by hand
                     v
purge_history.py  → rewrites a throwaway mirror clone, verifies, prints
                     the push command it will NOT run for you
```

## Background

`find_secrets.py` wraps [gitleaks](https://github.com/gitleaks/gitleaks),
which scans full git history (`git log -p --all` under the hood) rather
than just the working tree, so it catches secrets that were later deleted
from a file but still exist in old commits. We use a scanner instead of
hand-written regexes because a fixed pattern list (e.g. just `sk-proj-...`)
only catches key formats we already knew to look for.

`purge_history.py` wraps
[git-filter-repo](https://github.com/newren/git-filter-repo), which is what
[GitHub's own docs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
recommend for this over the deprecated BFG Repo-Cleaner / `git
filter-branch`.

## Run

Both require external binaries on `PATH`:

```bash
brew install gitleaks git-filter-repo
```

### 1. Find

```bash
python experimental/secrets_hygiene/find_secrets.py /path/to/repo-or-mirror \
    --out-dir experimental/secrets_hygiene/scratch
```

Read-only — scans the given repo/mirror and writes `findings.json` (raw
gitleaks report) and `replacements.txt` (draft `secret==>placeholder`
lines, deduped) into `--out-dir`. Does not touch the repo it scans.

### 2. Review (manual — see below)

### 3. Purge

```bash
python experimental/secrets_hygiene/purge_history.py \
    https://github.com/xenotaur/LCATS.git \
    experimental/secrets_hygiene/scratch/replacements.txt \
    --refs-file experimental/secrets_hygiene/scratch/refs.txt \
    --mirror-dir experimental/secrets_hygiene/scratch/mirror.git
```

Clones a fresh `--mirror` of `source` (never touches your working
checkout), runs `git-filter-repo --replace-text` scoped to the refs listed
in `--refs-file`, re-scans the result to confirm every listed secret is
gone, then **prints** the `git push --force` command for each ref instead
of running it.

`refs.txt` format — one ref per line, e.g.:

```
refs/heads/main
```

Omitting `--refs-file` is refused on purpose: an unscoped run would rewrite
every ref in the mirror, which is very likely broader than you intended.

## Manual steps

These are deliberately **not** automated, and the scripts stop right before
each one:

- **Deciding which secrets in `replacements.txt` are real.** gitleaks'
  regex+entropy detection has false positives (long test fixtures, hashes,
  placeholder examples like the literal `sk-proj-...` in
  `lcats/docs/secrets-setup.md`) and, more rarely, possible false
  negatives. Read `findings.json` and edit `replacements.txt` before it
  goes anywhere near `purge_history.py`.
- **Deciding which refs to purge.** `purge_history.py` refuses to guess this
  for you — you pass `--refs-file` explicitly. Check blast radius first:
  ```bash
  git branch --all --contains <earliest-offending-commit>
  ```
- **The actual `git push --force`.** `purge_history.py` verifies the
  rewrite and prints the exact command but does not run it. This is the
  point of no return for anyone tracking that branch — see "Before you run
  this" below.
- **Notifying every collaborator/branch owner** (human or bot — Kenny, and
  whatever owns the `bolt/*`, `codex/*`, `jules-*` branches) *before* you
  push, not after.
- **Filing a GitHub Support request to purge cached views**, if the repo
  was ever public with the secret exposed. Rewriting your own repo's
  history does not reach GitHub's caches, other people's forks, or clones
  made while the secret was live — only GitHub Support can address those,
  and only revocation actually stops them from being useful.

## Before you run this

`purge_history.py`'s output ends with the push command; running it is a
destructive, hard-to-reverse action with a blast radius easy to
underestimate. Concretely, for this repo:

- **The rewrite touches far more than one branch.** The earliest leaked-key
  commit was an ancestor of ~177 of this repo's refs — nearly every branch,
  including active work-item branches and every bot-owned branch
  (`bolt/*`, `codex/*`, `jules-*`, `claude/*`). Rewriting history changes
  the SHA of every commit downstream of the leak on every ref that
  contains it.
- **Every existing local clone of an affected branch becomes stale.**
  `git pull` on an old clone does not fail loudly — it silently
  reintroduces the old (secret-containing) history via merge. Collaborators
  must discard the clone and re-clone, not pull.
- **Open PRs off any affected branch will likely break** since their base
  history changes underneath them; expect to close/reopen or manually
  rebase them.
- **This does not fully undo the exposure.** Per GitHub's own docs, cached
  views on GitHub, and anyone who already forked or cloned the repo while
  it was public, keep the old data regardless of the rewrite — that
  requires a separate GitHub Support request.
- **The actual security fix already happened at revocation**, not here.
  If the leaked key is already revoked (as it was in this incident), a
  history purge is hygiene/compliance cleanup, not an active-exposure fix —
  which is exactly why it's reasonable to scope this down or defer it
  rather than force-pushing across dozens of branches with open work on
  them.

Given the above, the working default for this repo has been: **document
the runbook and tooling, but hold off on executing an all-branches purge**
until the affected branches' open work has landed and the actual scope can
be chosen deliberately.
