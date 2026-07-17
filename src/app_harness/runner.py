from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from src.classify import classify_candidates
from src.contracts import IngestConfig, NormalizedItem, RunManifest
from src.detect import detect_candidates
from src.ingest.pipeline import ingest_file
from src.report import build_run_summary
from src.report.reporter import content_hash
from src.rewrite import generate_rewrites
from src.state.store import atomic_json
from src.verify import verify_rewrites


HARNESS_VERSION = "easy-app-harness-1.0.1"
EXTERNAL_EFFECTS = {
    "network_calls": 0,
    "secrets_accessed": 0,
    "remote_jobs_submitted": 0,
    "external_spend_usd": 0,
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _write_jsonl_atomic(path: Path, rows: list[Mapping[str, Any]]) -> None:
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        for row in rows
    )
    _write_text_atomic(path, payload)


def _load_manifest(path: Path) -> tuple[dict[str, Any], RunManifest]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return value, RunManifest(**{**value, "model_destinations": tuple(value["model_destinations"])})


def _verified_suggestion(finding: Mapping[str, Any]) -> Mapping[str, Any] | None:
    return next((item for item in finding["suggestions"] if item["decision"] == "verified"), None)


def _suggested_copy(items: list[NormalizedItem], findings: list[dict[str, Any]]) -> str | None:
    if len(items) != 1:
        return None
    replacements: list[tuple[int, int, str]] = []
    for finding in findings:
        if finding["classification"]["label"] != "harmful":
            continue
        suggestion = _verified_suggestion(finding)
        if suggestion is None:
            continue
        candidate = finding["candidate"]
        # A standalone rewrite is not necessarily grammatical when spliced
        # into the middle of a larger sentence (for example, ``This is`` +
        # ``A decision tool``).  Only export a complete suggested copy when
        # the verified replacement begins at the sentence boundary.  The
        # review packet still presents every verified standalone suggestion.
        if candidate["span_start"] != candidate["sentence_start"]:
            return None
        replacements.append((candidate["span_start"], candidate["span_end"], suggestion["rewrite_text"]))
    if not replacements:
        return None
    text = items[0].text
    for start, end, replacement in sorted(replacements, reverse=True):
        following = text[end:end + 1]
        if following in ".!?" and replacement.endswith(following):
            replacement = replacement[:-1]
        text = text[:start] + replacement + text[end:]
    return text


def _review_markdown(summary: Mapping[str, Any], findings: list[dict[str, Any]], receipt_name: str) -> str:
    lines = [
        "# App Harness Review",
        "",
        f"- Items checked: {summary['item_count']}",
        f"- Findings: {summary['finding_count']}",
        f"- Harmful: {summary['harmful']}",
        f"- Legitimate: {summary['legitimate']}",
        f"- Needs review: {summary['uncertain']}",
        f"- Verified suggestions: {summary['verified_suggestion_count']}",
        "",
    ]
    if not findings:
        lines.extend(["No supported negative-parallelism patterns were found.", ""])
    for index, finding in enumerate(findings, 1):
        candidate, classification = finding["candidate"], finding["classification"]
        lines.extend([
            f"## Finding {index}: {classification['label']}",
            "",
            f"Item: `{finding['item_id']}`  ",
            f"Rule: `{candidate['matched_rule']}`  ",
            f"Confidence: {classification['confidence']:.2f}",
            "",
            "Source:",
            "",
            *[f"> {line}" for line in candidate["context_window"].splitlines()],
            "",
            classification["rationale"],
            "",
        ])
        if classification["label"] == "uncertain":
            lines.extend(["Decision required: review this finding before requesting a rewrite.", ""])
        elif classification["label"] == "legitimate":
            lines.extend(["No change suggested because the contrast appears materially useful.", ""])
        else:
            verified = [row for row in finding["suggestions"] if row["decision"] == "verified"]
            blocked = [row for row in finding["suggestions"] if row["decision"] != "verified"]
            if verified:
                lines.extend(["Verified, non-destructive suggestions:", ""])
                lines.extend(f"- {row['rewrite_text']}" for row in verified)
                lines.append("")
            if blocked:
                reasons = sorted({reason for row in blocked for reason in row["blocking_reasons"]})
                lines.extend([f"Blocked proposal reasons: {', '.join(reasons) or 'unknown'}", ""])
    lines.extend([
        "## What to do next",
        "",
        "Review the suggestions, then edit your source yourself. The harness never overwrites it.",
        f"Machine receipt: `{receipt_name}`",
        "",
    ])
    return "\n".join(lines)


def _existing_receipt(output: Path, input_metadata: Mapping[str, Any]) -> dict[str, Any] | None:
    receipt_path = output / "receipt.json"
    if not receipt_path.is_file():
        return None
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("harness_version") != HARNESS_VERSION:
        return None
    if receipt.get("input", {}).get("adapted_sha256") != input_metadata.get("adapted_sha256"):
        return None
    for artifact in receipt.get("artifacts", {}).values():
        path = Path(artifact["path"])
        if not path.is_file() or _sha256_file(path) != artifact["sha256"]:
            return None
    expected = content_hash({key: value for key, value in receipt.items() if key != "packet_hash"})
    return receipt if receipt.get("packet_hash") == expected else None


