"""End-to-end checks driven through the public launcher.

Stdlib-only by design.  The README tells a new user to verify this repository
with ``python3 -m unittest discover -s tests/e2e``; that command has to work on
a fresh checkout with nothing installed, or the harness cannot honestly ask an
app to trust its receipts.  The engine itself has no runtime dependencies, and
its verification should not quietly acquire one.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "harness"
PACKET_FILES = {
    "review.md",
    "results.jsonl",
    "summary.json",
    "receipt.json",
    "canonical-input.jsonl",
}
FAKE_SECRETS = {
    "OPENAI_API_KEY": "test-openai-key-must-not-be-used",
    "ANTHROPIC_API_KEY": "test-anthropic-key-must-not-be-used",
    "DEEPSEEK_API_KEY": "test-deepseek-key-must-not-be-used",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(
    *arguments: str | Path,
    cwd: Path,
    home: Path,
    expected_code: int | None = 0,
) -> subprocess.CompletedProcess[str]:
    """Invoke the public launcher as a user would, isolated from their home."""

    env = os.environ.copy()
    env.update(FAKE_SECRETS)
    env.update(
        {
            "HOME": str(home),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        }
    )
    completed = subprocess.run(
        [str(HARNESS), *(str(value) for value in arguments)],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if expected_code is not None:
        assert completed.returncode == expected_code, completed.stderr or completed.stdout
    combined = completed.stdout + completed.stderr
    for secret in FAKE_SECRETS.values():
        assert secret not in combined
    return completed


def _json_stdout(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    """Require JSON mode to emit exactly one object and no prose."""

    value = json.loads(completed.stdout)
    assert isinstance(value, dict)
    return value


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        assert isinstance(value, dict)
        rows.append(value)
    return rows


def _assert_packet(output: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    assert PACKET_FILES <= {path.name for path in output.iterdir() if path.is_file()}
    assert (output / "review.md").read_text(encoding="utf-8").strip()
    receipt = _read_json(output / "receipt.json")
    summary = _read_json(output / "summary.json")
    results = _read_jsonl(output / "results.jsonl")
    canonical = _read_jsonl(output / "canonical-input.jsonl")

    assert receipt["status"] == "complete"
    assert isinstance(receipt["run_id"], str) and receipt["run_id"]
    assert receipt["summary"] == summary
    assert canonical
    assert re.fullmatch(r"[0-9a-f]{64}", receipt["input"]["source_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", receipt["input"]["adapted_sha256"])
    assert receipt["input"]["row_count"] == len(canonical)
    assert re.fullmatch(r"[0-9a-f]{64}", receipt["packet_hash"])
    assert all(value == 0 for value in receipt["external_effects"].values())
    return receipt, results


def _without_volatile_fields(value: Any) -> Any:
    """Remove diagnostics that do not define replay identity."""

    if isinstance(value, list):
        return [_without_volatile_fields(item) for item in value]
    if not isinstance(value, dict):
        return value
    volatile_fragments = ("timestamp", "created_at", "updated_at", "generated_at", "duration", "elapsed")
    return {
        key: _without_volatile_fields(item)
        for key, item in value.items()
        if not any(fragment in key.casefold() for fragment in volatile_fragments)
    }


def _packet_identity(output: Path) -> dict[str, Any]:
    return {
        "canonical": _without_volatile_fields(_read_jsonl(output / "canonical-input.jsonl")),
        "results": _without_volatile_fields(_read_jsonl(output / "results.jsonl")),
        "summary": _without_volatile_fields(_read_json(output / "summary.json")),
        "receipt": _without_volatile_fields(_read_json(output / "receipt.json")),
    }


class HarnessTestCase(unittest.TestCase):
    """Every test runs from an unrelated cwd and an empty home."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.cwd = self.tmp / "unrelated-working-directory"
        self.home = self.tmp / "empty-home"
        self.cwd.mkdir(parents=True)
        self.home.mkdir(parents=True)


class TestLauncherIsReadOnlyBeforeWork(HarnessTestCase):
    def test_help_is_location_independent(self) -> None:
        completed = _run("--help", cwd=self.cwd, home=self.home)

        assert "analyze" in completed.stdout
        assert "demo" in completed.stdout
        assert "status" in completed.stdout
        assert "install" in completed.stdout
        assert list(self.cwd.iterdir()) == []

    def test_status_is_machine_readable_and_read_only(self) -> None:
        markers = (ROOT / "pipeline" / "state.json", ROOT / "pipeline" / "BUILD_COMPLETE")
        before = {str(path): (_sha256(path), path.stat().st_mtime_ns) for path in markers}

        payload = _json_stdout(_run("status", "--json", cwd=self.cwd, home=self.home))

        assert payload
        assert payload.get("status") not in {"error", "failed", "blocked"}
        after = {str(path): (_sha256(path), path.stat().st_mtime_ns) for path in markers}
        assert after == before
        assert list(self.cwd.iterdir()) == []


