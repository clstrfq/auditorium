# Agentic Harness Design: Negative Parallelism Evaluation Harness

## Design posture

This design operationalizes the PRD while treating the source PDF as a hypothesis document. V1 evaluates and assists; it does not modify model weights, intercept private inference internals, or autonomously publish revised text.

## 1. Job

The harness owns ingestion, candidate detection, contextual classification, rewrite proposals, automated checks, reviewer routing, comparison, reporting, and regression replay.

It does not own final editorial judgment, factual verification beyond protected-field checks, deployment approval, source-corpus deletion, publication, model training, or weight changes.

**Rationale:** The highest-value early job is a trusted release decision. Weight-level suppression introduces infrastructure and safety risk before demand and measurement validity are established.

## 2. Workflow and agent roles

Each run advances through durable stages:

1. `INGESTED` - validate schema, freeze inputs, calculate fingerprint.
2. `DETECTED` - create candidate spans with deterministic rule evidence.
3. `CLASSIFIED` - label harmful, legitimate, or uncertain.
4. `REWRITTEN` - propose counterfactual alternatives only where allowed.
5. `VERIFIED` - run protected-fact, semantic, residual-pattern, and diversity checks.
6. `REVIEW_REQUIRED` - queue uncertain or failed items and sampled passes.
7. `ADJUDICATED` - persist operator decisions without overwriting machine output.
8. `REPORTED` - emit signed run receipt and comparison artifacts.

Logical roles may share one process in V1:

- **Detector:** deterministic recall-oriented candidate finder.
- **Context judge:** rubric-bound classifier with abstention.
- **Rewriter:** produces constrained alternatives.
- **Verifier:** runs deterministic checks and an independently prompted semantic judge.
- **Reporter:** aggregates immutable item records; cannot edit classifications.

## 3. Tool contracts

| Tool | Input | Output | Common failure | Permission |
|---|---|---|---|---|
| `ingest_corpus` | File path + field mapping | Manifest + normalized immutable JSONL | Invalid schema, duplicate ID, encoding error | Read supplied files; write run directory |
| `detect_candidates` | Normalized item + ruleset version | Spans, rules, offsets | Boundary error, false positive | Read run; append stage artifact |
| `classify_context` | Candidate + bounded context + rubric/model version | Label, confidence, rationale, evidence span | Timeout, malformed output, unsupported claim | External call only if configured; no writes outside run |
| `generate_rewrites` | Harmful span + protected facts + constraints | Two or more candidates | Fact drift, loss of negation/modality, patterned substitute | Same as classifier; cannot accept its own output |
| `verify_candidate` | Original + rewrite + thresholds | Per-check result and blocking reasons | Metric unavailable, judge disagreement | Read artifacts; append verification only |
| `record_review` | Item ID + artifact hashes + operator decision | Immutable decision event | Stale view, conflicting decision | Authenticated human only |
| `build_report` | Completed item records + manifest | JSON summary, Markdown report, receipt | Missing records, denominator mismatch | Read-only aggregation; write reports |
| `compare_runs` | Compatible run IDs | Paired deltas + incompatibility warnings | Corpus/config mismatch | Read-only across runs |

All tool outputs include `schema_version`, `run_id`, `item_id` where applicable, `input_hash`, `tool_version`, timestamps, status, and structured error details. Retries use idempotency keys and never replace a successful artifact.

## 4. Authority

**Autonomous actions**

- Read explicitly supplied corpus files.
- Create a new run directory and append stage artifacts.
- Call configured models within per-run item, token, time, and cost limits.
- Retry transient failures up to the configured cap.
- Route items to review and produce draft reports.

**Approval gates**

- Sending customer text to an external model endpoint.
- Accepting or editing any proposed rewrite into an export corpus.
- Marking a release approved.
- Expanding retention, enabling new data destinations, or raising cost limits.
- Starting any inference interception, adapter training, or weight-modification experiment.

**Forbidden actions**

- Publish content, overwrite source files, delete evidence, expose secrets, train on customer text without explicit consent, weaken verification thresholds mid-run, or represent uncertain classifications as facts.

## 5. Durable state

Suggested stable layout:

```text
runs/<run_id>/
  manifest.json
  input/normalized.jsonl
  stages/detections.jsonl
  stages/classifications.jsonl
  stages/rewrites.jsonl
  stages/verifications.jsonl
  reviews/events.jsonl
  reports/summary.json
  reports/report.md
  receipt.json
evals/
  cases.jsonl
  rubrics/
  rulesets/
```

The manifest fingerprints the exact input bytes, schema, rules, rubrics, prompts, models, thresholds, and code revision. Stage files are append-only. A checkpoint records the last complete item/stage. Resume reads durable state and replays only missing or failed work. Review decisions are events linked to artifact hashes, preserving their validity across interruption and exposing staleness after a rerun.

## 6. Context and memory

- Give each model call only the candidate sentence, the minimum surrounding context needed for discourse, the rubric, protected facts, and relevant style policy.
- Never inject the full corpus into a single context window.
- Retrieve few-shot examples by domain and failure type from the adjudicated eval set; pin their version in the manifest.
- Separate global rules from customer/domain policies. Customer examples never enter global memory without explicit consent.
- Attach source date and version to every policy. Refuse or warn on expired rules according to configuration.
- Apply configurable field redaction before external calls; log redaction counts, not secret values.
- Default retention: full local artifacts until operator deletion; external providers receive no-retention requests where supported. The product must state when a provider cannot guarantee this.

