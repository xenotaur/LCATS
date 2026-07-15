# Prompt Execution Records

This directory stores lightweight records for meaningful prompt-driven work.
Records should identify the prompt ID, related work item, idempotence check,
summary of changes, tests run, and intentional deferrals.

A `scripts/prompts/record-execution` helper does not exist. This is intentional: the `lrh prompt
record-execution` CLI command creates the record stub directly, and records are then edited
manually to fill in the optional fields. No standalone script is planned.
