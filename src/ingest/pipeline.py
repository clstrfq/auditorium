from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from src.contracts.models import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    IngestConfig,
    NormalizedItem,
    RunManifest,
)
from src.state.store import RunStore, atomic_json


class ForbiddenDestinationError(ValueError):
    pass


@dataclass(frozen=True)
class IngestResult:
    run_id: str
    fingerprint: str
    receipt: dict[str, Any]
    deduplicated: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _validate_policy(config: IngestConfig) -> None:
    allowed = {"local", "fixture"}
    forbidden = sorted(set(config.model_destinations) - allowed)
    if forbidden:
        raise ForbiddenDestinationError(f"external model destinations forbidden: {', '.join(forbidden)}")


def _rows(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row_number, row in enumerate(csv.DictReader(handle), start=2):
                yield row_number, dict(row)
    elif path.suffix.lower() in {".jsonl", ".ndjson"}:
        with path.open("r", encoding="utf-8") as handle:
            for row_number, line in enumerate(handle, start=1):
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError("row is not an object")
                    yield row_number, value
                except (json.JSONDecodeError, ValueError) as exc:
                    yield row_number, {"__row_error__": str(exc)}
    else:
        raise ValueError("only CSV and JSONL inputs are supported")


def _append(handle: Any, value: dict[str, Any]) -> None:
    handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    handle.flush()


def _checkpoint_value(run_id: str, corpus_hash: str, processed: int, seen: set[str], status: str) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "run_id": run_id, "created_at": _utc_now(),
            "producer_version": PRODUCER_VERSION, "input_hash": corpus_hash, "status": status,
            "processed_source_rows": processed, "seen_ids": sorted(seen), "updated_at": _utc_now()}


def ingest_file(source: Path | str, config: IngestConfig, project_root: Path | str) -> IngestResult:
    """Stream a corpus into a content-addressed, resumable local run."""
    _validate_policy(config)  # Must happen before opening or hashing corpus content.
    source_path = Path(source)
    corpus_hash = _hash_file(source_path)
    config_hash = _stable_hash(config.to_dict())
    fingerprint = _stable_hash({"corpus_hash": corpus_hash, "configuration_hash": config_hash})
    run_id = fingerprint[:20]
    store = RunStore(project_root)
    prior = store.successful_receipt(fingerprint)
    if prior is not None:
        return IngestResult(run_id, fingerprint, prior, True)

    run_dir = store.run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = store.checkpoint(run_id) or {"processed_source_rows": 0, "seen_ids": []}
    processed = int(checkpoint["processed_source_rows"])
    seen = set(checkpoint["seen_ids"])
    normalized_path = run_dir / "normalized.jsonl"
    quarantine_path = run_dir / "quarantine.jsonl"
    normalized_count = sum(1 for _ in normalized_path.open(encoding="utf-8")) if normalized_path.exists() else 0
    quarantine_count = sum(1 for _ in quarantine_path.open(encoding="utf-8")) if quarantine_path.exists() else 0
    created_at = _utc_now()
    stopped_control: str | None = None

    with normalized_path.open("a", encoding="utf-8") as normalized, quarantine_path.open("a", encoding="utf-8") as quarantined:
        for ordinal, (source_row, row) in enumerate(_rows(source_path), start=1):
            if ordinal <= processed:
                continue
            control = store.control(run_id)
            if control in {"paused", "cancelled"}:
                stopped_control = control
                break
            error = row.get("__row_error__")
            item_id = str(row.get(config.field_map["item_id"], "")).strip() if not error else ""
            text = row.get(config.field_map["text"]) if not error else None
            if error or not item_id or not isinstance(text, str) or not text.strip() or item_id in seen:
                reason = error or ("duplicate_item_id" if item_id in seen else "missing_or_invalid_required_field")
                record = {"schema_version": SCHEMA_VERSION, "run_id": run_id, "created_at": created_at,
                          "producer_version": PRODUCER_VERSION, "input_hash": corpus_hash, "status": "quarantined",
                          "source_row_reference": source_row, "item_id": item_id or None, "reason": reason}
                _append(quarantined, record)
                quarantine_count += 1
            else:
                optional = {key: row.get(column) for key, column in config.field_map.items()
                            if key in {"context", "prompt", "model"}}
                item = NormalizedItem(SCHEMA_VERSION, run_id, created_at, PRODUCER_VERSION, corpus_hash,
                                      "normalized", item_id, text.strip(), source_row, **optional)
                _append(normalized, item.to_dict())
                seen.add(item_id)
                normalized_count += 1
            processed = ordinal
            store.write_checkpoint(run_id, _checkpoint_value(run_id, corpus_hash, processed, seen, "running"))

    if stopped_control is not None:
        store.write_checkpoint(run_id, _checkpoint_value(run_id, corpus_hash, processed, seen, stopped_control))
        return IngestResult(run_id, fingerprint, {"run_id": run_id, "status": stopped_control}, False)

    manifest = RunManifest(SCHEMA_VERSION, run_id, created_at, PRODUCER_VERSION, corpus_hash, "successful",
                           corpus_hash, config_hash, dict(config.field_map), config.ruleset_version,
                           config.rubric_version, config.threshold_version, config.model_destinations,
                           config.cost_cap, dict(config.consent_flags), normalized_count, quarantine_count,
                           config.dry_run)
    manifest_value = manifest.to_dict()
    if not config.dry_run:
        atomic_json(run_dir / "manifest.json", manifest_value)
    receipt = {"schema_version": SCHEMA_VERSION, "run_id": run_id, "created_at": created_at,
               "producer_version": PRODUCER_VERSION, "input_hash": corpus_hash, "status": "successful",
               "fingerprint": fingerprint, "manifest_hash": _stable_hash(manifest_value),
               "artifacts": {"normalized": str(normalized_path), "quarantine": str(quarantine_path)}}
    store.write_checkpoint(run_id, _checkpoint_value(run_id, corpus_hash, processed, seen, "successful"))
    store.record_success(fingerprint, receipt)
    return IngestResult(run_id, fingerprint, receipt, False)
