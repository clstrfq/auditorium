# Gate B Preregistration: Negative Parallelism and Slop Evaluation

## Status and scope

- Version: 1.1.0
- Status: design frozen; execution blocked on corpus acquisition and model access
- Evidence grade target: E2
- Banner: **PROXY - NOT REAL-USER VALIDATION**
- Primary claim scope: conditional effects for the named corpus frames, model checkpoints, and inference configurations
- Methodology addendum: `validation-proxy/gate-b/methodology-upgrade-2026-07-12.md`

## Corrections to the submitted blueprint

1. Pre-2022 is a low-synthetic-contamination proxy, not proof of human authorship.
2. Generic PubMed/Crossref, Reddit, and commercial news text do not provide uniform reuse rights.
3. The 3 lineages x 3 configurations are treatment arms, not nine independent judges.
4. Three derivatives of one base are within-family training-regime arms, not genuinely independent lineages.
5. Clustering follows author/source and prompt nesting; “paper-clustered” is used only when paper is the highest independent unit.
6. Stage-specific collapse, CDA, MUSE, and FTPO effects are literature-grounded hypotheses requiring local replication; published effect sizes are not pipeline guarantees.

## Corpus

Exactly 300 English-original items published no later than 2021-12-31:

| Domain ID | Frame | N | Unit | License rule |
|---|---|---:|---|---|
| D1 | PMC Open Access biomedical abstracts | 100 | One abstract | Per-item CC0 or CC BY preferred; license URI required |
| D2 | Stack Exchange prose-rich Q&A | 100 | One question or one answer | CC BY-SA; attribution and dump version required |
| D3 | Global Voices licensed journalism | 100 | One article body | Per-item Creative Commons status verified; exceptions excluded |

These are biomedical, edited Q&A, and licensed-journalism proxy frames. Results may not be generalized to all academia, social media, or commercial newsrooms.

Sampling rules:

- Frozen seed `20260712`; select from a complete eligible frame, not search rank.
- One item per author by default. If repeated authors are needed, cap at 3 and cluster author.
- Balance publication year, source/site/outlet, and preregistered token-length bands.
- Exclude license ambiguity, deleted content, sensitive personal narratives, minors, medical/legal crises in D2, quoted third-party passages, generated/translated text disclosures, and missing provenance.
- Deduplicate exact hashes and near-duplicates before sampling; all variants of an item remain in one fold.
- Store raw text under local access controls; model inputs omit usernames/profile fields.

## Experimental panels

### Panel A - within-base training-regime study

Purpose: estimate conditional training-regime differences. Arms are correlated and cannot count as independent ensemble families.

- Exact frozen base/control: Qwen2.5-Math-7B family, subject to checkpoint-card verification.
- Instruct arm: exact matching Qwen2.5-Math-7B-Instruct checkpoint if available and card-verified.
- CoT-distilled arm: `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B`, whose card identifies Qwen2.5-Math-7B ancestry and R1-derived training data.
- RL-Zero arm: omitted unless an exact same-base reproduction is trained with frozen data, reward code, recipe, and hashes. Official DeepSeek-R1-Zero is not a matched 7B arm.

Panel A cannot claim universal causality because pretraining and unpublished training details may confound comparisons.

### Panel B - cross-family robustness panel

Purpose: estimate robustness and residual correlation across distinct base families, not causal alignment effects.

- Qwen2.5-7B-Instruct family.
- Mistral-7B-Instruct-v0.3 family.
- Llama-3.1-8B-Instruct family, subject to gated license/AUP approval.

Matched decoding and prompts are mandatory. Licenses and exact model revisions are stored in `model-arms.json`.

### Generation configurations

Each eligible generation model receives three fixed treatments:

- A: unconstrained baseline.
- B: operational direct-answer instruction with reasoning text suppressed where supported. This is an inference treatment, not proof of weight-level causation.
- C: authoritative-pushback/sycophancy challenge with a fixed prompt template.

Temperature, top-p, seed, max output tokens, stop rules, retry policy, and prompt hashes are identical or explicitly model-adapted and recorded. The nine model/config cells remain matched repeated-measure treatment outputs.

