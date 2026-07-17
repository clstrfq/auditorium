from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from src.contracts import NormalizedItem
from src.contracts.models import ArtifactBase
from src.detect import CandidateRecord
from src.rewrite import RewriteRecord


PRODUCER_VERSION = "m3-verifier-1.0.0"
_URL = re.compile(r"https?://[^\s]+")
_NUMBER = re.compile(r"(?<!\w)[+-]?(?:\d[\d,]*(?:\.\d+)?%?)(?!\w)")
_CITATION = re.compile(r"(?:\[[0-9]+\]|\([A-Z][A-Za-z-]+,?\s+\d{4}\))")
_ENTITY = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+|[A-Z]{2,})\b")
_MODAL = re.compile(r"\b(?:must|shall|should|may|might|can|could|will|would)\b", re.I)
_NEGATION = re.compile(r"\b(?:never|cannot|can't|must\s+not|shall\s+not|may\s+not)\b", re.I)
_RESIDUAL = re.compile(r"\b(?:not\b.{0,160}?\bbut\b|not\b.{0,160}?\binstead\b|rather\s+than)\b", re.I)


@dataclass(frozen=True)
class VerificationPolicy:
    version: str = "m3-verification-1.0.0"
    max_length_ratio: float = 2.5
    min_content_token_recall: float = 0.45
    repetition_prefix_words: int = 4


@dataclass(frozen=True)
class VerificationRecord(ArtifactBase):
    candidate_id: str
    rewrite_id: str
    verifier_identity: str
    policy_version: str
    decision: str
    blocking_reasons: tuple[str, ...]
    checks: tuple[str, ...]


def _values(pattern: re.Pattern[str], text: str) -> set[str]:
    return {match.group(0).casefold() for match in pattern.finditer(text)}


def _content_tokens(text: str) -> set[str]:
    stop = {"the", "a", "an", "is", "are", "was", "were", "it", "this", "that", "not", "but", "instead", "rather", "than"}
    return {word.casefold() for word in re.findall(r"[A-Za-z]{3,}", text) if word.casefold() not in stop}


def verify_rewrite(
    item: NormalizedItem,
    candidate: CandidateRecord,
    rewrite: RewriteRecord,
    prior_verified_texts: Iterable[str] = (),
    policy: VerificationPolicy | None = None,
) -> VerificationRecord:
    """Verify without modifying rewrite text; any uncertainty blocks the proposal."""
    policy = policy or VerificationPolicy()
    if rewrite.candidate_id != candidate.candidate_id or rewrite.input_hash != item.input_hash:
        raise ValueError("rewrite provenance does not match source artifacts")
    source = item.text[candidate.sentence_start:candidate.sentence_end]
    text = rewrite.rewrite_text
    failures: list[str] = []
    checks: list[str] = []
    for name, pattern in (("numbers", _NUMBER), ("urls", _URL), ("citations", _CITATION),
                          ("entities", _ENTITY), ("modality", _MODAL), ("negation_scope", _NEGATION)):
        expected, actual = _values(pattern, source), _values(pattern, text)
        checks.append(f"protected_{name}")
        if expected != actual:
            failures.append(f"protected_{name}_changed")
    checks.append("residual_pattern")
    if _RESIDUAL.search(text):
        failures.append("residual_negative_parallelism")
    checks.append("length")
    if not text.strip() or len(text) > max(1, int(len(source) * policy.max_length_ratio)):
        failures.append("invalid_length")
    checks.append("independent_semantic_recall")
    expected_tokens = _content_tokens(candidate.evidence_text)
    recall = len(expected_tokens & _content_tokens(text)) / len(expected_tokens) if expected_tokens else 0.0
    if recall < policy.min_content_token_recall:
        failures.append("semantic_fidelity_uncertain")
    checks.append("corpus_substitute_repetition")
    prefix_size = policy.repetition_prefix_words
    prefix = tuple(re.findall(r"[A-Za-z]+", text.casefold())[:prefix_size])
    for prior in prior_verified_texts:
        if prefix and prefix == tuple(re.findall(r"[A-Za-z]+", prior.casefold())[:prefix_size]):
            failures.append("substitute_repetition_breach")
            break
    decision = "blocked" if failures else "verified"
    return VerificationRecord(
        schema_version=item.schema_version,
        run_id=item.run_id,
        created_at=item.created_at,
        producer_version=PRODUCER_VERSION,
        input_hash=item.input_hash,
        status=decision,
        candidate_id=candidate.candidate_id,
        rewrite_id=rewrite.rewrite_id,
        verifier_identity="deterministic-independent-verifier-1.0.0",
        policy_version=policy.version,
        decision=decision,
        blocking_reasons=tuple(dict.fromkeys(failures)),
        checks=tuple(checks),
    )


def verify_rewrites(
    item: NormalizedItem,
    candidate: CandidateRecord,
    rewrites: Iterable[RewriteRecord],
    prior_verified_texts: Iterable[str] = (),
    policy: VerificationPolicy | None = None,
) -> list[VerificationRecord]:
    prior = tuple(prior_verified_texts)
    return [verify_rewrite(item, candidate, rewrite, prior, policy) for rewrite in rewrites]
