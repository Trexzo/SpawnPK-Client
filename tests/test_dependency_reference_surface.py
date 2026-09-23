from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.bytecode_profile import (
    profile_class_constant_pool_references,
)
from spk_recovery.dependency_reference_surface import (
    scan_project_reference_surface,
)


class DependencyReferenceSurfaceTests(unittest.TestCase):
    def _fixture(self, root: Path) -> Path:
        src = root / "src"
        dep = src / "dep" / "Api.java"
        project = src / "project" / "Main.java"
        dep.parent.mkdir(parents=True)
        project.parent.mkdir(parents=True)
        dep.write_text(
            "package dep;\n"
            "public class Api {\n"
            "    public static int VALUE = 7;\n"
            "    public String ping(int value) {\n"
            "        return String.valueOf(value);\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        project.write_text(
            "package project;\n"
            "public class Main {\n"
            "    public String run(dep.Api api) {\n"
            "        return api.ping(dep.Api.VALUE);\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        classes = root / "classes"
        classes.mkdir()
        proc = subprocess.run(
            [
                "javac",
                "-d",
                str(classes),
                str(dep),
                str(project),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise AssertionError(
                "javac fixture failed: " + proc.stderr
            )
        jar = root / "fixture.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            for class_file in sorted(classes.rglob("*.class")):
                archive.write(
                    class_file,
                    class_file.relative_to(classes).as_posix(),
                )
        return jar

    def test_constant_pool_profile_extracts_exact_member_refs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            with zipfile.ZipFile(jar) as archive:
                profile = profile_class_constant_pool_references(
                    archive.read("project/Main.class")
                )

            self.assertEqual(
                profile["internal_name"],
                "project/Main",
            )
            self.assertIn(
                "dep/Api",
                profile["class_references"],
            )
            refs = {
                (
                    row["kind"],
                    row["owner"],
                    row["name"],
                    row["descriptor"],
                )
                for row in profile["member_references"]
            }
            self.assertIn(
                ("field", "dep/Api", "VALUE", "I"),
                refs,
            )
            self.assertIn(
                (
                    "method",
                    "dep/Api",
                    "ping",
                    "(I)Ljava/lang/String;",
                ),
                refs,
            )

    def test_scans_project_to_non_project_reference_surface(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            report = scan_project_reference_surface(
                jar,
                project_prefixes=("project/",),
            )

            self.assertEqual(report["project_class_count"], 1)
            self.assertTrue(
                report["reference_surface_id"].startswith("DEPREF_")
            )

            members = {
                (
                    row["kind"],
                    row["owner"],
                    row["name"],
                    row["descriptor"],
                ): row
                for row in report["member_references"]
            }
            field = members[
                ("field", "dep/Api", "VALUE", "I")
            ]
            self.assertEqual(field["reference_count"], 1)
            self.assertEqual(
                field["source_classes"],
                ["project/Main"],
            )
            method = members[
                (
                    "method",
                    "dep/Api",
                    "ping",
                    "(I)Ljava/lang/String;",
                )
            ]
            self.assertEqual(method["reference_count"], 1)

            namespaces = {
                row["namespace"]: row["reference_count"]
                for row in report["namespace_reference_counts"]
            }
            self.assertEqual(namespaces["dep"], 2)


if __name__ == "__main__":
    unittest.main()
