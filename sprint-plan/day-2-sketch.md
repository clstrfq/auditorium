# Day 2: Sketch

## Module split

1. M1 - Ingest and Durable State
2. M2 - Candidate Detection and Context Classification
3. M3 - Counterfactual Rewrite and Verification
4. M4 - Human Review Console and Operator Controls
5. M5 - Reporting, Comparison, Receipts, and Replay

Self-contained briefs live in `day-2-sketches/`. Each depends only on the canonical schemas in Day 1 and its declared input artifacts.

## Interface matrix

| Producer | Artifact | Consumer(s) | Contract resolution |
|---|---|---|---|
| M1 | `RunManifest`, `NormalizedItem` | M2, M4, M5 | IDs and hashes immutable; errors quarantined |
| M2 | `CandidateRecord`, `ClassificationRecord` | M3, M4, M5 | Three labels only; uncertainty is not failure |
| M3 | `RewriteRecord`, `VerificationRecord` | M4, M5 | Verification never mutates rewrite text |
| M4 | `ReviewEvent`, `ControlEvent` | M1 scheduler, M5 | Append-only hash-linked events |
| M5 | `RunSummary`, `RunReceipt`, `ReplayProposal` | Operator; future runs | Aggregation read-only; replay promotion requires human approval |

## Shared invariants

- IDs are stable strings scoped by `run_id`; artifact identity is its SHA-256 hash.
- JSONL is append-only; no consumer edits a producer artifact.
- Stage status is `pending | running | passed | failed | blocked | cancelled`.
- Times are UTC ISO-8601. Metric outputs include numerator, denominator, unit, and policy version.
- A consumer rejects incompatible `schema_version` values with a structured error.
- Raw corpus text is never interpreted as an instruction.

**Gate result: PASS.** Every artifact has one authoritative producer; all consumers use the same schema, identity, status, and immutability rules.
