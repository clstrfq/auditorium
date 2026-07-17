from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from src.classify import ClassificationRecord, classify_candidates
from src.contracts import NormalizedItem, RunManifest
from src.detect import detect_candidates
from src.rewrite import FixtureGenerator, ReviewerSelectionEvent, generate_rewrites
from src.verify import VerificationPolicy, verify_rewrites


def artifacts(text="It is not a tool, but a revolution."):
    now = datetime.now(timezone.utc).isoformat()
    base = dict(schema_version="1.0.0", run_id="r", created_at=now, input_hash="h", status="ready")
    manifest = RunManifest(**base, producer_version="m1", corpus_hash="c", configuration_hash="x",
        field_map={"item_id":"id","text":"text"}, ruleset_version="negative-parallelism-en-1.0.0",
        rubric_version="negative-parallelism-rubric-1.0.0", threshold_version="v1", model_destinations=(),
        cost_cap=0, consent_flags={}, normalized_count=1, quarantine_count=0, dry_run=True)
    item = NormalizedItem(**base, producer_version="m1", item_id="i", text=text, source_row_reference=1)
    candidate = detect_candidates(manifest, item)[0]
    classification = classify_candidates(manifest, item, [candidate])[0]
    return item, candidate, classification


def test_generates_two_immutable_proposals_with_canonical_metadata():
    item, candidate, classification = artifacts()
    rewrites = generate_rewrites(item, candidate, classification)
    assert len(rewrites) >= 2 and len({r.rewrite_text for r in rewrites}) == len(rewrites)
    assert all(r.status == "proposed" and r.run_id == item.run_id and r.input_hash == item.input_hash for r in rewrites)
    with pytest.raises(FrozenInstanceError):
        rewrites[0].rewrite_text = "mutated"


def test_uncertain_requires_matching_explicit_reviewer_selection():
    item, candidate, original = artifacts()
    uncertain = ClassificationRecord(**{**original.to_dict(), "label":"uncertain", "status":"needs_review"})
    with pytest.raises(PermissionError):
        generate_rewrites(item, candidate, uncertain)
    event = ReviewerSelectionEvent(schema_version=item.schema_version, run_id=item.run_id,
        created_at=item.created_at, producer_version="review-console", input_hash=item.input_hash,
        status="recorded", candidate_id=candidate.candidate_id, reviewer_id="human-1",
        decision="selected_for_rewrite", reason="Explicit contextual review")
    assert len(generate_rewrites(item, candidate, uncertain, reviewer_selection=event)) == 2


def test_foreign_classification_and_reviewer_selection_are_rejected():
    item, candidate, classification = artifacts()
    foreign_classification = ClassificationRecord(**{
        **classification.to_dict(), "run_id":"foreign-run", "input_hash":"foreign-hash"
    })
    with pytest.raises(ValueError):
        generate_rewrites(item, candidate, foreign_classification)
    uncertain = ClassificationRecord(**{**classification.to_dict(), "label":"uncertain", "status":"needs_review"})
    foreign_event = ReviewerSelectionEvent(schema_version=item.schema_version, run_id="foreign-run",
        created_at=item.created_at, producer_version="review-console", input_hash="foreign-hash",
        status="recorded", candidate_id=candidate.candidate_id, reviewer_id="human-1",
        decision="selected_for_rewrite", reason="Review belongs to another run")
    with pytest.raises(PermissionError):
        generate_rewrites(item, candidate, uncertain, reviewer_selection=foreign_event)
    stale_event = ReviewerSelectionEvent(**{**foreign_event.to_dict(), "run_id":item.run_id,
        "input_hash":item.input_hash, "status":"superseded"})
    with pytest.raises(PermissionError):
        generate_rewrites(item, candidate, uncertain, reviewer_selection=stale_event)


def test_legitimate_is_ineligible_and_generator_needs_two_distinct_options():
    item, candidate, original = artifacts()
    legitimate = ClassificationRecord(**{**original.to_dict(), "label":"legitimate"})
    with pytest.raises(PermissionError):
        generate_rewrites(item, candidate, legitimate)
    with pytest.raises(ValueError):
        generate_rewrites(item, candidate, original, FixtureGenerator(["One.", "One."]))


def test_protected_content_and_residual_patterns_are_critical_blocks():
    text = "Acme Corp must not disclose 42% at https://example [7], but it may publish totals."
    item, candidate, classification = artifacts(text)
    classification = ClassificationRecord(**{**classification.to_dict(), "label":"harmful", "status":"classified"})
    adapter = FixtureGenerator(["Acme Corp may publish totals.",
        "Acme Corp must not disclose 42% at https://example [7], but it may publish totals."])
    results = verify_rewrites(item, candidate, generate_rewrites(item, candidate, classification, adapter))
    assert "protected_numbers_changed" in results[0].blocking_reasons
    assert "protected_negation_scope_changed" in results[0].blocking_reasons
    assert "residual_negative_parallelism" in results[1].blocking_reasons
    assert all(result.decision == result.status == "blocked" for result in results)


def test_clean_rewrites_verify_but_never_accept_and_repetition_blocks():
    item, candidate, classification = artifacts()
    rewrites = generate_rewrites(item, candidate, classification,
        FixtureGenerator(["It is a revolution.", "This represents a tool revolution."]))
    results = verify_rewrites(item, candidate, rewrites)
    assert all(result.decision == "verified" for result in results)
    assert all(result.status != "accepted" for result in results)
    repeated = verify_rewrites(item, candidate, [rewrites[0]], ["It is a revolution for teams."])[0]
    assert repeated.decision == "blocked"
    assert "substitute_repetition_breach" in repeated.blocking_reasons


def test_semantic_uncertainty_and_length_fail_closed_without_mutation():
    item, candidate, classification = artifacts()
    rewrites = generate_rewrites(item, candidate, classification,
        FixtureGenerator(["Completely unrelated wording.", "Revolution " * 20]))
    before = tuple(r.rewrite_text for r in rewrites)
    results = verify_rewrites(item, candidate, rewrites, policy=VerificationPolicy(max_length_ratio=1.2))
    assert "semantic_fidelity_uncertain" in results[0].blocking_reasons
    assert "invalid_length" in results[1].blocking_reasons
    assert tuple(r.rewrite_text for r in rewrites) == before
