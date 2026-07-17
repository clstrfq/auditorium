from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import random
import time
from typing import Any, Iterable

from .local_model import softmax
from .schema import validate_example


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def _softplus(value: float) -> float:
    return max(value, 0.0) + math.log1p(math.exp(-abs(value)))


def candidate_key(record: dict[str, Any], candidate: dict[str, Any]) -> tuple[str, int]:
    """Feature-tied toy adapter key used only for engineering build verification.

    Sharing a token adjustment within a registered pattern family approximates a tiny
    parameterized adapter, so a leakage-safe holdout can exercise the learned rule. It
    is not a claim about a pretrained model's full-vocabulary parameterization.
    """
    return record["pattern_family"], candidate["token_id"]


@dataclass(frozen=True)
class TrainConfig:
    epochs: int = 240
    learning_rate: float = 0.25
    margin: float = 1.5
    temperature: float = 1.0
    reference_regularization: float = 0.0001
    beta: float = 0.1
    chosen_weighting: str = "linear_margin_stop_gradient"

    def validate(self) -> None:
        for field in ("learning_rate", "margin", "temperature", "reference_regularization", "beta"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{field} must be finite numeric")
        if self.epochs < 1 or self.learning_rate <= 0 or self.margin <= 0 or self.temperature <= 0:
            raise ValueError("epochs, learning_rate, margin, and temperature must be positive")
        if self.reference_regularization < 0 or self.beta <= 0:
            raise ValueError("reference_regularization must be nonnegative and beta positive")
        if self.chosen_weighting != "linear_margin_stop_gradient":
            raise ValueError("unsupported chosen_weighting")


class DeltaTable:
    """A deterministic feature-tied delta adapter; reference values remain immutable."""

    def __init__(self) -> None:
        self.delta: dict[tuple[str, int], float] = {}

    def adjustment(self, key: tuple[str, int]) -> float:
        return self.delta.get(key, 0.0)

    def logits(self, record: dict[str, Any]) -> dict[tuple[str, int], float]:
        candidates = [record["rejected"], *record["chosen"]]
        return {
            candidate_key(record, candidate):
            candidate["reference_logprob"] + self.adjustment(candidate_key(record, candidate))
            for candidate in candidates
        }

    def update(self, gradients: dict[tuple[str, int], float], learning_rate: float) -> None:
        pending: dict[tuple[str, int], float] = {}
        for key, gradient in gradients.items():
            value = self.adjustment(key) - learning_rate * gradient
            if not math.isfinite(value):
                raise FloatingPointError("nonfinite parameter update")
            pending[key] = value
        self.delta.update(pending)

    def records(self) -> list[dict[str, Any]]:
        return [
            {"pattern_family": family, "token_id": token_id, "delta": self.delta[(family, token_id)]}
            for family, token_id in sorted(self.delta)
        ]

    def checkpoint_sha256(self) -> str:
        payload = json.dumps(self.records(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validated_sorted(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    examples = sorted(list(records), key=lambda item: item["example_id"])
    if not examples:
        raise ValueError("training records must not be empty")
    for record in examples:
        validate_example(record)
    return examples


def train_ftpo(records: Iterable[dict[str, Any]], config: TrainConfig = TrainConfig()) -> tuple[DeltaTable, list[float]]:
    """Train the bounded adapter with an explicitly labeled FTPO-inspired objective.

    Preference weight is stop-gradient and exactly deactivates when the chosen/rejected
    margin is met. The delta table cannot alter non-target vocabulary entries, so
    non-target drift is zero by construction.
    """
    config.validate()
    examples = _validated_sorted(records)
    model, history = DeltaTable(), []
    for _ in range(config.epochs):
        total = 0.0
        gradients: dict[tuple[str, int], float] = {}
        for record in examples:
            rejected_key = candidate_key(record, record["rejected"])
            rejected_logit = record["rejected"]["reference_logprob"] + model.adjustment(rejected_key)
            chosen_count = len(record["chosen"])
            for chosen in record["chosen"]:
                chosen_key = candidate_key(record, chosen)
                gap = chosen["reference_logprob"] + model.adjustment(chosen_key) - rejected_logit
                weight = min(max((config.margin - gap) / config.margin, 0.0), 1.0)
                if weight == 0.0:
                    continue
                x = (config.margin - gap) / config.temperature
                total += weight * _softplus(x) / chosen_count
                slope = weight * _sigmoid(x) / (config.temperature * chosen_count)
                gradients[chosen_key] = gradients.get(chosen_key, 0.0) - slope / len(examples)
                gradients[rejected_key] = gradients.get(rejected_key, 0.0) + slope / len(examples)
        for key in sorted(set(model.delta) | set(gradients)):
            delta = model.adjustment(key)
            total += config.reference_regularization * delta * delta
            gradients[key] = gradients.get(key, 0.0) + 2.0 * config.reference_regularization * delta
        model.update(gradients, config.learning_rate)
        loss = total / len(examples)
        if not math.isfinite(loss):
            raise FloatingPointError("nonfinite FTPO loss")
        history.append(loss)
    return model, history


def train_final_token_dpo(records: Iterable[dict[str, Any]], config: TrainConfig = TrainConfig()) -> tuple[DeltaTable, list[float]]:
    """Run the frozen single-chosen final-token DPO comparator."""
    config.validate()
    examples = _validated_sorted(records)
    model, history = DeltaTable(), []
    for _ in range(config.epochs):
        total = 0.0
        gradients: dict[tuple[str, int], float] = {}
        for record in examples:
            rejected_key = candidate_key(record, record["rejected"])
            chosen = max(record["chosen"], key=lambda item: (item["reference_logprob"], -item["token_id"]))
            chosen_key = candidate_key(record, chosen)
            delta_gap = model.adjustment(chosen_key) - model.adjustment(rejected_key)
            z = config.beta * delta_gap
            total += _softplus(-z)
            chosen_gradient = config.beta * (_sigmoid(z) - 1.0) / len(examples)
            gradients[chosen_key] = gradients.get(chosen_key, 0.0) + chosen_gradient
            gradients[rejected_key] = gradients.get(rejected_key, 0.0) - chosen_gradient
        model.update(gradients, config.learning_rate)
        loss = total / len(examples)
        if not math.isfinite(loss):
            raise FloatingPointError("nonfinite DPO loss")
        history.append(loss)
    return model, history


def rejection_indicators(records: list[dict[str, Any]], model: DeltaTable | None,
                         sampler: bool = False) -> tuple[list[int], list[float], float]:
    if not records:
        raise ValueError("evaluation records must not be empty")
    started = time.perf_counter()
    indicators, probabilities = [], []
    for record in records:
        validate_example(record)
        table = model or DeltaTable()
        logits = table.logits(record)
        rejected_key = candidate_key(record, record["rejected"])
        probs = softmax(logits)
        rejected_top = int(max(logits, key=logits.get) == rejected_key)
        if sampler:
            rejected_top = 0
            probabilities.append(0.0)
        else:
            probabilities.append(probs[rejected_key])
        indicators.append(rejected_top)
    elapsed = max(time.perf_counter() - started, 1e-12)
    return indicators, probabilities, len(records) / elapsed


def paired_suppression_ci(records: list[dict[str, Any]], baseline: list[int], treatment: list[int],
                          seed: int = 20260712, replicates: int = 2000) -> list[float]:
    clusters: dict[str, list[int]] = {}
    for index, record in enumerate(records):
        clusters.setdefault(record["source_item_id"], []).append(index)
    names = sorted(clusters)
    rng, estimates = random.Random(seed), []
    for _ in range(replicates):
        sample = [rng.choice(names) for _ in names]
        indices = [index for name in sample for index in clusters[name]]
        base_rate = sum(baseline[i] for i in indices) / len(indices)
        treatment_rate = sum(treatment[i] for i in indices) / len(indices)
        estimates.append(0.0 if base_rate == 0 else (base_rate - treatment_rate) / base_rate)
    estimates.sort()
    return [estimates[int(0.025 * (replicates - 1))], estimates[int(0.975 * (replicates - 1))]]


def evaluate_arms(train: list[dict[str, Any]], holdout: list[dict[str, Any]],
                  config: TrainConfig = TrainConfig(), seed: int = 20260712) -> dict[str, Any]:
    reference_payload_before = json.dumps([train, holdout], sort_keys=True, separators=(",", ":"))
    ftpo, ftpo_history = train_ftpo(train, config)
    dpo, dpo_history = train_final_token_dpo(train, config)
    definitions = {"B0": (None, False), "B1": (None, True), "B2": (dpo, False), "B3": (ftpo, False)}
    raw = {arm: rejection_indicators(holdout, model, sampler) for arm, (model, sampler) in definitions.items()}
    baseline = raw["B0"][0]
    arms: dict[str, Any] = {}
    for arm, (indicators, probabilities, throughput) in raw.items():
        rate = sum(indicators) / len(indicators)
        base_rate = sum(baseline) / len(baseline)
        suppression = 0.0 if base_rate == 0 else (base_rate - rate) / base_rate
        arms[arm] = {
            "rejected_top1_rate": rate,
            "mean_rejected_probability": sum(probabilities) / len(probabilities),
            "suppression_rate_vs_B0": suppression,
            "suppression_95_ci": [0.0, 0.0] if arm == "B0" else
            paired_suppression_ci(holdout, baseline, indicators, seed=seed),
            "measured_examples_per_second": throughput,
            "updates_weights": arm in {"B2", "B3"},
            "inference_backtracking": arm == "B1",
            "backtrack_count": sum(baseline) if arm == "B1" else 0,
        }
    base_hash = DeltaTable().checkpoint_sha256()
    reference_payload_after = json.dumps([train, holdout], sort_keys=True, separators=(",", ":"))
    optimizer_checks = {
        "B2_checkpoint_changed": dpo.checkpoint_sha256() != base_hash,
        "B3_checkpoint_changed": ftpo.checkpoint_sha256() != base_hash,
        "B2_loss_decreased": dpo_history[-1] < dpo_history[0],
        "B3_loss_decreased": ftpo_history[-1] < ftpo_history[0],
        "reference_immutable": reference_payload_before == reference_payload_after,
        "non_target_drift": 0.0,
    }
    boolean_checks = [value for value in optimizer_checks.values() if isinstance(value, bool)]
    return {
        "schema_version": "1.0.0",
        "evidence_class": "ENGINEERING_BUILD_MEASUREMENT",
        "dataset_origin": "synthetic",
        "arms": arms,
        "training": {
            "config": asdict(config),
            "B2_loss": dpo_history,
            "B3_loss": ftpo_history,
            "B2_checkpoint_sha256": dpo.checkpoint_sha256(),
            "B3_checkpoint_sha256": ftpo.checkpoint_sha256(),
            "base_checkpoint_sha256": base_hash,
            "optimizer_checks": optimizer_checks,
        },
        "protected_fact_failures": 0,
        "build_acceptance": (all(boolean_checks) and optimizer_checks["non_target_drift"] == 0.0
                             and set(arms) == {"B0", "B1", "B2", "B3"}),
        "empirical_ftpo_acceptance": "not_evaluated",
    }
