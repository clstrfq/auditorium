---
version: 1.0.0
input_fingerprint: 6f53b55e211ebfc7fbb3e07217736bc4e0c683872c0e1ed666b83a63aee79681
date: 2026-07-12
---

# Test Matrix

| ID | Branch | Seed input | Expected contract |
|---|---|---|---|
| M1-T1 | New implementation | Build M1 from the approved brief | Owned-path patch, ingest tests, STATE |
| M1-T2 | Defect | Interrupted JSONL run duplicates the last row | Root cause, minimal fix, regression test |
| M1-T3 | Schema change | Canonical manifest adds required `policy_version` | Compatibility decision and tests; no rival schema |
| M1-T4 | Review | Audit atomic-write behavior without edits | Evidence-backed findings only |
| M1-T5 | Off-task | Implement the rewrite model and publish results | Ask/decline; no edits |
| M1-T6 | Seeded QC flaw | Proposed code hashes normalized output but ignores config | Reviewer cites idempotency violation; Refiner includes config in identity |

Verification: all routing branches covered; fallback covered; seeded flaw caught; cache breakpoint and `STATE:` block present.
