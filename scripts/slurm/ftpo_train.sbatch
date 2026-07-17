#!/usr/bin/env bash
# External execution template. The engineering build is complete; this file has not been submitted.
#SBATCH --job-name=ftpo-eval
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:h200:8
#SBATCH --cpus-per-task=64
#SBATCH --mem=0
#SBATCH --time=12:00:00
#SBATCH --output=logs/ftpo-%j.out
#SBATCH --error=logs/ftpo-%j.err

set -euo pipefail

: "${EXECUTION_CLEARANCE_RECEIPT:?required}"
: "${FTPO_RUNNER:?required absolute executable path}"
: "${BASE_CHECKPOINT:?required}"
: "${TRAIN_JSONL:?required}"
: "${VALIDATION_JSONL:?required}"
: "${HOLDOUT_JSONL:?required}"
: "${BASELINE_SPEC:?required}"
: "${OUTPUT_DIR:?required}"
: "${MAX_TRAIN_GPU_HOURS:?required}"

[[ -f "$EXECUTION_CLEARANCE_RECEIPT" ]]
[[ -x "$FTPO_RUNNER" ]]
[[ -e "$BASE_CHECKPOINT" ]]
[[ -f "$TRAIN_JSONL" && -f "$VALIDATION_JSONL" && -f "$HOLDOUT_JSONL" ]]
[[ -f "$BASELINE_SPEC" ]]
[[ -f pipeline/BUILD_COMPLETE ]]

mkdir -p "$OUTPUT_DIR" logs

srun "$FTPO_RUNNER" \
  --base-checkpoint "$BASE_CHECKPOINT" \
  --train "$TRAIN_JSONL" \
  --validation "$VALIDATION_JSONL" \
  --holdout "$HOLDOUT_JSONL" \
  --baseline-spec "$BASELINE_SPEC" \
  --output "$OUTPUT_DIR" \
  --max-gpu-hours "$MAX_TRAIN_GPU_HOURS" \
  --require-clearance "$EXECUTION_CLEARANCE_RECEIPT"
