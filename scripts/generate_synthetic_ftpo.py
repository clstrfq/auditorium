from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ftpo import validate_example


FAMILIES = {
    "negative_parallelism": ("not", ["The", "This", "Instead"]),
    "tricolon": ("and", ["because", "while", "so"]),
    "trailing_participle": ("highlighting", ["This", "Evidence", "Results"]),
    "em_dash": ("—", [".", ";", ","]),
    "curly_quote": ("“", ['"', "The", "A"]),
    "transition_pileup": ("Moreover", ["Next", "Evidence", "Separately"]),
    "bold_lead_in": ("**", ["The", "First", "A"]),
    "other_preregistered": ("Ultimately", ["In", "The", "Evidence"]),
}
DOMAINS = ("technical", "administrative", "explanatory", "narrative")


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def record(family: str, component: int, variant: int, seed: int) -> dict:
    domain = DOMAINS[component % len(DOMAINS)]
    scenario = f"{family}-{component:02d}"
    rejected_text, chosen_texts = FAMILIES[family]
    payload = f"Synthetic neutral fact {component} remains fixed at value {1000 + component}."
    prefix = f"[{domain}] {payload} Variant {variant}. "
    base_id = int(sha(f"{seed}:{scenario}:{variant}")[:8], 16)
    pair_type = "content_fixed_length_divergent" if component % 2 == 0 else "length_fixed_content_divergent"
    item = {
        "schema_version": "1.0.0",
        "example_id": f"ftpo-s0-{family}-{component:02d}-{variant}",
        "source_item_id": f"synthetic/{scenario}",
        "author_cluster_id": f"synthetic-author/{scenario}",
        "prompt_id": f"synthetic-prompt/{scenario}",
        "prompt_sha256": sha(prefix),
        "trace_id": f"synthetic-trace/{scenario}/{variant}",
        "model_id": "surrogate/s0-structural-fixture",
        "model_revision": "s0-no-weights",
        "tokenizer_sha256": sha("s0-fake-tokenizer-do-not-train"),
        "prefix_text": prefix,
        "prefix_token_ids": [base_id % 50000 + 1, (base_id // 7) % 50000 + 1, variant + 1],
        "pattern_id": f"synthetic-pattern/{scenario}",
        "pattern_family": family,
        "rejected": {"token_id": base_id % 100000 + 100, "token_text": rejected_text,
                     "reference_logprob": -0.1 - variant / 100},
        "chosen": [
            {"token_id": base_id % 100000 + 1000 + offset, "token_text": token,
             "reference_logprob": -0.8 - offset / 10}
            for offset, token in enumerate(chosen_texts)
        ],
        "protected_facts_sha256": [sha(payload)],
        "semantic_necessity": "unnecessary",
        "cda_validation": {
            "pair_type": pair_type,
            "protected_facts_match": True,
            "semantic_equivalence_pass": True if pair_type.startswith("content_fixed") else None,
            "length_tolerance_pass": True if pair_type.startswith("length_fixed") else None,
            "validator_version": "synthetic-ftpo-gen/1.0.0"
        },
        "review": {
            "status": "approved", "reviewer_id": "synthetic-qc/mechanical-1.0.0",
            "reviewed_at": "2026-07-12T00:00:00Z", "generator_family_excluded": True
        },
        "provenance": {
            "source_manifest_sha256": sha(f"synthetic-manifest:{seed}"),
            "trace_sha256": sha(f"{prefix}|{rejected_text}|{'|'.join(chosen_texts)}"),
            "detector_version": "synthetic-ftpo-gen/1.0.0",
            "created_at": "2026-07-12T00:00:00Z"
        }
    }
    validate_example(item)
    return item


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate S0 nonempirical FTPO structural fixtures.")
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=20260712)
    parser.add_argument("--components-per-family", type=int, default=30)
    parser.add_argument("--variants", type=int, default=3)
    args = parser.parse_args()
    if args.components_per_family < 1 or args.variants < 1:
        parser.error("component and variant counts must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    records = [record(family, component, variant, args.seed)
               for family in FAMILIES
               for component in range(args.components_per_family)
               for variant in range(args.variants)]
    jsonl = "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in records)
    data_path = args.output / "all.jsonl"
    data_path.write_text(jsonl, encoding="utf-8")
    manifest = {
        "schema_version": "1.0.0",
        "tier": "S0_STRUCTURAL_FIXTURE",
        "evidence_class": "SYNTHETIC_NONEMPIRICAL",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/generate_synthetic_ftpo.py",
        "generator_sha256": sha(Path(__file__).read_text(encoding="utf-8")),
        "seed": args.seed,
        "record_count": len(records),
        "components_per_family": args.components_per_family,
        "variants_per_component": args.variants,
        "pattern_families": list(FAMILIES),
        "domains": list(DOMAINS),
        "data_sha256": sha(jsonl),
        "permitted_uses": ["schema tests", "splitter tests", "loader tests", "SLURM smoke tests"],
        "forbidden_uses": ["weight updates", "scientific metrics", "gate evidence", "human baseline claims"],
        "logprob_status": "deterministic_fake_values_do_not_train"
    }
    (args.output / "dataset-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / "quarantine.jsonl").write_text("", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
