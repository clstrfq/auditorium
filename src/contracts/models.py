from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


SCHEMA_VERSION = "1.0.0"
PRODUCER_VERSION = "m1-1.0.0"


@dataclass(frozen=True)
class IngestConfig:
    field_map: Mapping[str, str]
    ruleset_version: str
    rubric_version: str
    threshold_version: str
    model_destinations: tuple[str, ...] = ()
    cost_cap: float = 0.0
    consent_flags: Mapping[str, bool] = field(default_factory=dict)
    dry_run: bool = False

    def __post_init__(self) -> None:
        if not self.ruleset_version or not self.rubric_version or not self.threshold_version:
            raise ValueError("ruleset, rubric, and threshold versions are required")
        if set(self.field_map) - {"item_id", "text", "context", "prompt", "model"}:
            raise ValueError("field_map contains an unknown canonical field")
        if not self.field_map.get("item_id") or not self.field_map.get("text"):
            raise ValueError("field_map must explicitly map item_id and text")
        if self.cost_cap < 0:
            raise ValueError("cost_cap cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["model_destinations"] = list(self.model_destinations)
        return value


@dataclass(frozen=True)
class ArtifactBase:
    schema_version: str
    run_id: str
    created_at: str
    producer_version: str
    input_hash: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedItem(ArtifactBase):
    item_id: str
    text: str
    source_row_reference: int
    context: str | None = None
    prompt: str | None = None
    model: str | None = None


@dataclass(frozen=True)
class RunManifest(ArtifactBase):
    corpus_hash: str
    configuration_hash: str
    field_map: Mapping[str, str]
    ruleset_version: str
    rubric_version: str
    threshold_version: str
    model_destinations: tuple[str, ...]
    cost_cap: float
    consent_flags: Mapping[str, bool]
    normalized_count: int
    quarantine_count: int
    dry_run: bool

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["model_destinations"] = list(self.model_destinations)
        return value
