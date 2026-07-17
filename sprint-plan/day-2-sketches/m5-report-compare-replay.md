# M5 Brief: Report, Compare, Receipt, and Replay

## Purpose and FR ownership

Aggregate traceable metrics, compare compatible runs, emit receipts, and propose adjudicated regression cases. Owns reporting portion of FR2 plus FR8, FR9, and FR10.

## Interface contract

**Input:** immutable artifacts and review/control events from M1-M4.  
**Output:** `RunSummary`, Markdown report, `RunReceipt`, paired comparison, and `ReplayProposal`.  
**Failure:** missing artifact, incompatible manifests, denominator mismatch, unresolved critical drift, absent human release approval.  
**Permission:** read-only aggregation; write report artifacts; cannot change source or approve replay promotion.

```text
validate hashes and schema compatibility
derive metrics from item-level records with explicit denominators
block paired comparison when corpus/policy mismatch is material
build report and unresolved queue
if named approval exists: issue release-decision receipt
propose adjudicated edge cases for human replay promotion
```

## Alternatives

- A: Python aggregation producing JSON + Markdown + signed hash receipt.
- B: SQLite analytics dashboard. Better exploration, unnecessary for the first evidence test.

## Verification

Recompute every aggregate from fixture records; denominator mutation test; incompatible-run block; receipt hash stability; replay proposal preserves source and adjudication provenance.
