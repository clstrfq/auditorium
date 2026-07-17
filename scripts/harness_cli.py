#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app_harness import AdaptError, adapt_corpus
from src.app_harness.installer import install_personal_skills, install_project
from src.app_harness.models import (
    ModelRegistryError,
    family_catalog,
    load_frozen_registry,
)
from src.app_harness.providers import UnknownSurfaceError, surface_catalog, surface_keys
from src.app_harness.runner import analyze_canonical


COMMANDS = {"status", "demo", "analyze", "install", "install-skills", "surfaces", "models"}

# The generated launcher resolves an interpreter from PATH instead of pinning
# one, so something must reject a genuinely too-old interpreter with a clear
# message rather than a cryptic SyntaxError from deep in an import.
#
# This is the *executable* floor, not the project's *support* policy. It is set
# by evidence: the engine uses PEP 604 unions and `zip(..., strict=True)`, both
# 3.10, and was observed importing and running a full analyze on 3.10.12. No
# 3.11-only construct exists anywhere in src/ or scripts/.
#
# pyproject's `requires-python = ">=3.11"` is a different statement — which
# interpreters the project intends to support — and is deliberately left alone.
# A runtime gate must refuse what cannot run, not what is merely unsupported;
# gating execution on support policy breaks working installs for nothing.
MINIMUM_PYTHON = (3, 10)

ENGINE_ENV_OVERRIDE = "APP_HARNESS_HOME"
PROJECT_ENV = "APP_HARNESS_PROJECT_ROOT"


def _floor(version: tuple[int, int]) -> str:
    return ".".join(str(part) for part in version)


def _check_interpreter() -> None:
    if sys.version_info < MINIMUM_PYTHON:
        running = ".".join(str(part) for part in sys.version_info[:3])
        raise RuntimeError(
            f"app-harness needs Python >={_floor(MINIMUM_PYTHON)} to run; this "
            f"interpreter is {running} ({sys.executable}). Put a newer python3 "
            "first on PATH, or set APP_HARNESS_HOME and invoke that engine directly."
        )


def _engine_discovery() -> dict[str, Any]:
    """Report how the engine was found, so an agent can diagnose it.

    ``apply-app-harness`` instructs every surface to fall back to
    ``$APP_HARNESS_HOME/harness`` when no project launcher exists.  That rung is
    only real if something reads the variable and can say whether it pointed at
    the engine now running.
    """

    configured = os.environ.get(ENGINE_ENV_OVERRIDE)
    resolved: str | None = None
    if configured:
        candidate = Path(configured).expanduser()
        if (candidate / "scripts" / "harness_cli.py").is_file():
            resolved = str(candidate.resolve())
    return {
        "name": ENGINE_ENV_OVERRIDE,
        "set": configured is not None,
        "value": configured,
        "resolves_to_an_engine": resolved is not None,
        "selects_running_engine": resolved == str(ROOT) if resolved else False,
    }


def _default_analysis_output(source: Path) -> Path:
    project_root = os.environ.get(PROJECT_ENV)
    if project_root:
        return Path(project_root).expanduser().resolve() / ".app-harness" / "reviews" / source.stem
    return source.with_name(f"{source.stem}-harness-results")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Apply the reusable app evidence and AI-output harness.",
        epilog="Shortcut: harness FILE is the same as harness analyze FILE.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="show whether the shared harness is ready")
    status.add_argument("--json", action="store_true")

    demo = sub.add_parser("demo", help="run the three-item safe demo")
    demo.add_argument("--output", type=Path, default=ROOT / "harness-output" / "demo")
    demo.add_argument("--json", action="store_true")

    analyze = sub.add_parser("analyze", help="analyze TXT, MD, CSV, JSONL, or NDJSON")
    analyze.add_argument("source", type=Path)
    analyze.add_argument("--output", type=Path)
    analyze.add_argument("--limit", type=int, default=500)
    analyze.add_argument("--id-field")
    analyze.add_argument("--text-field")
    analyze.add_argument("--context-field")
    analyze.add_argument("--prompt-field")
    analyze.add_argument("--model-field")
    analyze.add_argument("--json", action="store_true")

    surface_help = (
        "agent surface to install for; repeatable; use 'all' for every surface "
        f"(known: {', '.join(surface_keys())}; default: codex, claude)"
    )

    install = sub.add_parser("install", help="add the harness and agent skills to an app")
    install.add_argument("project", type=Path)
    install.add_argument("--surface", action="append", dest="surfaces", metavar="KEY",
                         help=surface_help)
    install.add_argument("--force", action="store_true")
    install.add_argument("--json", action="store_true")

    skills = sub.add_parser("install-skills", help="install personal agent skills")
    skills.add_argument("--surface", action="append", dest="surfaces", metavar="KEY",
                        help=surface_help)
    skills.add_argument("--force", action="store_true")
    skills.add_argument("--json", action="store_true")

    surfaces = sub.add_parser("surfaces", help="list agent surfaces the harness can install into")
    surfaces.add_argument("--json", action="store_true")

    models = sub.add_parser("models", help="list model families the harness can attribute text to")
    models.add_argument("--frozen-registry", type=Path,
                        help="attribute every model named in a frozen registry JSON file")
    models.add_argument("--json", action="store_true")
    return parser


