from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_replacement_extension import (
    DependencyReplacementExtensionError,
    build_dependency_replacement_extension,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DependencyReplacementExtensionTests(unittest.TestCase):
    def _compile(
        self,
        root: Path,
        package: str,
        names: tuple[str, ...],
        prefix: str,
    ) -> Path:
        src = root / f"{prefix}-src" / package
        src.mkdir(parents=True)
        paths: list[Path] = []
        for name in names:
            path = src / f"{name}.java"
            path.write_text(
                f"package {package}; public class {name} {{}}\n",
                encoding="utf-8",
            )
            paths.append(path)
        out = root / f"{prefix}-classes"
        out.mkdir()
        proc = subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-d",
                str(out),
                *[str(path) for path in paths],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return out

    def _fixture(
        self,
        root: Path,
        *,
        complete: bool = True,
        conflicting_static: bool = False,
    ) -> dict[str, Path]:
        bundled_classes = self._compile(
            root,
            "old",
            ("Static", "Dynamic"),
            "bundled",
        )
        official_classes = self._compile(
            root,
            "official",
            ("Static", "Dynamic"),
            "official",
        )

        bundled = root / "bundled.jar"
        with zipfile.ZipFile(
            bundled,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            for name in ("Static", "Dynamic"):
                archive.write(
                    bundled_classes / "old" / f"{name}.class",
                    f"old/{name}.class",
                )

        official = root / "official.jar"
        with zipfile.ZipFile(
            official,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            for name in ("Static", "Dynamic"):
                archive.write(
                    official_classes / "official" / f"{name}.class",
                    f"official/{name}.class",
                )

        bundled_sha = _sha(bundled)
        official_sha = _sha(official)
        replacement_id = "DEPREPLACE_" + "1" * 20
        dynamic_id = "DEPRUNTIMEDYNMAP_" + "2" * 20
        member_id = "DEPRUNTIMEDYNMEMBER_" + "3" * 20

        owners = [
            {
                "owner_id": "DEPOWNER_00001",
                "classification": "official_replaceable",
                "old_owner": "old/Static",
                "new_owner": "official/Static",
                "artifact": "official.jar",
            }
        ]
        if conflicting_static:
            owners.append(
                {
                    "owner_id": "DEPOWNER_00002",
                    "classification": "official_replaceable",
                    "old_owner": "old/Dynamic",
                    "new_owner": "official/Static",
                    "artifact": "official.jar",
                }
            )

        plan = {
            "schema_version": 1,
            "kind": "dependency_replacement_boundary_plan",
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "java_release": 9,
            "project_prefixes": ["rs/"],
            "official_artifacts": [
                {
                    "artifact": "official.jar",
                    "sha256": official_sha,
                    "multi_release_class_count": 0,
                    "java_release": 9,
                }
            ],
            "owners": owners,
            "identifiers_included": True,
        }
        plan_path = root / "replacement.json"
        plan_path.write_text(
            json.dumps(plan, indent=2) + "\n",
            encoding="utf-8",
        )

        dynamic = {
            "schema_version": 1,
            "kind": "dependency_runtime_dynamic_mapping_proof",
            "runtime_dynamic_mapping_id": dynamic_id,
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": [official_sha],
            "rows": [
                {
                    "dynamic_mapping_id": "DEPDYNMAPROW_00001",
                    "status": "accepted_class_mapping",
                    "strategy": "unique_structural",
                    "old_owner": "old/Dynamic",
                    "new_owner": "official/Dynamic",
                    "artifact": "official.jar",
                }
            ],
            "identifiers_included": True,
        }
        dynamic_path = root / "dynamic.json"
        dynamic_path.write_text(
            json.dumps(dynamic, indent=2) + "\n",
            encoding="utf-8",
        )

        member = {
            "schema_version": 1,
            "kind": "dependency_runtime_dynamic_member_proof",
            "runtime_dynamic_member_id": member_id,
            "runtime_dynamic_mapping_id": dynamic_id,
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": [official_sha],
            "classes": [
                {
                    "class_id": "DEPDYNCLASS_00001",
                    "source_dynamic_mapping_id": "DEPDYNMAPROW_00001",
                    "member_transport_complete": complete,
                    "old_owner": "old/Dynamic",
                    "new_owner": "official/Dynamic",
                    "artifact": "official.jar",
                }
            ],
            "members": [],
            "identifiers_included": True,
        }
        member_path = root / "member.json"
        member_path.write_text(
            json.dumps(member, indent=2) + "\n",
            encoding="utf-8",
        )

        return {
            "bundled": bundled,
            "official": official,
            "plan": plan_path,
            "dynamic": dynamic_path,
            "member": member_path,
        }

    def test_complete_dynamic_mapping_is_additively_promoted(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td), complete=True)
            report = build_dependency_replacement_extension(
                fx["plan"],
                fx["dynamic"],
                fx["member"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )

            self.assertEqual(
                report["kind"],
                "dependency_replacement_extension",
            )
            self.assertEqual(
                report["summary"]["promotion_eligible_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["promotion_blocked_count"],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "combined_official_replaceable_owner_count"
                ],
                2,
            )
            self.assertTrue(
                report["summary"][
                    "ready_for_augmented_closure_reaudit"
                ]
            )
            self.assertEqual(
                report["promoted_rows"][0]["old_owner"],
                "old/Dynamic",
            )
            self.assertEqual(
                report["promoted_rows"][0]["new_owner"],
                "official/Dynamic",
            )

    def test_incomplete_member_transport_blocks_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td), complete=False)
            report = build_dependency_replacement_extension(
                fx["plan"],
                fx["dynamic"],
                fx["member"],
                fx["bundled"],
                [fx["official"]],
            )

            self.assertEqual(
                report["summary"]["promotion_eligible_count"],
                0,
            )
            self.assertEqual(
                report["summary"]["promotion_blocked_count"],
                1,
            )
            self.assertFalse(
                report["summary"][
                    "ready_for_augmented_closure_reaudit"
                ]
            )

    def test_conflicting_static_authority_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(
                Path(td),
                complete=True,
                conflicting_static=True,
            )
            with self.assertRaisesRegex(
                DependencyReplacementExtensionError,
                "conflicts with existing DEPREPLACE",
            ):
                build_dependency_replacement_extension(
                    fx["plan"],
                    fx["dynamic"],
                    fx["member"],
                    fx["bundled"],
                    [fx["official"]],
                )

    def test_public_and_private_reports_share_extension_id(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td), complete=True)
            public = build_dependency_replacement_extension(
                fx["plan"],
                fx["dynamic"],
                fx["member"],
                fx["bundled"],
                [fx["official"]],
            )
            private = build_dependency_replacement_extension(
                fx["plan"],
                fx["dynamic"],
                fx["member"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )

            self.assertEqual(
                public["replacement_extension_id"],
                private["replacement_extension_id"],
            )
            rendered = json.dumps(public)
            self.assertNotIn("old/Dynamic", rendered)
            self.assertNotIn("official/Dynamic", rendered)


if __name__ == "__main__":
    unittest.main()
