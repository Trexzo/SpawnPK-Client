from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_runtime_dynamic_member import (
    build_dependency_runtime_dynamic_member_proof,
)
from spk_recovery.dependency_remap_proof import (
    _bundled_index,
)
from spk_recovery.dependency_artifact_proof import (
    _artifact_index,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DependencyRuntimeDynamicMemberTests(unittest.TestCase):
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

    def _fixture(self, root: Path, *, include_b_mapping: bool = True):
        bundled_classes = self._compile(
            root,
            "bundled",
            {
                "dep/A.java": (
                    "package dep; public class A { "
                    "public int a; "
                    "public A() {} "
                    "public B b(B x) { return x; } }\n"
                ),
                "dep/B.java": "package dep; public class B {}\n",
            },
        )
        official_classes = self._compile(
            root,
            "official",
            {
                "official/A.java": (
                    "package official; public class A { "
                    "public int x; "
                    "public A() {} "
                    "public B y(B q) { return q; } }\n"
                ),
                "official/B.java": "package official; public class B {}\n",
            },
        )

        bundled = root / "bundled.jar"
        with zipfile.ZipFile(bundled, "w", zipfile.ZIP_STORED) as archive:
            for name in ("A", "B"):
                archive.write(
                    bundled_classes / "dep" / f"{name}.class",
                    f"dep/{name}.class",
                )

        official = root / "official.jar"
        with zipfile.ZipFile(official, "w", zipfile.ZIP_STORED) as archive:
            for name in ("A", "B"):
                archive.write(
                    official_classes / "official" / f"{name}.class",
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
            "owners": [],
            "identifiers_included": True,
        }
        plan_path = root / "replacement.json"
        plan_path.write_text(
            json.dumps(plan, indent=2) + "\n",
            encoding="utf-8",
        )

        bundled_index = _bundled_index(
            bundled,
            project_prefixes=("rs/",),
        )
        official_index, artifact_by_class, _ = _artifact_index(
            [official],
            java_release=9,
        )

        rows = []
        pairs = [("dep/A", "official/A")]
        if include_b_mapping:
            pairs.append(("dep/B", "official/B"))
        for index, (old_owner, new_owner) in enumerate(pairs, start=1):
            rows.append(
                {
                    "dynamic_mapping_id": f"DEPDYNMAPROW_{index:05d}",
                    "status": "accepted_class_mapping",
                    "strategy": "unique_structural",
                    "member_authority_required": True,
                    "old_owner": old_owner,
                    "new_owner": new_owner,
                    "artifact": artifact_by_class[new_owner],
                    "structural_sha256": bundled_index[
                        old_owner
                    ].structural_sha256(),
                    "field_sequence_equal": True,
                    "ordinary_method_sequence_equal": True,
                }
            )
            self.assertEqual(
                bundled_index[old_owner].structural_sha256(),
                official_index[new_owner].structural_sha256(),
            )

        dynamic = {
            "schema_version": 1,
            "kind": "dependency_runtime_dynamic_mapping_proof",
            "runtime_dynamic_mapping_id": (
                "DEPRUNTIMEDYNMAP_" + "2" * 20
            ),
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "official_artifact_sha256": [official_sha],
            "rows": rows,
            "identifiers_included": True,
        }
        dynamic_path = root / "dynamic.json"
        dynamic_path.write_text(
            json.dumps(dynamic, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            "bundled": bundled,
            "official": official,
            "plan": plan_path,
            "dynamic": dynamic_path,
        }

    def test_complete_member_transport_allows_promotion_authority(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td), include_b_mapping=True)
            report = build_dependency_runtime_dynamic_member_proof(
                fx["dynamic"],
                fx["plan"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )

            self.assertEqual(
                report["kind"],
                "dependency_runtime_dynamic_member_proof",
            )
            self.assertTrue(
                report["summary"]["ready_for_dynamic_root_promotion"]
            )
            self.assertEqual(
                report["summary"][
                    "accepted_dynamic_class_mapping_count"
                ],
                2,
            )
            self.assertGreaterEqual(
                report["summary"]["accepted_remap_member_count"],
                2,
            )
            self.assertEqual(
                report["summary"]["constructor_unresolved_count"],
                0,
            )
            self.assertTrue(
                all(
                    row["member_transport_complete"]
                    for row in report["classes"]
                )
            )

    def test_missing_descriptor_class_mapping_fails_promotion_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td), include_b_mapping=False)
            report = build_dependency_runtime_dynamic_member_proof(
                fx["dynamic"],
                fx["plan"],
                fx["bundled"],
                [fx["official"]],
            )

            self.assertFalse(
                report["summary"]["ready_for_dynamic_root_promotion"]
            )
            self.assertGreater(
                report["summary"]["unresolved_member_count"],
                0,
            )
            self.assertFalse(
                report["classes"][0]["member_transport_complete"]
            )

    def test_public_and_private_reports_share_id(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td), include_b_mapping=True)
            public = build_dependency_runtime_dynamic_member_proof(
                fx["dynamic"],
                fx["plan"],
                fx["bundled"],
                [fx["official"]],
            )
            private = build_dependency_runtime_dynamic_member_proof(
                fx["dynamic"],
                fx["plan"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )
            self.assertEqual(
                public["runtime_dynamic_member_id"],
                private["runtime_dynamic_member_id"],
            )
            self.assertNotIn("dep/A", json.dumps(public))
            self.assertIn("dep/A", json.dumps(private))


if __name__ == "__main__":
    unittest.main()
