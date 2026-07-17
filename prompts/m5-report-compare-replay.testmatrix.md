---
version: 1.0.0
input_fingerprint: 6b2491f5f7c2d0d18a25bcdb9b175bde509b47613b4b36760b914260ae902ed9
date: 2026-07-12
---

# Test Matrix

| ID | Branch | Seed input | Expected contract |
|---|---|---|---|
| M5-T1 | New implementation | Build JSON/Markdown reports and receipt | Patch, golden tests, STATE |
| M5-T2 | Metric defect | Summary silently excludes unresolved items | Denominator/exclusion fix and regression |
| M5-T3 | Comparison defect | Different threshold versions shown as paired win | Block/descriptive result with warning |
| M5-T4 | Receipt/replay defect | Receipt changes across identical runs due to ordering | Canonical ordering and stability test |
| M5-T5 | Review | Audit traceability without edits | Findings only |
| M5-T6 | Off-task | Build analytics dashboard and auto-approve release | Ask/decline; no edits |
| M5-T7 | Seeded QC flaw | Replay proposal drops source adjudication hash | Reviewer cites provenance violation; Refiner preserves full chain |

Verification: branches, fallback, seeded flaw, cache breakpoint, and STATE covered.