def analyze_canonical(canonical_input: Path, output: Path, input_metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Run the deterministic evaluator and write a non-destructive review packet."""
    canonical_input = canonical_input.resolve()
    output = output.resolve()
    prior = _existing_receipt(output, input_metadata)
    if prior is not None:
        return {**prior, "reused": True}

    output.mkdir(parents=True, exist_ok=True)
    work = output / ".run-state"
    config = IngestConfig(
        field_map={"item_id": "item_id", "text": "text", "context": "context",
                   "prompt": "prompt", "model": "model"},
        ruleset_version="negative-parallelism-en-1.0.0",
        rubric_version="negative-parallelism-rubric-1.0.0",
        threshold_version="easy-harness-1.0.0",
        model_destinations=("local",),
    )
    ingested = ingest_file(canonical_input, config, work)
    run_dir = work / "runs" / ingested.run_id
    manifest_value, manifest = _load_manifest(run_dir / "manifest.json")
    items = [
        NormalizedItem(**json.loads(line))
        for line in (run_dir / "normalized.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    findings: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for item in items:
        candidates = detect_candidates(manifest, item)
        classifications = classify_candidates(manifest, item, candidates)
        summary_row = {**item.to_dict(), "detected": bool(candidates)}
        item_verified = False
        for candidate, classification in zip(candidates, classifications, strict=True):
            finding: dict[str, Any] = {
                "schema_version": "1.0.0",
                "run_id": item.run_id,
                "item_id": item.item_id,
                "source_text": item.text,
                "candidate": asdict(candidate),
                "classification": asdict(classification),
                "suggestions": [],
            }
            if classification.label == "harmful":
                try:
                    rewrites = generate_rewrites(item, candidate, classification)
                    checks = verify_rewrites(item, candidate, rewrites)
                    for rewrite, check in zip(rewrites, checks, strict=True):
                        finding["suggestions"].append({
                            "rewrite_id": rewrite.rewrite_id,
                            "rewrite_text": rewrite.rewrite_text,
                            "decision": check.decision,
                            "blocking_reasons": list(check.blocking_reasons),
                            "checks": list(check.checks),
                        })
                    item_verified = item_verified or any(check.decision == "verified" for check in checks)
                except Exception as exc:
                    finding["suggestions"].append({
                        "rewrite_id": None,
                        "rewrite_text": "",
                        "decision": "blocked",
                        "blocking_reasons": [f"generator_or_verifier_error:{type(exc).__name__}"],
                        "checks": [],
                    })
            elif classification.label == "uncertain":
                unresolved.append({"item_id": item.item_id, "candidate_id": candidate.candidate_id,
                                   "reason": "human_review_required"})
            findings.append(finding)
        if item_verified:
            summary_row["verification"] = {"decision": "verified", "status": "verified"}
        summary_rows.append(summary_row)

    run_summary = build_run_summary(
        summary_rows, manifest_value, policy_version="easy-harness-1.0.0",
        created_at=manifest.created_at, unresolved=unresolved,
    )
    label_counts = {
        label: sum(1 for finding in findings if finding["classification"]["label"] == label)
        for label in ("harmful", "legitimate", "uncertain")
    }
    summary = {
        "schema_version": "1.0.0",
        "run_id": ingested.run_id,
        "status": "complete",
        "item_count": len(items),
        "finding_count": len(findings),
        **label_counts,
        "verified_suggestion_count": sum(
            1 for finding in findings for row in finding["suggestions"] if row["decision"] == "verified"
        ),
        "unresolved_count": len(unresolved),
        "metrics": run_summary["metrics"],
        "summary_hash": run_summary["summary_hash"],
    }

    results_path = output / "results.jsonl"
    summary_path = output / "summary.json"
    review_path = output / "review.md"
    _write_jsonl_atomic(results_path, findings)
    atomic_json(summary_path, summary)
    _write_text_atomic(review_path, _review_markdown(summary, findings, "receipt.json"))

    suggested = _suggested_copy(items, findings)
    suggested_path: Path | None = None
    if suggested is not None and input_metadata.get("format") in {"txt", "md", "markdown"}:
        suffix = ".md" if input_metadata.get("format") in {"md", "markdown"} else ".txt"
        suggested_path = output / f"suggested{suffix}"
        _write_text_atomic(suggested_path, suggested + ("\n" if not suggested.endswith("\n") else ""))
    else:
        for stale in (output / "suggested.md", output / "suggested.txt"):
            if stale.exists():
                stale.unlink()

    artifact_paths = {
        "canonical_input": canonical_input,
        "results": results_path,
        "summary": summary_path,
        "review": review_path,
    }
    if suggested_path is not None:
        artifact_paths["suggested_copy"] = suggested_path
    artifacts = {
        name: {"path": str(path.resolve()), "sha256": _sha256_file(path)}
        for name, path in artifact_paths.items()
    }
    receipt = {
        "schema_version": "1.0.0",
        "harness_version": HARNESS_VERSION,
        "status": "complete",
        "run_id": ingested.run_id,
        "created_at": manifest.created_at,
        "input": dict(input_metadata),
        "summary": summary,
        "results": {"path": str(results_path.resolve()), "count": len(findings)},
        "artifacts": artifacts,
        "release_receipt": None,
        "external_effects": dict(EXTERNAL_EFFECTS),
        "limits": [
            "deterministic English pattern and context rules",
            "suggestions are proposals, not accepted edits",
            "uncertain findings require human review",
        ],
    }
    receipt["packet_hash"] = content_hash(receipt)
    atomic_json(output / "receipt.json", receipt)
    return {**receipt, "reused": False}


__all__ = ["EXTERNAL_EFFECTS", "HARNESS_VERSION", "analyze_canonical"]
