#!/usr/bin/env python3
"""Mechanically verify that every SKILL.md carries the five design guarantees.

The guarantees are a contract, so they are checked by a program rather than by
reading.  A guarantee that is only asserted in prose is not a guarantee.

Checked for each skill:

1. **Workflow** — at least five explicit, ordered ``### Step N`` headings.
2. **File-based outputs** — a canonical output path and an output template.
3. **Self-verification** — the final workflow step is a self-verify step.
4. **Idempotency contract** — an explicit section covering both the
   unchanged-inputs and changed-inputs halves, plus a no-duplicate-files rule.
5. **Standalone operation and bridges** — an explicit section declaring
   standalone operation, opt-in bridges in and out, and a ``## Next steps``
   block in the output template.

Exit status is 0 when every skill passes and 1 when any check fails, so the
linter can gate a build.  It reads files only: no network, no secrets, no spend.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable

# Ordered so a report reads in the same order as the guarantee list.
GUARANTEE_IDS = (
    "workflow_steps",
    "file_based_outputs",
    "self_verification",
    "idempotency_contract",
    "standalone_and_bridges",
)

MINIMUM_STEPS = 5
_STEP_RE = re.compile(r"^###\s+Step\s+(\d+)\s*[—:-]?\s*(.*)$", re.MULTILINE)
_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


class SkillLintError(ValueError):
    """Raised when a skill file cannot be read as a skill at all."""


def _sections(text: str) -> set[str]:
    return {match.strip().lower() for match in re.findall(r"^##\s+(.+)$", text, re.MULTILINE)}


def _steps(text: str) -> list[tuple[int, str]]:
    return [(int(number), title.strip()) for number, title in _STEP_RE.findall(text)]


def _section_body(text: str, heading: str) -> str:
    """Return the body of a level-2 section, or an empty string if absent."""

    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(text)
    return match.group(1) if match else ""


def _check_workflow_steps(text: str) -> tuple[bool, str]:
    steps = _steps(text)
    if len(steps) < MINIMUM_STEPS:
        return False, f"found {len(steps)} explicit '### Step N' headings; need at least {MINIMUM_STEPS}"
    numbers = [number for number, _ in steps]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        return False, f"steps are not consecutively numbered from 1: {numbers}"
    return True, f"{len(steps)} explicit, consecutively numbered steps"


def _check_file_based_outputs(text: str) -> tuple[bool, str]:
    reasons: list[str] = []
    # _sections() yields heading text without the leading '##'.
    if "output template" not in _sections(text):
        reasons.append("no '## Output template' section")
    # A canonical path the artifact is written to, e.g. ./agentic-artifacts/x.md
    if not re.search(r"`\.{0,2}/?[\w./-]+\.(md|json|jsonl)`", text):
        reasons.append("no canonical output file path in backticks")
    if not re.search(r"artifact-id:", text):
        reasons.append("output template has no stable 'artifact-id:' marker")
    if reasons:
        return False, "; ".join(reasons)
    return True, "output template with canonical path and stable artifact-id"


def _check_self_verification(text: str) -> tuple[bool, str]:
    steps = _steps(text)
    if not steps:
        return False, "no workflow steps at all"
    _, final_title = steps[-1]
    if not re.search(r"self[- ]?verif", final_title, re.IGNORECASE):
        return False, f"final step is {final_title!r}, which is not a self-verification step"
    return True, f"final step is {final_title!r}"


def _check_idempotency_contract(text: str) -> tuple[bool, str]:
    body = _section_body(text, "Idempotency contract")
    if not body.strip():
        return False, "no '## Idempotency contract' section"
    reasons: list[str] = []
    if not re.search(r"unchanged", body, re.IGNORECASE):
        reasons.append("does not state the unchanged-inputs rule")
    if not re.search(r"identical", body, re.IGNORECASE):
        reasons.append("does not promise identical output for unchanged inputs")
    if not re.search(r"in[- ]place", body, re.IGNORECASE):
        reasons.append("does not state the changed-inputs in-place update rule")
    # Match the rule, not one verb: "never write/emit/create/produce ... duplicate".
    # '.' does not cross newlines, which keeps the match inside a single bullet;
    # a character class excluding '.' would break on filenames like "report-v2.md".
    if not re.search(r"never\b.{0,160}duplicate", body, re.IGNORECASE):
        reasons.append("does not forbid duplicate files")
    if not re.search(r"\bID\b|IDs", body):
        reasons.append("does not commit to stable IDs")
    if reasons:
        return False, "; ".join(reasons)
    return True, "covers unchanged, changed-in-place, stable IDs, and no duplicates"


def _check_standalone_and_bridges(text: str) -> tuple[bool, str]:
    body = _section_body(text, "Standalone operation and bridges")
    if not body.strip():
        return False, "no '## Standalone operation and bridges' section"
    reasons: list[str] = []
    if not re.search(r"standalone", body, re.IGNORECASE):
        reasons.append("does not declare standalone operation")
    if not re.search(r"bridges in", body, re.IGNORECASE):
        reasons.append("does not declare 'Bridges in'")
    if not re.search(r"bridges out", body, re.IGNORECASE):
        reasons.append("does not declare 'Bridges out'")
    if not re.search(r"opt-in|confirm", body, re.IGNORECASE):
        reasons.append("does not make bridges opt-in / user-confirmed")
    if not re.search(r"declin", body, re.IGNORECASE):
        reasons.append("does not guarantee completeness if bridges are declined")
    if "## next steps" not in text.lower():
        reasons.append("output template has no '## Next steps' block")
    if reasons:
        return False, "; ".join(reasons)
    return True, "standalone, opt-in bridges in/out, complete when declined"


CHECKS: dict[str, Callable[[str], tuple[bool, str]]] = {
    "workflow_steps": _check_workflow_steps,
    "file_based_outputs": _check_file_based_outputs,
    "self_verification": _check_self_verification,
    "idempotency_contract": _check_idempotency_contract,
    "standalone_and_bridges": _check_standalone_and_bridges,
}


def _skill_name(text: str, path: Path) -> str:
    match = _FRONTMATTER_RE.search(text)
    if match:
        name = re.search(r"^name:\s*(.+)$", match.group(1), re.MULTILINE)
        if name:
            return name.group(1).strip()
    return path.parent.name


def lint_text(text: str, path: Path) -> dict[str, Any]:
    """Lint one skill's text and return a machine-readable result."""

    if not _FRONTMATTER_RE.search(text):
        raise SkillLintError(f"{path}: missing YAML frontmatter")

    guarantees: dict[str, Any] = {}
    for identifier in GUARANTEE_IDS:
        passed, detail = CHECKS[identifier](text)
        guarantees[identifier] = {"pass": passed, "detail": detail}
    failures = sorted(key for key, value in guarantees.items() if not value["pass"])
    return {
        "skill": _skill_name(text, path),
        "path": str(path),
        "pass": not failures,
        "failures": failures,
        "guarantees": guarantees,
    }


