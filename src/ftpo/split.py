from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable

from .schema import validate_example


LEAKAGE_FIELDS = ("pattern_id", "source_item_id", "prompt_id", "author_cluster_id")


@dataclass(frozen=True)
class SplitConfig:
    seed: int = 20260712
    train_fraction: float = 0.8
    validation_fraction: float = 0.1

    def __post_init__(self) -> None:
        if not (0 < self.train_fraction < 1):
            raise ValueError("train_fraction must be between zero and one")
        if not (0 <= self.validation_fraction < 1 - self.train_fraction):
            raise ValueError("validation_fraction leaves no holdout")


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def split_examples(examples: Iterable[dict[str, Any]], config: SplitConfig = SplitConfig()) -> dict[str, Any]:
    records = list(examples)
    if not records:
        raise ValueError("cannot split an empty dataset")
    seen_ids: set[str] = set()
    for record in records:
        validate_example(record)
        if record["example_id"] in seen_ids:
            raise ValueError(f"duplicate example_id: {record['example_id']}")
        seen_ids.add(record["example_id"])

    uf = _UnionFind(len(records))
    owners: dict[tuple[str, str], int] = {}
    for index, record in enumerate(records):
        for field in LEAKAGE_FIELDS:
            key = (field, record[field])
            if key in owners:
                uf.union(index, owners[key])
            else:
                owners[key] = index

    components: dict[int, list[int]] = {}
    for index in range(len(records)):
        components.setdefault(uf.find(index), []).append(index)

    assignments: dict[str, str] = {}
    component_receipts: list[dict[str, Any]] = []
    train_edge = config.train_fraction
    validation_edge = train_edge + config.validation_fraction
    for indices in components.values():
        identity = "|".join(sorted(records[i]["example_id"] for i in indices))
        score = int(_digest(f"{config.seed}:{identity}")[:16], 16) / float(0xFFFFFFFFFFFFFFFF)
        split = "train" if score < train_edge else "validation" if score < validation_edge else "holdout"
        for index in indices:
            assignments[records[index]["example_id"]] = split
        component_receipts.append({"component_sha256": _digest(identity), "size": len(indices), "split": split})

    output = {name: [] for name in ("train", "validation", "holdout")}
    for record in sorted(records, key=lambda item: item["example_id"]):
        output[assignments[record["example_id"]]].append(record)

    canonical = "\n".join(json.dumps(item, sort_keys=True, separators=(",", ":")) for item in
                          sorted(records, key=lambda item: item["example_id"]))
    return {
        "schema_version": "1.0.0",
        "seed": config.seed,
        "leakage_fields": list(LEAKAGE_FIELDS),
        "input_sha256": _digest(canonical),
        "counts": {name: len(items) for name, items in output.items()},
        "component_count": len(components),
        "components": sorted(component_receipts, key=lambda item: item["component_sha256"]),
        "assignments": dict(sorted(assignments.items())),
        "splits": output,
    }
