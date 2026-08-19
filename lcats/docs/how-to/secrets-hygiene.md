# Secrets Hygiene — Responding To and Preventing Leaked API Keys

This guide covers what to do when an API key may have leaked, and how to
harden the repository against future leaks. It complements
[Set up API keys](../secrets-setup.md), which covers day-to-day local key
storage via `.secrets/`.

## Background: how we found a leaked key

In August 2026 we noticed unexpected OpenAI usage ($62.41 in a single day)
and initially suspected a collaborator had accidentally used a personal key.
Investigation instead found a live OpenAI key committed directly into
`lcats/notebooks/04_rag_expt.ipynb`, saved as notebook **cell output** (from
a `print(...)` of the key while testing the OpenAI client) rather than as
code. The commit dated back to March 2025, and the repository is public on
GitHub, so the key had been publicly visible for well over a year.

Two things made this worse than it needed to be:

- **GitHub secret scanning / push protection was disabled** for the
  repository. GitHub scans public repos for free by default and, for
  partner-issued tokens (OpenAI, AWS, etc.), reports matches directly to the
  provider so the provider can auto-revoke — but only if scanning is
  enabled. See [Enabling this feature](#3-enable-github-secret-protection)
  below.
- Notebooks predate the `.secrets/` convention documented in
  [secrets-setup.md](../secrets-setup.md) and load keys in a way that can
  leave them in saved cell output.

**Update**: a second, unrelated live key was found the same way this
tooling's coverage was being evaluated — a hardcoded Azure OpenAI key in
`lcats/notebooks/05_prog_llm_csharp.ipynb` (committed January 2025, still on
`main` when found). It had gone undetected because Azure keys have no
distinguishing prefix and the notebook's JSON-escaped quoting defeated
gitleaks' generic context rule; see
[`lcats/experimental/secrets_hygiene/README.md`](../../experimental/secrets_hygiene/README.md)
for the technical detail and the `.gitleaks.toml` rule added to close that
specific gap. The key has been removed from the notebook (replaced with the
`Environment.GetEnvironmentVariable` pattern already used elsewhere in the
same file) — **revoke/regenerate it in the Azure portal** the same way as
any other confirmed leak, per the runbook below.

The sections below are written as reusable runbooks, not just a record of
this one incident.

## 1. Revoking a leaked or suspect API key

Do this **immediately** on suspicion of a leak — before investigating further.
A live key is actively billable and exploitable for as long as it exists.

1. Go to the [OpenAI API keys page](https://platform.openai.com/api-keys)
   (or the equivalent console for the affected provider — e.g.
   [Anthropic Console](https://console.anthropic.com/settings/keys)).
2. Identify the key by its prefix (OpenAI project keys look like
   `sk-proj-XXXXXXXX...`; the dashboard shows only a truncated prefix, which
   is enough to match against what you find in the repo — never re-paste a
   full key value anywhere to identify it).
3. Click **Revoke** / **Delete** next to the key. This takes effect
   immediately; any process still using it starts failing right away.
4. Treat **every** key that ever appeared anywhere in the repository's
   history as burned, not just the one you happened to notice — if one key
   leaked via a notebook or commit, assume any other key committed the same
   way is also compromised. Revoke all of them.
5. Issue a new key from the provider console, and distribute it only via the
   `.secrets/` pattern in [secrets-setup.md](../secrets-setup.md) — never by
   pasting it into a notebook, script, chat message, or commit.

**OpenAI API keys do not expire on their own** — there is no native TTL or
expiration date field. The dashboard's "Created" / "Last Used" columns are
exactly that; there is no "Expires" column. This was confirmed against the
OpenAI Developer Community, where the conclusion on this exact question is
that "OpenAI does not appear to offer a native feature to set expiration
dates on API keys themselves" (what people sometimes mistake for key
expiration is a free-trial *credit grant* expiring, which is a billing-level
thing, not the key) — see
[OpenAI Developer Community: OpenAI's API Key Expiration](https://community.openai.com/t/openais-api-key-expiration/102518).
This is unlike Azure OpenAI, whose keys do support configurable expiration
(commonly defaulting to around 6 months) at the Azure layer.

Because nothing enforces rotation for you, **periodically review
`platform.openai.com/api-keys` (and the equivalent page for every other
provider in use) and revoke anything old, unrecognized, or no longer in
active use** — don't wait for a suspected leak to do this. A stale key with
zero usage is still a live credential. If key sprawl becomes a recurring
problem, a short-lived-credential broker in front of the provider (e.g.
HashiCorp Vault's OpenAI secrets engine, which issues on-demand keys with an
enforced TTL and auto-revokes them) is the closest thing to real
expiration — likely overkill for this repo today, but worth knowing it
exists.
6. Rotating/revoking is the actual fix. Purging the dead key from git
   history (`git filter-repo`, followed by a force-push and having
   collaborators re-clone) is good hygiene afterward, but do not let history
   cleanup delay revocation — a dead key in old history is harmless once
   revoked, but a live key sitting in history is not. Tooling for the
   find-then-purge workflow lives in
   [`lcats/experimental/secrets_hygiene/`](../../experimental/secrets_hygiene/README.md);
   its README covers which steps are safe to automate and which must stay
   manual, plus the blast-radius considerations before force-pushing a
   rewritten history.

## 2. Confirming a suspicious charge matches a specific leaked key

Before assuming a collaborator's own usage explains an unexpected charge,
verify which key was actually billed. OpenAI tracks usage per API key
(automatic for keys created after December 20, 2023).

1. Open the [OpenAI usage dashboard](https://platform.openai.com/usage).
2. Filter by day to find the date of the unexpected spend.
3. Cross-reference the **API key ID** (or name, if you labeled it) shown
   against the usage line with the key ID for the key you're investigating —
   not just the total dollar amount, which alone doesn't tell you which key
   was used.
4. If the dashboard's per-key breakdown isn't precise enough, use the Admin
   API to pull usage scoped to one key ID directly, e.g.:

   ```bash
   curl "https://api.openai.com/v1/organization/usage/completions?start_time=<unix_ts>&api_key_ids[]=<key_id>" \
     -H "Authorization: Bearer $OPENAI_ADMIN_KEY"
   ```

5. Also ask the collaborator directly whether they made calls that day and
   with which key/account — in our case this confirmed the usage came from
   the collaborator's own key, not the leaked one, which meant the leaked
   key's usage was a separate, coincidental (and still real) exposure that
   needed its own revocation regardless.
6. Don't assume "collaborator says they made calls" and "there's a leaked
   key in the repo" are the same event — verify both independently. In this
   case both were true at once but for unrelated reasons: the collaborator's
   own key usage explained the specific charge in question, while the
   long-leaked notebook key was a separate, latent risk that still had to be
   revoked.

## 3. Enable GitHub Secret Protection

GitHub's secret scanning is free for public repositories, but it can be
turned off at the repository level — check that it actually is on rather
than assuming the default applies.

As of GitHub's current UI (the feature was renamed from "secret scanning"
under "Code security" to **Secret Protection** under **Advanced Security**):

1. Go to the repository on GitHub → **Settings**.
2. In the left sidebar, under the **Security** section, click
   **Advanced Security**.
3. Next to **Secret Protection**, click **Enable**.
4. Review the impact notice and confirm with **Enable Secret Protection**.
5. While there, also enable **push protection** if offered — it blocks
   pushes that contain a detected secret *before* they reach the remote,
   rather than only alerting after the fact.

You can verify current status from the CLI:

```bash
gh api repos/<owner>/<repo> --jq '.security_and_analysis'
```

Once enabled, GitHub scans the full history and all branches. For
partner-issued tokens (OpenAI, AWS, Anthropic, and others in GitHub's
partner program), a match is reported directly to the provider so they can
auto-revoke it — this is the mechanism that should have caught the leaked
key in this incident, and didn't, because the setting was off.

Any repository administrator can also disable this at any time, so it's
worth periodically re-checking the setting rather than treating "enabled
once" as permanent.

## Related

- [Set up API keys](../secrets-setup.md) — the `.secrets/` pattern for local
  key storage
- [OpenAI: Production best practices — API key safety](https://developers.openai.com/api/docs/guides/production-best-practices)
- [GitHub Docs: About secret scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning)
