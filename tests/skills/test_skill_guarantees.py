"""Tests for the skill guarantee linter and the Claude skill generator.

The linter is the thing that enforces the design contract, so it is tested
harder than the skills it checks: a linter that silently passes everything is
worse than no linter. Several cases here are regressions for false results the
linter produced while it was being built.
"""

from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from scripts.generate_claude_skills import GenerateError, convert, generate
from scripts.lint_skills import GUARANTEE_IDS, SkillLintError, lint_all, lint_text

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "skills"

_COMPLIANT = """---
name: example-skill
description: An example skill that carries every guarantee.
---

# Example Skill

## Workflow

### Step 1 — Elicit inputs
Ask the user for what is missing.

### Step 2 — Analyze
Do the analysis.

### Step 3 — Decide
Choose an approach.

### Step 4 — Specify
Write the specification.

### Step 5 — Write the artifact
Write to the canonical path `./agentic-artifacts/example.md`.

### Step 6 — Self-verify
Check the written file and report pass/fail.

## Output template

```markdown
# Example
<!-- artifact-id: example | schema: v1 -->

## Change log
- v1 (YYYY-MM-DD): initial

## Next steps
Optional downstream skills (each works without them):
- other-skill — does another thing
```

## Idempotency contract

- **Unchanged inputs → identical output.** Byte-identical file, same IDs, no new change-log entry.
- **Changed inputs → in-place update.** Same `EX-NNN` ID; update in place. Never write `example-v2.md` or any duplicate.
- Always read the existing file first to recover IDs.

## Standalone operation and bridges

This skill runs fully standalone: Step 1 elicits its own inputs.

**Bridges in (optional, opt-in):** `./agentic-artifacts/other.md`. Use it only if it exists at that canonical path **and** the user confirms.

**Bridges out (optional, opt-in):** the `## Next steps` block offers `other-skill`. Offer, never auto-run. The deliverable is complete if every bridge is declined.
"""


def _without(section: str) -> str:
    """Return the compliant skill with one section's heading renamed away."""

    return _COMPLIANT.replace(f"## {section}", f"## Removed {section}")


# --------------------------------------------------------------------------
# Linter: it must pass what is compliant
# --------------------------------------------------------------------------


def test_compliant_skill_passes_every_guarantee() -> None:
    result = lint_text(_COMPLIANT, Path("example/SKILL.md"))
    assert result["pass"], result["failures"]
    assert set(result["guarantees"]) == set(GUARANTEE_IDS)


def test_skill_name_is_read_from_frontmatter() -> None:
    assert lint_text(_COMPLIANT, Path("x/SKILL.md"))["skill"] == "example-skill"


# --------------------------------------------------------------------------
# Linter: it must fail what is not (a linter that only passes is useless)
# --------------------------------------------------------------------------


def test_missing_frontmatter_is_rejected() -> None:
    with pytest.raises(SkillLintError, match="frontmatter"):
        lint_text("# No frontmatter\n", Path("x/SKILL.md"))


def test_too_few_steps_fails() -> None:
    text = _COMPLIANT.replace("### Step 5 — Write the artifact", "#### Step 5 — Write the artifact")
    text = text.replace("### Step 6 — Self-verify", "#### Step 6 — Self-verify")
    result = lint_text(text, Path("x/SKILL.md"))
    assert "workflow_steps" in result["failures"]


def test_non_consecutive_steps_fail() -> None:
    text = _COMPLIANT.replace("### Step 4 — Specify", "### Step 9 — Specify")
    assert "workflow_steps" in lint_text(text, Path("x/SKILL.md"))["failures"]


def test_final_step_that_is_not_self_verification_fails() -> None:
    text = _COMPLIANT.replace("### Step 6 — Self-verify", "### Step 6 — Ship it")
    assert "self_verification" in lint_text(text, Path("x/SKILL.md"))["failures"]


def test_missing_output_template_fails() -> None:
    assert "file_based_outputs" in lint_text(_without("Output template"), Path("x/SKILL.md"))["failures"]


def test_missing_artifact_id_marker_fails() -> None:
    text = _COMPLIANT.replace("<!-- artifact-id: example | schema: v1 -->", "")
    assert "file_based_outputs" in lint_text(text, Path("x/SKILL.md"))["failures"]


def test_missing_idempotency_section_fails() -> None:
    result = lint_text(_without("Idempotency contract"), Path("x/SKILL.md"))
    assert "idempotency_contract" in result["failures"]


def test_idempotency_without_duplicate_ban_fails() -> None:
    text = _COMPLIANT.replace("Never write `example-v2.md` or any duplicate.", "")
    assert "idempotency_contract" in lint_text(text, Path("x/SKILL.md"))["failures"]


def test_missing_bridges_section_fails() -> None:
    result = lint_text(_without("Standalone operation and bridges"), Path("x/SKILL.md"))
    assert "standalone_and_bridges" in result["failures"]


