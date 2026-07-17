"""Prove the installed harness survives a lift and shift.

The engine already resolves its own root relatively, so it relocates cleanly.
The *generated* launcher is what an app actually invokes, and nothing here used
to execute it.  These tests close that gap: they install, physically move the
tree, and run the launcher from its new home.

Deliberately stdlib-only (``unittest``, no pytest).  A suite that proves
portability must not itself require an undeclared dependency to run.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]

# The minimum engine needed to install and analyze.  Copying only these keeps
# the "move the engine" tests fast and states what the engine actually is.
ENGINE_PARTS = ("harness", "scripts", "src", "skills")

# Machine facts that must never be frozen into a generated launcher.
FORBIDDEN_FRAGMENTS = ("/Users/", "/home/", "/opt/", "/.venv/", "site-packages")


def _copy_engine(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    for part in ENGINE_PARTS:
        source = ROOT / part
        target = destination / part
        if source.is_dir():
            shutil.copytree(
                source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
            )
        else:
            shutil.copy2(source, target)
            target.chmod(0o755)
    return destination


def _run(command: list[str], cwd: Path, env: dict[str, str] | None = None):
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(cwd),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if env:
        environment.update(env)
    return subprocess.run(
        [str(part) for part in command],
        cwd=str(cwd),
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )


class PortabilityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        sys.path.insert(0, str(ROOT))

    def _install(self, project: Path, engine: Path) -> dict:
        from src.app_harness.installer import install_project

        return install_project(project, engine)


class TestLauncherRecordsNoMachineFacts(PortabilityTestCase):
    """A generated launcher may record a hint; it may not record a dependency."""

    def test_launcher_records_no_interpreter_path(self) -> None:
        project = self.tmp / "app"
        self._install(project, ROOT)
        text = (project / "tools" / "app-harness").read_text(encoding="utf-8")

        self.assertNotIn(
            sys.executable,
            text,
            "launcher pinned the installing interpreter; it must resolve python3 at runtime",
        )
        for fragment in ("/opt/", "/usr/bin/python", "/.venv/"):
            self.assertNotIn(fragment, text, f"launcher froze an interpreter path: {fragment}")

    def test_launcher_records_no_project_root(self) -> None:
        project = self.tmp / "app"
        self._install(project, ROOT)
        text = (project / "tools" / "app-harness").read_text(encoding="utf-8")

        self.assertNotIn(
            str(project.resolve()),
            text,
            "launcher froze its project root; it must derive it from $0",
        )

    def test_launcher_prefers_a_relative_engine_hint_when_engine_is_inside_project(self) -> None:
        project = self.tmp / "app"
        engine = _copy_engine(project / "vendor" / "harness")
        self._install(project, engine)
        text = (project / "tools" / "app-harness").read_text(encoding="utf-8")

        self.assertIn("vendor/harness", text)
        self.assertNotIn(
            str(engine.resolve()),
            text,
            "engine lives inside the project; the hint must be relative, not absolute",
        )


class TestLauncherSurvivesRelocation(PortabilityTestCase):
    def test_launcher_runs_after_the_project_is_moved(self) -> None:
        original = self.tmp / "before"
        self._install(original, ROOT)

        moved = self.tmp / "after"
        shutil.move(str(original), str(moved))

        result = _run([moved / "tools" / "app-harness", "--help"], cwd=moved)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("analyze", result.stdout)

    def test_launcher_analyzes_into_the_moved_project_root(self) -> None:
        original = self.tmp / "before"
        self._install(original, ROOT)
        moved = self.tmp / "after"
        shutil.move(str(original), str(moved))

        source = moved / "note.md"
        source.write_text("The update improves page loading speed.\n", encoding="utf-8")

        result = _run(
            [moved / "tools" / "app-harness", "analyze", source, "--json"], cwd=moved
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        # Proves APP_HARNESS_PROJECT_ROOT was derived from $0, not from the
        # path recorded at install time: the packet lands under the NEW root.
        # macOS exposes /var as a symlink to /private/var. The launcher enters
        # the physical directory with `pwd`, while tempfile may retain the
        # logical spelling; compare canonical paths so that alias is not a
        # portability failure.
        self.assertEqual(
            Path(payload["output"]).resolve(),
            (moved / ".app-harness" / "reviews" / "note").resolve(),
        )
        self.assertTrue((moved / ".app-harness" / "reviews" / "note" / "receipt.json").is_file())

    def test_launcher_runs_when_the_engine_moves_and_home_is_set(self) -> None:
        engine = _copy_engine(self.tmp / "engine-original")
        project = self.tmp / "app"
        self._install(project, engine)

        relocated = self.tmp / "engine-relocated"
        shutil.move(str(engine), str(relocated))

        result = _run(
            [project / "tools" / "app-harness", "--help"],
            cwd=project,
            env={"APP_HARNESS_HOME": str(relocated)},
        )
        self.assertEqual(
            result.returncode, 0, f"APP_HARNESS_HOME did not override the hint: {result.stderr}"
        )
        self.assertIn("analyze", result.stdout)

    def test_launcher_fails_legibly_when_the_engine_is_gone(self) -> None:
        engine = _copy_engine(self.tmp / "engine")
        project = self.tmp / "app"
        self._install(project, engine)
        shutil.rmtree(engine)

        result = _run([project / "tools" / "app-harness", "--help"], cwd=project)

        self.assertEqual(result.returncode, 127, "a missing engine must exit 127")
        self.assertIn(
            "APP_HARNESS_HOME",
            result.stderr,
            "the failure must name the variable that fixes it",
        )


class TestContractIsRelocatable(PortabilityTestCase):
    def test_contract_declares_no_absolute_paths(self) -> None:
        project = self.tmp / "app"
        engine = _copy_engine(project / "vendor" / "harness")
        self._install(project, engine)
        installation = json.loads(
            (project / ".app-harness" / "contract.json").read_text(encoding="utf-8")
        )["installation"]

        # Asserted structurally, not by scanning for "/Users/": a fragment scan
        # passes vacuously on any machine whose paths differ from the author's,
        # which is exactly the machine this needs to catch.
        for key in ("project_root", "launcher", "engine_hint", "default_review_root"):
            self.assertFalse(
                Path(installation[key]).is_absolute(),
                f"contract declared an absolute {key}: {installation[key]!r}",
            )
        self.assertNotIn(
            "engine_hint_absolute",
            installation,
            "engine lives inside the project; no absolute fallback should be recorded",
        )

    def test_contract_paths_resolve_after_relocation(self) -> None:
        original = self.tmp / "before"
        engine = _copy_engine(original / "vendor" / "harness")
        self._install(original, engine)
        moved = self.tmp / "after"
        shutil.move(str(original), str(moved))

        contract_path = moved / ".app-harness" / "contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        installation = contract["installation"]

        self.assertEqual(contract["schema_version"], "1.2.0")
        self.assertEqual(installation["engine_env_override"], "APP_HARNESS_HOME")
        self.assertEqual(installation["interpreter"]["resolution"], "runtime-path-lookup")
        self.assertEqual(installation["paths_relative_to"], "project-root")
        self.assertEqual(installation["project_root_relative_to"], "contract-file-directory")

        # project_root resolves from the contract's own directory; everything
        # else resolves from the project root it points at.
        project_root = (contract_path.parent / installation["project_root"]).resolve()
        self.assertEqual(project_root, moved.resolve())
        self.assertTrue((project_root / installation["engine_hint"]).resolve().is_dir())
        self.assertTrue((project_root / installation["launcher"]).is_file())


class TestEngineDiscoveryIsReportable(PortabilityTestCase):
    """`apply-app-harness` tells agents to fall back to $APP_HARNESS_HOME.

    That rung only exists if something reads the variable and can report it.
    """

    def test_status_reports_the_override_as_unset(self) -> None:
        result = _run([ROOT / "harness", "status", "--json"], cwd=self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)
        override = json.loads(result.stdout)["engine_env_override"]

        self.assertEqual(override["name"], "APP_HARNESS_HOME")
        self.assertFalse(override["set"])

    def test_status_reports_when_the_override_selects_this_engine(self) -> None:
        result = _run(
            [ROOT / "harness", "status", "--json"],
            cwd=self.tmp,
            env={"APP_HARNESS_HOME": str(ROOT)},
        )
        override = json.loads(result.stdout)["engine_env_override"]

        self.assertTrue(override["set"])
        self.assertTrue(override["resolves_to_an_engine"])
        self.assertTrue(override["selects_running_engine"])

    def test_status_reports_an_override_that_resolves_to_nothing(self) -> None:
        result = _run(
            [ROOT / "harness", "status", "--json"],
            cwd=self.tmp,
            env={"APP_HARNESS_HOME": str(self.tmp / "nowhere")},
        )
        override = json.loads(result.stdout)["engine_env_override"]

        self.assertTrue(override["set"])
        self.assertFalse(override["resolves_to_an_engine"])
        self.assertFalse(override["selects_running_engine"])

    def test_status_reports_the_interpreter_it_resolved(self) -> None:
        result = _run([ROOT / "harness", "status", "--json"], cwd=self.tmp)
        interpreter = json.loads(result.stdout)["interpreter"]

        self.assertEqual(interpreter["resolution"], "runtime-path-lookup")
        # The runtime floor gates what can execute. It is intentionally NOT
        # pyproject's requires-python, which states support policy instead.
        self.assertEqual(interpreter["runtime_floor"], ">=3.10")
        expected = shutil.which("python3", path=os.environ.get("PATH", "")) or shutil.which(
            "python", path=os.environ.get("PATH", "")
        )
        self.assertIsNotNone(expected)
        self.assertEqual(
            Path(interpreter["executable"]).resolve(),
            Path(expected).resolve(),
            "status must report the interpreter the launcher resolved from PATH, not the "
            "interpreter that happened to run the parent test process",
        )


class TestInstallerIgnoresOsMetadata(PortabilityTestCase):
    def test_installer_is_idempotent_despite_os_metadata(self) -> None:
        """A stray .DS_Store must not turn a correct install into a conflict."""

        engine = _copy_engine(self.tmp / "engine")
        project = self.tmp / "app"
        self._install(project, engine)

        # Simulate macOS writing metadata into the canonical skill afterwards.
        (engine / "skills" / "apply-app-harness" / ".DS_Store").write_bytes(b"\x00\x01junk")

        result = self._install(project, engine)
        self.assertEqual(
            result["status"],
            "unchanged",
            "OS metadata in the canonical skill must not be treated as a change",
        )

    def test_os_metadata_is_not_copied_into_installed_skills(self) -> None:
        engine = _copy_engine(self.tmp / "engine")
        (engine / "skills" / "apply-app-harness" / ".DS_Store").write_bytes(b"\x00\x01junk")
        project = self.tmp / "app"
        self._install(project, engine)

        self.assertFalse(
            (project / ".claude" / "skills" / "apply-app-harness" / ".DS_Store").exists(),
            "OS metadata must not ship into an installed skill",
        )


if __name__ == "__main__":
    unittest.main()