def lint_file(path: Path) -> dict[str, Any]:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SkillLintError(f"could not read {path}: {exc}") from exc
    return lint_text(text, path)


def discover(roots: list[Path]) -> list[Path]:
    """Find every SKILL.md under the given roots, deterministically ordered."""

    found: set[Path] = set()
    for root in roots:
        root = Path(root)
        if root.is_file() and root.name == "SKILL.md":
            found.add(root.resolve())
        elif root.is_dir():
            found.update(p.resolve() for p in root.rglob("SKILL.md"))
    return sorted(found)


def lint_all(roots: list[Path]) -> dict[str, Any]:
    paths = discover(roots)
    results = [lint_file(path) for path in paths]
    failed = [result for result in results if not result["pass"]]
    return {
        "schema_version": "1.0.0",
        "tool": "lint_skills",
        "guarantees_checked": list(GUARANTEE_IDS),
        "skill_count": len(results),
        "pass_count": len(results) - len(failed),
        "fail_count": len(failed),
        "status": "pass" if not failed and results else ("fail" if failed else "empty"),
        "results": results,
        "external_effects": {
            "network_calls": 0,
            "secrets_accessed": 0,
            "remote_jobs_submitted": 0,
            "external_spend_usd": 0,
        },
    }


def _render(report: dict[str, Any]) -> str:
    lines: list[str] = []
    for result in report["results"]:
        mark = "PASS" if result["pass"] else "FAIL"
        lines.append(f"[{mark}] {result['skill']}  ({result['path']})")
        for identifier in GUARANTEE_IDS:
            guarantee = result["guarantees"][identifier]
            symbol = "ok  " if guarantee["pass"] else "FAIL"
            lines.append(f"    {symbol} {identifier}: {guarantee['detail']}")
    lines.append("")
    lines.append(
        f"{report['pass_count']}/{report['skill_count']} skills carry all "
        f"{len(GUARANTEE_IDS)} guarantees."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lint_skills",
        description="Verify every SKILL.md carries the five design guarantees.",
    )
    parser.add_argument("roots", nargs="*", type=Path, default=[Path("skills")],
                        help="directories or SKILL.md files to lint (default: skills)")
    parser.add_argument("--json", action="store_true", help="emit the machine-readable report")
    parser.add_argument("--receipt", type=Path, help="write the report to this path as JSON")
    args = parser.parse_args(argv)

    try:
        report = lint_all(list(args.roots))
    except SkillLintError as exc:
        print(f"lint_skills could not continue: {exc}", file=sys.stderr)
        return 2

    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_render(report))

    if report["status"] == "empty":
        print("No SKILL.md found.", file=sys.stderr)
        return 2
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
