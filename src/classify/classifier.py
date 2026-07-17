from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol

from src.contracts import NormalizedItem, RunManifest
from src.contracts.models import ArtifactBase
from src.detect import CandidateRecord


RUBRIC_VERSION = "negative-parallelism-rubric-1.0.0"
PRODUCER_VERSION = "m2-classifier-1.0.0"
LABELS = frozenset({"harmful", "legitimate", "uncertain"})


@dataclass(frozen=True)
class ClassificationRecord(ArtifactBase):
    candidate_id: str
    label: str
    confidence: float
    rationale: str
    evidence_offsets: tuple[int, int]
    classifier_identity: str


class ClassifierAdapter(Protocol):
    identity: str
    def classify(self, context: str, candidate: CandidateRecord) -> tuple[str, float, str]: ...


class FixtureClassifier:
    """Local deterministic facade. Corpus strings are inspected, never interpreted as commands."""
    identity = "fixture-context-classifier-1.0.0"

    def classify(self, context: str, candidate: CandidateRecord) -> tuple[str, float, str]:
        lower = context.lower()
        if re.search(r"\b(correct|distinguish|difference|contrast|whether|true|false)\b", lower):
            return "legitimate", .90, "The context uses negation to make a material distinction or correction."
        if candidate.matched_rule in {"not_but", "not_instead"} and len(candidate.evidence_text.split()) <= 30:
            return "harmful", .82, "The compact contrast matches a formulaic negative-to-positive framing pattern."
        return "uncertain", .50, "The bounded context does not support a reliable rubric decision."


def _looks_english(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum(c.isascii() for c in letters) / len(letters) >= .85


def classify_candidates(
    manifest: RunManifest,
    item: NormalizedItem,
    candidates: list[CandidateRecord],
    adapter: ClassifierAdapter | None = None,
    confidence_threshold: float = .70,
) -> list[ClassificationRecord]:
    if manifest.rubric_version != RUBRIC_VERSION:
        raise ValueError(f"unsupported rubric: {manifest.rubric_version}")
    classifier = adapter or FixtureClassifier()
    output = []
    for candidate in candidates:
        if candidate.item_id != item.item_id:
            raise ValueError("candidate item does not match normalized item")
        if not _looks_english(candidate.context_window):
            label, confidence, rationale = "uncertain", 0.0, "Unsupported language; human adjudication required."
        else:
            try:
                label, confidence, rationale = classifier.classify(candidate.context_window, candidate)
            except Exception:
                label, confidence, rationale = "uncertain", 0.0, "Classifier failure; human adjudication required."
            if label not in LABELS or not 0 <= confidence <= 1 or confidence < confidence_threshold:
                label = "uncertain"
                rationale = "Low-confidence or malformed classifier result; human adjudication required."
        output.append(ClassificationRecord(
            schema_version=item.schema_version,
            run_id=item.run_id,
            created_at=item.created_at,
            producer_version=PRODUCER_VERSION,
            input_hash=item.input_hash,
            status="classified" if label != "uncertain" else "needs_review",
            candidate_id=candidate.candidate_id,
            label=label,
            confidence=confidence,
            rationale=rationale[:240],
            evidence_offsets=(candidate.span_start, candidate.span_end),
            classifier_identity=classifier.identity,
        ))
    return output
