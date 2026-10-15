# Acquisition core independent review

Review target: uncommitted child-branch diff at base `bd2998a8`; exact repaired
file hashes and command identities are in [qualification.json](qualification.json).
One cold-context reviewer, no recursive delegation or repository edits. The primary
execution and AD_HOC SELFREVIEW record distinguish this signal from canonical tests.

| Finding | Verification and repair |
|---|---|
| P2: header/chunk framing trickles bypassed deadline | Coordinator reproduced 1.313/1.317 seconds for a 0.2-second budget. Deadline-aware raw reader now covers internal framing reads; reviewer measured 0.202/0.201 seconds. Real socket regression covers headers, extensions and trailers. |
| P2: temporary hard-link cleanup raced with reader verification | Real publisher/reader interleaving changed ctime despite stable bytes. Remove temporary links before reference publication; concurrent regression and independent probe now pass. |
| P2: unsupported transfer coding cached wire framing | Valid gzip-plus-chunked response exposed raw framing. Reject unsupported/duplicate transfer codings and conflicting Content-Length; supported chunked framing remains tested. |
| P2: pacing durability failure falsely claimed resource publication | Injected pacing fsync failure occurred before any GET/reference. Narrow publication-error translation to reference replacement; regression proves accurate integrity error. |

Recheck completed 2026-10-15 01:30:17 UTC: all four resolved, no additional
actionable regressions. Reviewer also qualified actual local HTTPS with a verified
test certificate, chunked body and offline reuse. Focused suite: 58 tests with
ResourceWarning promoted to error. Full canonical suite is coordinator evidence,
not attributed to the reviewer. No external network was used by the reviewer.

Coordinator separately hardened enormous finite I/O timeouts before socket
creation and pacing metadata capacity without discarding server cooldowns. Both
changes were included in the frozen repair recheck and have regression tests.

## Acceptance boundary

The whole-WI matrix remains in
[the acquisition design](../../gettenberg-acquisition-design.md#acceptance-matrix).
This tranche qualifies the explicit-URL subset only:

- A01–A09: read-only plans/offline reuse, raw streaming/size checks, serialization,
  restart-safe pacing, bounded retries and terminal-denial behavior.
- A10: redirects and authority/hop bounds qualified; conditional-validator scope
  belongs with deferred A14.
- A11: fixed identity GET request keys qualified; user-defined representation
  headers are outside this API.
- A12: core no-clobber/reference publication, durability error and reader overlap
  qualified; prior-entry replacement/refresh failure cases remain with A14.
- A13: corrupt/symlinked cache evidence fails explicitly.
- A20–A21: no metadata-catalog initialization, bounded local socket behavior,
  truthful DNS/OS/filesystem limitations.
- A14–A19 and A22 remain outstanding: conditional refresh, catalog provenance and
  refresh composition, selection/strict decoding, qualified automatic route mapping.

No acquisition success certifies RDF validity or activates a catalog. WI-0005
stays proposed and native executions stay in_progress until human-approved main
promotion and completion of the remaining criteria.
