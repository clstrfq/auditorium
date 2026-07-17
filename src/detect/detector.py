from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from src.contracts import NormalizedItem, RunManifest
from src.contracts.models import ArtifactBase


PRODUCER_VERSION = "m2-detector-1.0.0"
RULESET_VERSION = "negative-parallelism-en-1.0.0"

_RULES = (
    ("not_but", re.compile(r"\bnot\b[^.!?\n]{1,160}?\bbut\b[^.!?\n]*", re.IGNORECASE)),
    ("not_instead", re.compile(r"\bnot\b[^.!?\n]{1,160}?\binstead\b[^.!?\n]*", re.IGNORECASE)),
    ("rather_than", re.compile(r"\brather\s+than\b[^.!?\n]*", re.IGNORECASE)),
)


@dataclass(frozen=True)
class CandidateRecord(ArtifactBase):
    item_id: str
    candidate_id: str
    sentence_start: int
    sentence_end: int
    span_start: int
    span_end: int
    matched_rule: str
    evidence_text: str
    context_window: str


def _sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    left = max(text.rfind(".", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start))
    sentence_start = left + 1
    while sentence_start < len(text) and text[sentence_start].isspace():
        sentence_start += 1
    stops = [p for mark in ".!?" if (p := text.find(mark, end)) >= 0]
    sentence_end = min(stops) + 1 if stops else len(text)
    return sentence_start, sentence_end


def detect_candidates(manifest: RunManifest, item: NormalizedItem) -> list[CandidateRecord]:
    """Return deterministic, non-overlapping candidates with exact normalized offsets."""
    if manifest.ruleset_version != RULESET_VERSION:
        raise ValueError(f"unsupported ruleset: {manifest.ruleset_version}")
    found: list[tuple[int, int, str]] = []
    for rule, pattern in _RULES:
        for match in pattern.finditer(item.text):
            if not any(match.start() < end and match.end() > start for start, end, _ in found):
                found.append((match.start(), match.end(), rule))
    records = []
    for start, end, rule in sorted(found):
        sentence_start, sentence_end = _sentence_bounds(item.text, start, end)
        identity = f"{item.input_hash}:{item.item_id}:{start}:{end}:{rule}"
        records.append(CandidateRecord(
            schema_version=item.schema_version,
            run_id=item.run_id,
            created_at=item.created_at,
            producer_version=PRODUCER_VERSION,
            input_hash=item.input_hash,
            status="detected",
            item_id=item.item_id,
            candidate_id=hashlib.sha256(identity.encode()).hexdigest()[:24],
            sentence_start=sentence_start,
            sentence_end=sentence_end,
            span_start=start,
            span_end=end,
            matched_rule=rule,
            evidence_text=item.text[start:end],
            context_window=item.text[sentence_start:sentence_end],
        ))
    return records
