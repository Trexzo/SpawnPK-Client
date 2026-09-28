from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_runtime_augmented_closure import (
    build_dependency_runtime_augmented_closure,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DependencyRuntimeAugmentedClosureTests(unittest.TestCase):
    def _compile(
        self,
        root: Path,
        sources: dict[str, str],
        out_name: str,
    ) -> Path:
        src = root / (out_name + "-src")
        paths: list[Path] = []
        for relative, body in sources.items():
            path = src / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            paths.append(path)
        out = root / (out_name + "-classes")
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

    def _fixture(self, root: Path) -> dict:
        bundled_classes = self._compile(
            root,
            {
                "dep/A.java": "package dep; public class A {}\n",
                "dep/B.java": (
                    "package dep; public class B { "
                    "public E edge() { return new E(); } }\n"
                ),
                "dep/C.java": "package dep; public class C {}\n",
                "dep/D.java": "package dep; public class D {}\n",
                "dep/E.java": "package dep; public class E {}\n",
            },
            "bundled",
        )
        official_classes = self._compile(
            root,
            {
                "official/A.java": (
                    "package official; public class A {}\n"
                ),
                "official/B.java": (
                    "package official; public class B {}\n"
                ),
            },
            "official",
        )

        bundled = root / "bundled.jar"
        with zipfile.ZipFile(
            bundled,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            for name in ("A", "B", "C", "D", "E"):
                archive.write(
                    bundled_classes / "dep" / f"{name}.class",
                    f"dep/{name}.class",
                )

        official = root / "official.jar"
        with zipfile.ZipFile(
            official,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            for name in ("A", "B"):
                archive.write(
                    official_classes
                    / "official"
                    / f"{name}.class",
                    f"official/{name}.class",
                )

        bundled_sha = _sha(bundled)
        official_sha = _sha(official)
        replacement_id = "DEPREPLACE_" + "1" * 20

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
            "owners": [
                {
                    "owner_id": "DEPOWNER_00001",
                    "classification": "official_replaceable",
                    "old_owner": "dep/A",
                    "new_owner": "official/A",
                    "artifact": "official.jar",
                },
                {
                    "owner_id": "DEPOWNER_00002",
                    "classification": "official_replaceable",
                    "old_owner": "dep/B",
                    "new_owner": "official/B",
                    "artifact": "official.jar",
                },
                {
                    "owner_id": "DEPOWNER_00003",
                    "classification": "residual_bundled",
                    "old_owner": "dep/D",
                    "new_owner": None,
                    "artifact": None,
                },
                {
                    "owner_id": "DEPOWNER_00004",
                    "classification": "residual_bundled",
                    "old_owner": "dep/E",
                    "new_owner": None,
                    "artifact": None,
                },
            ],
            "identifiers_included": True,
        }
        plan_path = root / "replacement.json"
        plan_path.write_text(
            json.dumps(plan, indent=2) + "\n",
            encoding="utf-8",
        )

        static = {
            "schema_version": 1,
            "kind": "dependency_runtime_closure",
            "runtime_closure_id": (
                "DEPRUNTIMECLOSURE_" + "2" * 20
            ),
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": [official_sha],
            "summary": {
                "root_count": 1,
                "class_closure_blocker_count": 0,
            },
            "owners": [
                {
                    "closure_owner_id": "DEPCLOSUREOWNER_0001",
                    "status": "official_closure_mapped",
                    "owner": "dep/A",
                    "artifact": "official.jar",
                }
            ],
            "edges": [],
            "identifiers_included": True,
        }
        static_path = root / "closure.json"
        static_path.write_text(
            json.dumps(static, indent=2) + "\n",
            encoding="utf-8",
        )

        dynamic = {
            "schema_version": 1,
            "kind": (
                "dependency_runtime_dynamic_target_classification"
            ),
            "runtime_dynamic_target_id": (
                "DEPRUNTIMEDYNAMICTARGET_" + "3" * 20
            ),
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "targets": [
                {
                    "dynamic_target_id": "DYN_0001",
                    "category": "class_loading",
                    "classification": (
                        "dependency_official_replaceable"
                    ),
                    "normalized_class_target": "dep/A",
                },
                {
                    "dynamic_target_id": "DYN_0002",
                    "category": "class_loading",
                    "classification": (
                        "dependency_official_replaceable"
                    ),
                    "normalized_class_target": "dep/B",
                },
                {
                    "dynamic_target_id": "DYN_0003",
                    "category": "class_loading",
                    "classification": "bundled_unclassified",
                    "normalized_class_target": "dep/C",
                },
                {
                    "dynamic_target_id": "DYN_0004",
                    "category": "class_loading",
                    "classification": (
                        "dependency_residual_bundled"
                    ),
                    "normalized_class_target": "dep/D",
                },
                {
                    "dynamic_target_id": "DYN_0005",
                    "category": "resource_loading",
                    "classification": "resource_bundled_only",
                    "resource_entry": "config/x",
                },
                {
                    "dynamic_target_id": "DYN_0006",
                    "category": "native_loading",
                    "classification": "native_runtime_requirement",
                    "literal_target": "native-x",
                },
            ],
            "identifiers_included": True,
        }
        dynamic_path = root / "dynamic-target.json"
        dynamic_path.write_text(
            json.dumps(dynamic, indent=2) + "\n",
            encoding="utf-8",
        )

        return {
            "bundled": bundled,
            "official": official,
            "plan": plan_path,
            "static": static_path,
            "dynamic": dynamic_path,
        }

    def test_audits_static_authorized_gap_and_protected_roots(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_augmented_closure(
                fx["plan"],
                fx["static"],
                fx["dynamic"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )
            summary = report["summary"]
            self.assertEqual(summary["static_root_count"], 1)
            self.assertEqual(
                summary["proven_dynamic_class_target_count"],
                4,
            )
            self.assertEqual(
                summary[
                    "dynamic_target_already_in_static_closure_count"
                ],
                1,
            )
            self.assertEqual(
                summary["added_authorized_dynamic_root_count"],
                1,
            )
            self.assertEqual(
                summary["dynamic_mapping_authority_gap_count"],
                1,
            )
            self.assertEqual(
                summary["protected_dynamic_target_count"],
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

            statuses = {
                row["owner"]: row["status"]
                for row in report["new_owners"]
            }
            self.assertEqual(
                statuses["dep/E"],
                "residual_bundled",
            )
            self.assertGreaterEqual(
                summary["dynamic_closure_blocker_count"],
                1,
            )

    def test_public_and_private_reports_share_id(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            public = build_dependency_runtime_augmented_closure(
                fx["plan"],
                fx["static"],
                fx["dynamic"],
                fx["bundled"],
                [fx["official"]],
            )
            private = build_dependency_runtime_augmented_closure(
                fx["plan"],
                fx["static"],
                fx["dynamic"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )
            self.assertEqual(
                public["runtime_augmented_closure_id"],
                private["runtime_augmented_closure_id"],
            )
            rendered = json.dumps(public)
            self.assertNotIn("dep/B", rendered)
            self.assertNotIn("dep/C", rendered)


if __name__ == "__main__":
    unittest.main()
