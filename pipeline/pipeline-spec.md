# Coding Agent Pipeline Specification

## Version

- Version: 1.2.0
- Date: 2026-07-13
- Inputs: `sprint-plan/day-4-prototype.md`, `prompts/*.megaprompt.md`

## Cycle contract

One cycle selects every dependency-ready pending item, dispatches at most two coding agents, quality-gates their deterministic output paths, permits at most two refinement rounds, checkpoints state, and emits a cycle receipt.

Per-cycle done means every selected item is `done`, `failed`, or restored to `pending` with an explicit transient reason; state and the run log are atomically updated; the lock is released.

Overall finish line: M1-M5 and integration are `done`; all module commands and `python -m pytest tests/e2e -q` pass; the golden fixture run produces traceable artifacts; no critical privacy, provenance, or protected-fact failure remains.

## Build-completion contract

- The legacy `pipeline/PAUSED` and `pipeline/PREP_ONLY` sentinels are removed.
- `pipeline/BUILD_COMPLETE` records that schema validation, generated tokenizer-bound data, leakage-safe splitting, B0-B3 execution, checkpoint emission, and acceptance tests completed.
- Generated data is permitted whenever an input manifest identifies its origin and claim scope. It may drive engineering training and acceptance; it does not silently become human-corpus evidence.
- External API, secret, SSH, or SLURM execution is not part of build completion. The complete SLURM template accepts an explicit clearance receipt and runtime paths if an operator later invokes that separate workflow.
- `pipeline/RUNNING` is transient and absent after a successful build.

## Hard caps

- Concurrent sub-agents: 3
- Selected work items per cycle: 2
- Agent effort budget: 30 minutes and 40,000 model tokens per item
- Changed-file cap: 12 files per module item; integration may change 8
- Refinement rounds: 2 per item per cycle
- Attempts: 3 total; third unsuccessful attempt marks `failed`
- Cycle wall time: 60 minutes
- External model/API spend: USD 0; fixture adapters only
- External effects: none - no pushes, PRs, messages, publishing, deployments, or schedule installation

Crossing a cap fails the current run, records the reason in its receipt, and leaves the last verified artifacts intact.

## Work ledger and dependencies

| ID | Template | Depends on | Deterministic owned output |
|---|---|---|---|
| M1 | `prompts/m1-ingest-state.megaprompt.md` | none | `src/contracts/`, `src/ingest/`, `src/state/`, `tests/ingest/` |
| M2 | `prompts/m2-detect-classify.megaprompt.md` | M1 | `src/detect/`, `src/classify/`, `evals/rulesets/`, `evals/rubrics/`, `tests/detect/` |
| M3 | `prompts/m3-rewrite-verify.megaprompt.md` | M1, M2 | `src/rewrite/`, `src/verify/`, `tests/rewrite/` |
| M4 | `prompts/m4-review-console.megaprompt.md` | M1, M2, M3 | `src/review_app/`, `tests/review_app/` |
| M5 | `prompts/m5-report-compare-replay.megaprompt.md` | M1, M2, M3, M4 | `src/report/`, `src/compare/`, `src/replay/`, `tests/report/` |
| INT | Manager-authored bounded brief | M1-M5 | `pyproject.toml`, `README.md`, `scripts/`, `tests/e2e/` |

## Manager/sub-agent split

The manager acquires the lock, reads only `state.json` as cross-cycle memory, selects ready IDs, compiles each template with its item brief, dispatches, checks changed paths, runs schema/tests/review, requests bounded refinement, updates state, and emits receipts.

Each sub-agent receives one ID, the matching megaprompt, canonical plan excerpts, current shared schemas, acceptance command, changed-file cap, and explicit forbidden paths. It must not manage pipeline state, launch agents, or perform external effects.

## Quality gate

For each item, in order:

1. `STATE:` response parses and item ID matches.
2. Changed paths fall entirely within ownership; cap is respected.
3. Python/JSON schemas and artifacts parse.
4. Module test command passes.
5. Frozen brief acceptance criteria pass.
6. Manager reviews correctness, security/privacy, idempotency, contracts, and unnecessary complexity.

The manager may request two refinements. A second rejection increments the attempt and returns the item to `pending`; the third unsuccessful attempt marks it `failed`. No downstream dependency becomes ready until the item is `done`.

## Idempotency and external effects

- Stable item IDs are ledger keys; `done` is a no-op unless an approved input fingerprint changes.
- Outputs use the owned paths above. Tests and fixtures overwrite their deterministic paths rather than append duplicates.
- Checkpoints write `state.json.tmp`, fsync, then rename to `state.json`.
- The first wake action is atomic creation of `pipeline.lock`; a fresh existing lock exits quietly.
- There are no authorized external effects. Any later effect needs a key `project:item:input_fingerprint:effect` stored before firing.

## Observability and controls

- `pipeline/state.json`: only cross-cycle memory.
- `pipeline/runs.jsonl`: one bounded event line per cycle transition; raw customer text excluded.
- `pipeline/BUILD_COMPLETE`: final engineering build state and receipt pointer.
- `pipeline/pipeline.lock`: double-fire exclusion; stale only after 90 minutes and requires manager recovery logging.
- Human digest after each cycle: items attempted, results, tests, cap usage, failures, next ready items.

## Schedule

Suggested expression after human review and explicit installation: `0 * * * *` (hourly). No schedule is installed by this specification. Immediate cycles can be run by the active manager task.

## Changelog

- 1.2.0 - Removed obsolete PAUSED/PREP_ONLY blockade and completed the generated-data FTPO engineering lane with a model-corroborated receipt.
- 1.1.0 - Added two-lane PAUSED/PREP_ONLY semantics so deterministic local preparation can continue without external inference or false gate evidence.
- 1.0.0 - Initial five-module implementation pipeline with integration item, zero external spend, kill switch, atomic state, and quality gates.
