"""Prove the evidence verifier fails when it should.

A checker only observed passing is not a checker.  Each case here seeds a real
defect and asserts the verifier catches it — especially the mismatch case, which
is the one that matters: a file that no longer hashes to its recorded id is not
the artifact the claim was made against, and must never be quietly re-hashed
into a pass.

Stdlib-only, like the portability suite.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.verify_evidence import EvidenceError, verify  # noqa: E402


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class EvidenceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _catalog(self, sources: list[dict]) -> Path:
        path = self.tmp / "catalog.json"
        path.write_text(
            json.dumps({"catalog_id": "test-catalog", "sources": sources}), encoding="utf-8"
        )
        return path

    def _vendor(self, relative: str, content: bytes) -> str:
        path = self.tmp / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return _sha256(content)


class TestVerifiedArtifacts(EvidenceTestCase):
    def test_matching_bytes_verify(self) -> None:
        digest = self._vendor("vendored/report.md", b"evidence bytes\n")
        catalog = self._catalog([{
            "id": "s1", "resolution": "vendored",
            "artifacts": [{"role": "report", "content_id": f"sha256:{digest}",
                           "path": "vendored/report.md"}],
        }])

        report = verify(catalog, root=self.tmp)

        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["verifiable_offline"])
        self.assertEqual(report["counts"], {"verified": 1})

    def test_bare_hash_without_the_sha256_prefix_is_accepted(self) -> None:
        digest = self._vendor("vendored/report.md", b"evidence bytes\n")
        catalog = self._catalog([{
            "id": "s1", "resolution": "vendored",
            "artifacts": [{"role": "report", "content_id": digest, "path": "vendored/report.md"}],
        }])

        self.assertEqual(verify(catalog, root=self.tmp)["status"], "pass")


class TestSeededDefectsAreCaught(EvidenceTestCase):
    def test_changed_bytes_are_reported_as_mismatch_not_rehashed(self) -> None:
        recorded = _sha256(b"the bytes the claim was made against\n")
        self._vendor("vendored/report.md", b"different bytes entirely\n")
        catalog = self._catalog([{
            "id": "s1", "resolution": "vendored",
            "artifacts": [{"role": "report", "content_id": f"sha256:{recorded}",
                           "path": "vendored/report.md"}],
        }])

        report = verify(catalog, root=self.tmp)
        artifact = report["results"][0]["artifacts"][0]

        self.assertEqual(report["status"], "fail")
        self.assertEqual(artifact["state"], "mismatch")
        # The recorded id must survive the report unchanged: it is the claim.
        self.assertEqual(artifact["content_id"], f"sha256:{recorded}")
        self.assertNotEqual(artifact["observed_sha256"], recorded)

    def test_vendored_but_absent_is_reported_as_missing(self) -> None:
        catalog = self._catalog([{
            "id": "s1", "resolution": "vendored",
            "artifacts": [{"role": "report", "content_id": f"sha256:{'0' * 64}",
                           "path": "vendored/never-copied.pdf"}],
        }])

        report = verify(catalog, root=self.tmp)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["results"][0]["artifacts"][0]["state"], "missing")

    def test_absolute_path_is_rejected(self) -> None:
        catalog = self._catalog([{
            "id": "s1", "resolution": "vendored",
            "artifacts": [{"role": "report", "content_id": f"sha256:{'0' * 64}",
                           "path": "/Users/someone/Downloads/report.pdf"}],
        }])

        report = verify(catalog, root=self.tmp)
        artifact = report["results"][0]["artifacts"][0]

        self.assertEqual(report["status"], "fail")
        self.assertEqual(artifact["state"], "invalid")
        self.assertIn("repo-relative", artifact["detail"])

    def test_vendored_without_a_content_id_is_rejected(self) -> None:
        self._vendor("vendored/report.md", b"bytes\n")
        catalog = self._catalog([{
            "id": "s1", "resolution": "vendored",
            "artifacts": [{"role": "report", "content_id": None, "path": "vendored/report.md"}],
        }])

        report = verify(catalog, root=self.tmp)

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["results"][0]["artifacts"][0]["state"], "invalid")

    def test_unknown_resolution_is_rejected(self) -> None:
        catalog = self._catalog([{"id": "s1", "resolution": "probably-fine", "artifacts": []}])

        self.assertEqual(verify(catalog, root=self.tmp)["status"], "fail")

    def test_unreadable_catalog_raises(self) -> None:
        with self.assertRaises(EvidenceError):
            verify(self.tmp / "does-not-exist.json", root=self.tmp)


class TestExternalIsHonestNotHidden(EvidenceTestCase):
    def test_external_source_passes_but_is_not_verifiable_offline(self) -> None:
        catalog = self._catalog([{
            "id": "s1", "resolution": "external-unverifiable",
            "artifacts": [{"role": "paper", "content_id": None,
                           "path": "vendored/never-fetched.pdf"}],
        }])

        report = verify(catalog, root=self.tmp)

        # Not a failure — an unvendored claim is a real state, not a bug.
        self.assertEqual(report["status"], "pass")
        # But it must never read as fully checkable.
        self.assertFalse(report["verifiable_offline"])
        self.assertEqual(report["results"][0]["artifacts"][0]["state"], "external")

    def test_external_whose_bytes_are_present_is_flagged_promotable(self) -> None:
        self._vendor("vendored/arrived.pdf", b"someone vendored this\n")
        catalog = self._catalog([{
            "id": "s1", "resolution": "external-unverifiable",
            "artifacts": [{"role": "paper", "content_id": None, "path": "vendored/arrived.pdf"}],
        }])

        report = verify(catalog, root=self.tmp)

        self.assertEqual(report["results"][0]["artifacts"][0]["state"], "promotable")


class TestRepositoryCatalog(unittest.TestCase):
    """The shipped catalog must itself be well-formed."""

    def test_shipped_catalog_is_structurally_valid(self) -> None:
        report = verify(ROOT / "evals" / "references" / "ftpo-evidence-catalog-1.1.0.json")

        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["verifiable_offline"])

    def test_frozen_catalog_1_0_0_is_left_untouched(self) -> None:
        """1.0.0's sha256 is a recorded build input; editing it would lie."""

        frozen = ROOT / "evals" / "references" / "ftpo-evidence-catalog-1.0.0.json"
        receipt = json.loads(
            (ROOT / "artifacts" / "ftpo-build-cycle-0010" / "build-receipt.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertTrue(frozen.is_file())
        self.assertEqual(
            _sha256(frozen.read_bytes()),
            receipt["input_hashes"]["evidence_catalog"],
            "catalog 1.0.0 no longer hashes to the value recorded in build-receipt.json; "
            "the build's provenance link is broken",
        )


if __name__ == "__main__":
    unittest.main()
