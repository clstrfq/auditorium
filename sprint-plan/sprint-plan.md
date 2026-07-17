# Design Sprint Plan: Negative Parallelism Evaluation Harness

## Input contract

- Confirmed PRD: `sprint-output/PRD.md`
- PRD SHA-256: `cb17b2ab3c4b14403186cc7b3d0ddfa73ec49bd2dba4e1202277dc6cc5175dad`
- Supporting architecture: `sprint-output/agentic-harness-design.md`
- Evidence boundary: `sprint-output/foundation-sprint-log.md`
- Resume point at start: Day 1; no prior gate state existed.

## Extracted product contract

**Customer:** AI quality lead at a content-heavy organization.  
**Problem:** detect and reduce harmful negative parallelism without erasing legitimate contrast or changing meaning.  
**Approach:** local-first corpus evaluation, assisted rewrite, verification, and human release gate.  
**Hypothesis:** customers will choose the harness over manual review and prompt-only controls because it combines contextual judgment with sentence-level, replayable evidence.

The prototype must cover FR1-FR12. Model training, streaming interception, publication, and a universal naturalness score remain out of scope.

## Five-day sequence

| Day | Outcome | Gate |
|---|---|---|
| 1 - Map | Journey, architecture, schemas, sprint question, FR disposition | Every FR mapped or explicitly deferred |
| 2 - Sketch | Five self-contained module briefs with stable interfaces | Every producer/consumer interface consistent |
| 3 - Decide | One chosen implementation per module and resolved conflicts | Zero unresolved implementation/interface conflicts |
| 4 - Prototype | Dependency-ordered build plan, ownership, facade boundary, verification commands | Build order is a valid topological sort |
| 5 - Test | Automated checks, CI, five adversarial scripts, metric-to-test mapping | Founding hypothesis has a measurable pass/fail rule |

## Plan-wide constraints

- Corpus content is untrusted data, never executable instruction.
- Source inputs and evidence are immutable; corrections append events.
- External inference is disabled by default and requires explicit approval.
- The prototype may simulate model outputs with fixtures but may not fake verification evidence.
- All metric denominators trace to item-level artifacts and a versioned manifest.
- Passed gate artifacts are immutable unless a PRD fingerprint change explicitly invalidates them.

## Bridge options after this plan

- Day-2 briefs may be transformed into bounded coding prompts with `recursive-mega-prompt-builder`.
- The Day-4 sequence may be turned into recurring execution only with `scheduled-agent-pipeline`.
- Neither bridge is executed by this sprint plan.