def _json_requested(argv: list[str]) -> bool:
    return "--json" in argv


def _print(value: dict[str, Any], *, machine: bool) -> None:
    if machine:
        print(json.dumps(value, sort_keys=True))
        return
    status = value.get("status")
    if value.get("command") == "status":
        print(f"Harness: {status}")
        print(f"Engine: {value['engine_root']}")
        interpreter = value["interpreter"]
        print(f"Python: {interpreter['version']} (runtime floor {interpreter['runtime_floor']}, resolved from PATH)")
        override = value["engine_env_override"]
        if not override["set"]:
            print(f"{override['name']}: unset (using this engine)")
        elif override["selects_running_engine"]:
            print(f"{override['name']}: {override['value']} (selects this engine)")
        elif override["resolves_to_an_engine"]:
            print(f"{override['name']}: {override['value']} (points at a DIFFERENT engine)")
        else:
            print(f"{override['name']}: {override['value']} (does not resolve to an engine)")
        launcher = "./tools/app-harness" if os.environ.get(PROJECT_ENV) else "./harness"
        print(f"Next: {launcher} demo")
    elif value.get("command") in {"demo", "analyze"}:
        summary = value["summary"]
        print(
            f"Finished: {summary['item_count']} items, {summary['finding_count']} findings, "
            f"{summary['verified_suggestion_count']} verified suggestions, "
            f"{summary['uncertain']} need review."
        )
        print(f"Open: {value['review']}")
        print("Original file unchanged.")
    elif value.get("command") == "install":
        print(f"Harness {status}: {value['project_root']}")
        print(f"Run: {value['launcher']} status")
        for key, surface in value["surfaces"].items():
            print(f"{surface['display_name']} ({key}): {surface['invocation']}")
    elif value.get("command") == "install-skills":
        print(f"Personal skills {status}.")
        for key, surface in value["surfaces"].items():
            location = surface["path"] or surface.get("reason", "not applicable")
            print(f"{surface['display_name']} ({key}): {location}")
    elif value.get("command") == "surfaces":
        print("Agent surfaces the harness can install into:")
        for surface in value["surfaces"]:
            personal = surface["personal_skill_root"] or "-"
            print(f"  {surface['key']:<8} {surface['display_name']:<26} "
                  f"project={surface['project_skill_root']:<16} personal={personal}")
    elif value.get("command") == "models":
        print("Model families the harness can attribute produced text to:")
        for family in value["families"]:
            print(f"  {family['key']:<9} {family['display_name']:<9} "
                  f"{family['vendor']:<18} access={family['access']}")
        registry = value.get("frozen_registry")
        if registry:
            state = "all attributed" if registry["fully_attributed"] else "GAPS FOUND"
            print(f"\nFrozen registry: {registry['entry_count']} entries, {state}")
            for identifier in registry["unattributed_ids"]:
                print(f"  unattributed: {identifier}")
        print("\nProvenance only; no model is executed, fine-tuned, or benchmarked here.")
    else:
        print(json.dumps(value, indent=2, sort_keys=True))