class TestAnalysisProducesInspectablePackets(HarnessTestCase):
    def test_demo_writes_a_complete_inspectable_packet(self) -> None:
        output = self.cwd / "demo-packet"

        response = _json_stdout(_run("demo", "--output", output, "--json", cwd=self.cwd, home=self.home))
        receipt, results = _assert_packet(output)

        assert response["status"] == "complete"
        assert response["run_id"] == receipt["run_id"]
        assert receipt["summary"]["item_count"] >= 1
        assert receipt["summary"]["finding_count"] == len(results)

    def test_analyze_reports_harmful_finding_with_verified_suggestion(self) -> None:
        source = self.cwd / "release-note.txt"
        original = b"This is not a feature, but a revolution.\n"
        source.write_bytes(original)
        output = self.cwd / "review-packet"

        _json_stdout(_run("analyze", source, "--output", output, "--json", cwd=self.cwd, home=self.home))
        receipt, results = _assert_packet(output)

        harmful = [row for row in results if row["classification"]["label"] == "harmful"]
        assert harmful
        verified = [
            suggestion
            for row in harmful
            for suggestion in row["suggestions"]
            if suggestion["decision"] == "verified"
        ]
        assert verified
        assert all(suggestion["rewrite_text"].strip() for suggestion in verified)
        assert all(not suggestion["blocking_reasons"] for suggestion in verified)
        assert receipt["summary"]["harmful"] >= 1
        assert receipt["summary"]["verified_suggestion_count"] >= 1
        assert not (output / "suggested.md").exists()
        assert not (output / "suggested.txt").exists()
        assert source.read_bytes() == original

    def test_clean_text_has_zero_findings_and_preserves_source(self) -> None:
        source = self.cwd / "clean.md"
        original = b"The update improves page loading speed.\n"
        source.write_bytes(original)
        output = self.cwd / "clean-packet"

        _json_stdout(_run("analyze", source, "--output", output, "--json", cwd=self.cwd, home=self.home))
        receipt, results = _assert_packet(output)

        assert results == []
        assert receipt["summary"]["finding_count"] == 0
        assert receipt["summary"]["harmful"] == 0
        assert receipt["summary"]["legitimate"] == 0
        assert receipt["summary"]["uncertain"] == 0
        assert source.read_bytes() == original

    def test_analyze_supports_documented_input_formats(self) -> None:
        cases = [
            ("notes.txt", "The update improves page loading speed.\n"),
            ("notes.md", "# Release\n\nThe update improves page loading speed.\n"),
            ("notes.csv", 'item_id,text\nrow-1,"The update improves page loading speed."\n'),
            (
                "notes.jsonl",
                json.dumps({"item_id": "row-1", "text": "The update improves page loading speed."}) + "\n",
            ),
        ]
        for name, content in cases:
            with self.subTest(name=name):
                case_dir = self.cwd / f"case-{name.replace('.', '-')}"
                case_dir.mkdir()
                source = case_dir / name
                source.write_text(content, encoding="utf-8")
                source_hash = _sha256(source)
                output = case_dir / "packet"

                _json_stdout(
                    _run("analyze", source, "--output", output, "--json", cwd=self.cwd, home=self.home)
                )
                receipt, _ = _assert_packet(output)

                assert receipt["input"]["row_count"] >= 1
                assert receipt["input"]["format"].casefold().lstrip(".") == source.suffix.casefold().lstrip(".")
                assert _sha256(source) == source_hash

    def test_empty_or_malformed_input_fails_without_a_success_packet(self) -> None:
        cases = [
            ("empty.txt", ""),
            ("malformed.jsonl", '{"item_id":"row-1","text":\n'),
        ]
        for name, content in cases:
            with self.subTest(name=name):
                case_dir = self.cwd / f"bad-{name.replace('.', '-')}"
                case_dir.mkdir()
                source = case_dir / name
                source.write_text(content, encoding="utf-8")
                before = source.read_bytes()
                output = case_dir / "failed-packet"

                completed = _run(
                    "analyze", source, "--output", output, "--json",
                    cwd=self.cwd, home=self.home, expected_code=None,
                )
                payload = _json_stdout(completed)

                assert completed.returncode != 0
                assert (
                    payload.get("status") in {"error", "failed", "blocked"}
                    or payload.get("ok") is False
                    or bool(payload.get("error"))
                )
                if (output / "receipt.json").exists():
                    assert _read_json(output / "receipt.json").get("status") != "complete"
                assert source.read_bytes() == before

    def test_repeated_analysis_is_content_idempotent(self) -> None:
        source = self.cwd / "copy.txt"
        source.write_text("It is not merely a dashboard, but a decision tool.\n", encoding="utf-8")
        output = self.cwd / "packet"

        first = _json_stdout(_run("analyze", source, "--output", output, "--json", cwd=self.cwd, home=self.home))
        first_identity = _packet_identity(output)
        first_files = sorted(path.relative_to(output) for path in output.rglob("*") if path.is_file())
        second = _json_stdout(_run("analyze", source, "--output", output, "--json", cwd=self.cwd, home=self.home))
        second_identity = _packet_identity(output)
        second_files = sorted(path.relative_to(output) for path in output.rglob("*") if path.is_file())

        assert first["run_id"] == second["run_id"]
        assert first_identity == second_identity
        assert first_files == second_files
        assert _read_json(output / "receipt.json")["packet_hash"] == first_identity["receipt"]["packet_hash"]


