# Day 4: Prototype Plan

## Realistic facade rule

Build only the experience needed to test the founding hypothesis: import a fixed representative corpus, see contextual labels and evidence, review verified alternatives, compare baseline/candidate results, and issue a human-approved receipt. Use deterministic fixture adapters for classification and rewriting by default. Preserve real schemas, hashing, state, review events, metrics, and failure behavior.

Stub production authentication, billing, provider routing, scalable queues, deployment, and model training. Do not stub evidence provenance, protected-field failures, uncertainty, or approval gates.

## Ownership

| Module | Coding-agent assignment | Owned paths |
|---|---|---|
| M1 | Agent A - state and ingestion | `src/contracts/`, `src/ingest/`, `src/state/`, `tests/ingest/` |
| M2 | Agent B - evaluation | `src/detect/`, `src/classify/`, `evals/rulesets/`, `evals/rubrics/`, `tests/detect/` |
| M3 | Agent C - rewrite safety | `src/rewrite/`, `src/verify/`, `tests/rewrite/` |
| M4 | Agent D - review experience | `src/review_app/`, `tests/review_app/` |
| M5 | Agent E - evidence and comparison | `src/report/`, `src/compare/`, `src/replay/`, `tests/report/` |
| Integration | Sprint lead | `pyproject.toml`, `README.md`, `scripts/`, `tests/e2e/`, CI config |

Agents are assignments for later execution; this sprint does not launch coding work.

## Proposed file layout

```text
src/{contracts,ingest,state,detect,classify,rewrite,verify,review_app,report,compare,replay}/
evals/{cases.jsonl,rulesets/,rubrics/,thresholds/}
fixtures/{corpora,classifications,rewrites}/
tests/{ingest,detect,rewrite,review_app,report,e2e}/
scripts/run_prototype.py
runs/.gitkeep
pyproject.toml
README.md
```

## Dependency-ordered build sequence

1. **Contracts and fixtures (M1/lead):** canonical dataclasses/schemas, IDs, hashes, fixture corpus and expected artifacts.
2. **M1 ingestion/state:** produces manifest and normalized items; exercises identical-run and resume behavior.
3. **M2 detection/classification:** consumes only M1 schemas; fixture classifier first.
4. **M3 rewrite/verification:** consumes M1/M2 schemas; fixture rewriter first.
5. **M4 review console:** begins after schemas freeze; integrates M1-M3 evidence and emits events.
6. **M5 reporting/comparison/replay:** consumes immutable M1-M4 artifacts and emits summary/receipt.
7. **End-to-end integration:** one golden run, one interrupted run, one incompatible comparison, one external-inference-blocked run.

This is a valid topological sort for edges `contracts -> M1 -> M2 -> M3 -> M4 -> M5 -> E2E`, with M4 allowed to begin its shell after contracts while final integration waits for M3.

## Per-module verification commands

```bash
python -m pytest tests/ingest -q
python -m pytest tests/detect -q
python -m pytest tests/rewrite -q
python -m pytest tests/review_app -q
python -m pytest tests/report -q
python -m pytest tests/e2e -q
python scripts/run_prototype.py --fixture fixtures/corpora/golden.jsonl --dry-run
```

## Prototype exit evidence

- A fresh run and identical rerun produce the expected manifest/receipt behavior.
- Every displayed label, rewrite, metric, and decision links to its artifact hash.
- At least one legitimate, harmful, uncertain, semantic-drift, prompt-injection, and substitute-repetition case is visible.
- Operator pause/resume/cancel and external destination denial work in the facade.

**Gate result: PASS.** The build sequence is acyclic, dependency ordered, fully owned, and each module has an executable verification command.
