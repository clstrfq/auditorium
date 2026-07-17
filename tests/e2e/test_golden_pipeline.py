from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import shutil

from scripts.run_prototype import run
from src.ingest.pipeline import ForbiddenDestinationError


ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "fixtures" / "corpora" / "golden.jsonl"


class GoldenPipelineTests(unittest.TestCase):
    def test_all_modules_connect_and_no_implicit_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run(GOLDEN, Path(tmp))
        self.assertTrue(result["ledger_verified"])
        self.assertEqual(result["comparison_probe"]["comparison_type"], "blocked")
        self.assertIsNone(result["release_receipt"])
        self.assertEqual(result["summary"]["item_ids"], ["harmful-1", "legitimate-1", "uncertain-1"])
        self.assertEqual(result["summary"]["metrics"][0]["denominator"], 3)

    def test_identical_run_resumes_without_duplicate_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = run(GOLDEN, Path(tmp))
            second = run(GOLDEN, Path(tmp))
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual(first["summary"]["item_ids"], second["summary"]["item_ids"])
        self.assertEqual(first["ledger_event_count"], second["ledger_event_count"])

    def test_release_requires_explicit_fixture_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "approved.jsonl"
            shutil.copyfile(GOLDEN, fixture)
            fixture.with_name("approved.events.jsonl").write_text(
                json.dumps({"action": "approve_release", "reviewer_id": "release-manager",
                            "reason": "Fixture gate intentionally approved."}) + "\n", encoding="utf-8")
            result = run(fixture, root / "workspace")
        self.assertEqual(result["release_receipt"]["status"], "release_approved")
        self.assertEqual(result["release_receipt"]["approved_by"], "release-manager")

    def test_external_inference_is_denied_before_processing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ForbiddenDestinationError):
                run(GOLDEN, Path(tmp), destination="https://external.invalid")
            self.assertFalse((Path(tmp) / "runs").exists())

    def test_cli_dry_run_is_machine_readable(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_prototype.py"),
             "--fixture", str(GOLDEN), "--dry-run"], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIsNone(json.loads(completed.stdout)["release_receipt"])


if __name__ == "__main__":
    unittest.main()
