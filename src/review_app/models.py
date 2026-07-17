from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


SCHEMA_VERSION = "1.0.0"
PRODUCER_VERSION = "m4-review-console-1.0.0"
REVIEW_ACTIONS = frozenset({"accept", "edit", "reject", "defer"})
CONTROL_ACTIONS = frozenset({"pause", "resume", "cancel", "export",
                             "approve_external_inference", "approve_release"})


@dataclass(frozen=True)
class ReviewEvent:
    schema_version: str
    run_id: str
    created_at: str
    producer_version: str
    input_hash: str
    status: str
    event_id: str
    previous_event_hash: str | None
    event_hash: str
    reviewer_id: str
    action: str
    candidate_id: str
    artifact_hashes: Mapping[str, str]
    selected_rewrite_id: str | None = None
    edited_text: str | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControlEvent:
    schema_version: str
    run_id: str
    created_at: str
    producer_version: str
    input_hash: str
    status: str
    event_id: str
    previous_event_hash: str | None
    event_hash: str
    reviewer_id: str
    action: str
    artifact_hashes: Mapping[str, str]
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
