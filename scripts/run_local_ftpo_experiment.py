from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ftpo.schema import validate_example
from src.ftpo.split import LEAKAGE_FIELDS
from src.ftpo.trainer import TrainConfig, evaluate_arms, train_final_token_dpo, train_ftpo


RECEIPT_CLASS = "MODEL_CORROBORATED_BUILD_VERIFICATION"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256_bytes(payload.encode("utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records:
        raise ValueError(f"empty dataset: {path}")
    for record in records:
        validate_example(record)
    return records


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def verify_splits(splits: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    names = ("train", "validation", "holdout")
    ids = {name: {item["example_id"] for item in splits[name]} for name in names}
    overlaps: list[dict[str, Any]] = []
    for left_index, left in enumerate(names):
        for right in names[left_index + 1:]:
            duplicate_ids = sorted(ids[left] & ids[right])
            if duplicate_ids:
                overlaps.append({"field": "example_id", "splits": [left, right], "count": len(duplicate_ids)})
            for field in LEAKAGE_FIELDS:
                left_values = {item[field] for item in splits[left]}
                right_values = {item[field] for item in splits[right]}
                shared = left_values & right_values
                if shared:
                    overlaps.append({"field": field, "splits": [left, right], "count": len(shared)})
    if overlaps:
        raise ValueError(f"split leakage detected: {overlaps}")
    return {"status": "pass", "registered_overlap_count": 0, "fields": ["example_id", *LEAKAGE_FIELDS]}


def aggregate(seed_runs: list[dict[str, Any]]) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for arm in ("B0", "B1", "B2", "B3"):
        observations = [run["arms"][arm] for run in seed_runs]
        arms[arm] = {
            "mean_rejected_top1_rate": mean(item["rejected_top1_rate"] for item in observations),
            "mean_rejected_probability": mean(item["mean_rejected_probability"] for item in observations),
            "mean_suppression_rate_vs_B0": mean(item["suppression_rate_vs_B0"] for item in observations),
            "suppression_95_ci_envelope": [
                min(item["suppression_95_ci"][0] for item in observations),
                max(item["suppression_95_ci"][1] for item in observations),
            ],
            "mean_measured_examples_per_second": mean(
                item["measured_examples_per_second"] for item in observations
            ),
        }
    return {"arms": arms, "all_seed_runs_accepted": all(run["build_acceptance"] for run in seed_runs)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute the bounded FTPO engineering build and B0-B3 comparison.")
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--holdout", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--baseline-spec", type=Path, required=True)
    parser.add_argument("--evidence-catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    paths = {
        "train": args.train,
        "validation": args.validation,
        "holdout": args.holdout,
        "dataset_manifest": args.dataset_manifest,
        "baseline_spec": args.baseline_spec,
        "evidence_catalog": args.evidence_catalog,
    }
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"missing {name}: {path}")

    split_records = {name: read_jsonl(paths[name]) for name in ("train", "validation", "holdout")}
    split_check = verify_splits(split_records)
    manifest = json.loads(args.dataset_manifest.read_text(encoding="utf-8"))
    baseline = json.loads(args.baseline_spec.read_text(encoding="utf-8"))
    evidence = json.loads(args.evidence_catalog.read_text(encoding="utf-8"))
    if manifest.get("evidence_class") != "SYNTHETIC_NONEMPIRICAL":
        raise ValueError("bounded build requires the declared generated-data evidence boundary")
    if evidence.get("receipt_classification") != RECEIPT_CLASS:
        raise ValueError("evidence catalog classification mismatch")
    if {arm["id"] for arm in baseline["arms"]} != {"B0", "B1", "B2", "B3"}:
        raise ValueError("baseline specification must contain B0-B3")

    config = TrainConfig()
    seeds = baseline["shared"]["seeds"]
    input_hashes = {name: file_sha256(path) for name, path in paths.items()}
    fingerprint = canonical_sha256({
        "inputs": input_hashes,
        "config": asdict(config),
        "seeds": seeds,
        "runner_sha256": file_sha256(Path(__file__)),
        "trainer_sha256": file_sha256(Path(__file__).parents[1] / "src/ftpo/trainer.py"),
    })
    args.output.mkdir(parents=True, exist_ok=True)
    receipt_path = args.output / "build-receipt.json"
    metrics_path = args.output / "metrics.json"
    if receipt_path.is_file() and metrics_path.is_file():
        prior = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (prior.get("input_fingerprint") == fingerprint
                and prior.get("artifacts", {}).get("metrics_sha256") == file_sha256(metrics_path)):
            print(json.dumps({"status": "reused", "receipt": str(receipt_path), "input_fingerprint": fingerprint}))
            return 0

    seed_runs: list[dict[str, Any]] = []
    checkpoint_artifacts: list[dict[str, Any]] = []
    for seed in seeds:
        result = evaluate_arms(split_records["train"], split_records["holdout"], config, seed=seed)
        result["seed"] = seed
        seed_runs.append(result)
        dpo, _ = train_final_token_dpo(split_records["train"], config)
        ftpo, _ = train_ftpo(split_records["train"], config)
        for arm, model in (("B2", dpo), ("B3", ftpo)):
            checkpoint_path = args.output / "checkpoints" / f"{arm}-seed-{seed}.json"
            write_json(checkpoint_path, {
                "schema_version": "1.0.0",
                "arm": arm,
                "seed": seed,
                "adapter_kind": "feature_tied_delta_table",
                "dataset_origin": "synthetic",
                "records": model.records(),
                "checkpoint_sha256": model.checkpoint_sha256(),
            })
            checkpoint_artifacts.append({"arm": arm, "seed": seed, "path": str(checkpoint_path),
                                         "sha256": file_sha256(checkpoint_path)})

    metrics = {
        "schema_version": "1.0.0",
        "receipt_classification": RECEIPT_CLASS,
        "dataset_origin": "synthetic",
        "seed_runs": seed_runs,
        "seed_role": "cluster_bootstrap_replay; optimizer is deterministic full-batch",
        "aggregate": aggregate(seed_runs),
        "split_check": split_check,
        "claim_scope": "engineering_build_only",
    }
    write_json(metrics_path, metrics)
    engineering_pass = metrics["aggregate"]["all_seed_runs_accepted"]
    receipt = {
        "schema_version": "1.0.0",
        "receipt_id": "ftpo-build-cycle-0010",
        "receipt_type": "ftpo_engineering_build_verification",
        "receipt_classification": RECEIPT_CLASS,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if engineering_pass else "fail",
        "input_fingerprint": fingerprint,
        "input_hashes": input_hashes,
        "data": {
            "origin": "synthetic",
            "tier": manifest["tier"],
            "counts": {name: len(items) for name, items in split_records.items()},
            "split_integrity": split_check,
        },
        "execution": {
            "training_performed": True,
            "external_training": False,
            "arms": ["B0", "B1", "B2", "B3"],
            "weight_updating_arms": ["B2", "B3"],
            "config": asdict(config),
            "seeds": seeds,
            "seed_role": "cluster_bootstrap_replay; optimizer is deterministic full-batch",
        },
        "evidence": {
            "catalog_path": str(args.evidence_catalog),
            "catalog_sha256": input_hashes["evidence_catalog"],
            "method_evidence": ["antislop-iclr-2026", "liquid-antidoom-2026-07-07"],
            "model_runtime_corroboration": "solene-gpt-5-6-sol-runtime-eval-2026-07-11",
            "runtime_product_context": "openai-gpt-5-6-release-2026-07-09",
            "design_source": "negative-parallelism-design-report",
        },
        "acceptance": {
            "engineering_build": "pass" if engineering_pass else "fail",
            "empirical_ftpo": "not_evaluated",
            "literature_targets": "context_only_not_scored_as_local_measurements",
        },
        "artifacts": {
            "metrics_path": str(metrics_path),
            "metrics_sha256": file_sha256(metrics_path),
            "checkpoints": checkpoint_artifacts,
        },
        "external_effects": {
            "secret_access": 0,
            "external_inference_calls": 0,
            "remote_jobs_submitted": 0,
            "external_spend_usd": 0,
        },
        "claims": {
            "allowed": evidence["claim_policy"]["allowed"],
            "forbidden": evidence["claim_policy"]["forbidden"],
        },
    }
    write_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": str(receipt_path),
                      "input_fingerprint": fingerprint}, sort_keys=True))
    return 0 if engineering_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
