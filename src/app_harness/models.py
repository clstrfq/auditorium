"""Declarative registry of model families and lineage attribution.

The harness analyzer is deterministic and model-agnostic: it never calls a
model.  But the text it analyzes was *produced* by some model, and comparing
findings across producers is only meaningful when the producer's lineage is
known.  This module supplies that attribution layer.

Two rules keep it honest, matching the repository's evidence discipline:

1. **Never guess.**  A model string that does not match a registered family
   resolves to :data:`UNATTRIBUTED`, not to a plausible-looking family.
2. **Never imply an evaluation.**  Attribution records what produced the text.
   It is not a claim that any model was run, fine-tuned, or benchmarked here.

Families are drawn from the identifiers named in this repository's
``validation-proxy/gate-b/frozen-model-registry.json`` and ``model-arms.json``.
The registry is local data only: no network calls, no secrets, no spend.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable


UNATTRIBUTED = "unattributed"


@dataclass(frozen=True)
class ModelFamily:
    """One model lineage the harness can attribute produced text to.

    ``patterns`` are lowercase regular expressions matched against a normalized
    model identifier.  ``access`` mirrors the frozen registry's vocabulary:
    ``public``, ``manual-gated``, ``api-entitlement``, or ``unknown``.
    """

    key: str
    display_name: str
    vendor: str
    lineage: str
    access: str
    patterns: tuple[str, ...]
    notes: str

    def matches(self, normalized: str) -> bool:
        return any(re.search(pattern, normalized) for pattern in self.patterns)


# Every family named in the repository's frozen registry and model arms.
MODEL_FAMILIES: tuple[ModelFamily, ...] = (
    ModelFamily(
        key="llama",
        display_name="Llama",
        vendor="Meta",
        lineage="meta-llama",
        access="manual-gated",
        patterns=(r"\bllama", r"meta-llama", r"fsfairx", r"armorm", r"offsetbias"),
        notes="Includes Llama-3/3.1 instruct models and Llama-derived reward models.",
    ),
    ModelFamily(
        key="mistral",
        display_name="Mistral",
        vendor="Mistral AI",
        lineage="mistral",
        access="public",
        patterns=(r"\bmistral", r"\bmixtral", r"\bzephyr"),
        notes="Mistral-7B instruct lineage; zephyr-7b-beta is mistral-7b-v0.1 derived.",
    ),
    ModelFamily(
        key="qwen",
        display_name="Qwen",
        vendor="Alibaba",
        lineage="qwen",
        access="public",
        patterns=(r"\bqwen",),
        notes="Qwen1.5/2/2.5 chat, instruct, and math variants.",
    ),
    ModelFamily(
        key="deepseek",
        display_name="DeepSeek",
        vendor="DeepSeek",
        lineage="deepseek",
        access="public",
        patterns=(r"\bdeepseek",),
        notes="Includes R1 distillations, whose base lineage may differ from the vendor.",
    ),
    ModelFamily(
        key="gemma",
        display_name="Gemma",
        vendor="Google",
        lineage="google-gemma",
        access="manual-gated",
        patterns=(r"\bgemma",),
        notes="Gemma-2 instruction-tuned models.",
    ),
    ModelFamily(
        key="gemini",
        display_name="Gemini",
        vendor="Google",
        lineage="google-gemini",
        access="api-entitlement",
        patterns=(r"\bgemini",),
        notes="Hosted Google models; named as a candidate evaluator lineage.",
    ),
    ModelFamily(
        key="chatglm",
        display_name="ChatGLM",
        vendor="Zhipu / zai-org",
        lineage="chatglm",
        access="public-metadata",
        patterns=(r"\bchatglm", r"\bthudm\b", r"\bzai-org\b"),
        notes="License is flagged as requiring review in the frozen registry.",
    ),
    ModelFamily(
        key="gpt",
        display_name="GPT",
        vendor="OpenAI",
        lineage="openai",
        access="api-entitlement",
        patterns=(r"\bgpt-?\d", r"\bgpt\b", r"\bo[134]-(mini|preview)\b", r"\bcodex\b", r"\bchatgpt\b"),
        notes="Includes gpt-4-turbo evaluators and the gpt-5.6 / Codex runtime lineage.",
    ),
    ModelFamily(
        key="claude",
        display_name="Claude",
        vendor="Anthropic",
        lineage="anthropic",
        access="api-entitlement",
        patterns=(r"\bclaude", r"\bsonnet\b", r"\bopus\b", r"\bhaiku\b", r"\bfable\b"),
        notes="Named as a candidate evaluator lineage.",
    ),
)

_UNKNOWN_ATTRIBUTION: dict[str, Any] = {
    "family": UNATTRIBUTED,
    "display_name": None,
    "vendor": None,
    "lineage": None,
    "access": "unknown",
    "confidence": "none",
}


class ModelRegistryError(ValueError):
    """Raised when the frozen registry file cannot be read as expected."""


def _normalize(model: str) -> str:
    return re.sub(r"[\s_]+", "-", model.strip().lower())


def family_keys() -> tuple[str, ...]:
    """Return every registered family key, in registry order."""

    return tuple(family.key for family in MODEL_FAMILIES)


def attribute_model(model: str | None) -> dict[str, Any]:
    """Attribute a model identifier to a family, or mark it unattributed.

    Matching is conservative: an identifier matching two families is
    ``ambiguous`` rather than arbitrarily assigned to the first match, because
    silently picking a lineage would corrupt any cross-family comparison built
    on top of it.
    """

    if model is None or not str(model).strip():
        return dict(_UNKNOWN_ATTRIBUTION)

    normalized = _normalize(str(model))
    matches = [family for family in MODEL_FAMILIES if family.matches(normalized)]

    if not matches:
        return dict(_UNKNOWN_ATTRIBUTION)
    if len(matches) > 1:
        return {
            **_UNKNOWN_ATTRIBUTION,
            "confidence": "ambiguous",
            "candidates": sorted(family.key for family in matches),
        }

    family = matches[0]
    return {
        "family": family.key,
        "display_name": family.display_name,
        "vendor": family.vendor,
        "lineage": family.lineage,
        "access": family.access,
        "confidence": "matched",
    }


def attribute_models(models: Iterable[str | None]) -> dict[str, Any]:
    """Summarize attribution across many model identifiers.

    Returns per-family counts plus separate ``ambiguous`` and ``unknown``
    counts.  The two are not the same failure: ``ambiguous`` means the
    identifier names more than one real lineage (a DeepSeek distillation of a
    Qwen base names both), while ``unknown`` means no registered family matched
    at all.  Collapsing them would hide the case a cross-family comparison most
    needs to see.
    """

    counts: dict[str, int] = {}
    ambiguous = 0
    unknown = 0
    for model in models:
        attribution = attribute_model(model)
        if attribution["family"] != UNATTRIBUTED:
            counts[attribution["family"]] = counts.get(attribution["family"], 0) + 1
        elif attribution["confidence"] == "ambiguous":
            ambiguous += 1
        else:
            unknown += 1
    return {
        "families": dict(sorted(counts.items())),
        "distinct_family_count": len(counts),
        "ambiguous_count": ambiguous,
        "unknown_count": unknown,
        "unattributed_count": ambiguous + unknown,
        "cross_family": len(counts) > 1,
    }


def family_catalog() -> list[dict[str, Any]]:
    """Return a JSON-serializable description of every family."""

    return [
        {
            "key": family.key,
            "display_name": family.display_name,
            "vendor": family.vendor,
            "lineage": family.lineage,
            "access": family.access,
            "notes": family.notes,
        }
        for family in MODEL_FAMILIES
    ]


def load_frozen_registry(path: Path) -> dict[str, Any]:
    """Read the repository's frozen model registry and attribute each entry.

    This does not re-state the registry's claims; it reports which named models
    the harness can attribute, and flags any the registry names but this module
    cannot place.  A registry entry the harness cannot attribute is a gap to
    close, not a failure to hide.
    """

    path = Path(path)
    if not path.is_file():
        raise ModelRegistryError(f"frozen model registry not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ModelRegistryError(f"could not read frozen model registry {path}: {exc}") from exc

    entries: list[dict[str, Any]] = []
    for section in ("generation_models", "evaluators"):
        for record in payload.get(section, []):
            identifier = record.get("id")
            entries.append(
                {
                    "id": identifier,
                    "section": section,
                    "attribution": attribute_model(identifier),
                }
            )
    unattributed = [entry["id"] for entry in entries if entry["attribution"]["family"] == UNATTRIBUTED]
    return {
        "source": str(path),
        "observed_at": payload.get("observed_at"),
        "entry_count": len(entries),
        "entries": entries,
        "unattributed_ids": unattributed,
        "fully_attributed": not unattributed,
    }


__all__ = [
    "MODEL_FAMILIES",
    "UNATTRIBUTED",
    "ModelFamily",
    "ModelRegistryError",
    "attribute_model",
    "attribute_models",
    "family_catalog",
    "family_keys",
    "load_frozen_registry",
]
