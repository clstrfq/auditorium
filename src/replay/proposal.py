from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping


def build_replay_proposal(*, run_id: str, input_hash: str,
                          adjudicated_cases: Iterable[Mapping[str, Any]],
                          created_at: str) -> dict[str, Any]:
    cases = []
    for case in adjudicated_cases:
        required = {"item_id", "source_artifact_hash", "adjudication_event_id", "adjudicator_id", "expected"}
        missing = sorted(required - case.keys())
        if missing:
            raise ValueError(f"replay case missing provenance: {', '.join(missing)}")
        cases.append(dict(case))
    cases.sort(key=lambda row: (str(row["item_id"]), str(row["adjudication_event_id"])))
    value = {"schema_version": "1.0.0", "run_id": run_id, "created_at": created_at,
             "producer_version": "m5-replay-1.0.0", "input_hash": input_hash,
             "status": "proposed", "promotion_approved": False, "cases": cases}
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    value["proposal_hash"] = hashlib.sha256(encoded).hexdigest()
    return value
