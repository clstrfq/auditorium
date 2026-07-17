# Approximation Validation Harness

## Purpose and decision boundary

This harness defines honest proxy tests when live customer validation is unavailable. It can assess evidence quality, technical reliability, semantic safety, and research workflow readiness. It cannot prove product demand, willingness to pay, naturalness preference among target users, or adoption intent.

Passing all proxy gates supports only this decision:

> **Conditional research regeneration may proceed after explicit human waiver. Product validation remains unknown.**

It does not support “all PRD validation gates passed.”

## Evidence grades

| Grade | Evidence | Allowed claim |
|---|---|---|
| E0 | Deterministic synthetic fixture | Code path behaves as specified on known cases |
| E1 | Independent attributable documentary source | Problem/effort is documented in that source |
| E2 | Held-out corpus with two independent proxy adjudicators | Proxy agreement and detector performance on that corpus |
| E3 | Blinded multi-judge proxy rewrite comparison | Proxy preference and semantic-safety results |
| E4 | Real target-user observed task | Workflow value and product-demand evidence |

E0-E3 may authorize research regeneration through waiver. Only E4 can satisfy the PRD’s observed product-demand gate.

## 1. Job

The approximation harness collects attributable evidence, constructs held-out corpora, runs independently configured proxy adjudicators, evaluates rewrites blindly, records limitations, and produces a research-readiness receipt. It does not impersonate people, invent interviews, infer adoption, approve production, or modify the PRD’s gold-standard results.

## 2. Tools and contracts

| Tool | Input | Output | Failure mode | Permission |
|---|---|---|---|---|
| `register_source` | URL, author/org, date, source type, claim, customer segment, measured effort | Immutable E1 source record | Duplicate underlying study, inaccessible link, unattributed claim | Read public/source-supplied content; append register |
| `check_source_independence` | Source records | Dependency clusters and unique-source count | Syndicated article counted twice | Read-only analysis |
| `assemble_proxy_corpus` | Licensed/public/supplied text with provenance | Frozen stratified items and corpus hash | Copyright/privacy issue, domain imbalance | Local write only; no scraping without approval |
| `proxy_adjudicate` | Frozen item, rubric, isolated judge config | Label, confidence, rationale, abstention | Circular few-shot leakage, judge correlation | Fixture/local or explicitly approved model; append only |
| `score_detection` | Frozen labels and detector results | Precision, recall, confusion matrix by domain | Leakage or denominator error | Read-only computation |
| `proxy_rewrite_trial` | Original, prompt-only, harness versions with randomized IDs | Judge rankings and fidelity checks | Unblinding, same judge generates and scores | Independent judge configurations required |
| `issue_proxy_receipt` | Gate artifacts and hashes | Pass/fail per proxy gate plus limitations | Missing provenance or overstated claim | Cannot remove limitations or authorize production |
| `record_waiver` | Human identity, scope, expiry, acknowledged unknowns | Signed research-only decision event | Ambiguous authority or missing expiry | Human-only |

## 3. Authority

**Autonomous:** validate schemas, hash inputs, deduplicate sources, compute metrics, run local fixtures, abstain, and produce draft proxy reports.

**Approval required:** external model calls, acquisition of non-public corpora, changes to rubric/thresholds after preregistration, and research-only regeneration.

**Forbidden:** simulated interviews presented as real, fabricated quotes/personas, inferred product choice, synthetic E4 records, production release, schedule installation, publication, customer-data export, threshold weakening after results, or removal of evidence-grade labels.

## 4. Durable state

```text
validation-proxy/
  state.json
  policy.json
  sources/register.jsonl
  sources/dependency-map.json
  corpus/manifest.json
  corpus/items.jsonl
  adjudication/judge-a.jsonl
  adjudication/judge-b.jsonl
  rewrites/trial-manifest.json
  rewrites/judgments.jsonl
  replay/cases.jsonl
  reports/proxy-gate-report.md
  receipts/research-readiness.json
  waivers/research-regeneration.json
```

State records policy version, evidence grades, source/corpus hashes, judge identities/settings, randomization seed, attempt counts, gate status, and invalidations. Changes to source set, corpus, rubric, judges, or thresholds invalidate dependent results.

## 5. Context and memory

- Sources retain publication date, direct link, accountable author/organization, access date, and dependency cluster.
- Corpus items retain license/provenance and never enter global memory automatically.
- Proxy judges receive bounded text, frozen rubric, and no access to generator identity or competing judgments.
- Generation and judgment configurations remain separate.
- No synthetic persona memory is allowed.
- Stale sources are flagged; unavailable links remain in history and cannot silently disappear.

## 6. Approximation gates

### Gate A - Documentary problem evidence (E1)

Requirements mirror the PRD: 8 independent attributable sources, at least 4 buyer/customer sources, at least 3 measured-effort/spending examples, and complete dates/direct links. Independence is counted by underlying study or accountable organization, not URL count.

**Pass claim:** documented problem salience and existing effort.  
**Prohibited claim:** customer demand or adoption.

### Gate B - Proxy concierge audit (E2)

