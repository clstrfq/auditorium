from src.compare import compare_runs
from src.replay import build_replay_proposal
from src.report import ArtifactValidationError, build_markdown_report, build_run_summary, issue_release_receipt
from src.report.reporter import content_hash, validate_artifact


def base(**extra):
    value = {"schema_version": "1.0.0", "run_id": "r1", "created_at": "2026-01-01T00:00:00Z",
             "producer_version": "test", "input_hash": "i", "status": "complete"}
    value.update(extra)
    return value


def summary(policy="p1", corpus="c", ids=("a", "b")):
    manifest = base(corpus_hash=corpus)
    rows = [base(item_id=i, detected=i == "a", review={"action": "accept"},
                 verification={"schema_version": "1.0.0", "run_id": "r1",
                     "created_at": "2026-01-01T00:00:00Z", "producer_version": "m3-verifier-1.0.0",
                     "input_hash": "i", "status": "verified", "candidate_id": f"c-{i}",
                     "rewrite_id": f"rw-{i}", "verifier_identity": "deterministic-independent-verifier-1.0.0",
                     "policy_version": "m3-verification-1.0.0", "decision": "verified",
                     "blocking_reasons": [], "checks": ["protected_numbers"]}) for i in ids]
    return build_run_summary(rows, manifest, policy_version=policy, created_at="2026-01-01T00:00:00Z")


def approval(**changes):
    event = base(status="recorded", event_id="release", previous_event_hash="0" * 64,
                 reviewer_id="Ada", action="approve_release", artifact_hashes={"manifest": "h"},
                 reason="Reviewed evidence and approved release")
    event.update(changes)
    event["event_hash"] = content_hash(event)
    return event


def must_raise(error, function, *args):
    try:
        function(*args)
        assert False, f"expected {error.__name__}"
    except error:
        pass


def test_exact_metrics_markdown_and_stable_release_receipt():
    value = summary()
    detection = next(m for m in value["metrics"] if m["metric_id"] == "detection_rate")
    verification = next(m for m in value["metrics"] if m["metric_id"] == "verification_pass_rate")
    assert (detection["numerator"], detection["denominator"], detection["unit"], detection["policy_version"]) == (1, 2, "proportion", "p1")
    assert (verification["numerator"], verification["denominator"]) == (2, 2)
    assert "1/2 proportion" in build_markdown_report(value)
    external = approval(action="approve_external_inference")
    must_raise(PermissionError, issue_release_receipt, value, [external])
    release = approval()
    assert issue_release_receipt(value, [release]) == issue_release_receipt(value, [release])


def test_release_approval_rejects_cross_run_stale_missing_and_tampered_events():
    value = summary()
    for bad in (approval(run_id="other"), approval(input_hash="other"), approval(status="superseded"),
                approval(reviewer_id=""), approval(reason="")):
        must_raise(PermissionError, issue_release_receipt, value, [bad])
    missing_hash = approval()
    missing_hash.pop("event_hash")
    must_raise(ArtifactValidationError, issue_release_receipt, value, [missing_hash])
    tampered = approval()
    tampered["reason"] = "changed after signing"
    must_raise(ArtifactValidationError, issue_release_receipt, value, [tampered])


def test_full_canonical_metadata_requires_created_at():
    artifact = base()
    artifact.pop("created_at")
    must_raise(ArtifactValidationError, validate_artifact, artifact)


def test_comparison_blocks_incompatible_and_replay_preserves_provenance():
    assert compare_runs(summary(), summary(policy="p2"))["comparison_type"] == "blocked"
    paired = compare_runs(summary(), summary())
    assert paired["paired"] and paired["exclusions"] == {"left_only": [], "right_only": []}
    proposal = build_replay_proposal(run_id="r1", input_hash="i", created_at="2026-01-01T00:00:00Z",
        adjudicated_cases=[{"item_id": "a", "source_artifact_hash": "h", "adjudication_event_id": "e",
                             "adjudicator_id": "Ada", "expected": {"label": "negative"}}])
    assert proposal["status"] == "proposed" and proposal["promotion_approved"] is False
    assert proposal["cases"][0]["source_artifact_hash"] == "h"
