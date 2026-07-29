---
id: PROP-LCATS-PYPI-RELEASE-READINESS
type: design_proposal_set
status: proposed
implementation_status: partial
---

# LCATS PyPI Release Readiness

This proposal set records the design for getting LCATS to a real,
non-placeholder PyPI release: resolving the `gutenbergpy`
direct-VCS-dependency upload blocker, delivering minimal release-version
tooling, and gating any real publish behind a dedicated pre-launch
verification step.

## Documents

- [`00_proposal.md`](00_proposal.md) — background, PyPI upload-validation
  grounding, design decisions, non-goals, and implementation plan.

Governed by [`WS-RELEASE`](../../../workstreams/proposed/WS-RELEASE.md).
