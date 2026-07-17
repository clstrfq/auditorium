# PRD: Negative Parallelism Evaluation Harness

<!-- fs:overview:start -->
## Overview

**Status:** SIMULATED - requires human validation  
**Product type:** Local-first evaluation and rewrite harness for AI-generated professional prose  
**Source seed:** *Building AI Evals for Negative Parallelism* (16-page PDF supplied July 12, 2026)

The product helps AI quality leads measure and reduce negative parallelism - constructions such as "not X, but Y" - without silently damaging meaning, useful contrast, or stylistic variety. V1 evaluates saved model outputs, proposes declarative rewrites, compares the original and revised corpora, and emits auditable evidence. It does not require access to model logits or weights.

The source PDF supplies the problem framing and candidate mechanisms. Its quantitative, product-specific, and model-specific claims have not been independently verified and are treated as hypotheses.
<!-- fs:overview:end -->

<!-- fs:key-customer:start -->
## Key Customer

**Primary persona - AI quality lead at a content-heavy organization (SIMULATED - requires human validation)**

- Profile: 30-50; technical product, applied AI, content design, or editorial operations role; responsible for model-output quality across a team; can assemble JSONL/CSV test sets but may not control model weights.
- Ranked pains:
  1. Reviewers perceive recurring rhetorical templates as synthetic or low-quality, but the team lacks a reproducible measure.
  2. Prompt-only style constraints produce inconsistent results across models, releases, and content types.
  3. Aggressive phrase bans can remove legitimate contrast or shift meaning, creating a new quality problem.
  4. Quality changes are difficult to audit, compare, and reproduce after a model or prompt update.
- Existing success metric: human acceptance rate of generated copy before publication, supported by edit distance or average editorial revisions per output.

**Rejected secondary personas**

- Individual writer: has the pain, but usually lacks a corpus, repeatable release process, and budget for an evaluation harness.
- Foundation-model training researcher: needs logit/weight access and specialized optimization infrastructure; this would force an expensive research product before the core evaluator is validated.
- General-purpose grammar-tool user: expects broad grammar and tone correction, which would dilute the narrowly measurable job.
<!-- fs:key-customer:end -->

<!-- fs:problem:start -->
## Problem

AI quality leads cannot reliably determine whether a model, prompt, or editing pipeline overuses negative parallelism, nor can they reduce that pattern while proving semantic fidelity and preserving legitimate contrast. Manual review is subjective and slow; phrase counting misses context; blanket bans overcorrect. The urgent job is to turn a visible style complaint into a reproducible, reviewable release gate.

**Falsifiability:** Reject or materially narrow this problem if the documentary problem-evidence gate cannot establish independently attributable evidence of problem salience and current organizational effort, or if the subsequent observed prototype test shows no meaningful preference for the workflow over current practice. Documentary evidence cannot establish product demand or willingness to adopt.
<!-- fs:problem:end -->

<!-- fs:differentiation:start -->
## Differentiation

**Competitive set (SIMULATED - requires validation)**

| Alternative | Context sensitivity | Auditability | Limitation for this job |
|---|---:|---:|---|
| Do nothing / manual editing | High | Low | Slow, subjective, and not reproducible |
| Prompt or style-guide instruction | Medium | Low | Model-dependent compliance; limited release evidence |
| Regex phrase linter | Low | High | Cannot reliably distinguish useful contrast from empty rhetorical framing |
| General AI-writing detector/editor | Medium | Medium | Broad quality target; unclear traceability to this specific behavior |
| Proposed harness | High target | High target | Targets contextual evaluation, paired rewrites, and replayable release gates |

**2x2 map - winnable axes: contextual judgment x auditability**

|  | Low auditability | High auditability |
|---|---|---|
| **High contextual judgment** | Manual editing; prompt instruction | **Proposed harness** |
| **Low contextual judgment** | Do nothing | Regex linter |

**UVP:** Turn negative-parallelism complaints into a reproducible corpus test with sentence-level evidence, meaning-preserving rewrite candidates, and a human-reviewable release decision.

**Unevidenced claims:** Customer priority, willingness to pay, superiority over general editing tools, reliable context classification, and semantic-fidelity performance all require validation.
<!-- fs:differentiation:end -->

<!-- fs:approach:start -->
## Approach

Scores use 1 = weak/expensive/slow and 5 = strong/cheap/fast. For build cost, 5 means lowest cost.

| Candidate | Persona fit | Differentiation support | Build cost | Time to first test | Total |
|---|---:|---:|---:|---:|---:|
| A. Corpus evaluator + assisted rewrite + human gate | 5 | 5 | 4 | 5 | **19** |
| B. Runtime interception and resampling proxy | 3 | 4 | 2 | 2 | 11 |
| C. FTPO/LoRA weight optimization research stack | 2 | 4 | 1 | 1 | 8 |

