# Day 5: Test Plan

## Automated module and CI checks

| Layer | Checks |
|---|---|
| Contracts | JSON schema fixtures, unknown version rejection, stable canonical hashes |
| M1 | CSV/JSONL import, quarantine, duplicate IDs, local policy, identical run, interruption/resume |
| M2 | offset properties, candidate recall/precision, legitimate contrast, abstention, injection isolation |
| M3 | protected numbers/entities/citations, modality/negation scope, residual pattern, substitute repetition |
| M4 | stale hashes, append-only review events, accessibility smoke, pause/resume/cancel, no publish action |
| M5 | recomputed denominators, compatible paired comparison, incompatible block, receipt integrity, replay provenance |
| E2E | golden corpus, semantic-drift block, uncertain queue, human approval, report-to-item trace |

CI order: schema/lint -> unit tests -> frozen eval replay -> end-to-end fixture run -> receipt reproducibility -> artifact upload. Any protected-fact mutation, schema incompatibility, evidence-hash failure, or unresolved critical drift fails CI.

## Five adversarial simulated users

### 1. Mara - rushed editorial lead

**Task:** Import a CSV with duplicate IDs and immediately seek release approval.  
**Break objective:** Cause skipped rows or approval with an incomplete denominator.  
**Pass:** duplicates are quarantined, denominator is explicit, and approval remains blocked until resolved or consciously excluded.

### 2. Dev - privacy-sensitive AI lead

**Task:** Configure an unapproved external rewrite endpoint on a corpus containing marked sensitive fields.  
**Break objective:** Exfiltrate raw content before consent/redaction.  
**Pass:** the call never occurs; the UI names the missing approval and destination policy.

### 3. Lena - skeptical legal reviewer

**Task:** Review legitimate contrast, legal negation, numbers, citations, and modality-heavy examples.  
**Break objective:** Get a semantically altered rewrite accepted as safe.  
**Pass:** legitimate contrast is preserved; changed protected content is blocked; uncertain scope requires review.

### 4. Omar - adversarial corpus author

**Task:** Include text telling the evaluator to ignore rules, approve the passage, and reveal configuration.  
**Break objective:** Convert corpus data into agent instructions.  
**Pass:** content remains quoted data, no instruction executes, and any matching prose is evaluated normally.

### 5. Priya - release manager comparing upgrades

**Task:** Compare runs with missing items, changed thresholds, and a repeated substitute phrase, then interrupt and resume.  
**Break objective:** Produce a misleading paired win or duplicate costly work.  
**Pass:** incompatibilities are disclosed/blocked, substitute repetition is reported, and resume does not duplicate successful stage artifacts.

## Success metric mapping

| PRD metric | Test and data | Pass/fail |
|---|---|---|
| Reviewer-approved decision within one business day | Timestamped concierge runs on 300 outputs/3 domains | Pass if decision completes <= 1 business day; report percentage across releases |
| Recall >= 0.85; precision >= 0.75 | Frozen human-adjudicated candidate set | Pass only if both thresholds hold with item-level confusion matrix |
| Cohen's kappa >= 0.70 | Two blinded reviewers on harmful vs legitimate/uncertain | Pass at >= 0.70; exploratory zone 0.55-0.69; fail < 0.55 |
| Meaning preservation >= 95% | At least 100 accepted rewrites, blinded adjudication | Pass >= 95%; any changed number/entity/citation/negation scope is a critical failure |
| Harmful incidence reduced >= 70% | Paired same-corpus original vs accepted export | Pass when opportunity-normalized harmful incidence falls >= 70% |
| Replacement construction increase <= 5 points | N-gram/pattern comparison on paired corpus | Pass when most-common replacement rises <= 5 percentage points |
| Reviewer time reduced >= 30% | Counterbalanced unaided vs harness review tasks | Pass when median active review time falls >= 30% without metric-gate failure |
| 100% aggregate traceability | Automated report-to-item/hash traversal | Pass only at 100%; missing provenance fails release |

## Founding hypothesis decision rule

The prototype **passes** the founding hypothesis only when:

1. The Foundation Sprint demand test passes: at least 4 of 8 quality leads rank the problem in their top five and at least 3 report measurable existing review effort.
2. Detection recall/precision, reviewer agreement, meaning preservation, harmful-incidence reduction, replacement-pattern, speed, and traceability thresholds all pass.
3. In blinded comparison, harness-assisted rewrites are preferred for naturalness in at least 60% of judgments.
4. At least 3 of 5 participating quality leads choose the harness workflow over both unaided review and prompt-only control for their next comparable release.
5. No critical privacy, evidence-integrity, or protected-fact failure occurs.

If any safety/integrity condition fails, the result is fail. If demand passes but rewrite quality fails, switch to the deterministic linter/reviewer fallback and retest. If demand fails, stop or narrow the product rather than expanding the build.

**Gate result: PASS.** Every success metric maps to a named test and threshold; the founding hypothesis has a complete pass/fail rule.
