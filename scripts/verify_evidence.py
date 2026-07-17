#!/usr/bin/env python3
"""Mechanically verify that an evidence catalog resolves from this repository.

A catalog is the layer a claim is checked against.  If its references leave the
shipped unit, the claims cannot be re-checked after a move — so this program
asks one question per artifact: *do the bytes exist here, and are they the bytes
the claim was made against?*

Two rules keep it honest, mirroring :mod:`scripts.lint_skills`:

1. **The hash is the reference.**  ``content_id`` is a machine-independent
   identifier.  ``path`` is a repo-relative hint, resolved against the
   repository root, and is never authoritative on its own.
2. **A mismatch is a finding, not an error to paper over.**  A vendored file
   whose bytes no longer match its ``content_id`` is reported as ``mismatch``
   and exits non-zero.  It is never silently re-hashed: the recorded id is what
   the claim was made against, and quietly replacing it would convert a real
   discrepancy into a false ``pass``.

An ``external-unverifiable`` source is not a failure.  It is the honest state of
a claim whose bytes were never vendored, and saying so is the point — a path
rewritten to look local while resolving to nothing would be strictly worse than
the absolute path it replaced.

Exit status: 0 when every declared artifact holds, 1 on any mismatch or missing
vendored file, 2 when the catalog cannot be read.  Reads files only: no network,
no secrets, no spend.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "evals" / "references" / "ftpo-evidence-catalog-1.1.0.json"

VENDORED = "vendored"
EXTERNAL = "external-unverifiable"
VALID_RESOLUTIONS = (VENDORED, EXTERNAL)


class EvidenceError(ValueError):
    """Raised when a catalog cannot be read as a catalog at all."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalise_content_id(value: str | None) -> str | None:
    if value is None:
        return None
    return value.split(":", 1)[1] if value.startswith("sha256:") else value


def _check_artifact(artifact: dict[str, Any], resolution: str, root: Path) -> dict[str, Any]:
    """Return one artifact's verification state."""

    role = artifact.get("role", "<unnamed>")
    content_id = _normalise_content_id(artifact.get("content_id"))
    declared_path = artifact.get("path")

    result: dict[str, Any] = {
        "role": role,
        "content_id": artifact.get("content_id"),
        "path": declared_path,
    }

    if declared_path is not None and Path(declared_path).is_absolute():
        return {**result, "state": "invalid",
                "detail": "path is absolute; catalog paths must be repo-relative"}

    if resolution == EXTERNAL:
        # Not a failure. But a source claiming external-unverifiable while its
        # bytes actually sit in the repo is a stale record worth surfacing.
        if declared_path and (root / declared_path).is_file():
            return {**result, "state": "promotable",
                    "detail": "bytes are present; set resolution to 'vendored' and re-verify"}
        return {**result, "state": "external",
                "detail": "bytes absent by declaration; claim not re-checkable from this repository"}

    if not declared_path:
        return {**result, "state": "invalid", "detail": "vendored artifact declares no path"}
    if content_id is None:
        return {**result, "state": "invalid", "detail": "vendored artifact declares no content_id"}

    resolved = root / declared_path
    if not resolved.is_file():
        return {**result, "state": "missing",
                "detail": f"declared vendored but not present at {declared_path}"}

    observed = _sha256_file(resolved)
    if observed != content_id:
        return {**result, "state": "mismatch", "observed_sha256": observed,
                "detail": ("bytes differ from the recorded content_id; this file is not the "
                           "artifact the claim was made against. Do not re-hash — investigate.")}
    return {**result, "state": "verified", "detail": f"bytes match content_id ({observed[:12]}...)"}


