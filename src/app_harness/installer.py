"""Install the reusable app harness into projects and personal skill folders.

The installer is intentionally local-only.  It copies the canonical skill and
writes a small project contract and launcher; it never contacts a network,
loads secrets, invokes a model, or spends money.

Which agent surfaces receive the skill is decided by
:mod:`src.app_harness.providers`, not by branches here.  Every selected surface
gets byte-identical copies of one canonical skill, so the harness workflow
cannot drift between hosts.

**Generated artifacts bind late.**  The contract and launcher this module emits
outlive the machine that produced them, so they must not record that machine's
truth as a dependency.  A machine fact may appear only as a *hint* that a
runtime lookup overrides:

* the project root is derived from the launcher's own location (``$0``), never
  recorded;
* the interpreter is resolved from ``PATH`` at invocation, never pinned — the
  contract is a version floor, not a filesystem path;
* the engine root is looked up in order ``$APP_HARNESS_HOME`` → relative hint →
  absolute hint, so either the project or the engine can move.

An earlier version froze ``sys.executable`` and both absolute roots into the
launcher.  That is correct for reproducing one machine and fatal for lifting the
harness to another, which is the property this harness exists to provide.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import stat
from typing import Any, Iterable

from src.app_harness.models import family_catalog
from src.app_harness.providers import AgentSurface, resolve_surfaces


CONTRACT_VERSION = "1.2.0"
SKILL_NAME = "apply-app-harness"
ACCEPTED_TEXT_FORMATS = (
    ".txt",
    ".md",
    ".jsonl",
    ".ndjson",
    ".csv",
)

# The interpreter contract is a floor, not a path.  Mirrors requires-python.
REQUIRES_PYTHON = ">=3.11"
ENGINE_ENV_OVERRIDE = "APP_HARNESS_HOME"

# What a skill *is*, declared rather than inferred from directory contents.
# Copying "whatever is in the folder" let a macOS .DS_Store make a correct,
# unchanged install report a conflict; an allowlist cannot drift that way.
SKILL_MANIFEST = ("SKILL.md", "references", "agents")

# Never part of a skill, at either end of a copy.
_OS_METADATA_NAMES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini", ".localized"})


def _is_os_metadata(path: Path) -> bool:
    return (
        path.name in _OS_METADATA_NAMES
        or path.suffix == ".pyc"
        or "__pycache__" in path.parts
        or path.name.startswith("._")
    )


def _engine_hints(target: Path, engine_root: Path) -> dict[str, Any]:
    """Describe where the engine is, in terms that survive a move.

    The relative hint is the self-reference: it holds whenever the project and
    engine keep their arrangement, including when both are moved together or
    committed to one repository.  An absolute hint is recorded only when the
    engine lives *outside* the project — there is no way to derive an arbitrary
    external location from nothing — and even then it is the last of three
    candidates, behind the environment override and the relative hint.
    """

    relative = os.path.relpath(engine_root, target)
    inside = not relative.split(os.sep)[0] == os.pardir
    hints: dict[str, Any] = {
        "engine_hint": Path(relative).as_posix(),
        "engine_hint_kind": "relative" if inside else "relative-with-absolute-fallback",
        "engine_env_override": ENGINE_ENV_OVERRIDE,
    }
    if not inside:
        hints["engine_hint_absolute"] = str(engine_root)
        hints["engine_hint_absolute_note"] = (
            "Machine-specific fallback, tried last. The engine sits outside this "
            "project, so no purely self-referencing path to it exists. Set "
            f"${ENGINE_ENV_OVERRIDE} to override on any other machine."
        )
    return hints


def _contract(target: Path, engine_root: Path, surfaces: tuple[AgentSurface, ...]) -> dict[str, Any]:
    """Return the canonical, human-readable project contract."""

    installation: dict[str, Any] = {
        # Resolved from this contract file's own directory, so the project root
        # is discoverable after any move without being recorded.
        "project_root": "..",
        "project_root_relative_to": "contract-file-directory",
        "paths_relative_to": "project-root",
        "launcher": "tools/app-harness",
        "default_review_root": ".app-harness/reviews",
        "interpreter": {
            "requires_python": REQUIRES_PYTHON,
            "resolution": "runtime-path-lookup",
        },
        **_engine_hints(target, engine_root),
    }
    # Retain the original two flat keys so existing consumers and receipts keep
    # resolving, while the registry-driven map below carries every surface.
    installation["codex_skill"] = f".codex/skills/{SKILL_NAME}"
    installation["claude_skill"] = f".claude/skills/{SKILL_NAME}"
    installation["agent_surfaces"] = {
        surface.key: {
            "display_name": surface.display_name,
            "skill_path": f"{surface.project_skill_root}/{SKILL_NAME}",
            "invocation": surface.invocation,
        }
        for surface in surfaces
    }

    return {
        "schema_version": CONTRACT_VERSION,
        "name": "reusable-app-harness-contract",
        "description": (
            "A local evidence harness for reviewing application text without "
            "changing the application's source material."
        ),
        "installation": installation,
        "accepted_text_formats": list(ACCEPTED_TEXT_FORMATS),
        "model_attribution": {
            "purpose": (
                "Attribute analyzed text to the model lineage that produced it. "
                "Attribution records provenance only; it is not a claim that any "
                "model was executed, fine-tuned, or benchmarked by this harness."
            ),
            "families": [family["key"] for family in family_catalog()],
            "unmatched_policy": "unattributed",
        },
        "source_files": {
            "preserve_originals": True,
            "mutate_in_place": False,
            "write_generated_artifacts_separately": True,
        },
        "default_effects": {
            "network_access": False,
            "external_inference": False,
            "secret_access": False,
            "external_writes": False,
            "spend_usd": 0,
        },
    }


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _launcher_bytes(engine_root: Path, target: Path) -> bytes:
    """Generate a launcher that discovers, rather than remembers.

    Nothing machine-specific is frozen: the project root comes from ``$0``, the
    interpreter from ``PATH``, and the engine from the first of three candidates
    that actually contains the CLI.  When none does, the script exits 127 naming
    the variable that fixes it — a portable tool must fail legibly on the
    machine it was moved to, not with a bare ``exec: not found``.
    """

    hints = _engine_hints(target, engine_root)
    candidates = [f'"${{{ENGINE_ENV_OVERRIDE}:-}}"', f'"$here"/{shlex.quote(hints["engine_hint"])}']
    if "engine_hint_absolute" in hints:
        candidates.append(shlex.quote(hints["engine_hint_absolute"]))
    searched = " ".join(candidates)

    return f"""#!/bin/sh