def _analysis(source: Path, output: Path, args: argparse.Namespace, *, command: str) -> dict[str, Any]:
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    canonical = output / "canonical-input.jsonl"
    adapted = adapt_corpus(
        source,
        canonical,
        item_id_field=getattr(args, "id_field", None),
        text_field=getattr(args, "text_field", None),
        context_field=getattr(args, "context_field", None),
        prompt_field=getattr(args, "prompt_field", None),
        model_field=getattr(args, "model_field", None),
        limit=getattr(args, "limit", 500),
    )
    metadata = {**asdict(adapted), "source_path": str(source)}
    receipt = analyze_canonical(canonical, output, metadata)
    return {
        "schema_version": "1.0.0",
        "command": command,
        "status": "reused" if receipt["reused"] else "complete",
        "run_id": receipt["run_id"],
        "summary": receipt["summary"],
        "receipt": str((output / "receipt.json").resolve()),
        "review": receipt["artifacts"]["review"]["path"],
        "output": str(output),
        "reused": receipt["reused"],
    }


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and not raw[0].startswith("-") and raw[0] not in COMMANDS:
        raw.insert(0, "analyze")
    machine = _json_requested(raw)
    try:
        _check_interpreter()
        args = _parser().parse_args(raw)
        machine = bool(getattr(args, "json", False))
        if args.command == "status":
            state_path = ROOT / "pipeline" / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
            result = {
                "schema_version": "1.1.0",
                "command": "status",
                "status": "ready" if (ROOT / "pipeline" / "BUILD_COMPLETE").is_file() else "incomplete",
                "engine_root": str(ROOT),
                "engine_env_override": _engine_discovery(),
                "project_root": os.environ.get(PROJECT_ENV),
                "interpreter": {
                    "executable": sys.executable,
                    "version": ".".join(str(part) for part in sys.version_info[:3]),
                    "runtime_floor": ">=" + _floor(MINIMUM_PYTHON),
                    "resolution": "runtime-path-lookup",
                },
                "build_state": state.get("mode", "unknown"),
                "analyze_available": True,
                "install_available": True,
                "external_effects": {"network_calls": 0, "secrets_accessed": 0,
                                     "remote_jobs_submitted": 0, "external_spend_usd": 0},
            }
        elif args.command == "demo":
            result = _analysis(ROOT / "fixtures" / "corpora" / "golden.jsonl", args.output, args,
                               command="demo")
        elif args.command == "analyze":
            source = args.source.expanduser().resolve()
            default_output = _default_analysis_output(source)
            result = _analysis(args.source, args.output or default_output, args, command="analyze")
        elif args.command == "surfaces":
            result = {
                "schema_version": "1.0.0", "command": "surfaces", "status": "ready",
                "surfaces": surface_catalog(),
            }
        elif args.command == "models":
            result = {
                "schema_version": "1.0.0", "command": "models", "status": "ready",
                "families": family_catalog(),
                "attribution_policy": (
                    "Provenance only. Attribution does not assert that any model was "
                    "executed, fine-tuned, or benchmarked by this harness."
                ),
            }
            if args.frozen_registry:
                result["frozen_registry"] = load_frozen_registry(args.frozen_registry)
        elif args.command == "install":
            installed = install_project(args.project, ROOT, force=args.force,
                                        surfaces=args.surfaces)
            result = {
                "schema_version": "1.0.0", "command": "install", "status": installed["status"],
                "project_root": installed["target"], "launcher": installed["launcher"]["path"],
                "contract": installed["contract"]["path"],
                "surfaces": installed["surfaces"], "details": installed,
            }
        else:
            installed = install_personal_skills(ROOT, force=args.force, surfaces=args.surfaces)
            result = {
                "schema_version": "1.0.0", "command": "install-skills",
                "status": installed["status"], "surfaces": installed["surfaces"],
                "details": installed,
            }
        _print(result, machine=machine)
        return 0
    except (AdaptError, ModelRegistryError, UnknownSurfaceError, FileExistsError,
            FileNotFoundError, ValueError, OSError, RuntimeError) as exc:
        error = {"schema_version": "1.0.0", "status": "blocked", "error": type(exc).__name__,
                 "message": str(exc)}
        if machine:
            print(json.dumps(error, sort_keys=True))
        else:
            print(f"Harness could not continue: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