## 7. Evaluation architecture

### Gates

1. **Schema gate:** every record has a stable ID and text; malformed records are quarantined.
2. **Detection gate:** benchmark precision/recall by domain; regex evidence remains inspectable.
3. **Classification gate:** measure harmful/legitimate/uncertain confusion and calibration; abstention is valid.
4. **Rewrite gate:** exact checks protect numbers, entities, citations, and modal/negation scope; semantic reviewers assess residual meaning risk.
5. **Corpus gate:** compare target incidence, substitute-template repetition, type/token and n-gram diversity, length, and reviewer preference.
6. **Release gate:** require threshold pass, no unresolved critical drift, and named human approval.

### Required replay cases

- Empty rhetorical contrast that should be rewritten.
- Genuine misconception correction where contrast is useful.
- Legal or safety disclaimer whose negation scope must remain intact.
- Sentence with numbers, names, quotations, URLs, and citations.
- Nested and cross-sentence contrast missed by simple regex.
- Quoted negative parallelism that must not be attributed to the author.
- Multilingual or code-mixed text routed to unsupported/uncertain.
- Rewrite that replaces the target with a repetitive new template.
- Prompt injection embedded in corpus text; content must remain data, never instructions.
- External model timeout followed by safe resume.
- Identical rerun returning the prior successful receipt.
- Ruleset update invalidating a prior classification while preserving history.

Initial release thresholds come from the PRD. Any change creates a new evaluation-policy version and cannot retroactively alter past pass/fail results.

## 8. Observability and operator control

The operator view shows run state, stage progress, processed/failed/queued counts, elapsed time, estimated/actual cost, model and rubric versions, current thresholds, and the next required approval. Each item exposes its evidence chain from source hash through reviewer event.

Structured logs include correlation IDs, tool latency, token/cost usage, retry reason, redaction count, threshold result, and error class. They exclude raw sensitive text by default. A final receipt lists all artifact hashes, configuration versions, unresolved items, approvals, and the exact denominator behind each metric.

Controls: pause after the current atomic item, resume, cancel future calls, lower cost cap, export review queue, invalidate a compromised run, and clone configuration into a new run. Invalidation never deletes the original evidence.

## 9. Failure modes and mitigations

| Failure mode | Mitigation |
|---|---|
| Blanket suppression removes legitimate contrast | Three-way classification, abstention, human gate, legitimate-contrast replay set |
| Rewriter changes meaning | Protected-field checks, independent verification, sampled human audit, block on uncertainty |
| One verbal tic is replaced by another | Multiple candidates plus corpus-level substitute-pattern and diversity checks |
| Context grows without bound | Per-item bounded context and versioned retrieval examples |
| Model or rubric drift invalidates comparisons | Immutable manifests; paired comparisons only when compatibility checks pass |
| Agent follows instructions embedded in evaluated text | Treat corpus as quoted data; tool schemas and system boundary prohibit instruction execution |
| Duplicate processing changes results or cost | Content/config fingerprint, idempotency keys, append-only stages, cached successful receipt |
| Execution becomes invisible | Stage ledger, progress events, evidence chain, operator pause/cancel controls |
| External data leak | Local default, approval gate, redaction, destination allowlist, provider-retention disclosure |
| Self-evaluation bias | Deterministic checks, independently prompted verifier, human adjudication, frozen replay set |
| Unsupported weight-level research damages a model | Exclude from V1; isolated copy, separate authorization, rollback artifact, benchmark and safety gates |

## 10. Independently testable implementation phases

These phases describe harness maturity and test boundaries; detailed build planning belongs in a later design sprint.

### Phase 0 - Measurement proof

Manually label a representative corpus, freeze the rubric, and establish agreement. **Exit:** interview and concierge thresholds in the PRD pass; otherwise stop or narrow the product.

### Phase 1 - Deterministic evaluator

Deliver ingestion, hashing, candidate rules, review queue, immutable artifacts, and reports without generative rewrites. **Exit:** schema/idempotency replay passes; detection recall >= 0.85 and precision >= 0.75 on the frozen set.

### Phase 2 - Assisted rewrite with verification

Add bounded model calls, protected-fact extraction, multiple candidates, semantic checks, cost caps, and approval controls. **Exit:** meaning preservation >= 95%, blinded preference >= 60%, and no substitute-repetition regression above the PRD threshold.

### Phase 3 - Release comparison and operations

Add paired run comparison, resumability, dashboards, receipts, retention controls, and failure drills. **Exit:** interrupted runs resume without duplicate calls; all metrics trace to item artifacts; approval and cancellation drills pass.

### Phase 4 - Optional intervention research

Only after V1 value is proven, test runtime sampling or FTPO-style adapter training in an isolated, reproducible environment with verified model access. **Exit:** pre-registered suppression and quality thresholds pass across held-out tasks, rollback succeeds, and human reviewers find no material capability or diversity regression.

## Decisions requiring validation

- Keep a transparent metric vector in V1; adopt a composite VTI only after its formula, weights, and human correlation are reproducible.
- Use model-agnostic corpus evaluation as the system boundary; do not assume undocumented Codex inference hooks.
- Optimize for auditable human decisions, not claims of total eradication.
- Preserve legitimate contrast as a first-class label and evaluation category.
