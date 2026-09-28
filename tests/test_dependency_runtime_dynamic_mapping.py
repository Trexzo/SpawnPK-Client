from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_runtime_dynamic_mapping import (
    build_dependency_runtime_dynamic_mapping_proof,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DependencyRuntimeDynamicMappingTests(unittest.TestCase):
    def _compile(
        self,
        root: Path,
        sources: dict[str, str],
        name: str,
    ) -> Path:
        src = root / (name + "-src")
        paths: list[Path] = []
        for rel, body in sources.items():
            path = src / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            paths.append(path)
        out = root / (name + "-classes")
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
                "dep/Identity.java": (
                    "package dep; public class Identity { "
                    "public String x() { return \"identity\"; } }\n"
                ),
                "dep/Renamed.java": (
                    "package dep; public class Renamed { "
                    "public String x() { return \"renamed\"; } }\n"
                ),
                "dep/Ambiguous.java": (
                    "package dep; public class Ambiguous { "
                    "public String x() { return \"ambiguous\"; } }\n"
                ),
                "dep/NoMatch.java": (
                    "package dep; public class NoMatch { "
                    "public int x() { return 991; } }\n"
                ),
            },
            "bundled",
        )
        official_classes = self._compile(
            root,
            {
                "dep/Identity.java": (
                    "package dep; public class Identity { "
                    "public String x() { return \"identity\"; } }\n"
                ),
                "official/RenamedTarget.java": (
                    "package official; public class RenamedTarget { "
                    "public String x() { return \"renamed\"; } }\n"
                ),
                "official/AmbiguousOne.java": (
                    "package official; public class AmbiguousOne { "
                    "public String x() { return \"ambiguous\"; } }\n"
                ),
                "official/AmbiguousTwo.java": (
                    "package official; public class AmbiguousTwo { "
                    "public String x() { return \"ambiguous\"; } }\n"
                ),
            },
            "official",
        )

        bundled = root / "bundled.jar"
        with zipfile.ZipFile(bundled, "w", zipfile.ZIP_STORED) as archive:
            for name in ("Identity", "Renamed", "Ambiguous", "NoMatch"):
                archive.write(
                    bundled_classes / "dep" / f"{name}.class",
                    f"dep/{name}.class",
                )

        official = root / "official.jar"
        with zipfile.ZipFile(official, "w", zipfile.ZIP_STORED) as archive:
            archive.write(
                official_classes / "dep" / "Identity.class",
                "dep/Identity.class",
            )
            for name in (
                "RenamedTarget",
                "AmbiguousOne",
                "AmbiguousTwo",
            ):
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

        gaps = [
            "dep/Identity",
            "dep/Renamed",
            "dep/Ambiguous",
            "dep/NoMatch",
        ]
        augmented = {
            "schema_version": 1,
            "kind": "dependency_runtime_augmented_closure",
            "runtime_augmented_closure_id": (
                "DEPRUNTIMEAUGCLOSURE_" + "2" * 20
            ),
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "dynamic_roots": [
                {
                    "dynamic_root_id": f"ROOT_{index:04d}",
                    "status": "dynamic_mapping_authority_gap",
                    "owner": owner,
                }
                for index, owner in enumerate(gaps, start=1)
            ],
            "new_owners": [],
            "identifiers_included": True,
        }
        augmented_path = root / "augmented.json"
        augmented_path.write_text(
            json.dumps(augmented, indent=2) + "\n",
            encoding="utf-8",
        )

        return {
            "bundled": bundled,
            "official": official,
            "plan": plan_path,
            "augmented": augmented_path,
        }

    def test_classifies_identity_unique_ambiguous_and_no_match(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_dynamic_mapping_proof(
                fx["augmented"],
                fx["plan"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )
            summary = report["summary"]
            self.assertEqual(
                summary["dynamic_mapping_gap_target_count"],
                4,
            )
            self.assertEqual(
                summary["accepted_class_mapping_count"],
                2,
            )
            self.assertEqual(
                summary["identity_structural_count"],
                1,
            )
            self.assertEqual(
                summary["unique_structural_count"],
                1,
            )
            self.assertEqual(
                summary["renamed_class_mapping_count"],
                1,
            )
            self.assertEqual(
                summary["ambiguous_structural_match_count"],
                1,
            )
            self.assertEqual(
                summary["no_official_structural_match_count"],
                1,
            )
            self.assertEqual(
                summary["member_authority_required_count"],
                2,
            )
            self.assertFalse(
                summary["ready_for_dynamic_root_promotion"]
            )

            by_owner = {
                row["old_owner"]: row
                for row in report["rows"]
            }
            self.assertEqual(
                by_owner["dep/Identity"]["strategy"],
                "identity_structural",
            )
            self.assertEqual(
                by_owner["dep/Renamed"]["strategy"],
                "unique_structural",
            )
            self.assertEqual(
                by_owner["dep/Renamed"]["new_owner"],
                "official/RenamedTarget",
            )
            self.assertTrue(
                by_owner["dep/Renamed"]["field_sequence_equal"]
            )
            self.assertTrue(
                by_owner["dep/Renamed"][
                    "ordinary_method_sequence_equal"
                ]
            )

    def test_public_and_private_reports_share_id_and_redact_names(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            public = build_dependency_runtime_dynamic_mapping_proof(
                fx["augmented"],
                fx["plan"],
                fx["bundled"],
                [fx["official"]],
            )
            private = build_dependency_runtime_dynamic_mapping_proof(
                fx["augmented"],
                fx["plan"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )
            self.assertEqual(
                public["runtime_dynamic_mapping_id"],
                private["runtime_dynamic_mapping_id"],
            )
            rendered = json.dumps(public)
            self.assertNotIn("dep/Renamed", rendered)
            self.assertNotIn("official/RenamedTarget", rendered)


if __name__ == "__main__":
    unittest.main()
