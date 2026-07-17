from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from src.ftpo import validate_example


ROOT = Path(__file__).resolve().parents[2]


def test_s0_generator_is_deterministic_and_nonempirical(tmp_path: Path) -> None:
    left, right = tmp_path / "left", tmp_path / "right"
    command = [sys.executable, str(ROOT / "scripts/generate_synthetic_ftpo.py")]
    subprocess.run(command + [str(left), "--components-per-family", "2"], check=True, cwd=ROOT)
    subprocess.run(command + [str(right), "--components-per-family", "2"], check=True, cwd=ROOT)
    assert (left / "all.jsonl").read_bytes() == (right / "all.jsonl").read_bytes()
    manifest = json.loads((left / "dataset-manifest.json").read_text())
    assert manifest["tier"] == "S0_STRUCTURAL_FIXTURE"
    assert manifest["evidence_class"] == "SYNTHETIC_NONEMPIRICAL"
    assert "weight updates" in manifest["forbidden_uses"]
    records = [json.loads(line) for line in (left / "all.jsonl").read_text().splitlines()]
    assert len(records) == 8 * 2 * 3
    for item in records:
        validate_example(item)
        assert item["source_item_id"].startswith("synthetic/")
