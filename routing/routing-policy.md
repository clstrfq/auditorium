---
version: 1.1.0
input_fingerprint: 44ee9fb9d6a09803806afa39349aad1deebb436644ee4b49e130843f022bf7d3
date: 2026-07-12
---

# Hybrid LLM Routing Policy: Proxy Ensemble Forecasting

## Objective

Route each validation task to the cheapest tier that preserves its contract while separating generation treatment arms from a minimum five-lineage evaluator ensemble. Prompt variants within one family are cost experiments and correlated measurements; they never increase the independent-family count.

Accuracy and savings are projections until measured on the frozen Gate B/C evals.

## Tier definitions

| Tier | Class | Intended work | Failure-cost ceiling |
|---|---|---|---|
| T0 | Deterministic code/no LLM | Hashing, regex, metrics, bootstrap, schemas, reports | Any task fully specified by code |
| T1 | Small/quantized, roughly 0.5-8B or cheapest API tier | Bounded extraction, formatting, first-pass low-risk labels | No final safety/release decision |
| T2 | Mid capability | Bias detection, rubric classification, rewrite candidates, evidence extraction | May propose; cannot clear critical fidelity or governance gates alone |
| T3 | Frontier/top capability | Interaction reasoning, semantic safety, hard ambiguity | Required for high-severity review; still cannot self-approve |
| H | Human owner | Policy changes, waiver, unresolved conflicts, external effects | Final authority |

## Family separation

- Maintain at least five evaluator provider/model-lineage families, labeled F-A through F-E (or higher), in stored artifacts.
- At least one family must use a materially different provider or open-weight lineage from the others.
- Do not count distilled/mini/full variants of one lineage as separate families until empirical residual-correlation evidence supports that claim.
- Generation and judging for the same item must use different families.
- Rubric variants remain nested within family; each family receives equal initial weight regardless of prompt count.
- The 3x3 generation model/configuration cells are treatment arms and never enter evaluator `n_eff`.

## Task taxonomy and assignments

| ID | Task | Example | Output | Failure cost | Volume share | Difficulty | Route |
|---|---|---|---|---|---:|---:|---|
| T1 | Ingestion and provenance | Normalize JSONL and hash source | Canonical artifacts | High | 4% | 1/1/5/1 | T0 |
| T2 | Candidate phrase detection | Find `not X, but Y` offsets | Candidate spans | Medium | 8% | 1/2/5/2 | T0 |
| T3 | Clarvoy B bias pass | Flag anchoring, groupthink, confirmation | Bias vector + evidence | High | 22% | 3/3/4/3 | T2 across evaluator F-A through F-E |
| T4 | Clarvoy Q quant pass | Brier, ECE, dependence, n_eff, bootstrap | Metrics + intervals | Critical | 12% | 4/3/5/3 | T0 computation; T2 explanation only |
| T5 | Clarvoy C interaction pass | Authority plus compressed variance | Combo flags + risk | Critical | 14% | 4/4/5/4 | T3 across evaluator F-A through F-E; deterministic auto-fail rules T0 |
| T6 | Rewrite generation | Produce two declarative alternatives | Rewrite records | High | 14% | 4/3/4/4 | T2; escalate difficult cases to T3 using a non-judge family |
| T7 | Semantic/fidelity verification | Check modality and meaning | Verified/blocked record | Critical | 14% | 5/4/5/4 | Exact checks T0; semantic judges T3 across families |
| T8 | Documentary extraction | Extract claim/date/effort from source | E1 source record | Medium | 4% | 2/3/5/2 | T1; T2 on ambiguity |
| T9 | Report and receipt | Aggregate immutable results | JSON/Markdown/receipt | Critical | 4% | 2/3/5/1 | T0 only; no LLM arithmetic authority |
| T10 | Conflict/adjudication | B passes, Q/C block | Escalation packet | Critical | 4% | 5/5/5/5 | T3 cross-family review, then H |

Difficulty tuple is reasoning depth/context breadth/output precision/novelty, each 1-5.

## Escalation rules

For T1/T2 requests:

