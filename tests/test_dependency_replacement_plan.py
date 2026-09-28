from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_replacement_plan import (
    DependencyReplacementPlanError,
    build_dependency_replacement_plan,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DependencyReplacementPlanTests(unittest.TestCase):
    def _fixture(self, root: Path):
        src = root / "src" / "dep"
        src.mkdir(parents=True)

        sources = {
            "A.java": (
                "package dep; public class A { "
                "public void x() {} }\n"
            ),
            "B.java": (
                "package dep; public class B { "
                "public int y() { return 1; } }\n"
            ),
            "C.java": (
                "package dep; public class C { "
                "public String z() { return \"c\"; } }\n"
            ),
        }
        for name, text in sources.items():
            (src / name).write_text(text, encoding="utf-8")

        classes = root / "classes"
        classes.mkdir()
        proc = subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-d",
                str(classes),
                *[
                    str(src / name)
                    for name in sorted(sources)
                ],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            proc.stdout + proc.stderr,
        )

        bundled = root / "bundled.jar"
        with zipfile.ZipFile(
            bundled,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            for name in ("A", "B", "C"):
                entry = f"dep/{name}.class"
                archive.writestr(
                    entry,
                    (classes / "dep" / f"{name}.class").read_bytes(),
                )

        official = root / "official.jar"
        with zipfile.ZipFile(
            official,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr(
                "dep/A.class",
                (classes / "dep" / "A.class").read_bytes(),
            )

        official_sha = hashlib.sha256(
            official.read_bytes()
        ).hexdigest()
        bundled_sha = hashlib.sha256(
            bundled.read_bytes()
        ).hexdigest()
        artifact_rows = [
            {
                "artifact": "official.jar",
                "sha256": official_sha,
                "multi_release_class_count": 0,
                "java_release": 9,
            }
        ]

        surface = {
            "schema_version": 1,
            "kind": "project_non_project_reference_surface",
            "reference_surface_id": "DEPREF_" + "1" * 20,
            "class_references": [
                {"target": "dep/A", "source_class_count": 1},
                {"target": "dep/B", "source_class_count": 1},
                {"target": "dep/C", "source_class_count": 1},
                {
                    "target": "java/util/List",
                    "source_class_count": 1,
                },
            ],
            "member_references": [
                {
                    "kind": "method",
                    "owner": "dep/A",
                    "name": "x",
                    "descriptor": "()V",
                    "reference_count": 2,
                    "source_class_count": 1,
                },
                {
                    "kind": "method",
                    "owner": "dep/B",
                    "name": "y",
                    "descriptor": "()I",
                    "reference_count": 3,
                    "source_class_count": 1,
                },
                {
                    "kind": "method",
                    "owner": "dep/C",
                    "name": "z",
                    "descriptor": "()Ljava/lang/String;",
                    "reference_count": 4,
                    "source_class_count": 1,
                },
                {
                    "kind": "interface_method",
                    "owner": "java/util/List",
                    "name": "size",
                    "descriptor": "()I",
                    "reference_count": 5,
                    "source_class_count": 1,
                },
            ],
        }
        surface_path = root / "depref.json"
        surface_path.write_text(
            json.dumps(surface, indent=2) + "\n",
            encoding="utf-8",
        )

        remap = {
            "schema_version": 1,
            "kind": "dependency_structural_remap_proof",
            "dependency_remap_proof_id": "DEPREMAP_" + "2" * 20,
            "reference_surface_id": surface["reference_surface_id"],
            "bundled_jar_sha256": bundled_sha,
            "java_release": 9,
            "project_prefixes": ["rs/", "tools/"],
            "official_artifacts": artifact_rows,
            "referenced_class_mappings": [
                {
                    "old_name": "dep/A",
                    "new_name": "dep/A",
                    "strategy": "identity_structural",
                    "artifact": "official.jar",
                    "field_sequence_equal": True,
                    "ordinary_method_sequence_equal": True,
                }
            ],
            "member_results": [
                {
                    "kind": "method",
                    "old_owner": "dep/A",
                    "old_name": "x",
                    "old_descriptor": "()V",
                    "reference_count": 2,
                    "status": "accepted_identity",
                    "new_owner": "dep/A",
                    "new_name": "x",
                    "new_descriptor": "()V",
                    "artifact": "official.jar",
                },
                {
                    "kind": "method",
                    "old_owner": "dep/B",
                    "old_name": "y",
                    "old_descriptor": "()I",
                    "reference_count": 3,
                    "status": "bundled_unresolved_class",
                    "new_owner": None,
                    "new_name": None,
                    "new_descriptor": None,
                    "artifact": None,
                },
                {
                    "kind": "method",
                    "old_owner": "dep/C",
                    "old_name": "z",
                    "old_descriptor": "()Ljava/lang/String;",
                    "reference_count": 4,
                    "status": "bundled_unresolved_class",
                    "new_owner": None,
                    "new_name": None,
                    "new_descriptor": None,
                    "artifact": None,
                },
                {
                    "kind": "interface_method",
                    "old_owner": "java/util/List",
                    "old_name": "size",
                    "old_descriptor": "()I",
                    "reference_count": 5,
                    "status": "platform_runtime",
                    "new_owner": None,
                    "new_name": None,
                    "new_descriptor": None,
                    "artifact": None,
                },
            ],
        }
        remap_path = root / "depremap.json"
        remap_path.write_text(
            json.dumps(remap, indent=2) + "\n",
            encoding="utf-8",
        )

        retention = {
            "schema_version": 1,
            "kind": "dependency_source_retention_classification",
            "retention_report_id": "DEPRETAIN_" + "3" * 20,
            "reference_surface_id": surface["reference_surface_id"],
            "dependency_remap_proof_id": remap[
                "dependency_remap_proof_id"
            ],
            "bundled_jar_sha256": bundled_sha,
            "java_release": 9,
            "project_prefixes": ["rs/", "tools/"],
            "official_artifacts": artifact_rows,
            "classifications": [
                {
                    "class": "dep/C",
                    "status": "project_coupled_non_pom",
                }
            ],
            "member_reclassifications": [],
        }
        retention_path = root / "depretain.json"
        retention_path.write_text(
            json.dumps(retention, indent=2) + "\n",
            encoding="utf-8",
        )

        return (
            surface_path,
            remap_path,
            retention_path,
            bundled,
            official,
        )

    def test_four_way_replacement_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            (
                surface,
                remap,
                retention,
                bundled,
                official,
            ) = self._fixture(Path(td))

            report = build_dependency_replacement_plan(
                surface,
                remap,
                bundled,
                [official],
                retention_report_path=retention,
                include_identifiers=True,
            )

            self.assertEqual(
                report["summary"]["classification_counts"],
                {
                    "official_replaceable": 1,
                    "platform_runtime": 1,
                    "project_retained": 1,
                    "residual_bundled": 1,
                },
            )
            self.assertEqual(
                report["summary"][
                    "weighted_member_reference_counts"
                ],
                {
                    "official_replaceable": 2,
                    "platform_runtime": 5,
                    "project_retained": 4,
                    "residual_bundled": 3,
                },
            )
            by_owner = {
                row["old_owner"]: row
                for row in report["owners"]
            }
            self.assertEqual(
                by_owner["dep/A"]["classification"],
                "official_replaceable",
            )
            self.assertEqual(
                by_owner["dep/A"]["artifact"],
                "official.jar",
            )
            self.assertEqual(
                by_owner["dep/B"]["classification"],
                "residual_bundled",
            )
            self.assertEqual(
                by_owner["dep/C"]["classification"],
                "project_retained",
            )
            self.assertEqual(
                by_owner["java/util/List"]["classification"],
                "platform_runtime",
            )

    def test_public_private_authority_matches_and_redacts(self):
        with tempfile.TemporaryDirectory() as td:
            (
                surface,
                remap,
                retention,
                bundled,
                official,
            ) = self._fixture(Path(td))

            public = build_dependency_replacement_plan(
                surface,
                remap,
                bundled,
                [official],
                retention_report_path=retention,
            )
            private = build_dependency_replacement_plan(
                surface,
                remap,
                bundled,
                [official],
                retention_report_path=retention,
                include_identifiers=True,
            )

            self.assertEqual(
                public["replacement_plan_id"],
                private["replacement_plan_id"],
            )
            self.assertNotIn("dep/A", json.dumps(public))
            self.assertNotIn("official.jar", json.dumps(public))
            self.assertIn("dep/A", json.dumps(private))
            self.assertIn("official.jar", json.dumps(private))

    def test_official_artifact_sha_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            (
                surface,
                remap,
                retention,
                bundled,
                official,
            ) = self._fixture(Path(td))

            data = json.loads(remap.read_text(encoding="utf-8"))
            data["official_artifacts"][0]["sha256"] = "0" * 64
            remap.write_text(
                json.dumps(data, indent=2) + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(DependencyReplacementPlanError):
                build_dependency_replacement_plan(
                    surface,
                    remap,
                    bundled,
                    [official],
                    retention_report_path=retention,
                )


if __name__ == "__main__":
    unittest.main()
