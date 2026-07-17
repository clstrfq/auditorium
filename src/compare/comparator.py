from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping


def compare_runs(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    left_ids, right_ids = set(left["item_ids"]), set(right["item_ids"])
    exclusions = {"left_only": sorted(left_ids - right_ids), "right_only": sorted(right_ids - left_ids)}
    policy_match = left.get("policy_version") == right.get("policy_version")
    corpus_match = left.get("corpus_hash") == right.get("corpus_hash")
    if not policy_match or not corpus_match or left_ids != right_ids:
        reasons = []
        if not policy_match:
            reasons.append("metric_policy_mismatch")
        if not corpus_match:
            reasons.append("corpus_mismatch")
        if left_ids != right_ids:
            reasons.append("normalized_item_id_mismatch")
        return {"comparison_type": "blocked", "paired": False, "reasons": reasons,
                "exclusions": exclusions, "metrics": []}
    lm = {m["metric_id"]: m for m in left["metrics"]}
    rm = {m["metric_id"]: m for m in right["metrics"]}
    common = sorted(set(lm) & set(rm))
    rows = []
    for metric_id in common:
        a, b = lm[metric_id], rm[metric_id]
        if a["unit"] != b["unit"] or a["policy_version"] != b["policy_version"]:
            return {"comparison_type": "blocked", "paired": False,
                    "reasons": [f"metric_contract_mismatch:{metric_id}"],
                    "exclusions": exclusions, "metrics": []}
        rows.append({"metric_id": metric_id, "left": a["value"], "right": b["value"],
                     "delta": None if a["value"] is None or b["value"] is None else
                     str(Decimal(b["value"]) - Decimal(a["value"])), "unit": a["unit"],
                     "policy_version": a["policy_version"]})
    return {"comparison_type": "paired", "paired": True, "reasons": [],
            "exclusions": exclusions, "metrics": rows}
