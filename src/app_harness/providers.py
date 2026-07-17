"""Declarative registry of agent surfaces (hosts) that can carry the harness skill.

An *agent surface* is a program that loads a skill file and can operate the
harness workflow: Codex, Claude Code, Cursor, Gemini CLI, or any agent that
reads a repository-root ``AGENTS.md``.

The registry is data, not code paths.  Adding a surface means appending one
:class:`AgentSurface` entry; no installer branch changes.  Every surface
receives byte-identical copies of the same canonical skill, so the harness
workflow cannot drift between hosts.

This module performs no network calls, loads no secrets, invokes no model, and
spends nothing.  It only describes where files belong.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class AgentSurface:
    """One agent host that can load and operate the harness skill.

    ``project_skill_root`` and ``personal_skill_root`` are POSIX-style relative
    path fragments, resolved against a project root and a home directory
    respectively.  A ``None`` personal root means the surface has no documented
    per-user skill location and is installed per-project only.
    """

    key: str
    display_name: str
    project_skill_root: str
    personal_skill_root: str | None
    invocation: str
    notes: str

    def project_skill_path(self, project_root: Path, skill_name: str) -> Path:
        return Path(project_root).joinpath(*self.project_skill_root.split("/"), skill_name)

    def personal_skill_path(self, home: Path, skill_name: str) -> Path | None:
        if self.personal_skill_root is None:
            return None
        return Path(home).joinpath(*self.personal_skill_root.split("/"), skill_name)


# Ordered deliberately: the two surfaces the repository already shipped come
# first so existing receipts and docs keep reading naturally.
AGENT_SURFACES: tuple[AgentSurface, ...] = (
    AgentSurface(
        key="codex",
        display_name="Codex",
        project_skill_root=".codex/skills",
        personal_skill_root=".codex/skills",
        invocation="$apply-app-harness",
        notes="OpenAI Codex CLI reads skills from .codex/skills.",
    ),
    AgentSurface(
        key="claude",
        display_name="Claude Code",
        project_skill_root=".claude/skills",
        personal_skill_root=".claude/skills",
        invocation="/apply-app-harness",
        notes="Claude Code reads skills from .claude/skills.",
    ),
    AgentSurface(
        key="cursor",
        display_name="Cursor",
        project_skill_root=".cursor/skills",
        personal_skill_root=".cursor/skills",
        invocation="@apply-app-harness",
        notes="Cursor agent rules/skills directory.",
    ),
    AgentSurface(
        key="gemini",
        display_name="Gemini CLI",
        project_skill_root=".gemini/skills",
        personal_skill_root=".gemini/skills",
        invocation="apply-app-harness",
        notes="Gemini CLI extension/skill directory.",
    ),
    AgentSurface(
        key="agents",
        display_name="Generic AGENTS.md agent",
        project_skill_root=".agents/skills",
        personal_skill_root=None,
        invocation="Reference .agents/skills/apply-app-harness/SKILL.md from AGENTS.md",
        notes=(
            "Fallback for any agent that follows the AGENTS.md convention. "
            "Project-scoped only; no standard personal skill location exists."
        ),
    ),
)

DEFAULT_SURFACE_KEYS: tuple[str, ...] = ("codex", "claude")

_BY_KEY = {surface.key: surface for surface in AGENT_SURFACES}


class UnknownSurfaceError(ValueError):
    """Raised when a caller names a surface the registry does not define."""


def surface_keys() -> tuple[str, ...]:
    """Return every registered surface key, in registry order."""

    return tuple(surface.key for surface in AGENT_SURFACES)


def get_surface(key: str) -> AgentSurface:
    """Return one surface by key, or raise :class:`UnknownSurfaceError`."""

    try:
        return _BY_KEY[key]
    except KeyError:
        known = ", ".join(surface_keys())
        raise UnknownSurfaceError(f"unknown agent surface {key!r}; known surfaces: {known}") from None


def resolve_surfaces(keys: Iterable[str] | None) -> tuple[AgentSurface, ...]:
    """Resolve surface keys to surfaces, de-duplicated and in registry order.

    ``None`` selects :data:`DEFAULT_SURFACE_KEYS`.  The literal key ``"all"``
    selects every registered surface.  Order is always registry order, so an
    install plan is deterministic regardless of how the caller ordered flags.
    """

    if keys is None:
        selected = set(DEFAULT_SURFACE_KEYS)
    else:
        requested = list(keys)
        if not requested:
            raise UnknownSurfaceError("no agent surface selected; pass at least one surface key")
        if "all" in requested:
            selected = set(surface_keys())
        else:
            selected = {get_surface(key).key for key in requested}
    return tuple(surface for surface in AGENT_SURFACES if surface.key in selected)


def surface_catalog() -> list[dict[str, str | None]]:
    """Return a JSON-serializable description of every surface."""

    return [
        {
            "key": surface.key,
            "display_name": surface.display_name,
            "project_skill_root": surface.project_skill_root,
            "personal_skill_root": surface.personal_skill_root,
            "invocation": surface.invocation,
            "notes": surface.notes,
        }
        for surface in AGENT_SURFACES
    ]


__all__ = [
    "AGENT_SURFACES",
    "DEFAULT_SURFACE_KEYS",
    "AgentSurface",
    "UnknownSurfaceError",
    "get_surface",
    "resolve_surfaces",
    "surface_catalog",
    "surface_keys",
]