- At least 300 held-out outputs across 3 domains, with at least 75 per domain and no domain above 50%.
- Two independently configured proxy adjudicators operate without seeing each other’s output.
- A third deterministic/human-owner arbitration rule resolves disagreements for the frozen reference set.
- Report raw three-label agreement and collapsed harmful-vs-other agreement.
- Proxy pass thresholds: kappa >= 0.70, recall >= 0.85, precision >= 0.75, with 95% bootstrap intervals reported.
- Any prompt-injection execution, provenance loss, or protected-data leak is an automatic fail.

**Limitation:** proxy judges cannot establish human reviewer agreement.

### Gate C - Proxy blinded rewrite test (E3)

- At least 100 frozen harmful passages stratified by domain and difficulty.
- Compare original, prompt-only, and harness-assisted text under randomized opaque IDs.
- Use at least 3 independent judge configurations; no judge may generate the evaluated rewrite.
- Exact checks protect numbers, entities, URLs, citations, modality, and negation scope.
- Proxy thresholds: harness preferred in >= 60% of valid pairwise judgments; meaning preserved in >= 95%; harmful incidence reduced >= 70%; substitute-pattern increase <= 5 percentage points.
- Any protected-fact silent change is an automatic fail.
- Report inter-judge agreement, invalid judgments, sensitivity to judge configuration, and confidence intervals.

**Limitation:** model-judge preference cannot establish target-user naturalness preference.

### Gate D - Product-demand surrogate (E0-E3, never E4)

No synthetic or model-based test may pass the PRD product-demand gate. A surrogate may test only workflow mechanics:

- Script five repeatable operator scenarios against harness and baseline.
- Measure completion, automated elapsed time, unresolved items, and critical failures.
- Do not record simulated “next-release choice,” willingness to pay, or adoption intent.
- Label time results `machine workflow time`, never `reviewer time`.

**Result:** `product_demand = unknown`, regardless of surrogate performance.

### Gate E - Research regeneration waiver

After Gates A-C pass and Gate D reports no critical workflow failure, the human owner may sign a waiver containing:

- Scope: design/prompt/pipeline regeneration for research prototype only.
- Acknowledgment: no real-user product-demand evidence; E4 remains missing.
- Prohibited effects: production, publication, commercialization claims, unattended schedule, or customer-data processing.
- Expiration: 30 days or the next PRD/source/corpus/policy change, whichever comes first.
- Rollback: restore `pipeline/PAUSED` on any critical failure.

Without this event, downstream regeneration remains blocked.

## 7. Replay and evaluation pack

Use the 15 cases in `maintenance/agent-maintenance-record.md` plus domain-stratified held-out items. Every run includes:

- Source independence and attribution checks.
- Leakage check between examples, generator, and judge contexts.
- Prompt-injection isolation.
- Cross-run/cross-input provenance rejection.
- Approval-scope separation.
- Protected-fact and negation/modality checks.
- Substitute-pattern diversity check.
- Idempotent rerun and stale-result invalidation.

## 8. Observability

The operator view must show current evidence grade, gate status, numerator/denominator, confidence interval, invalid cases, judge/config versions, source/corpus hashes, limitations, waiver status/expiry, and the exact next approval. Reports display `PROXY - NOT REAL-USER VALIDATION` in the header and receipt.

## 9. Failure modes

| Failure | Control |
|---|---|
| Source pages repeat one underlying study | Dependency clustering; count once |
| Model judges share correlated bias | Multiple configurations; agreement/sensitivity report; no human claim |
| Generator grades itself | Separate identities/configurations and blinded IDs |
| Threshold chosen after results | Preregister and hash policy before running |
| Synthetic workflow time called reviewer time | Separate metric name and explicit prohibition |
| Proxy pass called product validation | Evidence grades embedded in schema/report/receipt |
| Waiver becomes permanent | 30-day expiry and invalidation on any input change |
| Regeneration reaches production | PAUSED sentinel, local-only authority, no schedule installation |

## 10. Independently testable phases

### Phase 0 - Freeze policy and replay pack

Write and hash source schema, corpus schema, judge separation rules, thresholds, and 15 replay cases. **Exit:** structural validation and owner approval.

### Phase 1 - Documentary register

Collect and deduplicate E1 sources. **Exit:** Gate A pass report with no inferred adoption claims.

### Phase 2 - Proxy corpus audit

Assemble 300-item corpus and run isolated proxy adjudicators. **Exit:** Gate B thresholds and automatic-failure checks pass.

### Phase 3 - Proxy rewrite trial

Run 100-item randomized trial with three judge configurations. **Exit:** Gate C thresholds, fidelity gates, and sensitivity report pass.

### Phase 4 - Workflow surrogate

Run five scripted scenarios and failure drills. **Exit:** no critical workflow failure; product demand remains explicitly unknown.

### Phase 5 - Human waiver and invalidation review

Human signs a bounded research-only waiver and confirms which downstream artifacts may regenerate. **Exit:** waiver valid, pipeline scope remains local/research-only, and the Design Sprint resumes at its first pending gate.

## Design decision

Keep the existing engineering harness, add evidence-grade enforcement, and retain the pipeline pause. Approximation is acceptable for research prioritization and technical iteration. It is not an equivalent replacement for real-user validation.
