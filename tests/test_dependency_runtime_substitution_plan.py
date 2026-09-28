from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_runtime_substitution_plan import (
    DependencyRuntimeSubstitutionPlanError,
    build_dependency_runtime_substitution_plan,
)
from spk_recovery.dependency_runtime_substitution_apply import (
    DependencyRuntimeSubstitutionApplyError,
    apply_dependency_runtime_substitution,
    verify_dependency_runtime_substitution_postimage,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DependencyRuntimeSubstitutionPlanTests(unittest.TestCase):
    def _fixture(self, root: Path) -> dict:
        bundled = root / "bundled.jar"
        with zipfile.ZipFile(bundled, "w", zipfile.ZIP_STORED) as archive:
            archive.writestr("old/A.class", b"bundled-A")
            archive.writestr("old/Residual.class", b"residual")
            archive.writestr("META-INF/services/example.Service", b"old.A\n")
            archive.writestr("keep.txt", b"keep")

        official = root / "official.jar"
        with zipfile.ZipFile(official, "w", zipfile.ZIP_STORED) as archive:
            archive.writestr("official/A.class", b"official-A")
            archive.writestr("META-INF/services/example.Service", b"old.A\n")

        bundled_sha = _sha(bundled)
        official_sha = _sha(official)
        replacement_id = "DEPREPLACE_" + "1" * 20
        extension_id = "DEPREPLACEEXT_" + "2" * 20
        closure_id = "DEPRUNTIMEEXTCLOSURE_" + "3" * 20
        resource_id = "DEPRUNTIMEEXTRESOURCE_" + "4" * 20
        readiness_id = "DEPRUNTIMEREADY_" + "5" * 20

        replacement = {
            "schema_version": 1,
            "kind": "dependency_replacement_boundary_plan",
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "owners": [
                {
                    "owner_id": "DEPOWNER_00001",
                    "classification": "official_replaceable",
                    "old_owner": "old/A",
                    "new_owner": "official/A",
                    "artifact": "official.jar",
                },
                {
                    "owner_id": "DEPOWNER_00002",
                    "classification": "residual_bundled",
                    "old_owner": "old/Residual",
                    "new_owner": None,
                    "artifact": None,
                },
            ],
            "identifiers_included": True,
        }
        replacement_path = root / "replacement.json"
        replacement_path.write_text(json.dumps(replacement) + "\n", encoding="utf-8")

        extension = {
            "schema_version": 1,
            "kind": "dependency_replacement_extension",
            "replacement_extension_id": extension_id,
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "promoted_rows": [],
            "combined_owner_rows": replacement["owners"],
            "identifiers_included": True,
        }
        extension_path = root / "extension.json"
        extension_path.write_text(json.dumps(extension) + "\n", encoding="utf-8")

        resource = {
            "schema_version": 1,
            "kind": "dependency_runtime_extended_resource_equivalence",
            "runtime_extended_resource_id": resource_id,
            "runtime_extended_closure_id": closure_id,
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": [official_sha],
            "resources": [
                {
                    "resource_id": "RESOURCE_1",
                    "entry": "META-INF/services/example.Service",
                    "status": "exact_byte_match",
                    "service_entry": True,
                    "providers": [
                        {
                            "artifact": "official.jar",
                            "sha256": hashlib.sha256(b"old.A\n").hexdigest(),
                            "bytes": len(b"old.A\n"),
                        }
                    ],
                }
            ],
            "identifiers_included": True,
        }
        resource_path = root / "resource.json"
        resource_path.write_text(json.dumps(resource) + "\n", encoding="utf-8")

        closure = {
            "schema_version": 1,
            "kind": "dependency_runtime_extended_closure",
            "runtime_extended_closure_id": closure_id,
            "replacement_plan_id": replacement_id,
            "replacement_extension_id": extension_id,
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": [official_sha],
            "dynamic_roots": [],
            "new_owners": [],
            "identifiers_included": True,
        }
        closure_path = root / "closure.json"
        closure_path.write_text(
            json.dumps(closure) + "\n",
            encoding="utf-8",
        )

        readiness = {
            "schema_version": 1,
            "kind": "dependency_runtime_substitution_readiness",
            "runtime_readiness_id": readiness_id,
            "runtime_extended_closure_id": closure_id,
            "runtime_extended_resource_id": resource_id,
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": [official_sha],
            "summary": {
                "class_closure_ready": True,
                "dynamic_target_ready": True,
                "resource_equivalence_ready": True,
                "native_runtime_ready": True,
                "runtime_dependency_substitution_ready": True,
            },
        }
        readiness_path = root / "readiness.json"
        readiness_path.write_text(json.dumps(readiness) + "\n", encoding="utf-8")

        return {
            "bundled": bundled,
            "official": official,
            "replacement": replacement_path,
            "extension": extension_path,
            "closure": closure_path,
            "resource": resource_path,
            "readiness": readiness_path,
        }

    def _private_plan(self, root: Path, fx: dict) -> Path:
        report = build_dependency_runtime_substitution_plan(
            fx["readiness"],
            fx["replacement"],
            fx["extension"],
            fx["closure"],
            fx["resource"],
            fx["bundled"],
            [fx["official"]],
            include_identifiers=True,
        )
        path = root / "substitution-plan.json"
        path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def test_ready_authority_produces_plan_but_never_apply_authority(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_substitution_plan(
                fx["readiness"],
                fx["replacement"],
                fx["extension"],
                fx["closure"],
                fx["resource"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )
            self.assertEqual(
                report["kind"],
                "dependency_runtime_substitution_plan",
            )
            self.assertEqual(report["summary"]["class_removal_count"], 1)
            self.assertEqual(report["summary"]["resource_removal_count"], 1)
            self.assertEqual(
                report["summary"]["required_official_artifact_count"],
                1,
            )
            self.assertTrue(report["summary"]["preimage_verified"])
            self.assertTrue(report["summary"]["official_artifacts_verified"])
            self.assertFalse(report["apply_authorized"])
            self.assertFalse(report["summary"]["apply_authorized"])
            self.assertEqual(
                report["class_removals"][0]["entry"],
                "old/A.class",
            )

    def test_not_ready_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            readiness = json.loads(fx["readiness"].read_text(encoding="utf-8"))
            readiness["summary"]["native_runtime_ready"] = False
            readiness["summary"]["runtime_dependency_substitution_ready"] = False
            fx["readiness"].write_text(
                json.dumps(readiness) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DependencyRuntimeSubstitutionPlanError,
                "not fully ready",
            ):
                build_dependency_runtime_substitution_plan(
                    fx["readiness"],
                    fx["replacement"],
                    fx["extension"],
                    fx["closure"],
                    fx["resource"],
                    fx["bundled"],
                    [fx["official"]],
                )

    def test_retained_resource_overlap_is_informational(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            with zipfile.ZipFile(
                fx["official"],
                "a",
                zipfile.ZIP_STORED,
            ) as archive:
                archive.writestr("keep.txt", b"official-copy")

            official_sha = _sha(fx["official"])
            for path in (
                fx["readiness"],
                fx["closure"],
                fx["resource"],
            ):
                value = json.loads(path.read_text(encoding="utf-8"))
                value["official_artifact_sha256"] = [official_sha]
                path.write_text(
                    json.dumps(value) + "\n",
                    encoding="utf-8",
                )

            report = build_dependency_runtime_substitution_plan(
                fx["readiness"],
                fx["replacement"],
                fx["extension"],
                fx["closure"],
                fx["resource"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )
            self.assertTrue(report["summary"]["collision_free"])
            self.assertEqual(report["summary"]["collision_count"], 0)
            self.assertEqual(
                report["summary"]["resource_overlap_count"],
                1,
            )
            self.assertIn(
                "retained_bundled_official",
                {row["kind"] for row in report["resource_overlaps"]},
            )

    def test_retained_class_collision_remains_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            with zipfile.ZipFile(
                fx["official"],
                "a",
                zipfile.ZIP_STORED,
            ) as archive:
                archive.writestr(
                    "old/Residual.class",
                    b"official-collision",
                )

            official_sha = _sha(fx["official"])
            for path in (
                fx["readiness"],
                fx["closure"],
                fx["resource"],
            ):
                value = json.loads(path.read_text(encoding="utf-8"))
                value["official_artifact_sha256"] = [official_sha]
                path.write_text(
                    json.dumps(value) + "\n",
                    encoding="utf-8",
                )

            report = build_dependency_runtime_substitution_plan(
                fx["readiness"],
                fx["replacement"],
                fx["extension"],
                fx["closure"],
                fx["resource"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )
            self.assertFalse(report["summary"]["collision_free"])
            self.assertEqual(report["summary"]["collision_count"], 1)
            self.assertIn(
                "retained_bundled_official",
                {row["kind"] for row in report["collisions"]},
            )

    def test_plan_id_binds_exact_private_entry_set(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            first = build_dependency_runtime_substitution_plan(
                fx["readiness"],
                fx["replacement"],
                fx["extension"],
                fx["closure"],
                fx["resource"],
                fx["bundled"],
                [fx["official"]],
            )

            extension = json.loads(
                fx["extension"].read_text(encoding="utf-8")
            )
            extension["combined_owner_rows"][0]["old_owner"] = (
                "old/Residual"
            )
            fx["extension"].write_text(
                json.dumps(extension) + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                DependencyRuntimeSubstitutionPlanError
            ):
                build_dependency_runtime_substitution_plan(
                    fx["readiness"],
                    fx["replacement"],
                    fx["extension"],
                    fx["closure"],
                    fx["resource"],
                    fx["bundled"],
                    [fx["official"]],
                )

            self.assertTrue(first["runtime_substitution_plan_id"])

    def test_wrong_replacement_extension_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            closure = json.loads(
                fx["closure"].read_text(encoding="utf-8")
            )
            closure["replacement_extension_id"] = (
                "DEPREPLACEEXT_" + "9" * 20
            )
            fx["closure"].write_text(
                json.dumps(closure) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DependencyRuntimeSubstitutionPlanError,
                "different replacement extension",
            ):
                build_dependency_runtime_substitution_plan(
                    fx["readiness"],
                    fx["replacement"],
                    fx["extension"],
                    fx["closure"],
                    fx["resource"],
                    fx["bundled"],
                    [fx["official"]],
                )

    def test_apply_builds_verified_residual_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fx = self._fixture(root)
            plan = self._private_plan(root, fx)
            out = root / "postimage"

            manifest = apply_dependency_runtime_substitution(
                plan,
                fx["bundled"],
                [fx["official"]],
                out,
            )

            self.assertTrue(manifest["verified"])
            self.assertEqual(
                manifest["runtime_classpath"],
                [
                    "residual-dependency-capsule.jar",
                    "official/official.jar",
                ],
            )
            with zipfile.ZipFile(
                out / "residual-dependency-capsule.jar"
            ) as archive:
                names = set(archive.namelist())
                self.assertIn("old/Residual.class", names)
                self.assertIn("keep.txt", names)
                self.assertNotIn("old/A.class", names)
                self.assertNotIn(
                    "META-INF/services/example.Service",
                    names,
                )
            self.assertEqual(
                (out / "official" / "official.jar").read_bytes(),
                fx["official"].read_bytes(),
            )

            verified = verify_dependency_runtime_substitution_postimage(
                plan,
                fx["bundled"],
                [fx["official"]],
                out,
            )
            self.assertEqual(
                verified["runtime_postimage_id"],
                manifest["runtime_postimage_id"],
            )

    def test_apply_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fx = self._fixture(root)
            plan = self._private_plan(root, fx)

            first = apply_dependency_runtime_substitution(
                plan,
                fx["bundled"],
                [fx["official"]],
                root / "postimage-a",
            )
            second = apply_dependency_runtime_substitution(
                plan,
                fx["bundled"],
                [fx["official"]],
                root / "postimage-b",
            )

            self.assertEqual(
                first["residual_capsule_sha256"],
                second["residual_capsule_sha256"],
            )
            self.assertEqual(
                first["runtime_postimage_id"],
                second["runtime_postimage_id"],
            )
            self.assertEqual(
                (root / "postimage-a" / "residual-dependency-capsule.jar").read_bytes(),
                (root / "postimage-b" / "residual-dependency-capsule.jar").read_bytes(),
            )

    def test_postimage_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fx = self._fixture(root)
            plan = self._private_plan(root, fx)
            out = root / "postimage"
            apply_dependency_runtime_substitution(
                plan,
                fx["bundled"],
                [fx["official"]],
                out,
            )

            with zipfile.ZipFile(
                out / "residual-dependency-capsule.jar",
                "a",
                zipfile.ZIP_STORED,
            ) as archive:
                archive.writestr("tampered.txt", b"no")

            with self.assertRaisesRegex(
                DependencyRuntimeSubstitutionApplyError,
                "residual capsule bytes differ",
            ):
                verify_dependency_runtime_substitution_postimage(
                    plan,
                    fx["bundled"],
                    [fx["official"]],
                    out,
                )

    def test_tampered_private_plan_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fx = self._fixture(root)
            plan = self._private_plan(root, fx)
            value = json.loads(plan.read_text(encoding="utf-8"))
            value["runtime_substitution_plan_id"] = (
                "DEPRUNTIMESUBPLAN_" + "F" * 20
            )
            plan.write_text(
                json.dumps(value) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DependencyRuntimeSubstitutionApplyError,
                "plan ID does not verify",
            ):
                apply_dependency_runtime_substitution(
                    plan,
                    fx["bundled"],
                    [fx["official"]],
                    root / "postimage",
                )

    def test_public_and_private_reports_share_plan_id(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            public = build_dependency_runtime_substitution_plan(
                fx["readiness"],
                fx["replacement"],
                fx["extension"],
                fx["closure"],
                fx["resource"],
                fx["bundled"],
                [fx["official"]],
            )
            private = build_dependency_runtime_substitution_plan(
                fx["readiness"],
                fx["replacement"],
                fx["extension"],
                fx["closure"],
                fx["resource"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )
            self.assertEqual(
                public["runtime_substitution_plan_id"],
                private["runtime_substitution_plan_id"],
            )
            self.assertNotIn("old/A.class", json.dumps(public))
            self.assertIn("old/A.class", json.dumps(private))


if __name__ == "__main__":
    unittest.main()
