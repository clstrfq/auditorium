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
from src.ftpo.local_model import (REFERENCE_SPEC, TOKENIZER_SPEC, log_softmax,
                                  reference_logits, reference_sha256, sha256_text,
                                  stable_token_id, tokenize, tokenizer_sha256)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind S0 fixtures to the deterministic local reference model.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source_records = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line]
    args.output.mkdir(parents=True, exist_ok=True)
    contract_hash = sha256_text(f"{file_sha(args.input)}:{TOKENIZER_SPEC}:{REFERENCE_SPEC}")
    records: list[dict] = []
    scores: list[dict] = []
    for source in source_records:
        item = json.loads(json.dumps(source))
        rejected_text = item["rejected"]["token_text"]
        chosen_texts = [candidate["token_text"] for candidate in item["chosen"]]
        raw_logits = reference_logits(item["prefix_text"], rejected_text, chosen_texts)
        log_probs = log_softmax(raw_logits)
        item["model_id"] = "surrogate/local-synthetic-reference"
        item["model_revision"] = reference_sha256()
        item["tokenizer_sha256"] = tokenizer_sha256()
        item["prefix_token_ids"] = [token_id for token_id, _ in tokenize(item["prefix_text"])]
        item["rejected"] = {
            "token_id": stable_token_id(rejected_text), "token_text": rejected_text,
            "reference_logprob": log_probs[rejected_text]
        }
        item["chosen"] = [
            {"token_id": stable_token_id(text), "token_text": text, "reference_logprob": log_probs[text]}
            for text in chosen_texts
        ]
        item["provenance"]["source_manifest_sha256"] = contract_hash
        item["provenance"]["trace_sha256"] = sha256_text(json.dumps(
            {"prefix": item["prefix_text"], "logits": raw_logits}, sort_keys=True))
        item["provenance"]["detector_version"] = "local-s1-binder/1.0.0"
        validate_example(item)
        records.append(item)
        candidate_distribution_sha256 = sha256_text(json.dumps(
            {"logits": raw_logits, "log_probs": log_probs}, sort_keys=True, separators=(",", ":")))
        scores.append({
            "example_id": item["example_id"], "prefix_sha256": item["prompt_sha256"],
            "reference_model_sha256": reference_sha256(), "tokenizer_sha256": tokenizer_sha256(),
            "candidate_set_normalized": True,
            "candidate_distribution_sha256": candidate_distribution_sha256,
            "candidates": [
                {"role": "rejected", "token_id": item["rejected"]["token_id"],
                 "token_text": rejected_text, "raw_logit": raw_logits[rejected_text],
                 "log_prob": log_probs[rejected_text]}
            ] + [
                {"role": "chosen", "token_id": stable_token_id(text), "token_text": text,
                 "raw_logit": raw_logits[text], "log_prob": log_probs[text]} for text in chosen_texts
            ]
        })
    data_payload = "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in records)
    score_payload = "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in scores)
    (args.output / "all.jsonl").write_text(data_payload, encoding="utf-8")
    (args.output / "reference-scores.jsonl").write_text(score_payload, encoding="utf-8")
    manifest = {
        "schema_version": "1.0.0", "tier": "S1_LOCAL_SYNTHETIC",
        "evidence_class": "SYNTHETIC_NONEMPIRICAL", "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": str(args.input), "source_sha256": file_sha(args.input),
        "record_count": len(records), "tokenizer_spec": TOKENIZER_SPEC,
        "tokenizer_sha256": tokenizer_sha256(), "reference_spec": REFERENCE_SPEC,
        "reference_model_sha256": reference_sha256(), "binding_contract_sha256": contract_hash,
        "data_sha256": sha256_text(data_payload), "reference_scores_sha256": sha256_text(score_payload),
        "score_scope": "candidate_set_normalized_not_full_vocabulary",
        "permitted_uses": ["local synthetic FTPO/DPO/control training", "end-to-end build acceptance"],
        "forbidden_uses": ["Gemma claims", "frontier-model claims", "human baseline claims", "Gate B empirical evidence"]
    }
    (args.output / "dataset-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
