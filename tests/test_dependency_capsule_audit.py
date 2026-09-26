from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_capsule_audit import (
    audit_dependency_capsule,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DependencyCapsuleAuditTests(unittest.TestCase):
    def _fixture(self, root: Path):
        src = root / "src" / "dep"
        src.mkdir(parents=True)
        source = src / "Fallback.java"
        source.write_text(
            "package dep; public class Fallback {}\n",
            encoding="utf-8",
        )

        classes = root / "classes"
        classes.mkdir()
        proc = subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-d",
                str(classes),
                str(source),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        readable = root / "readable.jar"
        capsule = root / "dependency-capsule.jar"
        entry = "dep/Fallback.class"
        data = (classes / "dep" / "Fallback.class").read_bytes()

        for path in (readable, capsule):
            with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
                z.writestr(entry, data)

        plan = {
            "schema_version": 1,
            "kind": "javac_missing_class_recovery_plan",
            "plan_id": "JCLASSPLAN_" + "1" * 20,
            "identifiers_included": True,
            "candidates": [
                {
                    "candidate_id": "JCLASSMISS_001",
                    "candidate_internal_name": "dep/Fallback",
                }
            ],
        }
        return plan, readable, capsule

    def test_exact_dependency_entry_is_byte_identical_and_resolves(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan, readable, capsule = self._fixture(root)

            report = audit_dependency_capsule(
                plan,
                readable,
                capsule,
                javac_command="javac",
                release=9,
            )

            self.assertEqual(
                report["summary"]["candidate_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["readable_present_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["capsule_present_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["byte_identical_count"],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "capsule_release_resolved_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "capsule_default_resolved_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "readable_release_resolved_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"]["javap_resolved_count"],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "capsule_release_classifications"
                ],
                {"javac_resolves_exact_class": 1},
            )
            self.assertEqual(
                report["summary"][
                    "capsule_default_classifications"
                ],
                {"javac_resolves_exact_class": 1},
            )
            self.assertEqual(
                report["summary"][
                    "readable_release_classifications"
                ],
                {"javac_resolves_exact_class": 1},
            )
            self.assertEqual(
                report["summary"]["javap_classifications"],
                {"javap_resolves_exact_class": 1},
            )

    def test_transitive_dependency_pruning_is_distinguished_from_target_lookup(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "src"
            dep = src / "dep"
            missing = src / "missing"
            dep.mkdir(parents=True)
            missing.mkdir(parents=True)

            missing_source = missing / "Missing.java"
            missing_source.write_text(
                "package missing; public class Missing {}\n",
                encoding="utf-8",
            )
            fallback_source = dep / "Fallback.java"
            fallback_source.write_text(
                "package dep; public class Fallback { "
                "public missing.Missing value; }\n",
                encoding="utf-8",
            )

            classes = root / "classes"
            classes.mkdir()
            proc = subprocess.run(
                [
                    "javac",
                    "--release",
                    "9",
                    "-d",
                    str(classes),
                    str(missing_source),
                    str(fallback_source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                proc.returncode,
                0,
                proc.stdout + proc.stderr,
            )

            readable = root / "readable.jar"
            capsule = root / "dependency-capsule.jar"
            fallback_bytes = (
                classes / "dep" / "Fallback.class"
            ).read_bytes()
            missing_bytes = (
                classes / "missing" / "Missing.class"
            ).read_bytes()

            with zipfile.ZipFile(
                readable,
                "w",
                zipfile.ZIP_STORED,
            ) as z:
                z.writestr(
                    "dep/Fallback.class",
                    fallback_bytes,
                )
                z.writestr(
                    "missing/Missing.class",
                    missing_bytes,
                )

            with zipfile.ZipFile(
                capsule,
                "w",
                zipfile.ZIP_STORED,
            ) as z:
                z.writestr(
                    "dep/Fallback.class",
                    fallback_bytes,
                )

            plan = {
                "schema_version": 1,
                "kind": "javac_missing_class_recovery_plan",
                "plan_id": "JCLASSPLAN_" + "2" * 20,
                "identifiers_included": True,
                "candidates": [
                    {
                        "candidate_id": "JCLASSMISS_001",
                        "candidate_internal_name": "dep/Fallback",
                    }
                ],
            }

            first = audit_dependency_capsule(
                plan,
                readable,
                capsule,
                javac_command="javac",
                release=9,
            )
            second = audit_dependency_capsule(
                plan,
                readable,
                capsule,
                javac_command="javac",
                release=9,
            )

            self.assertEqual(
                first["audit_id"],
                second["audit_id"],
            )
            self.assertEqual(
                first["summary"][
                    "capsule_release_resolved_count"
                ],
                0,
            )
            self.assertEqual(
                first["summary"][
                    "capsule_default_resolved_count"
                ],
                0,
            )
            self.assertEqual(
                first["summary"][
                    "readable_release_resolved_count"
                ],
                1,
            )
            self.assertEqual(
                first["summary"]["javap_resolved_count"],
                1,
            )
            self.assertEqual(
                first["summary"][
                    "readable_release_classifications"
                ],
                {"javac_resolves_exact_class": 1},
            )

    def test_missing_capsule_entry_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan, readable, capsule = self._fixture(root)

            with zipfile.ZipFile(
                capsule,
                "w",
                zipfile.ZIP_STORED,
            ) as z:
                z.writestr("dep/Other.class", b"not-a-class")

            report = audit_dependency_capsule(
                plan,
                readable,
                capsule,
                javac_command="javac",
                release=None,
            )

            self.assertEqual(
                report["summary"]["readable_present_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["capsule_present_count"],
                0,
            )
            self.assertEqual(
                report["summary"]["byte_identical_count"],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "capsule_release_classifications"
                ],
                {"not_run": 1},
            )
            self.assertEqual(
                report["summary"][
                    "capsule_default_classifications"
                ],
                {"not_run": 1},
            )
            self.assertEqual(
                report["summary"][
                    "readable_release_classifications"
                ],
                {"not_run": 1},
            )
            self.assertEqual(
                report["summary"]["javap_classifications"],
                {"not_run": 1},
            )

    def test_public_report_redacts_exact_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan, readable, capsule = self._fixture(root)

            public = audit_dependency_capsule(
                plan,
                readable,
                capsule,
                javac_command="javac",
                release=None,
            )
            private = audit_dependency_capsule(
                plan,
                readable,
                capsule,
                javac_command="javac",
                release=None,
                include_identifiers=True,
            )

            self.assertEqual(public["audit_id"], private["audit_id"])
            self.assertNotIn("dep/Fallback", str(public))
            self.assertIn("dep/Fallback", str(private))


if __name__ == "__main__":
    unittest.main()
