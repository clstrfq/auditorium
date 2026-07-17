from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.generate_synthetic_ftpo import FAMILIES, record
from src.ftpo import validate_example
from src.ftpo.local_model import (
    log_softmax,
    reference_logits,
    reference_sha256,
    stable_token_id,
    tokenize,
    tokenizer_sha256,
)
from src.ftpo.trainer import (
    TrainConfig,
    candidate_key,
    evaluate_arms,
    train_final_token_dpo,
    train_ftpo,
)


ROOT = Path(__file__).resolve().parents[2]


def _bind_record(family: str, component: int, *, seed: int = 20260712) -> dict:
    """Create the same deterministic binding as the local S1 CLI, in memory."""
    item = record(family, component, 0, seed)
    rejected_text = item["rejected"]["token_text"]
    chosen_texts = [candidate["token_text"] for candidate in item["chosen"]]
    log_probs = log_softmax(reference_logits(item["prefix_text"], rejected_text, chosen_texts))

    item["model_id"] = "surrogate/local-synthetic-reference"
    item["model_revision"] = reference_sha256()
    item["tokenizer_sha256"] = tokenizer_sha256()
    item["prefix_token_ids"] = [token_id for token_id, _ in tokenize(item["prefix_text"])]
    item["rejected"] = {
        "token_id": stable_token_id(rejected_text),
        "token_text": rejected_text,
        "reference_logprob": log_probs[rejected_text],
    }
    item["chosen"] = [
        {
            "token_id": stable_token_id(text),
            "token_text": text,
            "reference_logprob": log_probs[text],
        }
        for text in chosen_texts
    ]
    validate_example(item)
    return item


def test_tokenizer_and_reference_scores_replay_deterministically() -> None:
    text = "It's not merely useful—it's direct."
    first = tokenize(text)
    second = tokenize(text)

    assert first == second
    assert "".join(piece for _, piece in first) == text
    assert all(token_id == stable_token_id(piece) for token_id, piece in first)
    assert len({token_id for token_id, _ in first}) < len(first)  # repeated whitespace replays IDs
    assert len(tokenizer_sha256()) == len(reference_sha256()) == 64

    prefix = "Explain the result. "
    chosen = ["The", "Evidence", "Instead"]
    logits = reference_logits(prefix, "not", chosen)
    assert logits == reference_logits(prefix, "not", chosen)
    assert max(logits, key=logits.get) == "not"

    log_probs = log_softmax(logits)
    assert set(log_probs) == {"not", *chosen}
    assert sum(math.exp(value) for value in log_probs.values()) == pytest.approx(1.0)
    assert all(math.isfinite(value) and value <= 0 for value in log_probs.values())


def test_local_s1_binder_replays_scores_and_preserves_evidence_boundary(tmp_path: Path) -> None:
    s0 = tmp_path / "s0"
    left, right = tmp_path / "left", tmp_path / "right"
    environment = {**os.environ, "PYTHONPATH": str(ROOT)}
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/generate_synthetic_ftpo.py"),
            str(s0),
            "--components-per-family",
            "1",
            "--variants",
            "1",
        ],
        check=True,
        cwd=ROOT,
        env=environment,
    )
    binder = [sys.executable, str(ROOT / "scripts/generate_local_s1_ftpo.py"), str(s0 / "all.jsonl")]
    subprocess.run([*binder, str(left)], check=True, cwd=ROOT, env=environment)
    subprocess.run([*binder, str(right)], check=True, cwd=ROOT, env=environment)

    assert (left / "all.jsonl").read_bytes() == (right / "all.jsonl").read_bytes()
    assert (left / "reference-scores.jsonl").read_bytes() == (
        right / "reference-scores.jsonl"
    ).read_bytes()

    manifest = json.loads((left / "dataset-manifest.json").read_text(encoding="utf-8"))
    assert manifest["tier"] == "S1_LOCAL_SYNTHETIC"
    assert manifest["evidence_class"] == "SYNTHETIC_NONEMPIRICAL"
    assert manifest["score_scope"] == "candidate_set_normalized_not_full_vocabulary"
    assert "Gate B empirical evidence" in manifest["forbidden_uses"]
    assert manifest["record_count"] == len(FAMILIES)

    items = [json.loads(line) for line in (left / "all.jsonl").read_text().splitlines()]
    scores = [json.loads(line) for line in (left / "reference-scores.jsonl").read_text().splitlines()]
    assert [item["example_id"] for item in items] == [score["example_id"] for score in scores]

    for item, score in zip(items, scores, strict=True):
        validate_example(item)
        assert item["prefix_token_ids"] == [token_id for token_id, _ in tokenize(item["prefix_text"])]
        assert item["tokenizer_sha256"] == tokenizer_sha256()
        assert item["model_revision"] == reference_sha256()

        rejected_text = item["rejected"]["token_text"]
        chosen_texts = [candidate["token_text"] for candidate in item["chosen"]]
        expected_logits = reference_logits(item["prefix_text"], rejected_text, chosen_texts)
        expected_log_probs = log_softmax(expected_logits)
        assert score["candidate_set_normalized"] is True
        assert sum(math.exp(candidate["log_prob"]) for candidate in score["candidates"]) == pytest.approx(1.0)
        for candidate in [item["rejected"], *item["chosen"]]:
            text = candidate["token_text"]
            assert candidate["token_id"] == stable_token_id(text)
            assert candidate["reference_logprob"] == pytest.approx(expected_log_probs[text])
        for candidate in score["candidates"]:
            text = candidate["token_text"]
            assert candidate["raw_logit"] == pytest.approx(expected_logits[text])
            assert candidate["log_prob"] == pytest.approx(expected_log_probs[text])
            assert math.isfinite(candidate["raw_logit"])
            assert math.isfinite(candidate["log_prob"])


