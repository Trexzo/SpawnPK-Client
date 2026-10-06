from __future__ import annotations

from contextlib import redirect_stdout
import io
from unittest import mock
import unittest

from spk_recovery import source_authority_artifact_cli


class SourceAuthorityArtifactCliTests(unittest.TestCase):
    def test_build_defaults_publication_to_authority_repository(self):
        fake_report = {
            "artifact_id": "SRCAUTHART_TEST",
            "preflight_milestone_id": "SRCMILESTONE_TEST",
            "source_tree_sha256": "a" * 64,
            "source_file_count": 1,
        }

        argv = [
            "build",
            "--authority-commit",
            "f" * 40,
            "--class-lineage",
            "class-lineage.json",
            "--member-lineage",
            "member-lineage.json",
            "--readable-manifest",
            "readable-client-manifest.json",
            "--recovered-manifest",
            "recovered-source-manifest.json",
            "--clean-rebuild",
            "clean-rebuild.json",
            "--release-manifest",
            "recovery-release.json",
            "--release-verification",
            "release-verification.json",
            "--source-root",
            "src",
            "--out-dir",
            "authority",
        ]

        with (
            mock.patch.object(
                source_authority_artifact_cli,
                "load_authority_artifact_inputs",
                return_value={},
            ),
            mock.patch.object(
                source_authority_artifact_cli,
                "build_source_authority_artifact",
                return_value=fake_report,
            ) as build,
            redirect_stdout(io.StringIO()),
        ):
            code = source_authority_artifact_cli.main(argv)

        self.assertEqual(code, 0)
        kwargs = build.call_args.kwargs
        self.assertEqual(
            kwargs["authority_repository"],
            "Trexzo/SpawnPK-Client",
        )
        self.assertEqual(
            kwargs["publication_repository"],
            "Trexzo/SpawnPK-Client",
        )


if __name__ == "__main__":
    unittest.main()