**Selected:** A local-first corpus evaluator. It uses deterministic pattern candidates, a contextual classifier, counterfactual rewrite generation, semantic/style checks, and explicit reviewer decisions. This tests demand and measurement validity without privileged inference access.

**Fallback:** A deterministic linter plus reviewer workflow, omitting model-generated rewrites if contextual classification or rewrite fidelity fails initial tests.

Runtime sampling and weight optimization remain research extensions behind separate evidence, access, safety, and approval gates.
<!-- fs:approach:end -->

<!-- fs:hypothesis:start -->
## Founding Hypothesis

If we solve the inability to reproducibly detect and reduce harmful negative parallelism without changing meaning for AI quality leads at content-heavy organizations with a local-first corpus evaluator, assisted rewrite workflow, and human release gate, they will choose it over manual editing and prompt-only style constraints because it combines contextual judgment with sentence-level, replayable audit evidence.
<!-- fs:hypothesis:end -->

<!-- fs:validation:start -->
## Validation Plan

1. **Documentary problem-evidence gate:** Assemble an evidence register containing at least 8 independent, attributable sources. At least 4 sources must directly represent the defined buyer/customer population: people or organizations responsible for AI-output quality in content-heavy operational settings. At least 3 sources must document measurable organizational effort or spending, such as staff hours, review volume, budget, tool development, throughput cost, or purchased services. Every record must include publication date, author or accountable organization, direct source link, source type, relevant customer segment, the supported claim, and the measured effort where applicable. Simulated interviews, invented personas, inferred rankings, fabricated quotations, and inferred product-choice or adoption claims are prohibited. Pass only when every minimum and provenance field is satisfied; otherwise remain blocked.
2. **Documentary-gate limitation:** A pass establishes problem salience and evidence of existing effort only. It does not establish product demand, willingness to pay, workflow preference, or intent to adopt this harness. Those claims remain unevidenced until real users perform an observed prototype task and make a recorded choice.
3. **Limited concierge corpus audit:** After the documentary gate passes, run a manually supervised prototype on at least 300 outputs from 3 content domains. Pass if two independent reviewers reach Cohen's kappa >= 0.70 on `harmful / legitimate / uncertain` labels, candidate detection recall is >= 0.85, and precision is >= 0.75 on the adjudicated set. Fail if kappa < 0.55, recall < 0.70, or a critical privacy/provenance failure occurs; revise and retest in the intermediate zone.
4. **Blinded rewrite test:** Compare original, prompt-only, and harness-assisted versions across at least 100 flagged passages. Pass if assisted versions are preferred for naturalness in >= 60% of pairwise judgments, preserve intended meaning in >= 95%, reduce harmful incidence by >= 70%, and do not increase repeated substitute phrasing by more than 5 percentage points. Any silent change to a number, named entity, citation, modality, or negation scope is a critical failure.
5. **Observed product-demand test:** At least 5 real members of the defined customer population must complete the same realistic corpus-review task using the prototype and a baseline workflow. Record task completion, active review time, critical errors, workflow choice for their next comparable release, and rationale. Pass only if at least 3 of 5 choose the harness for the next comparable release, median reviewer time falls by >= 30%, all aggregate results remain traceable, and no critical safety or evidence-integrity failure occurs. This gate, not documentary research, supplies the first evidence of product demand.
<!-- fs:validation:end -->

<!-- fs:requirements:start -->
## Functional Requirements

1. **FR1 - Corpus ingestion:** Import UTF-8 JSONL or CSV containing stable item IDs, prompts or context when available, generated text, model identifier, and run metadata. *Trace: reproducibility and auditability.*
2. **FR2 - Immutable run manifest:** Hash input bytes, configuration, detector version, rewrite model/version, and rubric; detect identical successful runs and return the prior receipt. *Trace: reproducibility and safe reruns.*
3. **FR3 - Candidate detection:** Identify sentence spans matching versioned negative-parallelism patterns and record the matched span and rule. *Trace: measurable detection.*
4. **FR4 - Context classification:** Label each candidate `harmful`, `legitimate`, or `uncertain`, with confidence and a short rationale grounded in surrounding text. *Trace: prevent blanket-ban overcorrection; contextual differentiation.*
5. **FR5 - Counterfactual rewrites:** For harmful or reviewer-selected spans, generate at least two direct alternatives that preserve factual content, modality, entities, numbers, and citations. *Trace: reduce the pattern without meaning loss.*
6. **FR6 - Verification:** Check exact protected facts, semantic similarity, residual target patterns, length shift, and corpus-level substitute repetition; block auto-acceptance when a threshold fails. *Trace: semantic fidelity and variety preservation.*
7. **FR7 - Human review queue:** Show original context, flagged span, classification, rewrite candidates, metric deltas, and accept/edit/reject controls. *Trace: trusted release gate.*
8. **FR8 - Evaluation report:** Emit machine-readable item results plus a Markdown summary containing incidence, harmful/legitimate/uncertain rates, reviewer agreement, rewrite acceptance, meaning failures, repetition shift, and unresolved items. *Trace: replayable audit evidence.*
9. **FR9 - Baseline comparison:** Compare two or more model/prompt/pipeline runs on the same stratified item set without overwriting prior results. *Trace: release decision support.*
10. **FR10 - Replay suite:** Save adjudicated examples, including false positives, legitimate contrast, subtle cases, and rewrite failures, as versioned regression cases. *Trace: stable quality across updates.*
11. **FR11 - Operator controls:** Support pause, resume, cancel, dry-run, export, and rerun-from-failed-stage without losing accepted reviewer decisions. *Trace: observable, recoverable operation.*
12. **FR12 - Data handling:** Default to local storage, redact configured sensitive fields from model-bound requests, and require explicit configuration for external inference. *Trace: enterprise usability and trust.*
<!-- fs:requirements:end -->

