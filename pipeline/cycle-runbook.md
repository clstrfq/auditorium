# Pipeline Cycle Runbook

## Build cycle

1. Acquire `pipeline/pipeline.lock` atomically; a fresh existing lock exits without mutation.
2. Read and validate `pipeline/state.json`, input hashes, prior receipts, and deterministic artifact paths.
3. Generate data when required and write a provenance manifest before using it.
4. Validate the FTPO schema, candidate scores, protected-fact contract, and registered leakage fields.
5. Freeze train, validation, and holdout splits before measuring an arm.
6. Run B0 untreated, B1 sampler, B2 final-token DPO, and B3 FTPO with the same split and seed contract.
7. Emit hashed adapter checkpoints, metrics, and a typed evidence receipt.
8. Run the focused FTPO suite, full regression suite, JSON validation, and Python compilation.
9. On success, remove `RUNNING` if present, create `BUILD_COMPLETE`, checkpoint state, and append one cycle event.
10. On failure, retain prior verified artifacts, record the exact failed predicate, and do not create `BUILD_COMPLETE`.

## Evidence handling

- Receipt title: `MODEL_CORROBORATED_BUILD_VERIFICATION`.
- Generated dataset origin remains machine-readable in its manifest and receipt data block.
- The attached 5.6 Sol Ultra report is design and target provenance.
- The separate Solene `gpt-5.6-sol` receipt bundle corroborates model-runtime and receipt mechanics only.
- The Antislop paper and Liquid Antidoom report support the method rationale and literature targets.
- Engineering build acceptance is distinct from an empirical pretrained-model FTPO acceptance decision.

## Separate external execution

The repository includes `scripts/slurm/ftpo_train.sbatch`, but build completion does not claim a remote job, secret access, API call, model-weight update, or spend. If an operator later invokes that template, its explicit runtime paths, clearance receipt, budget, scheduler response, and model artifacts form a new run and receipt.

## Recovery and idempotency

- A matching input fingerprint and verified artifact hashes return the existing build receipt.
- A changed dataset, baseline, evidence catalog, runner, or trainer produces a new fingerprint.
- Reference scores are immutable inputs; B2/B3 updates are emitted as separate delta checkpoints.
- Failed or nonfinite updates stop before checkpoint replacement.

## Changelog

- 1.2.0 - Replaced preparation-only lifecycle with executable generated-data build and final BUILD_COMPLETE state.
- 1.1.0 - Added PREP_ONLY operation under the former external-execution pause.
- 1.0.0 - Initial manager runbook.