def _check_source(source: dict[str, Any], root: Path) -> dict[str, Any]:
    identifier = source.get("id", "<unnamed>")
    resolution = source.get("resolution")
    if resolution not in VALID_RESOLUTIONS:
        return {
            "id": identifier,
            "resolution": resolution,
            "pass": False,
            "artifacts": [],
            "failures": [f"unknown resolution {resolution!r}; expected one of {VALID_RESOLUTIONS}"],
        }

    artifacts = [_check_artifact(item, resolution, root) for item in source.get("artifacts", [])]
    if not artifacts:
        return {"id": identifier, "resolution": resolution, "pass": False, "artifacts": [],
                "failures": ["source declares no artifacts"]}

    failures = [
        f"{item['role']}: {item['detail']}"
        for item in artifacts
        if item["state"] in {"missing", "mismatch", "invalid"}
    ]
    return {
        "id": identifier,
        "resolution": resolution,
        "pass": not failures,
        "artifacts": artifacts,
        "failures": failures,
    }


def verify(catalog_path: Path, root: Path = ROOT) -> dict[str, Any]:
    catalog_path = Path(catalog_path)
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise EvidenceError(f"could not read evidence catalog {catalog_path}: {exc}") from exc
    if not isinstance(catalog, dict) or "sources" not in catalog:
        raise EvidenceError(f"{catalog_path}: not an evidence catalog (no 'sources')")

    results = [_check_source(source, root) for source in catalog["sources"]]
    states = [item["state"] for result in results for item in result["artifacts"]]
    failed = [result for result in results if not result["pass"]]

    return {
        "schema_version": "1.0.0",
        "tool": "verify_evidence",
        "catalog": str(catalog_path.relative_to(root)) if catalog_path.is_relative_to(root)
                   else str(catalog_path),
        "catalog_id": catalog.get("catalog_id"),
        "source_count": len(results),
        "artifact_count": len(states),
        "counts": {state: states.count(state) for state in sorted(set(states))},
        "status": "fail" if failed else "pass",
        "verifiable_offline": all(state == "verified" for state in states) if states else False,
        "results": results,
        "external_effects": {
            "network_calls": 0,
            "secrets_accessed": 0,
            "remote_jobs_submitted": 0,
            "external_spend_usd": 0,
        },
    }


_SYMBOL = {
    "verified": "ok  ",
    "external": "ext ",
    "promotable": "PROM",
    "missing": "MISS",
    "mismatch": "DIFF",
    "invalid": "BAD ",
}


def _render(report: dict[str, Any]) -> str:
    lines: list[str] = []
    for result in report["results"]:
        mark = "PASS" if result["pass"] else "FAIL"
        lines.append(f"[{mark}] {result['id']}  ({result['resolution']})")
        for item in result["artifacts"]:
            lines.append(f"    {_SYMBOL.get(item['state'], '????')} {item['role']}: {item['detail']}")
        for failure in result["failures"]:
            lines.append(f"    FAIL {failure}")
    counts = ", ".join(f"{state}={count}" for state, count in report["counts"].items())
    lines.extend(["", f"{report['artifact_count']} artifacts across "
                      f"{report['source_count']} sources: {counts}"])
    if not report["verifiable_offline"]:
        lines.append(
            "\nNot fully verifiable offline. Sources marked 'ext' have no bytes in this "
            "repository, so their claims cannot be re-checked from a clone. This is "
            "reported, not hidden: vendor the bytes and confirm the recorded content_id "
            "to promote them."
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_evidence",
        description="Verify that an evidence catalog resolves from this repository.",
    )
    parser.add_argument("catalog", nargs="?", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--json", action="store_true", help="emit the machine-readable report")
    parser.add_argument("--receipt", type=Path, help="write the report to this path as JSON")
    parser.add_argument(
        "--require-offline",
        action="store_true",
        help="also fail when any source is external-unverifiable",
    )
    args = parser.parse_args(argv)

    try:
        report = verify(args.catalog)
    except EvidenceError as exc:
        print(f"verify_evidence could not continue: {exc}", file=sys.stderr)
        return 2

    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else _render(report))

    if report["status"] == "fail":
        return 1
    if args.require_offline and not report["verifiable_offline"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
