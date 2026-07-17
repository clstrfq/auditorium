from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Protocol, Sequence

from src.classify import ClassificationRecord
from src.contracts import NormalizedItem
from src.contracts.models import ArtifactBase
from src.detect import CandidateRecord


PRODUCER_VERSION = "m3-rewriter-1.0.0"


@dataclass(frozen=True)
class ReviewerSelectionEvent(ArtifactBase):
    candidate_id: str
    reviewer_id: str
    decision: str
    reason: str


@dataclass(frozen=True)
class RewriteRecord(ArtifactBase):
    candidate_id: str
    rewrite_id: str
    alternative_index: int
    rewrite_text: str
    generator_identity: str


class GeneratorAdapter(Protocol):
    identity: str

    def generate(self, item: NormalizedItem, candidate: CandidateRecord) -> Sequence[str]: ...


class FixtureGenerator:
    """Deterministic local facade; no external calls or command interpretation."""

    identity = "fixture-template-generator-1.0.0"

    def __init__(self, alternatives: Sequence[str] | None = None) -> None:
        self._alternatives = tuple(alternatives) if alternatives is not None else None

    def generate(self, item: NormalizedItem, candidate: CandidateRecord) -> Sequence[str]:
        if self._alternatives is not None:
            return self._alternatives
        evidence = candidate.evidence_text.strip()
        direct = re.sub(r"^(.*?)\bnot\b.{1,160}?\b(?:but|instead)\b\s*", r"\1", evidence,
                        count=1, flags=re.IGNORECASE).strip(" ,;:")
        if candidate.matched_rule == "rather_than":
            direct = re.sub(r"^rather\s+than\b\s*", "", evidence,
                            count=1, flags=re.IGNORECASE).strip(" ,;:")
        if not direct:
            return ()
        direct = direct[0].upper() + direct[1:]
        return (f"{direct}.", f"Directly stated: {direct[0].lower() + direct[1:]}.")


def _eligible(
    item: NormalizedItem,
    classification: ClassificationRecord,
    candidate: CandidateRecord,
    selection: ReviewerSelectionEvent | None,
) -> None:
    if classification.candidate_id != candidate.candidate_id:
        raise ValueError("classification does not match candidate")
    if classification.run_id != item.run_id or classification.input_hash != item.input_hash:
        raise ValueError("classification provenance does not match normalized item")
    if classification.label == "harmful":
        return
    if classification.label == "uncertain":
        if selection is None:
            raise PermissionError("uncertain candidate requires an explicit reviewer-selection event")
        if (selection.candidate_id != candidate.candidate_id or selection.run_id != item.run_id
                or selection.input_hash != item.input_hash or selection.status != "recorded"
                or selection.decision != "selected_for_rewrite"
                or not selection.reviewer_id or not selection.reason.strip()):
            raise PermissionError("reviewer-selection event is invalid or does not match candidate")
        return
    raise PermissionError(f"classification label {classification.label!r} is not rewrite-eligible")


def generate_rewrites(
    item: NormalizedItem,
    candidate: CandidateRecord,
    classification: ClassificationRecord,
    adapter: GeneratorAdapter | None = None,
    reviewer_selection: ReviewerSelectionEvent | None = None,
) -> list[RewriteRecord]:
    """Create immutable proposals only. This function cannot accept or export them."""
    if (candidate.item_id != item.item_id or candidate.run_id != item.run_id
            or candidate.input_hash != item.input_hash):
        raise ValueError("candidate does not match normalized item")
    _eligible(item, classification, candidate, reviewer_selection)
    generator = adapter or FixtureGenerator()
    alternatives = [text.strip() for text in generator.generate(item, candidate) if text.strip()]
    if len(alternatives) < 2 or len(set(alternatives)) < 2:
        raise ValueError("generator must produce at least two distinct alternatives")
    records = []
    for index, text in enumerate(alternatives, 1):
        identity = f"{candidate.candidate_id}:{generator.identity}:{index}:{text}"
        records.append(RewriteRecord(
            schema_version=item.schema_version,
            run_id=item.run_id,
            created_at=item.created_at,
            producer_version=PRODUCER_VERSION,
            input_hash=item.input_hash,
            status="proposed",
            candidate_id=candidate.candidate_id,
            rewrite_id=hashlib.sha256(identity.encode()).hexdigest()[:24],
            alternative_index=index,
            rewrite_text=text,
            generator_identity=generator.identity,
        ))
    return records
