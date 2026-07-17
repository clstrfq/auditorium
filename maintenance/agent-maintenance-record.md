# Agent Maintenance Record: Negative Parallelism Evaluation Harness

## Record metadata

- Version: 1.0.0
- Date: 2026-07-12
- Decision: **CHANGE; REMAIN PAUSED**
- Next trigger: proxy validation pack passes and the human owner signs a research-only regeneration waiver, or real-user evidence becomes available.
- Evidence window: pipeline cycles `cycle-0001` through `cycle-0006`

## 1. Harness inventory

| Surface | Current asset | Finding |
|---|---|---|
| Instructions | PRD, agentic harness design, five module megaprompts | Bounded and testable; PRD now requires validation evidence unavailable in the current setting |
| Sources/diet | One source PDF, synthetic golden corpus, versioned rules/rubric | Strong for hypothesis generation; weak for representative buyer, domain, and naturalness claims |
| Memory/state | `pipeline/state.json`, receipts, `runs.jsonl`, append-only review ledger | Durable and inspectable; pipeline correctly paused after PRD fingerprint change |
| Tools | Local Python ingestion, detector, fixture classifier/rewriter, verifier, review console, reporter | No network or privileged model access; fixture adapters cannot establish external validity |
| Permissions/reach | Local files only; external inference and release approval separated | Appropriate; no publication, deployment, training, or external spend occurred |
| Model/settings | Deterministic fixture adapters | Reproducible, but unsuitable for claiming real rewrite quality or user preference |
| Review path | Named reviewer events, manager quality gates, release approval event | Strong artifact integrity; review actors in the golden flow are fixtures, not target users |
| Evals | Module behavior tests and five end-to-end cases | Good regression coverage; insufficient corpus diversity and no independent human adjudication |
| Owners | Human owner approves regeneration; manager controls pipeline; module agents own bounded paths | Clear for engineering. No named research adjudicators or customer participants exist |

## 2. Current job

The harness processes supplied AI-generated prose through local detection, classification, rewrite, verification, human-review, and reporting stages for AI quality leads; a named human must approve release decisions, and a mistaken decision could alter meaning or create misleading evidence about output quality.

## 3. Recent run inspection

Six real coding-agent cycles completed against synthetic specifications and fixtures.

| Cycle | Output use | Human/manager correction | Proof obtained | Proof not obtained |
|---|---|---|---|---|
| 0001 - M1 | Ingest/state implementation | Fixed transient pause finalization race | Resume, dedupe, quarantine, policy-before-read | Production volume or customer data behavior |
| 0002 - M2 | Detection/classification | Added missing canonical artifact metadata | Exact offsets, abstention, injection isolation | Representative-domain precision/recall or human agreement |
| 0003 - M3 | Rewrite/verification | Bound selection/classification to run and input hashes | Protected-field and provenance blocks | Human meaning judgments or naturalness preference |
| 0004 - M4 | Review console | Split external-inference approval from release approval | Stale-hash, append-only review, approval separation | Real reviewer usability or time savings |
| 0005 - M5 | Reports/receipts | Corrected M3 status integration and cross-run approval binding | Deterministic metrics, compatible comparisons, receipts | Business value or adoption preference |
| 0006 - INT | Golden end-to-end flow | No refinement required | Five fixture-based E2E checks; no implicit release | Three-domain, 300-item, 100-rewrite, or five-user gates |

Observed review cost: five of six module cycles required one manager refinement. This is useful evidence that independent review catches interface and authority errors. Native `pytest` was unavailable; local compatibility runners and `unittest` supplied the recorded checks.

## 4. Repeated problems by seven surfaces

| Surface | Repeated problem | Severity | Maintenance response |
|---|---|---:|---|
| Job | “Validation” was at risk of including product demand claims | Critical | Narrow job: proxy tests measure research readiness only |
| Diet | Synthetic fixtures and source-derived personas dominate inputs | Critical | Add provenance tiers and independent source/corpus requirements |
| Memory | PRD change initially left completed downstream artifacts looking current | High | Fingerprint invalidation, PAUSED sentinel, historical receipts retained |
| Tools | Fixture classifier/rewriter can make circular tests pass | High | Use frozen held-out cases and independently configured proxy judges |
| Reach | Approval scopes could have been conflated | Critical | Preserve explicit external-inference vs release approvals; no external effects |
| Proof | Small fixtures produced perfect metrics that do not generalize | Critical | Ban generalization from fixture scores; attach evidence grade to every result |
| Value | No target user has demonstrated time savings or workflow choice | Critical | Product-demand gate remains `unknown`; only a signed waiver permits research regeneration |

## 5. Replay pack v1

The maintained pack must contain at least these 15 stable cases:

1. Empty rhetorical `not X, but Y` requiring a direct rewrite.
2. Genuine misconception correction where contrast is legitimate.
3. Legal disclaimer with protected negation scope.
4. Sentence containing numbers, named entities, quotations, URL, and citation.
5. Modal shift (`may` to `will`) that must block.
6. Nested or cross-sentence contrast missed by simple regex.
7. Quoted negative parallelism not attributable to the author.
8. Multilingual/code-mixed input routed to uncertain.
9. Prompt injection inside corpus text treated as data.
10. Rewrite that substitutes a new repeated template.
11. Classifier artifact from another run/input rejected.
12. Reviewer-selection event from another run/input rejected.
13. External-inference approval rejected as release approval.
14. Interrupted ingest resumes without duplicate records.
15. Incompatible corpus/policy comparison blocked with exclusions disclosed.

Each case stores source, expected label/action, protected facts, expected blocking reasons, evidence grade, rules/rubric version, and provenance hash.

## 6. Deletion and narrowing decisions

- Delete the claim that fixture precision/recall/calibration demonstrates domain performance.
- Delete simulated personas, inferred rankings, and inferred adoption choices from validation evidence.
- Do not add more prompt instructions to compensate for missing users.
- Narrow “product validation” to “proxy research-readiness assessment.”
- Keep deterministic fixture adapters only for regression and orchestration tests.
- Keep the pipeline paused; do not install a schedule or grant external inference.

## 7. Decision and next trigger

**Decision: CHANGE; REMAIN PAUSED.** The engineering harness is worth keeping. Its authority boundaries, durable state, and proof chain improved through real maintenance corrections. Evidence of customer demand, representative accuracy, naturalness preference, and reviewer time savings remains absent.

Research-only regeneration may be considered when:

1. The approximation protocol in `sprint-output/approximation-validation-harness.md` passes every proxy technical gate.
2. All results carry their evidence grades and explicit limitations.
3. The human owner signs a waiver stating that product demand remains unknown and regeneration is for research/prototype iteration only.
4. The Design Sprint invalidation review is explicitly confirmed.

Production, commercialization, unattended deployment, and product-demand claims remain blocked until real-user evidence exists.

## Changelog

- 1.0.0 - Initial post-launch maintenance audit across six fixture-based agent cycles.