## Evaluator ensemble

Generation arms are judged by a separate, blinded evaluator panel. The generator family is excluded from judging its own output.

- Target at least 5 distinct evaluator lineages so correlation-adjusted `n_eff >= 4` is mathematically attainable.
- Two rubric formulations per evaluator family may test prompt sensitivity, but family weight remains equal and prompt variants do not count as independent families.
- Opaque randomized IDs; no source condition, model name, or competing judgment visible.
- Separate Clarvoy B bias, Q quantitative, and C interaction records are frozen before fusion.

## Endpoints

Primary endpoint: negative-parallelism/verbal-tic event rate per 1,000 generated tokens.

```text
VTI_rate_arm = 1000 * sum(events_i) / sum(tokens_i)
```

The phrase/tic ontology, tokenizer, overlap/deduplication rule, and classifier thresholds are frozen before generation. “VTI” is treated as a transparent metric vector/rate unless its composite weighting is independently validated.

Secondary endpoints:

- Vendi effective diversity, recomputed from the full domain x arm similarity matrix for every bootstrap replicate.
- Length-Controlled Win Rate with randomized/blinded presentation, preregistered ties/abstentions, and length bands set before judging.
- Brier/log scores, calibration error, Clarvoy B/Q/C risks, substitute-pattern rate, protected-fact failures, refusal/missingness.

## Statistical model

Experimental unit is the source document/prompt. All generation arms for one prompt form a matched block. If authors repeat, documents/prompts nest within author and author is the independent resampling cluster.

- Count outcome: negative-binomial GLMM after overdispersion check.
- Offset: log generated tokens.
- Fixed effects: panel/model, configuration, interaction, domain.
- Random intercept: author; prompt nested within author where repeated.
- LC-WR: paired/conditional logistic or ordinal model with ties modeled separately.
- Equal-domain-weighted marginal contrasts.

```text
log E[Y_ia] = log(tokens_ia) + beta_0 + beta_model + beta_config
              + beta_model*config + beta_domain + u_author + u_prompt
```

## Cross-validation and uncertainty

- GroupKFold is for leakage-safe fitting/tuning, not interval estimation.
- Outer 5 folds grouped by author/source family; inner folds fit thresholds/calibration. All nine treatment outputs stay together.
- Primary CI: author-cluster bootstrap within domain, retaining complete treatment blocks, 10,000 replicates, seed `20260712`.
- With few clusters: wild cluster bootstrap-t and t critical values.
- Vendi: recompute kernel/eigenspectrum within each bootstrap replicate; no ordinary per-item SE.
- Confirmatory contrasts use simultaneous max-|t| cluster-bootstrap bounds or Holm FWER. Exploratory Clarvoy families may report BH q-values.

## CLT and correlation rules

Asymptotic claims require finite moments, no dominant cluster, at least 30 independent authors overall and preferably 20 per domain, stable leave-one-cluster-out results, and bootstrap/analytic agreement.

For true replicate evaluators only:

```text
DE = 1 + (m - 1) * rho
n_eff = m / DE
```

Treatment arms never enter this equation as judges. If evaluator-family `n_eff < 4`, the ensemble result is inconclusive. With fewer than required clusters, heavy tails, >10% influential-cluster shift, or CI disagreement crossing a threshold, use exact/randomization inference or report inconclusive.

## Automatic failures

- Broken blinding or inconsistent configuration implementation.
- Same-base arms claimed as independent lineages.
- Missing author/provenance/license IDs.
- Duplicate or paraphrase leakage across folds.
- Threshold, kernel, or endpoint changed after unblinding.
- Differential missing outputs >5% without a preregistered failure estimand.
- Generator family judges itself.
- Evaluator `n_eff < 4` for ensemble claims.
- Protected-fact, provenance, privacy, or prompt-injection failure.
- Confirmatory CI crosses the gate threshold or multiplicity is uncontrolled.

## Gate B execution exit

Gate B may be scored only after all 300 manifest records validate, exact model revisions and access are frozen, every treatment output is complete or covered by the missingness rule, evaluator independence passes, and the preregistered analysis runs without automatic failure.
