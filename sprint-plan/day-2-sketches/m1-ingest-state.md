# M1 Brief: Ingest and Durable State

## Purpose and FR ownership

Normalize CSV/JSONL safely, create an immutable manifest, enforce local-first policy, deduplicate identical runs, and support resume/cancel checkpoints. Owns FR1, core FR2, FR11 scheduler state, and FR12 policy initialization.

## Interface contract

**Input:** file path, field map, ruleset/rubric/threshold versions, model-destination policy, cost cap, `dry_run`.  
**Output:** `RunManifest`, `NormalizedItem[]`, quarantine records, checkpoint and control-state view.  
**Failure:** unsupported encoding, duplicate/missing ID, invalid schema, forbidden destination, hash/read error.  
**Permission:** read selected file; create one run directory; no external network.

```text
validate_policy(config)
stream source rows -> validate -> normalize or quarantine
hash source bytes + exact config
if successful receipt exists: return receipt reference
atomically persist manifest, normalized JSONL, checkpoint
```

## Alternatives

- A: Python CLI with Pydantic-style schemas and atomic JSONL/filesystem writes. Simple, testable, local-first.
- B: SQLite event store with import UI. Strong queries, but adds migration and locking scope before hypothesis testing.

## Verification

Golden CSV/JSONL imports; duplicate IDs quarantine; identical rerun returns same receipt; interrupted import resumes without duplicate records; forbidden external destination blocks before text leaves disk.
