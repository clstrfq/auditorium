---
version: 1.1.0
input_fingerprint: 44ee9fb9d6a09803806afa39349aad1deebb436644ee4b49e130843f022bf7d3
date: 2026-07-12
---

# Routing Decision Table

| Task ID | Default | Family requirement | Retry | Escalation | Terminal | Decision authority |
|---|---|---|---|---|---|---|
| T1 | T0 | None | Deterministic retry once | None | H on persistent I/O/schema failure | T0 |
| T2 | T0 | None | Ruleset retry once | T2 only for context classification, not offsets | H/uncertain | T0 offsets |
| T3 | T2 | At least F-A through F-E; equal family weight | Same tier once | T3 once | H/abstain | Ensemble after n_eff check |
| T4 | T0 | None for computation | Recompute once | T2 explanation only | H on incompatible/missing data | T0 |
| T5 | T3 | At least five evaluator families; generation-disjoint | Formatting retry once | None | H | T0 auto-fails + ensemble/H |
| T6 | T2 | Generator family excluded from judging same item | Same tier once | T3 once | H/no rewrite | Proposal only |
| T7 | T0 + T3 | At least 5 judging families; generator excluded | Formatting retry once | None | H/block | T0 exact blocks; ensemble cannot auto-accept |
| T8 | T1 | One family sufficient; source link mandatory | Same tier once | T2 once | H/unverified | Human/source record |
| T9 | T0 | None | Recompute once | None | H/block | T0 only |
| T10 | T3 | At least 2 non-generator families | Formatting retry once | None | H | Human |

## Route predicates

```text
if task in {hash, schema, regex, scoring, bootstrap, report}: T0
elif task == documentary_extraction and source_is_clear: T1
elif task in {bias_pass, rewrite_generation}: T2
elif task in {combo_interaction, semantic_safety, unresolved_conflict}: T3

if schema_invalid or evidence_missing or confidence_low:
    retry_same_tier_once
    then escalate_one_tier_once if current_tier < T3
    else abstain_to_human

if automatic_failure: BLOCK
if n_eff < 4: INCONCLUSIVE
if family_conflict or interval_crosses_threshold: REVIEW
```

## Downgrade checklist

- At least 200 shadow cases.
- Lower 95% performance bound within 2 points of incumbent.
- No increase in critical failures.
- No domain or Clarvoy-family subgroup collapses.
- Effective-family count unchanged.
- Human owner approves policy version bump.

## Changelog

- 1.0.0 - Initial stable T1-T10 decision table.
- 1.1.0 - Raised evaluator lineage floor to five and excluded generation treatment cells from evidence counts.
