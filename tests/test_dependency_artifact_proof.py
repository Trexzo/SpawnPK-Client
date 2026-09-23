from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_artifact_proof import (
    prove_official_artifact_compatibility,
)


class DependencyArtifactProofTests(unittest.TestCase):
    def _compile_jar(
        self,
        root: Path,
        name: str,
        sources: dict[str, str],
    ) -> Path:
        src = root / (name + "-src")
        classes = root / (name + "-classes")
        src.mkdir()
        classes.mkdir()
        paths = []
        for rel, text in sources.items():
            path = src / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            paths.append(str(path))
        proc = subprocess.run(
            ["javac", "-d", str(classes), *paths],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise AssertionError("javac fixture failed: " + proc.stderr)
        jar = root / (name + ".jar")
        with zipfile.ZipFile(jar, "w") as archive:
            for class_file in sorted(classes.rglob("*.class")):
                archive.write(
                    class_file,
                    class_file.relative_to(classes).as_posix(),
                )
        return jar

    def _surface(self, root: Path) -> Path:
        path = root / "depref.json"
        payload = {
            "schema_version": 1,
            "kind": "project_non_project_reference_surface",
            "reference_surface_id": "DEPREF_TEST",
            "class_references": [
                {
                    "target": "dep/Api",
                    "source_class_count": 1,
                    "source_classes": ["project/Main"],
                }
            ],
            "member_references": [
                {
                    "kind": "field",
                    "owner": "dep/Api",
                    "name": "VALUE",
                    "descriptor": "I",
                    "reference_count": 2,
                    "source_class_count": 1,
                    "source_classes": ["project/Main"],
                },
                {
                    "kind": "method",
                    "owner": "dep/Api",
                    "name": "ping",
                    "descriptor": "(I)Ljava/lang/String;",
                    "reference_count": 3,
                    "source_class_count": 1,
                    "source_classes": ["project/Main"],
                },
            ],
        }
        path.write_text(
            json.dumps(payload, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def test_direct_api_compatibility_resolves_exact_members(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifact = self._compile_jar(
                root,
                "dep",
                {
                    "dep/Api.java": (
                        "package dep; public class Api { "
                        "public static int VALUE = 1; "
                        "public String ping(int x) { return String.valueOf(x); } "
                        "}"
                    )
                },
            )
            report = prove_official_artifact_compatibility(
                self._surface(root),
                [artifact],
            )

            self.assertEqual(
                report["summary"]["member_status_counts"],
                {"direct": 2},
            )
            self.assertEqual(
                report["summary"]["weighted_member_status_counts"],
                {"direct": 5},
            )

    def test_inherited_member_resolves_directly(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifact = self._compile_jar(
                root,
                "dep",
                {
                    "dep/Base.java": (
                        "package dep; public class Base { "
                        "public static int VALUE = 1; "
                        "public String ping(int x) { return String.valueOf(x); } "
                        "}"
                    ),
                    "dep/Api.java": (
                        "package dep; public class Api extends Base {}"
                    ),
                },
            )
            report = prove_official_artifact_compatibility(
                self._surface(root),
                [artifact],
            )

            self.assertEqual(
                report["summary"]["member_status_counts"],
                {"direct": 2},
            )
            owners = {
                row["resolved_owner"]
                for row in report["member_results"]
            }
            self.assertEqual(owners, {"dep/Base"})

    def test_same_descriptor_different_name_requires_structural_remap(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifact = self._compile_jar(
                root,
                "dep",
                {
                    "dep/Api.java": (
                        "package dep; public class Api { "
                        "public static int REAL_VALUE = 1; "
                        "public String realPing(int x) { return String.valueOf(x); } "
                        "}"
                    )
                },
            )
            report = prove_official_artifact_compatibility(
                self._surface(root),
                [artifact],
            )

            self.assertEqual(
                report["summary"]["member_status_counts"],
                {"structural_remap_required": 2},
            )
            candidates = {
                row["name"]: row["descriptor_candidates"]
                for row in report["member_results"]
            }
            self.assertEqual(
                candidates["VALUE"],
                [{"owner": "dep/Api", "name": "REAL_VALUE"}],
            )
            self.assertEqual(
                candidates["ping"],
                [{"owner": "dep/Api", "name": "realPing"}],
            )

    def test_module_descriptors_do_not_create_duplicate_class_ownership(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = self._compile_jar(
                root,
                "dep",
                {
                    "dep/Api.java": (
                        "package dep; public class Api { "
                        "public static int VALUE = 1; "
                        "public String ping(int x) { return String.valueOf(x); } "
                        "}"
                    )
                },
            )
            second = self._compile_jar(
                root,
                "other",
                {
                    "other/Thing.java": (
                        "package other; public class Thing {}"
                    )
                },
            )
            for jar in (first, second):
                with zipfile.ZipFile(jar, "a") as out:
                    out.writestr("module-info.class", b"not-a-real-class")

            report = prove_official_artifact_compatibility(
                self._surface(root),
                [first, second],
            )
            self.assertEqual(
                report["summary"]["member_status_counts"],
                {"direct": 2},
            )

    def test_multi_release_artifact_requires_explicit_java_release(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = self._compile_jar(
                root,
                "dep",
                {
                    "dep/Api.java": (
                        "package dep; public class Api { "
                        "public static int VALUE = 1; "
                        "public String ping(int x) { return String.valueOf(x); } "
                        "}"
                    )
                },
            )
            multi = root / "dep-mr.jar"
            with zipfile.ZipFile(base) as source, zipfile.ZipFile(multi, "w") as out:
                for name in source.namelist():
                    out.writestr(name, source.read(name))
                out.writestr(
                    "META-INF/versions/9/dep/Api.class",
                    source.read("dep/Api.class"),
                )

            with self.assertRaisesRegex(
                Exception,
                "multi-release JAR requires explicit java_release",
            ):
                prove_official_artifact_compatibility(
                    self._surface(root),
                    [multi],
                )

            report = prove_official_artifact_compatibility(
                self._surface(root),
                [multi],
                java_release=9,
            )
            self.assertEqual(
                report["summary"]["member_status_counts"],
                {"direct": 2},
            )
            self.assertEqual(report["java_release"], 9)
            self.assertEqual(
                report["official_artifacts"][0][
                    "multi_release_class_count"
                ],
                1,
            )

    def test_missing_owner_remains_unresolved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifact = self._compile_jar(
                root,
                "dep",
                {
                    "other/Thing.java": (
                        "package other; public class Thing {}"
                    )
                },
            )
            report = prove_official_artifact_compatibility(
                self._surface(root),
                [artifact],
            )

            self.assertEqual(
                report["summary"]["member_status_counts"],
                {"missing_owner": 2},
            )
            self.assertEqual(
                report["summary"]["direct_class_reference_count"],
                0,
            )


if __name__ == "__main__":
    unittest.main()
