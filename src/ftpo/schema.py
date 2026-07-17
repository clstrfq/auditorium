from __future__ import annotations

from datetime import datetime
import math
import re
from typing import Any


SHA256 = re.compile(r"^[a-f0-9]{64}$")
EXAMPLE_ID = re.compile(r"^ftpo-[a-zA-Z0-9._-]+$")
PATTERN_FAMILIES = {
    "negative_parallelism", "tricolon", "trailing_participle", "em_dash",
    "curly_quote", "transition_pileup", "bold_lead_in", "other_preregistered",
}


class ValidationError(ValueError):
    """Raised when an FTPO example violates the frozen input contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _sha(value: Any, field: str) -> None:
    _require(isinstance(value, str) and SHA256.fullmatch(value) is not None,
             f"{field} must be a lowercase sha256")


def _token(candidate: Any, field: str) -> tuple[int, str]:
    _require(isinstance(candidate, dict), f"{field} must be an object")
    _require(set(candidate) == {"token_id", "token_text", "reference_logprob"},
             f"{field} has unexpected fields")
    _require(isinstance(candidate["token_id"], int) and not isinstance(candidate["token_id"], bool)
             and candidate["token_id"] >= 0,
             f"{field}.token_id must be nonnegative")
    _require(isinstance(candidate["token_text"], str) and bool(candidate["token_text"]),
             f"{field}.token_text must be nonempty")
    logprob = candidate["reference_logprob"]
    _require(isinstance(logprob, (int, float)) and not isinstance(logprob, bool)
             and math.isfinite(logprob), f"{field}.reference_logprob must be finite numeric")
    return candidate["token_id"], candidate["token_text"]


def validate_example(value: dict[str, Any], *, require_approved: bool = True) -> None:
    required = {
        "schema_version", "example_id", "source_item_id", "author_cluster_id",
        "prompt_id", "prompt_sha256", "trace_id", "model_id", "model_revision",
        "tokenizer_sha256", "prefix_text", "prefix_token_ids", "pattern_id",
        "pattern_family", "rejected", "chosen", "protected_facts_sha256",
        "semantic_necessity", "cda_validation", "review", "provenance",
    }
    _require(isinstance(value, dict) and set(value) == required,
             "example fields must exactly match schema 1.0.0")
    _require(value["schema_version"] == "1.0.0", "unsupported schema_version")
    _require(isinstance(value["example_id"], str) and EXAMPLE_ID.fullmatch(value["example_id"]) is not None,
             "invalid example_id")
    for field in ("source_item_id", "author_cluster_id", "prompt_id", "trace_id",
                  "model_id", "model_revision", "prefix_text", "pattern_id"):
        _require(isinstance(value[field], str) and bool(value[field]), f"{field} must be nonempty")
    _sha(value["prompt_sha256"], "prompt_sha256")
    _sha(value["tokenizer_sha256"], "tokenizer_sha256")
    _require(isinstance(value["prefix_token_ids"], list) and value["prefix_token_ids"] and
             all(isinstance(v, int) and not isinstance(v, bool) and v >= 0
                 for v in value["prefix_token_ids"]),
             "prefix_token_ids must be a nonempty nonnegative integer list")
    _require(value["pattern_family"] in PATTERN_FAMILIES, "unknown pattern_family")
    rejected = _token(value["rejected"], "rejected")
    chosen = value["chosen"]
    _require(isinstance(chosen, list) and 2 <= len(chosen) <= 8, "chosen must contain 2-8 tokens")
    chosen_keys = [_token(item, f"chosen[{i}]") for i, item in enumerate(chosen)]
    _require(len(set(chosen_keys)) == len(chosen_keys), "chosen tokens must be unique")
    _require(rejected not in set(chosen_keys), "rejected token cannot be chosen")
    all_tokens = [rejected, *chosen_keys]
    token_ids = [item[0] for item in all_tokens]
    _require(len(token_ids) == len(set(token_ids)), "candidate token IDs must be unique")
    facts = value["protected_facts_sha256"]
    _require(isinstance(facts, list) and len(facts) == len(set(facts)), "protected facts must be unique")
    for index, fact in enumerate(facts):
        _sha(fact, f"protected_facts_sha256[{index}]")
    _require(value["semantic_necessity"] in {"unnecessary", "necessary", "uncertain"},
             "invalid semantic_necessity")

    cda = value["cda_validation"]
    _require(isinstance(cda, dict) and set(cda) == {"pair_type", "protected_facts_match",
             "semantic_equivalence_pass", "length_tolerance_pass", "validator_version"},
             "invalid cda_validation fields")
    _require(cda["pair_type"] in {"content_fixed_length_divergent",
             "length_fixed_content_divergent", "not_applicable"}, "invalid pair_type")
    _require(cda["protected_facts_match"] is True, "protected facts must match")
    if cda["pair_type"] == "content_fixed_length_divergent":
        _require(cda["semantic_equivalence_pass"] is True, "content-fixed pair needs semantic equivalence")
    if cda["pair_type"] == "length_fixed_content_divergent":
        _require(cda["length_tolerance_pass"] is True, "length-fixed pair needs length tolerance")
    _require(isinstance(cda["validator_version"], str) and bool(cda["validator_version"]),
             "validator_version must be nonempty")

    review = value["review"]
    _require(isinstance(review, dict) and set(review) == {"status", "reviewer_id", "reviewed_at",
             "generator_family_excluded"}, "invalid review fields")
    _require(review["status"] in {"approved", "rejected", "pending"}, "invalid review status")
    if require_approved:
        _require(review["status"] == "approved", "training examples require approved review")
    _require(review["generator_family_excluded"] is True, "generator family must be excluded")
    try:
        datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValidationError("reviewed_at must be ISO-8601") from exc

    provenance = value["provenance"]
    _require(isinstance(provenance, dict) and set(provenance) == {"source_manifest_sha256",
             "trace_sha256", "detector_version", "created_at"}, "invalid provenance fields")
    _sha(provenance["source_manifest_sha256"], "source_manifest_sha256")
    _sha(provenance["trace_sha256"], "trace_sha256")
    _require(isinstance(provenance["detector_version"], str) and bool(provenance["detector_version"]),
             "detector_version must be nonempty")