class TestProjectInstall(HarnessTestCase):
    def test_project_install_creates_contract_launcher_and_both_agent_skills(self) -> None:
        target = self.cwd / "sample app"

        response = _json_stdout(_run("install", target, "--json", cwd=self.cwd, home=self.home))

        contract_path = target / ".app-harness" / "contract.json"
        launcher = target / "tools" / "app-harness"
        codex_skill = target / ".codex" / "skills" / "apply-app-harness" / "SKILL.md"
        claude_skill = target / ".claude" / "skills" / "apply-app-harness" / "SKILL.md"
        assert response["status"] in {"complete", "installed", "unchanged"}
        assert contract_path.is_file()
        assert launcher.is_file() and os.access(launcher, os.X_OK)
        assert codex_skill.is_file()
        assert claude_skill.is_file()
        assert codex_skill.read_bytes() == claude_skill.read_bytes()

        contract = _read_json(contract_path)
        assert {".txt", ".md", ".csv", ".jsonl"} <= set(contract["accepted_text_formats"])
        assert contract["source_files"]["preserve_originals"] is True
        assert contract["source_files"]["mutate_in_place"] is False
        assert all(value in {False, 0} for value in contract["default_effects"].values())
        assert contract["installation"]["default_review_root"] == ".app-harness/reviews"
        # Contract 1.2.0: project_root is relative to the contract's own
        # directory rather than frozen absolute at install time, so it still
        # resolves after the project is moved.
        assert contract["installation"]["project_root"] == ".."
        assert (contract_path.parent / contract["installation"]["project_root"]).resolve() == target.resolve()

        installed_help = subprocess.run(
            [str(launcher), "--help"],
            cwd=target,
            env={
                **os.environ,
                **FAKE_SECRETS,
                "HOME": str(self.home),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        assert installed_help.returncode == 0, installed_help.stderr
        assert "analyze" in installed_help.stdout
        assert all(secret not in installed_help.stdout + installed_help.stderr for secret in FAKE_SECRETS.values())

        installed_status = subprocess.run(
            [str(launcher), "status"],
            cwd=target,
            env={**os.environ, "HOME": str(self.home), "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        assert installed_status.returncode == 0, installed_status.stderr
        assert "Next: ./tools/app-harness demo" in installed_status.stdout

        source = target / "release.md"
        original = b"This is not just a dashboard, but a direct decision tool.\n"
        source.write_bytes(original)
        installed_analysis = subprocess.run(
            [str(launcher), "analyze", str(source), "--json"],
            cwd=target,
            env={
                **os.environ,
                **FAKE_SECRETS,
                "HOME": str(self.home),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        assert installed_analysis.returncode == 0, installed_analysis.stderr
        installed_payload = _json_stdout(installed_analysis)
        expected_output = target / ".app-harness" / "reviews" / "release"
        # macOS may spell the same temporary directory as /var/... or
        # /private/var/... depending on whether a shell resolved the symlink.
        assert Path(installed_payload["output"]).resolve() == expected_output.resolve()
        _assert_packet(expected_output)
        assert source.read_bytes() == original


if __name__ == "__main__":
    unittest.main()
