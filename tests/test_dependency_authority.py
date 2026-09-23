from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_authority import (
    compare_external_class_surfaces,
    scan_dependency_authority,
)


class DependencyAuthorityTests(unittest.TestCase):
    def _jar(self, path: Path, *, external_byte: bytes = b"x") -> None:
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("rs/Client.class", b"project")
            z.writestr("com/example/Lib.class", external_byte)
            z.writestr("tools/Probe.class", b"probe")
            z.writestr(
                "META-INF/maven/com.example/lib/pom.properties",
                "version=1.2.3\n"
                "groupId=com.example\n"
                "artifactId=lib\n",
            )

    def test_extracts_exact_maven_coordinate_and_namespace_counts(self):
        with tempfile.TemporaryDirectory() as td:
            jar = Path(td) / "client.jar"
            self._jar(jar)

            report = scan_dependency_authority(jar)

            self.assertEqual(report["project_class_count"], 1)
            self.assertEqual(report["non_project_class_count"], 2)
            self.assertEqual(
                report["maven_coordinates"],
                [
                    {
                        "group_id": "com.example",
                        "artifact_id": "lib",
                        "version": "1.2.3",
                        "source_entry": (
                            "META-INF/maven/com.example/lib/pom.properties"
                        ),
                    }
                ],
            )
            namespaces = {
                row["namespace"]: row["class_count"]
                for row in report["non_project_namespaces"]
            }
            self.assertEqual(namespaces["com/example"], 1)
            self.assertEqual(namespaces["tools"], 1)
            self.assertTrue(
                report["dependency_authority_id"].startswith("DEPAUTH_")
            )

    def test_cross_build_external_class_comparison_is_byte_exact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            left = root / "left.jar"
            right = root / "right.jar"
            self._jar(left, external_byte=b"same")
            self._jar(right, external_byte=b"same")

            report = compare_external_class_surfaces(left, right)

            self.assertEqual(report["common_non_project_class_count"], 2)
            self.assertEqual(
                report["byte_identical_common_non_project_class_count"],
                2,
            )
            self.assertEqual(
                report["different_common_non_project_class_count"],
                0,
            )

    def test_cross_build_comparison_reports_different_external_bytecode(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            left = root / "left.jar"
            right = root / "right.jar"
            self._jar(left, external_byte=b"left")
            self._jar(right, external_byte=b"right")

            report = compare_external_class_surfaces(left, right)

            self.assertEqual(
                report["different_common_non_project_classes"],
                ["com/example/Lib.class"],
            )


if __name__ == "__main__":
    unittest.main()