<!-- fs:non-goals:start -->
## Non-goals

- Proving that all negative parallelism is undesirable.
- Detecting whether text was written by AI.
- General grammar, plagiarism, factuality, or brand-voice correction.
- Streaming token interception, logit manipulation, model-weight training, or claims of permanent "unlearning" in V1.
- Supporting an asserted "Codex 5.6 Sol Ultra" runtime without verified interfaces and access.
- Fully autonomous publication or irreversible modification of source corpora.
- A universal scalar "naturalness" score presented as objective truth.
<!-- fs:non-goals:end -->

### FTPO research-extension status (2026-07-13)

The V1 product-demand gates above remain unchanged. Separately, the FTPO engineering extension is now build-complete: generated tokenizer-bound data, leakage-safe splits, B0-B3 execution, adapter checkpoints, SLURM template, and acceptance tests exist under a typed `MODEL_CORROBORATED_BUILD_VERIFICATION` receipt. The attached Codex 5.6 Sol Ultra report supplies design/target provenance; a separate hashed `gpt-5.6-sol` evaluation corroborates Codex runtime and receipt mechanics. Neither source establishes that GPT-5.6 Sol Ultra weights were fine-tuned or that this generated-data result predicts empirical adoption or pretrained-model efficacy.

<!-- fs:metrics:start -->
## Success Metrics

- Documentary evidence register: >= 8 independent attributable sources, including >= 4 buyer/customer sources and >= 3 measured-effort or spending examples; 100% include publication date and direct source link.
- Primary: percentage of evaluated releases for which the harness produces a reviewer-approved pass/fail decision within one business day.
- Detection recall >= 0.85 and precision >= 0.75 on the adjudicated domain-specific test set.
- Reviewer agreement: Cohen's kappa >= 0.70 on harmful vs legitimate/uncertain classifications.
- Meaning preservation >= 95% on accepted rewrites; zero tolerance for silently changed numbers, named entities, citations, or negation scope.
- Harmful negative-parallelism incidence reduced >= 70% relative to the same-corpus baseline.
- No more than 5 percentage-point increase in the most common replacement construction.
- Median reviewer time reduced >= 30% versus unaided review.
- Observed workflow choice: >= 3 of 5 real target users choose the harness for their next comparable release.
- 100% of reported aggregate results trace to immutable item-level records and a versioned run manifest.
<!-- fs:metrics:end -->

<!-- fs:questions:start -->
## Open Questions

1. Which content domain provides the first corpus: marketing, executive communications, documentation, education, or another?
2. Is the initial buyer an AI quality lead, editorial operations leader, model vendor, or consultancy?
3. What unit should define incidence: sentence, response, 1,000 words, or opportunity-normalized occurrence?
4. Which contrasts are legitimate by policy, and who adjudicates ambiguous cases?
5. Can customer text leave the local environment for rewrite generation?
6. Which model and prompt metadata can be stored under customer retention rules?
7. Should the "Verbal Tic Index" be retained after its formula and human correlation are independently validated, or should V1 expose a transparent metric vector instead?
8. What verified runtime would support any later inference-time or training-time intervention?
9. Which 8 documentary sources satisfy independence and attribution without double-counting multiple pages derived from the same underlying study or organization?
10. Which 5 real target users and baseline workflow will be used for the observed product-demand test?
<!-- fs:questions:end -->

<!-- fs:next:start -->
## Next steps

After the documentary problem-evidence gate, concierge audit, blinded rewrite test, and observed product-demand test all pass, the optional new-product chain is: `design-sprint-orchestrator` -> `recursive-mega-prompt-builder` -> `scheduled-agent-pipeline`. Documentary evidence alone may authorize the limited concierge experiment; it may not authorize the build-planning chain or be represented as product-demand validation.
<!-- fs:next:end -->
