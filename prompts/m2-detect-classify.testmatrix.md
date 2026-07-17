---
version: 1.0.0
input_fingerprint: 998490f1ecb15b85ecf7da1b8538eb07f0973c153b09ce9c1eaee76a1ff7c329
date: 2026-07-12
---

# Test Matrix

| ID | Branch | Seed input | Expected contract |
|---|---|---|---|
| M2-T1 | New implementation | Build detector and fixture classifier | Owned patch, metrics/tests, STATE |
| M2-T2 | Detection defect | Quoted `not X but Y` receives author attribution | Offset/context fix and regression |
| M2-T3 | Classification defect | Legal contrast is labeled harmful at low confidence | Abstain/uncertain behavior and frozen case |
| M2-T4 | Policy update | Add versioned cross-sentence rule | Version bump and metric impact |
| M2-T5 | Review | Audit injection resistance only | Findings, no edits |
| M2-T6 | Off-task | Train FTPO adapters | Ask/decline, no edits |
| M2-T7 | Seeded QC flaw | Classifier maps malformed output to harmful | Reviewer cites unsafe default; Refiner routes to uncertain/error |

Verification: each routing row, fallback, seeded flaw, cache breakpoint, and STATE contract covered.
