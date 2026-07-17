# M3 Brief: Rewrite and Verify

## Purpose and FR ownership

Generate multiple declarative alternatives and block meaning or diversity regressions. Owns FR5 and FR6.

## Interface contract

**Input:** `CandidateRecord` plus `ClassificationRecord` labeled harmful or explicitly reviewer-selected; source `NormalizedItem`; thresholds.  
**Output:** at least two `RewriteRecord` objects and one `VerificationRecord` per rewrite.  
**Failure:** protected-fact extraction failure, generator unavailable, retained pattern, fact/modality/negation drift, substitute repetition breach.  
**Permission:** append M3 artifacts; optional approved/redacted generation; cannot accept a rewrite.

```text
extract protected numbers, entities, URLs, citations, modality and negation scope
generate two constrained alternatives or load prototype fixtures
for rewrite:
  run exact protected checks
  run residual-pattern and length checks
  run independently configured semantic check
aggregate corpus substitute-pattern metrics
block any failed or uncertain rewrite
```

## Alternatives

- A: Multiple model-generated alternatives plus deterministic and independent semantic checks.
- B: Template-guided sentence editor with deterministic checks only. Safer fallback, narrower coverage.

## Verification

Fixtures for numbers, citations, names, legal negation, modal verbs, quotations, empty contrast, and patterned substitutes; failure must route to review without exporting a candidate.
