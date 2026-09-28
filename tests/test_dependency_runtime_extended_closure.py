from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_runtime_extended_closure import (
    build_dependency_runtime_extended_closure,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DependencyRuntimeExtendedClosureTests(unittest.TestCase):
    def _compile(
        self,
        root: Path,
        name: str,
        sources: dict[str, str],
    ) -> Path:
        src = root / f"{name}-src"
        paths: list[Path] = []
        for rel, body in sources.items():
            path = src / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            paths.append(path)
        out = root / f"{name}-classes"
        out.mkdir()
        proc = subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-d",
                str(out),
                *[str(path) for path in sorted(paths)],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return out

    def _fixture(self, root: Path) -> dict[str, Path]:
        bundled_classes = self._compile(
            root,
            "bundled",
            {
                "old/Dynamic.java": (
                    "package old; public class Dynamic { "
                    "public Residual make() { return new Residual(); } }\n"
                ),
                "old/Residual.java": (
                    "package old; public class Residual {}\n"
                ),
                "rs/Project.java": (
                    "package rs; public class Project {}\n"
                ),
            },
        )
        official_classes = self._compile(
            root,
            "official",
            {
                "official/Dynamic.java": (
                    "package official; public class Dynamic {}\n"
                ),
            },
        )

        bundled = root / "bundled.jar"
        with zipfile.ZipFile(
            bundled,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            for name in ("Dynamic", "Residual"):
                archive.write(
                    bundled_classes / "old" / f"{name}.class",
                    f"old/{name}.class",
                )
            archive.write(
                bundled_classes / "rs" / "Project.class",
                "rs/Project.class",
            )

        official = root / "official.jar"
        with zipfile.ZipFile(
            official,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.write(
                official_classes / "official" / "Dynamic.class",
                "official/Dynamic.class",
            )

        bundled_sha = _sha(bundled)
        official_sha = _sha(official)
        replacement_id = "DEPREPLACE_" + "1" * 20
        extension_id = "DEPREPLACEEXT_" + "2" * 20
        closure_id = "DEPRUNTIMECLOSURE_" + "3" * 20
        dynamic_target_id = "DEPRUNTIMEDYNAMICTARGET_" + "4" * 20

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
            "owners": [],
            "identifiers_included": True,
        }
        plan_path = root / "replacement.json"
        plan_path.write_text(
            json.dumps(plan, indent=2) + "\n",
            encoding="utf-8",
        )

        extension = {
            "schema_version": 1,
            "kind": "dependency_replacement_extension",
            "replacement_extension_id": extension_id,
            "replacement_plan_id": replacement_id,
            "runtime_dynamic_mapping_id": (
                "DEPRUNTIMEDYNMAP_" + "5" * 20
            ),
            "runtime_dynamic_member_id": (
                "DEPRUNTIMEDYNMEMBER_" + "6" * 20
            ),
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": [official_sha],
            "summary": {
                "ready_for_augmented_closure_reaudit": True,
            },
            "promoted_rows": [
                {
                    "extension_row_id": "DEPREPLACEEXTROW_00001",
                    "source_dynamic_mapping_id": "DEPDYNMAPROW_00001",
                    "source_dynamic_member_class_id": "DEPDYNCLASS_00001",
                    "classification": "official_replaceable",
                    "status": "promotion_eligible",
                    "member_transport_complete": True,
                    "official_artifact_bound": True,
                    "old_owner": "old/Dynamic",
                    "new_owner": "official/Dynamic",
                    "artifact": "official.jar",
                }
            ],
            "blocked_rows": [],
            "already_authorized_rows": [],
            "identifiers_included": True,
        }
        extension_path = root / "extension.json"
        extension_path.write_text(
            json.dumps(extension, indent=2) + "\n",
            encoding="utf-8",
        )

        static = {
            "schema_version": 1,
            "kind": "dependency_runtime_closure",
            "runtime_closure_id": closure_id,
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": [official_sha],
            "summary": {
                "root_count": 0,
                "class_closure_blocker_count": 0,
            },
            "owners": [],
            "edges": [],
            "resources": {
                "artifact_count": 0,
                "resource_entry_count": 0,
                "resource_bytes": 0,
                "service_entry_count": 0,
                "native_entry_count": 0,
                "artifacts": [],
            },
            "identifiers_included": True,
        }
        static_path = root / "static.json"
        static_path.write_text(
            json.dumps(static, indent=2) + "\n",
            encoding="utf-8",
        )

        dynamic = {
            "schema_version": 1,
            "kind": "dependency_runtime_dynamic_target_classification",
            "runtime_dynamic_target_id": dynamic_target_id,
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "targets": [
                {
                    "dynamic_target_id": "DEPRUNTIME_DYNAMIC_TARGET_00001",
                    "source_callsite_id": "CALL_1",
                    "category": "class_loading",
                    "classification": "bundled_unclassified",
                    "literal_target_proven": True,
                    "normalized_class_target": "old/Dynamic",
                },
                {
                    "dynamic_target_id": "DEPRUNTIME_DYNAMIC_TARGET_00004",
                    "source_callsite_id": "CALL_4",
                    "category": "class_loading",
                    "classification": "project_class",
                    "literal_target_proven": True,
                    "normalized_class_target": "rs/Project",
                },
                {
                    "dynamic_target_id": "DEPRUNTIME_DYNAMIC_TARGET_00002",
                    "source_callsite_id": "CALL_2",
                    "category": "resource_loading",
                    "classification": "resource_bundled_only",
                    "literal_target_proven": True,
                    "resource_entry": "x.dat",
                },
                {
                    "dynamic_target_id": "DEPRUNTIME_DYNAMIC_TARGET_00003",
                    "source_callsite_id": "CALL_3",
                    "category": "native_loading",
                    "classification": "native_runtime_requirement",
                    "literal_target_proven": True,
                    "literal_target": "nativeX",
                },
            ],
            "identifiers_included": True,
        }
        dynamic_path = root / "dynamic.json"
        dynamic_path.write_text(
            json.dumps(dynamic, indent=2) + "\n",
            encoding="utf-8",
        )

        return {
            "plan": plan_path,
            "extension": extension_path,
            "static": static_path,
            "dynamic": dynamic_path,
            "bundled": bundled,
            "official": official,
        }

    def test_extension_resolves_root_gap_and_surfaces_reachable_gap(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_extended_closure(
                fx["plan"],
                fx["extension"],
                fx["static"],
                fx["dynamic"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )

            summary = report["summary"]
            self.assertEqual(
                summary["extension_promoted_dynamic_root_count"],
                1,
            )
            self.assertEqual(
                summary["prior_mapping_gap_resolved_count"],
                1,
            )
            self.assertEqual(
                summary["remaining_mapping_gap_count"],
                1,
            )
            self.assertEqual(
                summary["resource_dynamic_requirement_count"],
                1,
            )
            self.assertEqual(
                summary["native_dynamic_requirement_count"],
                1,
            )
            self.assertFalse(
                summary["runtime_capsule_mutation_ready"]
            )
            self.assertEqual(
                report["dynamic_roots"][0]["status"],
                "authorized_dynamic_root",
            )
            self.assertEqual(
                report["dynamic_roots"][0]["authority_source"],
                "replacement_extension",
            )
            project_rows = [
                row
                for row in report["dynamic_roots"]
                if row.get("owner") == "rs/Project"
            ]
            self.assertEqual(len(project_rows), 1)
            self.assertEqual(
                project_rows[0]["status"],
                "project_dynamic_target",
            )
            by_owner = {
                row.get("owner"): row
                for row in report["new_owners"]
            }
            self.assertEqual(
                by_owner["old/Residual"]["status"],
                "remaining_mapping_authority_gap",
            )

    def test_public_and_private_reports_share_id(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            public = build_dependency_runtime_extended_closure(
                fx["plan"],
                fx["extension"],
                fx["static"],
                fx["dynamic"],
                fx["bundled"],
                [fx["official"]],
            )
            private = build_dependency_runtime_extended_closure(
                fx["plan"],
                fx["extension"],
                fx["static"],
                fx["dynamic"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )

            self.assertEqual(
                public["runtime_extended_closure_id"],
                private["runtime_extended_closure_id"],
            )
            rendered = json.dumps(public)
            self.assertNotIn("old/Dynamic", rendered)
            self.assertNotIn("old/Residual", rendered)


if __name__ == "__main__":
    unittest.main()
