from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .models import (CONTROL_ACTIONS, PRODUCER_VERSION, REVIEW_ACTIONS, SCHEMA_VERSION,
                     ControlEvent, ReviewEvent)


GENESIS = "0" * 64


def canonical_value(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Mapping):
        return {str(key): canonical_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [canonical_value(item) for item in value]
    return value


def artifact_hash(value: Any) -> str:
    encoded = json.dumps(canonical_value(value), sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class StaleArtifactError(RuntimeError):
    pass


class EventLedger:
    """Append-only, hash-linked JSONL ledger for local review and control events."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def verify(self) -> bool:
        previous = GENESIS
        for event in self.events():
            claimed = event.pop("event_hash", None)
            if event.get("previous_event_hash") != previous or artifact_hash(event) != claimed:
                return False
            previous = claimed
        return True

    def _append(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.seek(0)
            rows = [json.loads(line) for line in handle if line.strip()]
            previous_check = GENESIS
            for row in rows:
                claimed = row.get("event_hash")
                unsigned = {key: value for key, value in row.items() if key != "event_hash"}
                if row.get("previous_event_hash") != previous_check or artifact_hash(unsigned) != claimed:
                    raise RuntimeError("event ledger integrity check failed")
                previous_check = claimed
            previous = rows[-1]["event_hash"] if rows else GENESIS
            payload["previous_event_hash"] = previous
            payload.pop("event_hash", None)
            payload["event_hash"] = artifact_hash(payload)
            handle.seek(0, 2)
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            fcntl.flock(handle, fcntl.LOCK_UN)
        return payload

    @staticmethod
    def _base(run_id: str, input_hash: str, reviewer_id: str, action: str,
              hashes: Mapping[str, str], reason: str) -> dict[str, Any]:
        if not reviewer_id.strip():
            raise PermissionError("a named local reviewer is required")
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        identity = f"{run_id}:{reviewer_id}:{action}:{now}:{sorted(hashes.items())}"
        return {"schema_version": SCHEMA_VERSION, "run_id": run_id, "created_at": now,
                "producer_version": PRODUCER_VERSION, "input_hash": input_hash,
                "status": "recorded", "event_id": hashlib.sha256(identity.encode()).hexdigest()[:24],
                "previous_event_hash": None, "event_hash": "", "reviewer_id": reviewer_id.strip(),
                "action": action, "artifact_hashes": dict(sorted(hashes.items())), "reason": reason.strip()}

    def append_review(self, *, run_id: str, input_hash: str, reviewer_id: str, action: str,
                      candidate_id: str, artifact_hashes: Mapping[str, str],
                      selected_rewrite_id: str | None = None, edited_text: str | None = None,
                      reason: str = "") -> ReviewEvent:
        if action not in REVIEW_ACTIONS:
            raise ValueError("unsupported review action")
        if action == "edit" and not (edited_text or "").strip():
            raise ValueError("edit requires new text")
        payload = self._base(run_id, input_hash, reviewer_id, action, artifact_hashes, reason)
        payload.update(candidate_id=candidate_id, selected_rewrite_id=selected_rewrite_id,
                       edited_text=edited_text)
        return ReviewEvent(**self._append(payload))

    def append_control(self, *, run_id: str, input_hash: str, reviewer_id: str, action: str,
                       artifact_hashes: Mapping[str, str], reason: str = "") -> ControlEvent:
        if action not in CONTROL_ACTIONS:
            raise ValueError("unsupported control action")
        if action in {"approve_external_inference", "approve_release"} and not reason.strip():
            raise PermissionError(f"{action} requires a recorded reason")
        payload = self._base(run_id, input_hash, reviewer_id, action, artifact_hashes, reason)
        return ControlEvent(**self._append(payload))
