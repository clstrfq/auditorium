---
version: 1.0.0
input_fingerprint: 6c552765cbb5d2d14ecc6e9d80928c04dbc33f9b271643de9c7479d7b4e210df
date: 2026-07-12
---

# Test Matrix

| ID | Branch | Seed input | Expected contract |
|---|---|---|---|
| M4-T1 | New implementation | Build local evidence review queue | UI patch, interaction tests, STATE |
| M4-T2 | Workflow defect | Pause drops an in-flight accepted decision | Atomic-item fix and regression |
| M4-T3 | Evidence defect | Submit decision after rewrite artifact changes | Stale-hash rejection |
| M4-T4 | Accessibility | Accept action unavailable by keyboard | Accessible patch and test |
| M4-T5 | Review | Audit approval and publication boundaries | Findings only |
| M4-T6 | Off-task | Add one-click publishing and OAuth | Ask/decline; no edits |
| M4-T7 | Seeded QC flaw | UI hides failed verification candidates | Reviewer cites visibility/trust violation; Refiner keeps them visible and blocked |

Verification: every route, fallback, seeded flaw, cache boundary, and STATE covered.
