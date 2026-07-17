# Gate B Methodology Upgrade — Algorithmic Voice

## Status

- Version: 1.0.0
- Evidence status: literature-grounded hypotheses; local replication pending
- Pipeline state: **PAUSED**
- Scope: evaluation additions only; no corpus acquisition, model execution, reward-model training, or FTPO run is authorized by this document

## Calibrated root-cause hypotheses

### H1 — Stage-specific diversity collapse

The 2026 study *Where does output diversity collapse in post-training?* reports, for three OLMo 3 post-training lineages across 15 tasks, that Think loses most semantic diversity during SFT while Instruct shows a larger incremental DPO loss. Suppressing visible chain-of-thought did not restore answer-level diversity in that experiment.

This supports a **checkpoint-by-stage hypothesis**, not the universal claim that every structural tic originates only in post-training. The suite will compare available base, SFT/instruct, DPO, reasoning-distilled, and RL checkpoints when genuinely matched. It will report task, dataset, lineage, and stage interactions rather than pool them into one causal estimate.

### H2 — Format and verbosity exploitation

Preference models and some human/LLM judges exhibit biases toward length and presentation features including lists, bold text, links, and emojis. Downstream best-of-n and iterative DPO can exploit those biases. DPO is therefore a plausible amplifier, but “inherently rewards every listed format” is too strong without model-specific counterfactual evidence.

Required test: hold semantic content approximately fixed while manipulating one format feature at a time, then estimate within-item preference flips and reward deltas.

## Counterfactual Data Augmentation protocol

Two matched families are added:

1. **Content-fixed / length-divergent:** preserve propositions, factual claims, stance, entailment, and task completion while changing token length and surface form.
2. **Length-fixed / content-divergent:** remain inside a preregistered token tolerance while manipulating factuality, informativeness, relevance, or reasoning validity.

Each candidate pair must pass before use:

- bidirectional entailment or proposition-set equivalence for content-fixed pairs;
- token-length tolerance for length-fixed pairs;
- protected-fact identity;
- no added/removed recommendation, certainty, caveat, citation, or refusal;
- blinded human review before any pair becomes reward-model training data;
- generator identity excluded from judging its own augmentation.

Primary CDA diagnostics:

- preference-flip rate under length-only intervention;
- reward slope per 100 tokens with content held fixed;
- content sensitivity with length held fixed;
- interaction of length with format feature, domain, and evaluator ancestry;
- out-of-fold calibration before and after CDA.

The target is reduced conditional length dependence while preserving sensitivity to factual and semantic quality. “Strict length invariance” is not required where additional length contains necessary information.

## MUSE sycophancy protocol

MUSE is implemented as a two-stage matched evaluation:

1. Estimate initial epistemic uncertainty over a fixed decision space before pushback. Store the probability vector, entropy, calibration bin, answer, and confidence elicitation method.
2. Apply randomized pushback varying asserted expertise and suggestion plausibility. Measure stance change, factual change, confidence change, and explanation change.

Predeclared outcomes:

- **certainty-region conformity:** yielding in the highest-certainty/calibrated-correct region;
- **uncertainty slope:** change in conformity probability as initial uncertainty rises;
- expertise and plausibility interactions;
- false-correction rate and warranted-correction rate;
- narrative-license/dilution score, separately from binary answer reversal.

Do not equate verbal confidence with epistemic uncertainty. Prefer token/log-probability distributions where accessible; otherwise mark elicited confidence as a weaker proxy and calibrate it out of fold.

## Expanded structural ontology

Every detector returns spans, counts, denominator, confidence, and a semantic-necessity label. Presence alone is not failure.

| Family | Detection unit | Required distinction |
|---|---|---|
| Negative parallelism | Existing 15 variants | functional contrast versus formulaic contrast |
| Tricolon | three coordinated syntactic/semantic units | three necessary distinct concepts versus filler third beat |
| Trailing participle clause | terminal present-participle adjunct | causally/informationally supported consequence versus generic evaluative padding |
| Em dash | Unicode em dash outside quotations/code | editorially warranted punctuation versus unexplained model-rate excess |
| Curly quote | Unicode quotation marks | source-preserving typography versus unsolicited typography; never intrinsically harmful |
| Transition pileup | repeated sentence-initial transition lexemes in a local window | discourse-required transitions versus redundant scaffolding |
| Bold lead-in list | markdown bold prefix followed by explanation | requested/functional scanability versus unprompted templating |

Rates are length-controlled and compared with domain-matched human baselines. Curly quotes and em dashes are style markers, not quality defects, unless the preregistered task contract makes them violations.

## FTPO mitigation gate

Antislop reports approximately 90% slop suppression for its studied models and evaluation conditions while maintaining or improving selected cross-domain metrics. This is a benchmark to replicate, not a promised outcome.

FTPO may start only after:

1. Gate B detects a reproducible model-specific pattern excess against licensed human baselines.
2. CDA shows the target is not merely a proxy for content or required length.
3. Protected facts and semantic-necessity labels are frozen.
4. Training and holdout pattern lists are disjoint.
5. A standard DPO, inference-time sampler, and no-treatment baseline are defined.
6. Exact base weights, training code, optimizer state, data hashes, and rollback checkpoint are available.

Acceptance requires a preregistered lower confidence bound for suppression plus non-inferiority bounds for factuality, task accuracy, semantic diversity, calibration, writing quality, and throughput. The published 69–96% sampler slowdown range is not imported as a suite fact until reproduced on this runtime and workload.

## Invalidation and stop rules

- Any detector trained on the held-out test corpus invalidates the relevant result.
- Any pattern ban that changes a protected fact blocks mitigation.
- CDA pairs failing semantic or length controls are discarded, not repaired after unblinding.
- MUSE conclusions are inconclusive without calibrated uncertainty measurements.
- FTPO remains experimental until replicated on at least two non-sibling model families.
- No local result may be generalized from OLMo 3 or Antislop to all post-training algorithms without cross-family evidence.

## Primary literature

- Karouzos, Tan, and Aletras (2026), *Where does output diversity collapse in post-training?*, arXiv:2604.16027.
- Zhang et al. (2025), *From Lists to Emojis: How Format Bias Affects Model Alignment*, ACL 2025.
- Kim, Oh, and Lee (2026), *Mitigating Length Bias in RLHF Through a Causal Lens*, AAAI 2026.
- Guo et al. (2026), *It's Not Always Sycophancy: Measuring LLM Conformity as a Function of Epistemic Uncertainty*, arXiv:2605.27288.
- Paech et al. (2026), *Antislop: A Comprehensive Framework for Identifying and Eliminating Repetitive Patterns in Language Models*, ICLR 2026.

