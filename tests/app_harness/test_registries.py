"""Tests for the agent-surface and model-family registries.

These cover the behavior that makes multi-LLM integration trustworthy: every
surface gets a byte-identical skill, and attribution never guesses a lineage.
Several cases below are regression tests for bugs found while building this:
word-boundary matching that silently failed on ``Qwen2.5-Math-7B``, and the
distinction between an ambiguous identifier and an unknown one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.app_harness.installer import install_personal_skills, install_project
from src.app_harness.models import (
    UNATTRIBUTED,
    ModelRegistryError,
    attribute_model,
    attribute_models,
    family_catalog,
    load_frozen_registry,
)
from src.app_harness.providers import (
    UnknownSurfaceError,
    resolve_surfaces,
    surface_catalog,
    surface_keys,
)

ROOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------
# Agent surface registry
# --------------------------------------------------------------------------


def test_default_surfaces_preserve_historical_codex_and_claude() -> None:
    assert [surface.key for surface in resolve_surfaces(None)] == ["codex", "claude"]


def test_all_selects_every_registered_surface() -> None:
    assert [surface.key for surface in resolve_surfaces(["all"])] == list(surface_keys())


def test_surface_order_is_registry_order_regardless_of_request_order() -> None:
    forward = resolve_surfaces(["codex", "gemini", "claude"])
    reverse = resolve_surfaces(["gemini", "claude", "codex"])
    assert [s.key for s in forward] == [s.key for s in reverse] == ["codex", "claude", "gemini"]


def test_duplicate_surface_keys_are_collapsed() -> None:
    assert [s.key for s in resolve_surfaces(["codex", "codex"])] == ["codex"]


def test_unknown_surface_is_rejected_with_the_known_list() -> None:
    with pytest.raises(UnknownSurfaceError, match="hal9000"):
        resolve_surfaces(["hal9000"])


def test_empty_surface_selection_is_rejected() -> None:
    with pytest.raises(UnknownSurfaceError):
        resolve_surfaces([])


def test_surface_catalog_is_json_serializable() -> None:
    json.dumps(surface_catalog())


# --------------------------------------------------------------------------
# Installer across surfaces
# --------------------------------------------------------------------------


def test_install_writes_byte_identical_skill_to_every_surface(tmp_path: Path) -> None:
    result = install_project(tmp_path / "app", ROOT, surfaces=["all"])
    paths = [Path(surface["path"]) / "SKILL.md" for surface in result["surfaces"].values()]
    assert len(paths) == len(surface_keys())
    bodies = {path.read_bytes() for path in paths}
    # One distinct body across every host: the workflow cannot drift per host.
    assert len(bodies) == 1


def test_install_is_idempotent_across_surfaces(tmp_path: Path) -> None:
    target = tmp_path / "app"
    assert install_project(target, ROOT, surfaces=["all"])["status"] == "installed"
    assert install_project(target, ROOT, surfaces=["all"])["status"] == "unchanged"


def test_install_conflict_is_refused_without_force(tmp_path: Path) -> None:
    target = tmp_path / "app"
    install_project(target, ROOT, surfaces=["codex"])
    skill = target / ".codex" / "skills" / "apply-app-harness" / "SKILL.md"
    skill.write_text("divergent local edit", encoding="utf-8")
    with pytest.raises(FileExistsError):
        install_project(target, ROOT, surfaces=["codex"])
    # The conflicting file is preserved, not silently clobbered.
    assert skill.read_text(encoding="utf-8") == "divergent local edit"
    install_project(target, ROOT, surfaces=["codex"], force=True)
    assert skill.read_text(encoding="utf-8") != "divergent local edit"


def test_install_records_every_selected_surface_in_the_contract(tmp_path: Path) -> None:
    target = tmp_path / "app"
    install_project(target, ROOT, surfaces=["all"])
    contract = json.loads((target / ".app-harness" / "contract.json").read_text(encoding="utf-8"))
    assert set(contract["installation"]["agent_surfaces"]) == set(surface_keys())
    # Backward-compatible flat keys survive for existing consumers.
    assert contract["installation"]["codex_skill"].endswith("apply-app-harness")
    assert contract["installation"]["claude_skill"].endswith("apply-app-harness")


def test_personal_install_skips_surfaces_without_a_personal_location(tmp_path: Path) -> None:
    result = install_personal_skills(ROOT, home=tmp_path, surfaces=["all"])
    agents = result["surfaces"]["agents"]
    assert agents["status"] == "not_applicable"
    assert agents["path"] is None
    # A surface with no documented personal path is reported, never invented.
    assert not (tmp_path / ".agents").exists()


def test_personal_install_is_idempotent(tmp_path: Path) -> None:
    assert install_personal_skills(ROOT, home=tmp_path, surfaces=["codex"])["status"] == "installed"
    assert install_personal_skills(ROOT, home=tmp_path, surfaces=["codex"])["status"] == "unchanged"


# --------------------------------------------------------------------------
# Model family attribution
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("meta-llama/Meta-Llama-3-8B-Instruct", "llama"),
        ("mistralai/Mistral-7B-Instruct-v0.2", "mistral"),
        ("Qwen/Qwen2-7B-Instruct", "qwen"),
        # Regression: bare vendor-less id with no word boundary before the digit.
        ("Qwen2.5-Math-7B", "qwen"),
        ("google/gemma-2-9b-it", "gemma"),
        ("gemini-1.5-pro", "gemini"),
        ("zai-org/chatglm3-6b", "chatglm"),
        ("openai/gpt-4-turbo", "gpt"),
        ("gpt-5.6-sol", "gpt"),
        ("claude-opus-4-8", "claude"),
        # Derived models attribute to their true lineage, not their publisher.
        ("HuggingFaceH4/zephyr-7b-beta", "mistral"),
        ("sfairXC/FsfairX-LLaMA3-RM-v0.1", "llama"),
    ],
)
def test_known_identifiers_attribute_to_their_family(identifier: str, expected: str) -> None:
    assert attribute_model(identifier)["family"] == expected


def test_unknown_identifier_is_unattributed_rather_than_guessed() -> None:
    result = attribute_model("totally-made-up-model-9000")
    assert result["family"] == UNATTRIBUTED
    assert result["confidence"] == "none"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_model_is_unattributed(value: str | None) -> None:
    assert attribute_model(value)["family"] == UNATTRIBUTED


def test_multi_lineage_identifier_is_ambiguous_not_arbitrarily_assigned() -> None:
    # A DeepSeek distillation of a Qwen base genuinely names two lineages.
    # Silently picking one would corrupt any cross-family comparison built on it.
    result = attribute_model("deepseek-ai/DeepSeek-R1-Distill-Qwen-7B")
    assert result["family"] == UNATTRIBUTED
    assert result["confidence"] == "ambiguous"
    assert result["candidates"] == ["deepseek", "qwen"]


def test_summary_separates_ambiguous_from_unknown() -> None:
    summary = attribute_models(
        [
            "Qwen/Qwen2-7B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",  # ambiguous
            "who-knows",  # unknown
        ]
    )
    assert summary["families"] == {"mistral": 1, "qwen": 1}
    assert summary["ambiguous_count"] == 1
    assert summary["unknown_count"] == 1
    assert summary["unattributed_count"] == 2
    assert summary["cross_family"] is True


def test_single_family_corpus_is_not_reported_as_cross_family() -> None:
    summary = attribute_models(["Qwen/Qwen2-7B-Instruct", "Qwen2.5-Math-7B"])
    assert summary["cross_family"] is False
    assert summary["distinct_family_count"] == 1


def test_attribution_is_case_and_separator_insensitive() -> None:
    assert attribute_model("MISTRAL_7B_INSTRUCT")["family"] == "mistral"
    assert attribute_model("  Mistral-7B  ")["family"] == "mistral"


def test_family_catalog_is_json_serializable() -> None:
    json.dumps(family_catalog())


# --------------------------------------------------------------------------
# Frozen registry
# --------------------------------------------------------------------------


def test_every_model_in_the_repository_frozen_registry_is_attributable() -> None:
    registry = load_frozen_registry(
        ROOT / "validation-proxy" / "gate-b" / "frozen-model-registry.json"
    )
    assert registry["entry_count"] > 0
    # A named model the harness cannot place is a gap to close, not to hide.
    assert registry["unattributed_ids"] == []
    assert registry["fully_attributed"] is True


def test_missing_frozen_registry_raises_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ModelRegistryError, match="not found"):
        load_frozen_registry(tmp_path / "absent.json")


def test_malformed_frozen_registry_raises_a_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ModelRegistryError):
        load_frozen_registry(path)
