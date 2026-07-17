#!/usr/bin/env python3
"""Generate Claude skills from the packaged Codex skills in this repository.

The five packaged skills are already host-portable: their workflows, output
templates, idempotency contracts, and bridge declarations contain nothing
Codex-specific.  Only the install banner names a host.  So this generator does
the smallest correct thing — rewrite the banner, keep the body byte-for-byte —
rather than forking five documents that would immediately drift apart.

The generator obeys the same contract as the skills it generates:

* **Unchanged inputs → identical output.**  Re-running writes byte-identical
  files and reports ``unchanged``; nothing is rewritten and no duplicate is
  created.
* **Changed inputs → in-place update.**  A changed source updates the same
  destination path; it never writes ``-v2`` or ``(1)`` variants.
* **Self-verifying.**  Every generated skill is linted against the five design
  guarantees before this script reports success.

It reads and writes local files only: no network, no secrets, no spend.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import re
import sys
from typing import Any
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lint_skills import lint_text  # noqa: E402

SOURCE_DIR = ROOT / "chatgpt-skill-packages"
SKILL_DIR = ROOT / "skills"
PACKAGE_DIR = ROOT / "claude-skill-packages"

_BANNER_RE = re.compile(r"^> \*\*Codex skill\.\*\*.*$", re.MULTILINE)

_CLAUDE_BANNER = (
    "> **Claude skill.** Install this file as "
    "`~/.claude/skills/{name}/SKILL.md` for personal use, or keep it in-repo at "
    "`.claude/skills/{name}/SKILL.md` so the whole project shares it. Invoke it as "
    "`/{name}`. Uses only standard file operations; artifacts are written relative to "
    "the repository root. Makes no network call, reads no secret, and spends nothing."
)


class GenerateError(RuntimeError):
    """Raised when a source skill cannot be converted faithfully."""


def _read_source(package: Path) -> tuple[str, str]:
    """Return ``(skill_name, skill_text)`` from a packaged ``.skill`` archive."""

    try:
        with zipfile.ZipFile(package) as archive:
            members = [name for name in archive.namelist() if name.endswith("SKILL.md")]
            if len(members) != 1:
                raise GenerateError(
                    f"{package.name}: expected exactly one SKILL.md, found {len(members)}"
                )
            text = archive.read(members[0]).decode("utf-8")
    except (zipfile.BadZipFile, OSError) as exc:
        raise GenerateError(f"could not read {package}: {exc}") from exc
    return package.stem, text


def convert(text: str, name: str) -> str:
    """Rewrite the host banner for Claude, leaving every other byte untouched."""

    if not _BANNER_RE.search(text):
        raise GenerateError(
            f"{name}: no Codex banner found; refusing to guess where the host note belongs"
        )
    converted = _BANNER_RE.sub(_CLAUDE_BANNER.format(name=name), text, count=1)
    if "**Codex skill.**" in converted:
        raise GenerateError(f"{name}: more than one Codex banner remained after conversion")
    return converted


def _write_if_changed(path: Path, content: str) -> str:
    """Write only when bytes differ, so re-runs are true no-ops."""

    payload = content.encode("utf-8")
    if path.is_file() and path.read_bytes() == payload:
        return "unchanged"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return "written"


def _package(path: Path, name: str, content: str) -> str:
    """Write a deterministic .skill archive (fixed timestamps → stable bytes).

    The archive is built in memory so an unchanged re-run touches the
    filesystem exactly zero times — no temp file to create, compare, and clean
    up, and therefore no partial state if the process dies mid-run.
    """

    buffer = io.BytesIO()
    info = zipfile.ZipInfo(f"{name}/SKILL.md", date_time=(1980, 1, 1, 0, 0, 0))
    info.external_attr = 0o644 << 16
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(info, content)
    payload = buffer.getvalue()
    if path.is_file() and path.read_bytes() == payload:
        return "unchanged"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return "written"


def generate(*, package: bool = True) -> dict[str, Any]:
    if not SOURCE_DIR.is_dir():
        raise GenerateError(f"source packages not found: {SOURCE_DIR}")
    sources = sorted(SOURCE_DIR.glob("*.skill"))
    if not sources:
        raise GenerateError(f"no .skill packages found in {SOURCE_DIR}")

    results: list[dict[str, Any]] = []
    for source in sources:
        name, text = _read_source(source)
        converted = convert(text, name)

        # Self-verify before writing: never emit a skill that fails the contract.
        destination = SKILL_DIR / name / "SKILL.md"
        lint = lint_text(converted, destination)
        if not lint["pass"]:
            raise GenerateError(
                f"{name}: generated skill fails the design guarantees: {', '.join(lint['failures'])}"
            )

        skill_status = _write_if_changed(destination, converted)
        entry: dict[str, Any] = {
            "skill": name,
            "source": str(source.relative_to(ROOT)),
            "skill_path": str(destination.relative_to(ROOT)),
            "skill_status": skill_status,
            "guarantees_pass": lint["pass"],
        }
        if package:
            archive = PACKAGE_DIR / f"{name}.skill"
            entry["package_path"] = str(archive.relative_to(ROOT))
            entry["package_status"] = _package(archive, name, converted)
        results.append(entry)

    statuses = [entry["skill_status"] for entry in results]
    statuses += [entry["package_status"] for entry in results if "package_status" in entry]
    return {
        "schema_version": "1.0.0",
        "tool": "generate_claude_skills",
        "status": "unchanged" if all(s == "unchanged" for s in statuses) else "generated",
        "skill_count": len(results),
        "results": results,
        "external_effects": {
            "network_calls": 0,
            "secrets_accessed": 0,
            "remote_jobs_submitted": 0,
            "external_spend_usd": 0,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_claude_skills",
        description="Generate Claude skills from the packaged Codex skills.",
    )
    parser.add_argument("--no-package", action="store_true", help="skip writing .skill archives")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        report = generate(package=not args.no_package)
    except GenerateError as exc:
        print(f"generate_claude_skills could not continue: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for entry in report["results"]:
            package_status = entry.get("package_status", "-")
            print(f"  {entry['skill']:<30} skill={entry['skill_status']:<10} "
                  f"package={package_status}")
        print(f"\n{report['skill_count']} Claude skills {report['status']}; "
              "all carry the five design guarantees.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
