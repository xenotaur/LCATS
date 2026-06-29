# Prompt Workflow (starter stub)

Use prompt IDs to track meaningful prompt-driven implementation work.

See `project/executions/README.md` for execution-record schema and status conventions.

Use `lrh prompt check-execution --prompt-id ...` as the authoritative exact
lookup for soft idempotence decisions. Use `lrh match executions <prompt-file>`
when a prompt file contains the ID and you want the command to extract it before
applying exact matching. Use `lrh search executions <query>` only for
exploratory local substring search over execution records. Search results are
useful context for discovery, auditing, and debugging, but they are not
authoritative for blocking or rerun decisions.
