from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


class RunStore:
    """Filesystem state with atomic mutable views and immutable successful runs."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def run_dir(self, run_id: str) -> Path:
        return self.root / "runs" / run_id

    def successful_receipt(self, fingerprint: str) -> dict[str, Any] | None:
        pointer = self.root / "receipts" / f"{fingerprint}.json"
        if not pointer.exists():
            return None
        return json.loads(pointer.read_text(encoding="utf-8"))

    def checkpoint(self, run_id: str) -> dict[str, Any] | None:
        path = self.run_dir(run_id) / "checkpoint.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def write_checkpoint(self, run_id: str, value: dict[str, Any]) -> None:
        atomic_json(self.run_dir(run_id) / "checkpoint.json", value)

    def set_control(self, run_id: str, action: str) -> dict[str, Any]:
        if action not in {"running", "paused", "cancelled"}:
            raise ValueError("control action must be running, paused, or cancelled")
        checkpoint = self.checkpoint(run_id) or {}
        value = {"schema_version": checkpoint.get("schema_version", "1.0.0"), "run_id": run_id,
                 "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                 "producer_version": checkpoint.get("producer_version", "m1-1.0.0"),
                 "input_hash": checkpoint.get("input_hash", "unknown"), "status": action}
        atomic_json(self.run_dir(run_id) / "control.json", value)
        return value

    def control(self, run_id: str) -> str:
        path = self.run_dir(run_id) / "control.json"
        return json.loads(path.read_text(encoding="utf-8"))["status"] if path.exists() else "running"

    def record_success(self, fingerprint: str, receipt: dict[str, Any]) -> None:
        path = self.root / "receipts" / f"{fingerprint}.json"
        if path.exists():
            return
        atomic_json(path, receipt)
