from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from spk_recovery.source_authority_artifact import (
    SourceAuthorityArtifactError,
    _read_json as _artifact_read_json,
)
from spk_recovery.source_milestone import (
    SourceMilestoneError,
    verify_source_publication_bundle,
)
from spk_recovery.source_milestone_cli import (
    _load as _milestone_load_json,
)


class SourcePublicationJsonIntegrityTests(unittest.TestCase):
    def _duplicate_document(self, root: Path) -> Path:
        path = root / "duplicate.json"
        path.write_text(
            '{"kind":"first","kind":"second"}\n',
            encoding="utf-8",
        )
        return path

    def test_source_milestone_loader_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._duplicate_document(Path(td))
            with self.assertRaisesRegex(
                SourceMilestoneError,
                "duplicate JSON key: 'kind'",
            ):
                _milestone_load_json(path)

    def test_publication_bundle_verifier_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "bundle"
            root.mkdir()
            (root / "src").mkdir()
            provenance = root / "provenance"
            provenance.mkdir()
            (root / "BUNDLE.json").write_text(
                '{"kind":"source_publication_bundle","kind":"drift"}\n',
                encoding="utf-8",
            )
            (root / "SOURCE-MILESTONE.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            (provenance / "SOURCE-PROVENANCE.json").write_text(
                "{}\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                SourceMilestoneError,
                "duplicate JSON key: 'kind'",
            ):
                verify_source_publication_bundle(root)

    def test_source_authority_artifact_loader_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._duplicate_document(Path(td))
            with self.assertRaisesRegex(
                SourceAuthorityArtifactError,
                "duplicate JSON key: 'kind'",
            ):
                _artifact_read_json(path)


if __name__ == "__main__":
    unittest.main()
