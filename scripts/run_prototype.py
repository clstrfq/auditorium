#!/usr/bin/env python3
"""Run the local, fixture-only prototype through all five module contracts."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.classify import classify_candidates
from src.compare.comparator import compare_runs
from src.contracts import IngestConfig, NormalizedItem, RunManifest
from src.detect import detect_candidates
from src.ingest.pipeline import ingest_file
from src.report import build_run_summary, issue_release_receipt
from src.review_app.store import EventLedger, artifact_hash
from src.rewrite import ReviewerSelectionEvent, generate_rewrites
from src.verify import verify_rewrites


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _events_path(fixture: Path) -> Path:
    return fixture.with_name(f"{fixture.stem}.events.jsonl")


def run(fixture: Path, workspace: Path, *, destination: str = "fixture") -> dict:
    config = IngestConfig(
        field_map={"item_id": "item_id", "text": "text", "context": "context"},
        ruleset_version="negative-parallelism-en-1.0.0",
        rubric_version="negative-parallelism-rubric-1.0.0",
        threshold_version="prototype-1.0.0",
        model_destinations=(destination,),
    )
    ingested = ingest_file(fixture, config, workspace)
    run_dir = workspace / "runs" / ingested.run_id
    manifest_dict = _load(run_dir / "manifest.json")
    manifest = RunManifest(**{**manifest_dict, "model_destinations": tuple(manifest_dict["model_destinations"])})
    ledger = EventLedger(run_dir / "review-events.jsonl")
    prior_reviews = {event.get("candidate_id"): event for event in ledger.events()
                     if event.get("action") in {"accept", "edit", "reject", "defer"}}
    rows: list[dict] = []

    for line in (run_dir / "normalized.jsonl").read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        item = NormalizedItem(**value)
        candidates = detect_candidates(manifest, item)
        classifications = classify_candidates(manifest, item, candidates)
        row = {**value, "detected": bool(candidates)}
        for candidate, classification in zip(candidates, classifications):
            selection = None
            if classification.label == "uncertain":
                selection = ReviewerSelectionEvent(
                    item.schema_version, item.run_id, item.created_at, "integration-1.0.0",
                    item.input_hash, "recorded", candidate.candidate_id, "fixture-reviewer",
                    "selected_for_rewrite", "Golden fixture exercises the uncertain queue.")
            if classification.label == "legitimate":
                continue
            rewrites = generate_rewrites(item, candidate, classification, reviewer_selection=selection)
            verifications = verify_rewrites(item, candidate, rewrites)
            verified = next(((rewrite, check) for rewrite, check in zip(rewrites, verifications)
                             if check.decision == "verified"), None)
            if verified:
                rewrite, check = verified
                hashes = {"candidate": artifact_hash(candidate), "classification": artifact_hash(classification),
                          "rewrite": artifact_hash(rewrite), "verification": artifact_hash(check)}
                event = prior_reviews.get(candidate.candidate_id)
                if event is None:
                    event = ledger.append_review(run_id=item.run_id, input_hash=item.input_hash,
                                                 reviewer_id="fixture-reviewer", action="accept",
                                                 candidate_id=candidate.candidate_id,
                                                 selected_rewrite_id=rewrite.rewrite_id,
                                                 artifact_hashes=hashes, reason="Verified fixture proposal").to_dict()
                row["review"] = {"action": event["action"]}
                row["verification"] = {"decision": check.decision, "status": check.status}
                break
            row["verification"] = {"decision": "blocked", "status": "blocked"}
        rows.append(row)

    summary = build_run_summary(rows, manifest_dict, policy_version="prototype-1.0.0")
    fixture_events = _events_path(fixture)
    if fixture_events.exists():
        for line in fixture_events.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event.get("action") == "approve_release":
                ledger.append_control(run_id=ingested.run_id, input_hash=manifest.input_hash,
                                      reviewer_id=event["reviewer_id"], action="approve_release",
                                      artifact_hashes={"summary": summary["summary_hash"]},
                                      reason=event["reason"])
    controls = [event for event in ledger.events() if event.get("action") == "approve_release"]
    receipt = issue_release_receipt(summary, controls) if controls else None
    incompatible = dict(summary)
    incompatible["policy_version"] = "incompatible-policy"
    return {"run_id": ingested.run_id, "manifest_hash": ingested.receipt["manifest_hash"],
            "summary": summary, "comparison_probe": compare_runs(summary, incompatible),
            "ledger_verified": ledger.verify(), "ledger_event_count": len(ledger.events()),
            "release_receipt": receipt}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="use an ephemeral workspace")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--destination", default="fixture")
    args = parser.parse_args()
    try:
        if args.dry_run:
            with tempfile.TemporaryDirectory(prefix="negative-parallelism-") as tmp:
                result = run(args.fixture.resolve(), Path(tmp), destination=args.destination)
        else:
            output = (args.output or ROOT / ".prototype-run").resolve()
            result = run(args.fixture.resolve(), output, destination=args.destination)
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": type(exc).__name__, "message": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
