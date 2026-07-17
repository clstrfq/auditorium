from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ftpo import SplitConfig, split_examples


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and leakage-safely split FTPO JSONL data.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=20260712)
    args = parser.parse_args()
    examples = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = split_examples(examples, SplitConfig(seed=args.seed))
    args.output.mkdir(parents=True, exist_ok=True)
    split_hashes: dict[str, str] = {}
    for name, records in result.pop("splits").items():
        payload = "".join(json.dumps(record, sort_keys=True) + "\n" for record in records)
        (args.output / f"{name}.jsonl").write_text(payload, encoding="utf-8")
        split_hashes[name] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    result["split_sha256"] = split_hashes
    result["bundle_sha256"] = hashlib.sha256(
        json.dumps(split_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    (args.output / "split-receipt.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