1. Validate schema and confidence.
2. On malformed output, missing evidence, confidence below threshold, or self-reported uncertainty, retry the same tier once with identical evidence and a repair instruction.
3. If still invalid, escalate one tier once.
4. If still invalid, abstain and route to H. Never cascade through multiple frontier calls.

T3 failures route directly to H after one formatting-only retry. Automatic failures from T0 cannot be overturned by a model. Every route logs task ID, family, tier, model/version, prompt/rubric hash, tokens, latency, retry/escalation, outcome, and item hash.

## Clarvoy-aware routing controls

- A1/B1/B7: all family judgments are blind and identity-hidden until frozen.
- A3/Q20: T3 reasoning requires a reference class or emits `inside_view_only`.
- B3/Q1-Q14: family weights use held-out Brier skill with shrinkage; model confidence never sets weight.
- Q24/UQ3: influence Gini and uniformity pressure can force H review.
- Q27: residual family correlation determines effective sample size.
- C15: recalibration is selected on training folds; overfit blocks promotion.
- UC1-UC5: governance/learning failures are T0/T3 hard-review triggers.

## Classifier specification

Use deterministic rule dispatch keyed by task ID because the current taxonomy is small and stable. A learned router is not justified yet.

Per-task routing evaluation:

- T3/T5: bias/combo macro-F1, evidence-span overlap, abstention accuracy.
- T6: protected-fact retention and rewrite eligibility.
- T7: critical-error recall, false-block rate, semantic agreement.
- T8: exact-match dates/URLs and claim-evidence precision.
- T1/T2/T4/T9: exact schema, deterministic recomputation, and hash equality.

Promote a task to a cheaper tier only when its lower 95% performance bound remains within 2 percentage points of the incumbent and no critical-error rate increases.

## Shadow sampling

- Shadow 10% of T2 traffic to T1 after Gate B begins.
- Shadow outputs cannot affect decisions.
- Evaluate by domain and Clarvoy flag family.
- Downgrade only after at least 200 shadow items and the promotion rule passes.

## Economics

Planning workload example: 300 Gate-B items plus 100 Gate-C passages x 3 variants, each judged by 5 evaluator lineages = approximately 3,000 evaluator calls, separate from generation treatment calls. Assume 1,200 input and 250 output tokens per evaluator call before caching.

```text
monthly_cost = calls * ((input_tokens/1M)*input_price + (output_tokens/1M)*output_price)
savings = 1 - routed_cost / all_frontier_cost
```

Using public list-price anchors available July 12, 2026, frontier input/output can span roughly $2-$15 / $12-$75 per million tokens, while efficient tiers can be around $0.25-$3 / $1.50-$15. Under the stated workload:

- All-frontier evaluator envelope: approximately $16-$110 per full proxy evaluation.
- Routed evaluator envelope: approximately $5-$45, depending on escalation and family mix.
- Headline estimated reduction: roughly 60%-85%, not guaranteed.

These estimates exclude caching discounts, batch discounts, generation calls, tools, and provider minimums. Pricing changes invalidate the estimate, not the task routing.

Pricing references, accessed 2026-07-12:

- Google Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Anthropic API pricing documentation: https://docs.anthropic.com/en/docs/about-claude/pricing
- OpenAI pricing page: https://openai.com/api/pricing/

## Severe-risk floors

- T5 interaction judgment: T3 minimum.
- T7 semantic safety: T0 exact checks plus T3 semantic judges.
- T9 arithmetic/provenance: T0 deterministic; no generative substitution.
- T10 unresolved conflict: T3 then human.
- External inference approval, release approval, waiver, production, or schedule installation: human only.

## Verification

- Every task has an example and tier.
- Severe-risk tasks have mandatory floors.
- Every non-top model route has a one-tier escalation and human terminal state.
- Economics formula, workload, ranges, source date, and exclusions are explicit.
- Family correlation and effective sample size govern evidence, independent of cost routing.

## Changelog

- 1.0.0 - Initial routing design for Clarvoy B/Q/C proxy ensemble.
- 1.1.0 - Separated 3x3 generation treatments from evaluator evidence and raised evaluator minimum to five distinct lineages.
