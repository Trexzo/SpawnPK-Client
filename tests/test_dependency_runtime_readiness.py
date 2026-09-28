from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from spk_recovery.dependency_runtime_readiness import (
    DependencyRuntimeReadinessError,
    build_dependency_runtime_readiness,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DependencyRuntimeReadinessTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        blocked: bool = False,
    ) -> dict[str, Path]:
        bundled = root / "bundled.jar"
        official = root / "official.jar"
        bundled.write_bytes(b"bundled")
        official.write_bytes(b"official")

        bundled_sha = _sha(bundled)
        official_sha = _sha(official)
        closure_id = "DEPRUNTIMEEXTCLOSURE_" + "1" * 20
        resource_id = "DEPRUNTIMEEXTRESOURCE_" + "2" * 20
        target_id = "DEPRUNTIMEDYNAMICTARGET_" + "3" * 20
        replacement_id = "DEPREPLACE_" + "4" * 20
        base_resource_id = "DEPRUNTIMERESOURCE_" + "5" * 20

        if blocked:
            roots = [
                {
                    "extended_root_id": "ROOT_1",
                    "source_dynamic_target_id": "TARGET_1",
                    "status": "remaining_mapping_authority_gap",
                },
                {
                    "extended_root_id": "ROOT_3",
                    "source_dynamic_target_id": "TARGET_3",
                    "status": "authorized_dynamic_root",
                },
            ]
            closure_summary = {
                "static_class_closure_blocker_count": 0,
                "dynamic_closure_blocker_count": 1,
                "remaining_mapping_gap_count": 1,
                "native_dynamic_requirement_count": 1,
            }
            resource_summary = {
                "non_native_blocker_count": 1,
                "native_entry_count": 1,
                "native_blocker_count": 1,
                "resource_equivalence_complete": False,
            }
            targets = [
                {
                    "dynamic_target_id": "TARGET_1",
                    "category": "class_loading",
                    "classification": "bundled_unclassified",
                    "literal_target_proven": True,
                },
                {
                    "dynamic_target_id": "TARGET_2",
                    "category": "resource_loading",
                    "classification": "resource_bundled_only",
                    "literal_target_proven": True,
                },
                {
                    "dynamic_target_id": "TARGET_3",
                    "category": "service_loading",
                    "classification": (
                        "service_dependency_official_replaceable"
                    ),
                    "literal_target_proven": True,
                },
                {
                    "dynamic_target_id": "TARGET_4",
                    "category": "native_loading",
                    "classification": "native_runtime_requirement",
                    "literal_target_proven": True,
                },
            ]
        else:
            roots = [
                {
                    "extended_root_id": "ROOT_1",
                    "source_dynamic_target_id": "TARGET_1",
                    "status": "project_dynamic_target",
                }
            ]
            closure_summary = {
                "static_class_closure_blocker_count": 0,
                "dynamic_closure_blocker_count": 0,
                "remaining_mapping_gap_count": 0,
                "native_dynamic_requirement_count": 0,
            }
            resource_summary = {
                "non_native_blocker_count": 0,
                "native_entry_count": 0,
                "native_blocker_count": 0,
                "resource_equivalence_complete": True,
            }
            targets = [
                {
                    "dynamic_target_id": "TARGET_1",
                    "category": "class_loading",
                    "classification": "project_class",
                    "literal_target_proven": True,
                },
                {
                    "dynamic_target_id": "TARGET_2",
                    "category": "resource_loading",
                    "classification": "resource_official_equivalent",
                    "literal_target_proven": True,
                },
            ]

        closure = {
            "schema_version": 1,
            "kind": "dependency_runtime_extended_closure",
            "runtime_extended_closure_id": closure_id,
            "replacement_plan_id": replacement_id,
            "runtime_dynamic_target_id": target_id,
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": [official_sha],
            "summary": closure_summary,
            "dynamic_roots": roots,
        }
        closure_path = root / "closure.json"
        closure_path.write_text(
            json.dumps(closure, indent=2) + "\n",
            encoding="utf-8",
        )

        resource = {
            "schema_version": 1,
            "kind": "dependency_runtime_extended_resource_equivalence",
            "runtime_extended_resource_id": resource_id,
            "runtime_extended_closure_id": closure_id,
            "runtime_resource_id": base_resource_id,
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": [official_sha],
            "summary": resource_summary,
        }
        resource_path = root / "resource.json"
        resource_path.write_text(
            json.dumps(resource, indent=2) + "\n",
            encoding="utf-8",
        )

        dynamic = {
            "schema_version": 1,
            "kind": "dependency_runtime_dynamic_target_classification",
            "runtime_dynamic_target_id": target_id,
            "runtime_resource_id": base_resource_id,
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "targets": targets,
        }
        dynamic_path = root / "dynamic.json"
        dynamic_path.write_text(
            json.dumps(dynamic, indent=2) + "\n",
            encoding="utf-8",
        )

        return {
            "bundled": bundled,
            "official": official,
            "closure": closure_path,
            "resource": resource_path,
            "dynamic": dynamic_path,
        }

    def test_all_composed_gates_can_be_ready(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_readiness(
                fx["closure"],
                fx["resource"],
                fx["dynamic"],
                fx["bundled"],
                [fx["official"]],
            )
            summary = report["summary"]
            self.assertTrue(summary["class_closure_ready"])
            self.assertTrue(summary["dynamic_target_ready"])
            self.assertTrue(summary["resource_equivalence_ready"])
            self.assertTrue(summary["native_runtime_ready"])
            self.assertTrue(
                summary["runtime_dependency_substitution_ready"]
            )

    def test_blockers_remain_separate_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td), blocked=True)
            report = build_dependency_runtime_readiness(
                fx["closure"],
                fx["resource"],
                fx["dynamic"],
                fx["bundled"],
                [fx["official"]],
            )
            summary = report["summary"]
            self.assertFalse(summary["class_closure_ready"])
            self.assertFalse(summary["dynamic_target_ready"])
            self.assertFalse(summary["resource_equivalence_ready"])
            self.assertFalse(summary["native_runtime_ready"])
            self.assertFalse(
                summary["runtime_dependency_substitution_ready"]
            )
            self.assertEqual(
                summary["remaining_mapping_gap_count"],
                1,
            )
            self.assertEqual(
                summary["service_provider_discovery_blocker_count"],
                1,
            )
            self.assertEqual(
                summary["dynamic_resource_target_blocker_count"],
                1,
            )
            self.assertEqual(
                summary["native_dynamic_loading_blocker_count"],
                1,
            )

    def test_missing_required_summary_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            closure = json.loads(
                fx["closure"].read_text(encoding="utf-8")
            )
            del closure["summary"][
                "static_class_closure_blocker_count"
            ]
            fx["closure"].write_text(
                json.dumps(closure) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DependencyRuntimeReadinessError,
                "static_class_closure_blocker_count",
            ):
                build_dependency_runtime_readiness(
                    fx["closure"],
                    fx["resource"],
                    fx["dynamic"],
                    fx["bundled"],
                    [fx["official"]],
                )

    def test_resource_ancestry_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            resource = json.loads(
                fx["resource"].read_text(encoding="utf-8")
            )
            resource["runtime_resource_id"] = (
                "DEPRUNTIMERESOURCE_" + "9" * 20
            )
            fx["resource"].write_text(
                json.dumps(resource) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DependencyRuntimeReadinessError,
                "different R8DEP26",
            ):
                build_dependency_runtime_readiness(
                    fx["closure"],
                    fx["resource"],
                    fx["dynamic"],
                    fx["bundled"],
                    [fx["official"]],
                )

    def test_cross_authority_id_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            resource = json.loads(
                fx["resource"].read_text(encoding="utf-8")
            )
            resource["runtime_extended_closure_id"] = (
                "DEPRUNTIMEEXTCLOSURE_" + "9" * 20
            )
            fx["resource"].write_text(
                json.dumps(resource) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DependencyRuntimeReadinessError,
                "different closure",
            ):
                build_dependency_runtime_readiness(
                    fx["closure"],
                    fx["resource"],
                    fx["dynamic"],
                    fx["bundled"],
                    [fx["official"]],
                )


if __name__ == "__main__":
    unittest.main()
