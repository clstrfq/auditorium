from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from src.ftpo import SplitConfig, ValidationError, split_examples, validate_example


ROOT = Path(__file__).resolve().parents[2]


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def example(index: int, *, pattern: str | None = None, source: str | None = None,
            prompt: str | None = None, author: str | None = None) -> dict:
    return {
        "schema_version": "1.0.0",
        "example_id": f"ftpo-{index}",
        "source_item_id": source or f"source-{index}",
        "author_cluster_id": author or f"author-{index}",
        "prompt_id": prompt or f"prompt-{index}",
        "prompt_sha256": sha(f"prompt-{index}"),
        "trace_id": f"trace-{index}",
        "model_id": "fixture/model",
        "model_revision": "fixture-revision",
        "tokenizer_sha256": sha("tokenizer"),
        "prefix_text": f"Prefix {index}",
        "prefix_token_ids": [10, 20, index],
        "pattern_id": pattern or f"pattern-{index}",
        "pattern_family": "negative_parallelism",
        "rejected": {"token_id": 100 + index, "token_text": "not", "reference_logprob": -0.1},
        "chosen": [
            {"token_id": 200 + index, "token_text": "Instead", "reference_logprob": -0.8},
            {"token_id": 300 + index, "token_text": "The", "reference_logprob": -1.0}
        ],
        "protected_facts_sha256": [sha(f"fact-{index}")],
        "semantic_necessity": "unnecessary",
        "cda_validation": {
            "pair_type": "content_fixed_length_divergent",
            "protected_facts_match": True,
            "semantic_equivalence_pass": True,
            "length_tolerance_pass": None,
            "validator_version": "fixture-1"
        },
        "review": {
            "status": "approved", "reviewer_id": "fixture-reviewer",
            "reviewed_at": "2026-07-12T00:00:00Z", "generator_family_excluded": True
        },
        "provenance": {
            "source_manifest_sha256": sha("manifest"), "trace_sha256": sha(f"trace-{index}"),
            "detector_version": "fixture-1", "created_at": "2026-07-12T00:00:00Z"
        }
    }


def test_schema_artifact_and_valid_example() -> None:
    schema = json.loads((ROOT / "evals/schemas/ftpo-training-example-1.0.0.schema.json").read_text())
    assert schema["additionalProperties"] is False
    assert schema["properties"]["chosen"]["minItems"] == 2
    validate_example(example(1))


def test_rejects_protected_fact_or_semantic_failures() -> None:
    bad_fact = example(1)
    bad_fact["cda_validation"]["protected_facts_match"] = False
    with pytest.raises(ValidationError, match="protected facts"):
        validate_example(bad_fact)
    bad_semantics = example(2)
    bad_semantics["cda_validation"]["semantic_equivalence_pass"] = False
    with pytest.raises(ValidationError, match="semantic equivalence"):
        validate_example(bad_semantics)


def test_rejects_pending_review_and_generator_self_judging() -> None:
    pending = example(1)
    pending["review"]["status"] = "pending"
    with pytest.raises(ValidationError, match="approved"):
        validate_example(pending)
    self_judged = example(2)
    self_judged["review"]["generator_family_excluded"] = False
    with pytest.raises(ValidationError, match="generator family"):
        validate_example(self_judged)


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), float("-inf")])
def test_rejects_nonfinite_or_boolean_logprob(value: object) -> None:
    invalid = example(3)
    invalid["rejected"]["reference_logprob"] = value
    with pytest.raises(ValidationError, match="finite numeric"):
        validate_example(invalid)


def test_rejects_duplicate_candidate_token_ids() -> None:
    invalid = example(4)
    invalid["chosen"][0]["token_id"] = invalid["rejected"]["token_id"]
    with pytest.raises(ValidationError, match="token IDs"):
        validate_example(invalid)


def test_split_is_deterministic_and_complete() -> None:
    records = [example(i) for i in range(40)]
    first = split_examples(records)
    second = split_examples(list(reversed(records)))
    assert first["assignments"] == second["assignments"]
    assert first["input_sha256"] == second["input_sha256"]
    assert sum(first["counts"].values()) == 40
    assert all(first["counts"][name] > 0 for name in ("train", "validation", "holdout"))


def test_connected_component_blocks_all_registered_leakage() -> None:
    records = [
        example(1, pattern="shared-pattern"),
        example(2, pattern="shared-pattern", source="bridge-source"),
        example(3, source="bridge-source", prompt="bridge-prompt"),
        example(4, prompt="bridge-prompt", author="bridge-author"),
        example(5, author="bridge-author"),
    ]
    result = split_examples(records, SplitConfig(train_fraction=0.5, validation_fraction=0.2))
    assert len({result["assignments"][record["example_id"]] for record in records}) == 1
    assert result["component_count"] == 1


def test_duplicate_id_is_rejected() -> None:
    duplicate = copy.deepcopy(example(1))
    with pytest.raises(ValueError, match="duplicate example_id"):
        split_examples([example(1), duplicate])


def test_baseline_contract_contains_all_comparators_and_noninferiority_gates() -> None:
    baseline = json.loads((ROOT / "evals/baselines/ftpo-baselines-1.0.0.json").read_text())
    assert {arm["id"] for arm in baseline["arms"]} == {"B0", "B1", "B2", "B3"}
    assert baseline["shared"]["train_holdout_pattern_overlap_allowed"] == 0
    assert baseline["acceptance"]["throughput_noninferiority_ratio_min"] == 0.95
    assert baseline["acceptance"]["family_replications_min"] == 2


def test_slurm_template_is_complete_and_requires_explicit_external_inputs() -> None:
    script = (ROOT / "scripts/slurm/ftpo_train.sbatch").read_text()
    assert "# External execution template" in script
    assert '${EXECUTION_CLEARANCE_RECEIPT:?required}' in script
    assert '[[ -f pipeline/BUILD_COMPLETE ]]' in script
    assert 'pipeline/PAUSED' not in script
    assert 'pipeline/PREP_ONLY' not in script
    assert "srun" in script


def test_pipeline_reports_completed_build_without_legacy_sentinels() -> None:
    assert not (ROOT / "pipeline/PAUSED").exists()
    assert not (ROOT / "pipeline/PREP_ONLY").exists()
    assert not (ROOT / "pipeline/RUNNING").exists()
    assert (ROOT / "pipeline/BUILD_COMPLETE").is_file()
    state = json.loads((ROOT / "pipeline/state.json").read_text())
    assert state["mode"] == "build_complete"
    assert state["paused"] is False
    assert state["budget"]["external_spend_usd"] == 0