# Generated by the reusable app harness installer. Portable by construction:
# no interpreter path, no project root, and an engine hint that any of three
# lookups can override. Do not hand-edit; re-run `harness install` instead.
set -eu

# Project root: derived from this file's location, so it follows a move.
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export APP_HARNESS_PROJECT_ROOT="$here"

# Engine root: environment override, then relative hint, then absolute hint.
engine=""
for candidate in {searched}; do
    if [ -n "$candidate" ] && [ -f "$candidate/scripts/harness_cli.py" ]; then
        engine=$(CDPATH= cd -- "$candidate" && pwd)
        break
    fi
done
if [ -z "$engine" ]; then
    echo "app-harness: harness engine not found." >&2
    # Names the variable literally: expanding it here would abort under `set -u`
    # and swallow the very diagnostic the user needs.
    echo "  searched: {ENGINE_ENV_OVERRIDE}, then the hints in .app-harness/contract.json" >&2
    echo "  fix: export {ENGINE_ENV_OVERRIDE}=/path/to/harness-engine" >&2
    echo "   or: /path/to/harness-engine/harness install \\"$here\\"" >&2
    exit 127
fi

# Interpreter: resolved at runtime and version-checked by the CLI ({REQUIRES_PYTHON}).
python=""
for name in python3 python; do
    if command -v "$name" >/dev/null 2>&1; then
        python=$(command -v "$name")
        break
    fi
