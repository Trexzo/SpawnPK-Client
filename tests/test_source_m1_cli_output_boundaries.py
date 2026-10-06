from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from spk_recovery import source_authority_artifact_cli
from spk_recovery import source_milestone_cli


class SourceM1CliOutputBoundaryTests(unittest.TestCase):
    def _common_build_args(
        self,
        root: Path,
        source: Path,
        out: Path,
    ) -> list[str]:
        return [
            "build",
            "--authority-commit",
            "f" * 40,
            "--class-lineage",
            str(root / "class-lineage.json"),
            "--member-lineage",
            str(root / "member-lineage.json"),
            "--readable-manifest",
            str(root / "readable.json"),
            "--recovered-manifest",
            str(root / "recovered.json"),
            "--clean-rebuild",
            str(root / "clean.json"),
            "--release-manifest",
            str(root / "release.json"),
            "--release-verification",
            str(root / "verification.json"),
            "--source-root",
            str(source),
            "--out",
            str(out),
        ]

    def test_milestone_build_refuses_output_inside_source_before_build(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            out = source / "SOURCE-MILESTONE.json"

            with mock.patch.object(
                source_milestone_cli,
                "build_source_milestone_manifest",
                side_effect=AssertionError("core build must not run"),
            ) as core:
                code = source_milestone_cli.main(
                    self._common_build_args(root, source, out)
                )

            self.assertEqual(code, 2)
            core.assert_not_called()
            self.assertFalse(out.exists())

    def test_milestone_verify_refuses_overwriting_manifest_before_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            manifest = root / "manifest.json"

            args = self._common_build_args(
                root,
                source,
                root / "unused.json",
            )
            args[0] = "verify"
            args.extend(["--manifest", str(manifest)])
            out_index = args.index("--out") + 1
            args[out_index] = str(manifest)

            with mock.patch.object(
                source_milestone_cli,
                "verify_source_milestone_manifest",
                side_effect=AssertionError("core verify must not run"),
            ) as core:
                code = source_milestone_cli.main(args)

            self.assertEqual(code, 2)
            core.assert_not_called()
            self.assertFalse(manifest.exists())

    def test_bundle_verify_refuses_output_inside_bundle_before_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = root / "bundle"
            bundle.mkdir()
            out = bundle / "verification.json"

            with mock.patch.object(
                source_milestone_cli,
                "verify_source_publication_bundle",
                side_effect=AssertionError("bundle verify must not run"),
            ) as core:
                code = source_milestone_cli.main(
                    [
                        "verify-bundle",
                        "--bundle-dir",
                        str(bundle),
                        "--manifest",
                        str(root / "manifest.json"),
                        "--expected-authority-commit",
                        "f" * 40,
                        "--out",
                        str(out),
                    ]
                )

            self.assertEqual(code, 2)
            core.assert_not_called()
            self.assertFalse(out.exists())

    def test_artifact_verify_refuses_output_inside_artifact_before_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifact = root / "artifact"
            artifact.mkdir()
            out = artifact / "verification.json"

            with mock.patch.object(
                source_authority_artifact_cli,
                "verify_source_authority_artifact",
                side_effect=AssertionError("artifact verify must not run"),
            ) as core:
                code = source_authority_artifact_cli.main(
                    [
                        "verify",
                        "--artifact-dir",
                        str(artifact),
                        "--expected-authority-commit",
                        "f" * 40,
                        "--expected-milestone-id",
                        "SRCMILESTONE_" + "A" * 20,
                        "--out",
                        str(out),
                    ]
                )

            self.assertEqual(code, 2)
            core.assert_not_called()
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
