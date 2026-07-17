from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from typing import Any, Callable, Iterable, Mapping

SCHEMA_VERSION = "1.0.0"
PRODUCER_VERSION = "m5-report-1.0.0"


class ArtifactValidationError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def validate_artifact(artifact: Mapping[str, Any], *, expected_hash: str | None = None,
                      schema_version: str = SCHEMA_VERSION) -> None:
    required = {"schema_version", "run_id", "created_at", "producer_version", "input_hash", "status"}
    missing = sorted(required - artifact.keys())
    if missing:
        raise ArtifactValidationError(f"missing canonical metadata: {', '.join(missing)}")
    if artifact["schema_version"] != schema_version:
        raise ArtifactValidationError(f"unsupported schema_version: {artifact['schema_version']}")
    if expected_hash is not None and content_hash(artifact) != expected_hash:
        raise ArtifactValidationError("artifact hash mismatch")


def _path(record: Mapping[str, Any], dotted: str) -> Any:
    value: Any = record
    for part in dotted.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def _truthy(path: str) -> Callable[[Mapping[str, Any]], bool]:
    return lambda record: bool(_path(record, path))


DEFAULT_METRICS: Mapping[str, tuple[str, Callable[[Mapping[str, Any]], bool]]] = {
    "detection_rate": ("detected", _truthy("detected")),
    "acceptance_rate": ("accepted", lambda r: _path(r, "review.action") in {"accept", "edit"}),
    "verification_pass_rate": ("verified", lambda r: _path(r, "verification.decision") == "verified"
                               and _path(r, "verification.status") == "verified"),
}


def _metric(metric_id: str, numerator_label: str, records: list[Mapping[str, Any]],
            predicate: Callable[[Mapping[str, Any]], bool], policy_version: str) -> dict[str, Any]:
    numerator = sum(1 for record in records if predicate(record))
    denominator = len(records)
    exact = None if denominator == 0 else str(
        (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    )
    return {"metric_id": metric_id, "numerator": numerator, "numerator_label": numerator_label,
            "denominator": denominator, "denominator_label": "eligible_items", "unit": "proportion",
            "value": exact, "policy_version": policy_version}


def build_run_summary(records: Iterable[Mapping[str, Any]], manifest: Mapping[str, Any], *,
                      policy_version: str, created_at: str | None = None,
                      metrics: Mapping[str, tuple[str, Callable[[Mapping[str, Any]], bool]]] | None = None,
                      unresolved: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    validate_artifact(manifest)
    rows = sorted(list(records), key=lambda row: str(row.get("item_id", "")))
    seen: set[str] = set()
    for row in rows:
        validate_artifact(row)
        if row["run_id"] != manifest["run_id"]:
            raise ArtifactValidationError("item run_id does not match manifest")
        item_id = str(row.get("item_id", ""))
        if not item_id or item_id in seen:
            raise ArtifactValidationError("item_id must be non-empty and unique")
        seen.add(item_id)
    definitions = metrics or DEFAULT_METRICS
    when = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result = {"schema_version": SCHEMA_VERSION, "run_id": manifest["run_id"], "created_at": when,
              "producer_version": PRODUCER_VERSION, "input_hash": manifest["input_hash"],
              "status": "complete", "corpus_hash": manifest.get("corpus_hash"),
              "policy_version": policy_version, "item_ids": sorted(seen),
              "metrics": [_metric(mid, label, rows, pred, policy_version)
                          for mid, (label, pred) in sorted(definitions.items())],
              "unresolved": sorted(list(unresolved), key=canonical_json)}
    result["summary_hash"] = content_hash(result)
    return result


def build_markdown_report(summary: Mapping[str, Any]) -> str:
    lines = [f"# Run {summary['run_id']}", "", f"Policy: `{summary['policy_version']}`", "",
             "## Metrics", ""]
    for metric in sorted(summary["metrics"], key=lambda row: row["metric_id"]):
        lines.append(f"- **{metric['metric_id']}**: {metric['numerator']}/{metric['denominator']} "
                     f"{metric['unit']} (value {metric['value']}; policy `{metric['policy_version']}`)")
    lines.extend(["", "## Unresolved", ""])
    lines.extend(f"- {canonical_json(item)}" for item in summary["unresolved"])
    if not summary["unresolved"]:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def issue_release_receipt(summary: Mapping[str, Any], control_events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    unsigned_summary = {key: value for key, value in summary.items() if key != "summary_hash"}
    if content_hash(unsigned_summary) != summary.get("summary_hash"):
        raise ArtifactValidationError("summary hash mismatch")
    approvals = sorted((event for event in control_events if event.get("action") == "approve_release"),
                       key=lambda e: (e.get("created_at", ""), e.get("event_id", "")))
    if not approvals:
        raise PermissionError("release receipt requires a named approve_release event")
    approval = approvals[-1]
    validate_artifact(approval)
    event_required = {"event_id", "previous_event_hash", "event_hash", "reviewer_id", "action",
                      "artifact_hashes", "reason"}
    missing = sorted(event_required - approval.keys())
    if missing:
        raise ArtifactValidationError(f"approval missing canonical event metadata: {', '.join(missing)}")
    if approval["run_id"] != summary["run_id"] or approval["input_hash"] != summary["input_hash"]:
        raise PermissionError("approve_release event does not belong to this run and input")
    if approval["status"] != "recorded":
        raise PermissionError("approve_release event is stale or not recorded")
    if not str(approval["reviewer_id"]).strip() or not str(approval["reason"]).strip():
        raise PermissionError("approve_release requires a named reviewer and recorded reason")
    unsigned_event = {key: value for key, value in approval.items() if key != "event_hash"}
    if content_hash(unsigned_event) != approval["event_hash"]:
        raise ArtifactValidationError("approval event hash mismatch")
    receipt = {"schema_version": SCHEMA_VERSION, "run_id": summary["run_id"],
               "created_at": approval["created_at"], "producer_version": PRODUCER_VERSION,
               "input_hash": summary["input_hash"], "status": "release_approved",
               "summary_hash": summary["summary_hash"], "approval_event_id": approval["event_id"],
               "approved_by": approval["reviewer_id"], "approval_action": "approve_release"}
    receipt["receipt_hash"] = content_hash(receipt)
    return receipt