done
if [ -z "$python" ]; then
    echo "app-harness: no python3 found on PATH (need {REQUIRES_PYTHON})." >&2
    exit 127
fi

exec "$python" "$engine/scripts/harness_cli.py" "$@"
""".encode("utf-8")


def _skill_files(root: Path) -> dict[str, bytes]:
    """Read a skill as its declared contents: ``{posix relative path: bytes}``.

    Only entries named in :data:`SKILL_MANIFEST` are a skill.  OS metadata is
    excluded at both ends of a copy, so a ``.DS_Store`` appearing on either side
    can neither ship into an install nor fake a conflict.
    """

    files: dict[str, bytes] = {}
    for entry in SKILL_MANIFEST:
        path = root / entry
        if path.is_file() and not _is_os_metadata(path):
            files[entry] = path.read_bytes()
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and not _is_os_metadata(child):
                    files[child.relative_to(root).as_posix()] = child.read_bytes()
    return files


def _canonical_skill_files(source: Path) -> dict[str, bytes]:
    if not source.is_dir():
        raise FileNotFoundError(f"canonical harness skill not found: {source}")
    files = _skill_files(source)
    if "SKILL.md" not in files:
        raise FileNotFoundError(f"canonical harness skill has no SKILL.md: {source}")
    return files


def _same_skill(files: dict[str, bytes], destination: Path) -> bool:
    return destination.is_dir() and _skill_files(destination) == files


def _preflight_file(path: Path, content: bytes, *, force: bool) -> None:
    """Reject a conflicting file before an installation mutates anything."""

    if not (path.exists() or path.is_symlink()):
        return
    if path.is_file() and not path.is_symlink() and path.read_bytes() == content:
        return
    if not force:
        raise FileExistsError(f"conflicting harness file: {path}")


def _preflight_skill(files: dict[str, bytes], destination: Path, *, force: bool) -> None:
    """Reject a conflicting skill tree before an installation begins."""

    if not (destination.exists() or destination.is_symlink()):
        return
    if _same_skill(files, destination):
        return
    if not force:
        raise FileExistsError(f"conflicting harness skill: {destination}")


def _write_exact(path: Path, content: bytes, *, force: bool) -> str:
    """Write exact bytes, refusing to overwrite a conflict unless forced."""

    if path.exists() or path.is_symlink():
        if path.is_file() and not path.is_symlink() and path.read_bytes() == content:
            return "unchanged"
        if not force:
            raise FileExistsError(f"conflicting harness file: {path}")
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return "installed"


def _write_skill_exact(files: dict[str, bytes], destination: Path, *, force: bool) -> str:
    """Write the declared skill contents, idempotently, detecting conflicts."""

    if destination.exists() or destination.is_symlink():
        if _same_skill(files, destination):
            return "unchanged"
        if not force:
            raise FileExistsError(f"conflicting harness skill: {destination}")
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        else:
            destination.unlink()
    for relative, content in sorted(files.items()):
        path = destination.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return "installed"


def _rollup(statuses: Iterable[str]) -> str:
    return "unchanged" if all(status == "unchanged" for status in statuses) else "installed"


def install_project(
    target: Path,
    engine_root: Path,
    *,
    force: bool = False,
    surfaces: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Install the app harness contract, agent skills, and local launcher.

    ``surfaces`` selects agent hosts by key (see
    :mod:`src.app_harness.providers`); ``None`` keeps the historical default of
    Codex and Claude, and ``["all"]`` installs every registered surface.

    Existing exact artifacts are reported as ``unchanged``.  A differing
    artifact raises :class:`FileExistsError` unless ``force`` is true.
    """

    target = Path(target).expanduser().resolve()
    engine_root = Path(engine_root).expanduser().resolve()
    cli = engine_root / "scripts" / "harness_cli.py"
    if not cli.is_file():
        raise FileNotFoundError(f"harness CLI not found: {cli}")
    skill_files = _canonical_skill_files(engine_root / "skills" / SKILL_NAME)

    selected = resolve_surfaces(surfaces)
    contract_path = target / ".app-harness" / "contract.json"
    launcher = target / "tools" / "app-harness"
    skill_paths = {
        surface.key: surface.project_skill_path(target, SKILL_NAME) for surface in selected
    }

    contract_content = _json_bytes(_contract(target, engine_root, selected))
    launcher_content = _launcher_bytes(engine_root, target)
    # Preflight every destination so a conflict cannot leave a partial install.
    _preflight_file(contract_path, contract_content, force=force)
    for path in skill_paths.values():
        _preflight_skill(skill_files, path, force=force)
    _preflight_file(launcher, launcher_content, force=force)

    target.mkdir(parents=True, exist_ok=True)
    contract_status = _write_exact(contract_path, contract_content, force=force)
    skill_statuses = {
        key: _write_skill_exact(skill_files, path, force=force)
        for key, path in skill_paths.items()
    }
    launcher_status = _write_exact(launcher, launcher_content, force=force)
    previous_mode = launcher.stat().st_mode
    launcher.chmod(previous_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if launcher_status == "unchanged" and launcher.stat().st_mode != previous_mode:
        launcher_status = "permissions_repaired"

    installed_surfaces = {
        surface.key: {
            "display_name": surface.display_name,
            "path": str(skill_paths[surface.key]),
            "status": skill_statuses[surface.key],
            "invocation": surface.invocation,
        }
        for surface in selected
    }

    result: dict[str, Any] = {
        "target": str(target),
        "status": _rollup([contract_status, launcher_status, *skill_statuses.values()]),
        "contract": {"path": str(contract_path), "status": contract_status},
        "launcher": {"path": str(launcher), "status": launcher_status},
        "surfaces": installed_surfaces,
        "surface_keys": [surface.key for surface in selected],
    }
    # Backward-compatible flat keys for the two original surfaces.
    for key in ("codex", "claude"):
        if key in installed_surfaces:
            result[f"{key}_skill"] = {
                "path": installed_surfaces[key]["path"],
                "status": installed_surfaces[key]["status"],
            }
    return result


def install_personal_skills(
    engine_root: Path,
    home: Path | None = None,
    *,
    force: bool = False,
    surfaces: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Install the canonical skill into personal agent skill folders.

    Surfaces with no documented personal skill location are skipped and
    reported as ``not_applicable`` rather than being invented a path.
    """

    engine_root = Path(engine_root).expanduser().resolve()
    home_path = Path.home() if home is None else Path(home).expanduser()
    home_path = home_path.resolve()
    skill_files = _canonical_skill_files(engine_root / "skills" / SKILL_NAME)

    selected = resolve_surfaces(surfaces)
    targets: dict[str, Path] = {}
    skipped: dict[str, dict[str, Any]] = {}
    for surface in selected:
        path = surface.personal_skill_path(home_path, SKILL_NAME)
        if path is None:
            skipped[surface.key] = {
                "display_name": surface.display_name,
                "path": None,
                "status": "not_applicable",
                "reason": "surface defines no personal skill location",
            }
            continue
        targets[surface.key] = path

    for path in targets.values():
        _preflight_skill(skill_files, path, force=force)
    statuses = {
        key: _write_skill_exact(skill_files, path, force=force) for key, path in targets.items()
    }

    installed_surfaces: dict[str, Any] = {
        surface.key: {
            "display_name": surface.display_name,
            "path": str(targets[surface.key]),
            "status": statuses[surface.key],
            "invocation": surface.invocation,
        }
        for surface in selected
        if surface.key in targets
    }
    installed_surfaces.update(skipped)

    result: dict[str, Any] = {
        "home": str(home_path),
        "status": _rollup(statuses.values()) if statuses else "unchanged",
        "surfaces": installed_surfaces,
        "surface_keys": [surface.key for surface in selected],
    }
    for key in ("codex", "claude"):
        if key in installed_surfaces:
            result[f"{key}_skill"] = {
                "path": installed_surfaces[key]["path"],
                "status": installed_surfaces[key]["status"],
            }
    return result


__all__ = ["install_personal_skills", "install_project"]
