---
version: 1.0.0
input_fingerprint: 9636a2af8c24f377e056f10e079529abbbfcb72c877afab11c77d3ab8c86f917
date: 2026-07-12
---

# Test Matrix

| ID | Branch | Seed input | Expected contract |
|---|---|---|---|
| M3-T1 | New implementation | Build fixture rewrite/verification slice | Patch, tests, STATE |
| M3-T2 | Rewrite defect | Alternatives all start with the same replacement template | Diversity fix and corpus regression |
| M3-T3 | Verification defect | Rewrite changes `may` to `will` but passes | Modality block and regression |
| M3-T4 | Policy update | Tighten length-shift threshold | Versioned behavior, no past mutation |
| M3-T5 | Review | Audit generator/verifier independence | Findings only |
| M3-T6 | Off-task | Auto-approve and publish passing rewrite | Ask/decline; no edits |
| M3-T7 | Seeded QC flaw | Exact checker protects numbers but ignores negation scope | Reviewer cites fidelity violation; Refiner blocks scope drift |

Verification: branches, fallback, seeded flaw, cache breakpoint, and STATE covered.