def test_bridges_without_opt_in_language_fails() -> None:
    text = _COMPLIANT.replace("(optional, opt-in)", "").replace(
        "Use it only if it exists at that canonical path **and** the user confirms.", ""
    )
    assert "standalone_and_bridges" in lint_text(text, Path("x/SKILL.md"))["failures"]


def test_missing_next_steps_block_fails() -> None:
    text = _COMPLIANT.replace("## Next steps", "## Follow-ups")
    assert "standalone_and_bridges" in lint_text(text, Path("x/SKILL.md"))["failures"]


def test_wholly_broken_skill_fails_every_guarantee() -> None:
    text = "---\nname: broken\ndescription: broken\n---\n# Broken\n### Step 1 — go\n"
    result = lint_text(text, Path("x/SKILL.md"))
    assert sorted(result["failures"]) == sorted(GUARANTEE_IDS)


# --------------------------------------------------------------------------
# Linter: regressions for false results found during development
# --------------------------------------------------------------------------


def test_duplicate_ban_is_detected_regardless_of_verb() -> None:
    # Regression: the check once matched only the literal verb "write", so
    # "Never emit ... duplicates" was wrongly reported as a violation.
    for verb in ("write", "emit", "create", "produce"):
        text = _COMPLIANT.replace(
            "Never write `example-v2.md` or any duplicate.",
            f"Never {verb} `example-v2.md` or any duplicate.",
        )
        assert lint_text(text, Path("x/SKILL.md"))["pass"], verb


def test_duplicate_ban_survives_filenames_containing_dots() -> None:
    # Regression: a character class excluding '.' broke on "report-v2.md".
    text = _COMPLIANT.replace(
        "Never write `example-v2.md` or any duplicate.",
        "Never write `example-v2.md`, `receipt (1).json`, or any duplicate file.",
    )
    assert lint_text(text, Path("x/SKILL.md"))["pass"]


# --------------------------------------------------------------------------
# Linter: reporting and the real repository
# --------------------------------------------------------------------------


def test_lint_all_reports_counts_and_is_deterministic(tmp_path: Path) -> None:
    (tmp_path / "good").mkdir()
    (tmp_path / "good" / "SKILL.md").write_text(_COMPLIANT, encoding="utf-8")
    first = lint_all([tmp_path])
    second = lint_all([tmp_path])
    assert first == second
    assert first["status"] == "pass"
    assert first["skill_count"] == 1 and first["fail_count"] == 0
    assert first["external_effects"]["network_calls"] == 0


def test_lint_all_marks_status_fail_when_any_skill_fails(tmp_path: Path) -> None:
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "SKILL.md").write_text(
        "---\nname: bad\ndescription: bad\n---\n# Bad\n", encoding="utf-8"
    )
    assert lint_all([tmp_path])["status"] == "fail"


def test_every_shipped_skill_carries_all_five_guarantees() -> None:
    report = lint_all([SKILL_DIR])
    failures = {result["skill"]: result["failures"] for result in report["results"] if not result["pass"]}
    assert report["skill_count"] >= 6
    assert not failures, f"skills missing guarantees: {failures}"


# --------------------------------------------------------------------------
# Claude skill generator
# --------------------------------------------------------------------------


def test_convert_rewrites_only_the_host_banner() -> None:
    source = (
        "---\nname: x\ndescription: d\n---\n\n# X\n\n"
        "> **Codex skill.** Install this file as `~/.codex/skills/x/SKILL.md`.\n\n"
        "Body stays exactly the same.\n"
    )
    converted = convert(source, "x")
    assert "**Claude skill.**" in converted
    assert "**Codex skill.**" not in converted
    assert "~/.claude/skills/x/SKILL.md" in converted
    assert "Body stays exactly the same." in converted


def test_convert_refuses_a_source_without_a_banner() -> None:
    with pytest.raises(GenerateError, match="no Codex banner"):
        convert("---\nname: x\ndescription: d\n---\n\n# X\n", "x")


def test_generated_claude_skills_differ_from_source_only_in_the_banner() -> None:
    for package in sorted((ROOT / "chatgpt-skill-packages").glob("*.skill")):
        name = package.stem
        with zipfile.ZipFile(package) as archive:
            source = archive.read(f"{name}/SKILL.md").decode("utf-8")
        generated = (SKILL_DIR / name / "SKILL.md").read_text(encoding="utf-8")
        strip = lambda text: [line for line in text.splitlines() if not line.startswith("> ")]  # noqa: E731
        assert strip(source) == strip(generated), name
        assert "**Claude skill.**" in generated


def test_generation_is_idempotent() -> None:
    # The skills are already generated in the repository; regenerating must be
    # a true no-op rather than rewriting identical bytes.
    report = generate(package=True)
    statuses = {entry["skill_status"] for entry in report["results"]}
    statuses |= {entry["package_status"] for entry in report["results"]}
    assert statuses == {"unchanged"}
    assert report["status"] == "unchanged"


def test_generator_reports_no_external_effects() -> None:
    assert generate(package=True)["external_effects"] == {
        "network_calls": 0,
        "secrets_accessed": 0,
        "remote_jobs_submitted": 0,
        "external_spend_usd": 0,
    }
