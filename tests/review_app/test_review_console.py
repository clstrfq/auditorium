from dataclasses import replace

import pytest

from src.classify import ClassificationRecord
from src.contracts import NormalizedItem
from src.detect import CandidateRecord
from src.review_app import EventLedger, ReviewBundle, ReviewConsole, StaleArtifactError
from src.rewrite import RewriteRecord
from src.verify import VerificationRecord


def records():
    base = dict(schema_version="1.0.0", run_id="run-1", created_at="2026-07-12T00:00:00Z",
                input_hash="input-1")
    item = NormalizedItem(**base, producer_version="m1", status="normalized", item_id="item-1",
                          text="It is not fast but reliable.", source_row_reference=1)
    candidate = CandidateRecord(**base, producer_version="m2", status="detected", item_id="item-1",
        candidate_id="candidate-1", sentence_start=0, sentence_end=28, span_start=6, span_end=28,
        matched_rule="not_but", evidence_text="not fast but reliable", context_window=item.text)
    classification = ClassificationRecord(**base, producer_version="m2", status="needs_review",
        candidate_id="candidate-1", label="uncertain", confidence=.5, rationale="Human review needed.",
        evidence_offsets=(6, 28), classifier_identity="fixture")
    rewrites = [RewriteRecord(**base, producer_version="m3", status="proposed",
        candidate_id="candidate-1", rewrite_id="rewrite-1", alternative_index=1,
        rewrite_text="It is reliable.", generator_identity="fixture")]
    verifications = [VerificationRecord(**base, producer_version="m3", status="blocked",
        candidate_id="candidate-1", rewrite_id="rewrite-1", verifier_identity="fixture",
        policy_version="v1", decision="blocked", blocking_reasons=("semantic_fidelity_uncertain",),
        checks=("independent_semantic_recall",))]
    return item, candidate, classification, rewrites, verifications


def console(tmp_path):
    bundle = ReviewBundle(*records())
    return ReviewConsole(EventLedger(tmp_path / "events.jsonl"), {"candidate-1": bundle}), bundle


def test_review_and_edit_are_append_only_hash_linked_events(tmp_path):
    app, bundle = console(tmp_path)
    first = app.decide("candidate-1", bundle.hashes, "Ada", "accept", "rewrite-1", reason="Reviewed")
    second = app.decide("candidate-1", bundle.hashes, "Ada", "edit", "rewrite-1",
                        edited_text="Reliability is the priority.")
    events = app.ledger.events()
    assert first.event_hash == second.previous_event_hash
    assert events[0]["edited_text"] is None
    assert events[1]["edited_text"] == "Reliability is the priority."
    assert app.ledger.verify()


def test_submit_rejects_stale_display_hashes(tmp_path):
    app, bundle = console(tmp_path)
    stale = dict(bundle.hashes)
    stale["classification"] = "0" * 64
    with pytest.raises(StaleArtifactError):
        app.decide("candidate-1", stale, "Ada", "defer")
    assert app.ledger.events() == []


def test_control_semantics_and_forbidden_publish(tmp_path):
    app, bundle = console(tmp_path)
    for action in ("pause", "resume", "cancel", "export",
                   "approve_external_inference", "approve_release"):
        app.control("candidate-1", bundle.hashes, "Ada", action, "operator action")
    with pytest.raises(ValueError):
        app.control("candidate-1", bundle.hashes, "Ada", "publish")
    assert [event["action"] for event in app.ledger.events()] == [
        "pause", "resume", "cancel", "export",
        "approve_external_inference", "approve_release"]
    assert app.ledger.verify()


def test_render_keeps_uncertain_failed_evidence_visible_and_accessible(tmp_path):
    app, _ = console(tmp_path)
    html = app.render("candidate-1")
    assert 'role="alert"' in html
    assert "Human review needed" in html
    assert "semantic_fidelity_uncertain" in html
    assert "Source context" in html and "Provenance" in html
    assert '<button name="action" value="publish">' not in html
    assert all(f'value="{action}"' in html for action in
               ("accept", "edit", "reject", "defer", "pause", "resume", "cancel"))
    assert 'value="approve_external_inference"' in html
    assert 'value="approve_release"' in html
    assert 'value="approval"' not in html


def test_missing_identity_and_unknown_rewrite_fail_closed(tmp_path):
    app, bundle = console(tmp_path)
    with pytest.raises(PermissionError):
        app.decide("candidate-1", bundle.hashes, " ", "defer")
    with pytest.raises(ValueError):
        app.decide("candidate-1", bundle.hashes, "Ada", "accept", "unknown")


def test_approval_scopes_are_distinct_reasoned_hash_linked_events(tmp_path):
    app, bundle = console(tmp_path)
    external = app.control("candidate-1", bundle.hashes, "Ada",
                           "approve_external_inference", "Fixture provider approved")
    release = app.control("candidate-1", bundle.hashes, "Ada",
                          "approve_release", "Evidence packet approved")
    assert external.action != release.action
    assert release.previous_event_hash == external.event_hash
    assert app.ledger.events()[0]["action"] == "approve_external_inference"
    assert app.ledger.events()[1]["action"] == "approve_release"
    assert app.ledger.verify()
    for action in ("approve_external_inference", "approve_release"):
        with pytest.raises(PermissionError):
            app.control("candidate-1", bundle.hashes, "Ada", action)