def test_ftpo_training_decreases_loss_and_deactivates_at_margin() -> None:
    records = [_bind_record(family, component) for family in FAMILIES for component in range(3)]
    config = TrainConfig(epochs=240, learning_rate=0.25, margin=1.5)
    model, history = train_ftpo(records, config)

    assert len(history) == config.epochs
    assert history[-1] < history[0]
    assert all(math.isfinite(loss) and loss >= 0 for loss in history)
    assert all(math.isfinite(value) for value in model.delta.values())

    final_gaps = []
    for item in records:
        rejected_key = candidate_key(item, item["rejected"])
        rejected_logit = item["rejected"]["reference_logprob"] + model.adjustment(rejected_key)
        for chosen in item["chosen"]:
            chosen_logit = chosen["reference_logprob"] + model.adjustment(candidate_key(item, chosen))
            final_gaps.append(chosen_logit - rejected_logit)
    assert min(final_gaps) > 0.0

    already_satisfied = json.loads(json.dumps(records[0]))
    already_satisfied["rejected"]["reference_logprob"] = -10.0
    for index, chosen in enumerate(already_satisfied["chosen"]):
        chosen["reference_logprob"] = -1.0 - index
    inactive, inactive_history = train_ftpo(
        [already_satisfied],
        TrainConfig(epochs=1, learning_rate=0.25, margin=1.5, reference_regularization=0.0),
    )
    assert inactive.delta == {}
    assert inactive_history == [0.0]


def test_all_baseline_arms_execute_with_bounded_metrics_and_synthetic_evidence() -> None:
    train = [_bind_record(family, component) for family in FAMILIES for component in range(3)]
    holdout = [_bind_record(family, 4) for family in FAMILIES]
    config = TrainConfig(epochs=240, learning_rate=0.25, margin=1.5)

    _, dpo_history = train_final_token_dpo(train, config)
    assert dpo_history[-1] < dpo_history[0]

    result = evaluate_arms(train, holdout, config)
    assert set(result["arms"]) == {"B0", "B1", "B2", "B3"}
    assert result["evidence_class"] == "ENGINEERING_BUILD_MEASUREMENT"
    assert result["dataset_origin"] == "synthetic"
    assert result["empirical_ftpo_acceptance"] == "not_evaluated"
    assert result["protected_fact_failures"] == 0
    assert result["build_acceptance"] is True

    for metrics in result["arms"].values():
        assert 0.0 <= metrics["rejected_top1_rate"] <= 1.0
        assert 0.0 <= metrics["mean_rejected_probability"] <= 1.0
        assert 0.0 <= metrics["suppression_rate_vs_B0"] <= 1.0
        assert metrics["suppression_95_ci"][0] <= metrics["suppression_95_ci"][1]
        assert metrics["measured_examples_per_second"] > 0
        assert all(
            math.isfinite(value)
            for value in (
                metrics["rejected_top1_rate"],
                metrics["mean_rejected_probability"],
                metrics["suppression_rate_vs_B0"],
                *metrics["suppression_95_ci"],
                metrics["measured_examples_per_second"],
            )
        )

    assert result["arms"]["B0"]["rejected_top1_rate"] == 1.0
    assert result["arms"]["B1"]["backtrack_count"] == len(holdout)
    assert all(result["arms"][arm]["backtrack_count"] == 0 for arm in ("B0", "B2", "B3"))
    assert result["arms"]["B3"]["rejected_top1_rate"] == 0.0
    assert result["arms"]["B3"]["mean_rejected_probability"] < result["arms"]["B0"][
        "mean_rejected_probability"
    ]
    assert result["arms"]["B3"]["suppression_rate_vs_B0"] > 0.0
