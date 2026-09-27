from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_capsule_audit import (
    _source_name_profile,
    audit_dependency_capsule,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DependencyCapsuleAuditTests(unittest.TestCase):
    def test_source_name_profile_accepts_ordinary_binary_name(self):
        self.assertEqual(
            _source_name_profile("com/example/Fallback"),
            {
                "classification": "source_spellable",
                "segment_count": 3,
                "failure_count": 0,
                "failures": [],
            },
        )

    def test_source_name_profile_rejects_keyword_segments(self):
        profile = _source_name_profile("com/if/Fallback")
        self.assertEqual(
            profile["classification"],
            "source_unspellable_keyword",
        )
        self.assertEqual(
            profile["failures"],
            [
                {
                    "segment_index": 1,
                    "segment_role": "package",
                    "shape": "keyword",
                }
            ],
        )

        class_keyword = _source_name_profile("com/example/do")
        self.assertEqual(
            class_keyword["classification"],
            "source_unspellable_keyword",
        )
        self.assertEqual(
            class_keyword["failures"][0]["segment_role"],
            "class",
        )

    def test_source_name_profile_rejects_illegal_identifier_spelling(self):
        profile = _source_name_profile("com/bad-name/Fallback")
        self.assertEqual(
            profile["classification"],
            "source_unspellable_identifier",
        )
        self.assertEqual(
            profile["failures"][0]["shape"],
            "invalid_part",
        )

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
                report["summary"]["package_depths"],
                {"1": 1},
            )
            self.assertEqual(
                report["summary"]["default_package_count"],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "class_signature_attribute_count"
                ],
                0,
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
            for source_form in (
                "import_simple",
                "qualified_type",
                "same_package_simple",
            ):
                for channel in (
                    "capsule_release",
                    "capsule_default",
                    "readable_release",
                ):
                    self.assertEqual(
                        report["summary"][
                            "source_form_classifications"
                        ][source_form][channel],
                        {"javac_resolves_exact_class": 1},
                    )
                    self.assertEqual(
                        report["summary"][
                            "source_form_diagnostic_keys"
                        ][source_form][channel],
                        {},
                    )
                    self.assertEqual(
                        report["summary"][
                            "source_form_target_loaded_counts"
                        ][source_form][channel],
                        1,
                    )

    def test_source_forms_distinguish_default_package_import_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "Fallback.java"
            source.write_text(
                "public class Fallback {}\n",
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
            self.assertEqual(
                proc.returncode,
                0,
                proc.stdout + proc.stderr,
            )

            data = (classes / "Fallback.class").read_bytes()
            readable = root / "readable.jar"
            capsule = root / "dependency-capsule.jar"
            for jar in (readable, capsule):
                with zipfile.ZipFile(
                    jar,
                    "w",
                    zipfile.ZIP_STORED,
                ) as z:
                    z.writestr("Fallback.class", data)

            plan = {
                "schema_version": 1,
                "kind": "javac_missing_class_recovery_plan",
                "plan_id": "JCLASSPLAN_" + "3" * 20,
                "identifiers_included": True,
                "candidates": [
                    {
                        "candidate_id": "JCLASSMISS_001",
                        "candidate_internal_name": "Fallback",
                    }
                ],
            }

            report = audit_dependency_capsule(
                plan,
                readable,
                capsule,
                javac_command="javac",
                release=9,
            )
            summary = report["summary"]

            self.assertEqual(
                summary["package_depths"],
                {"0": 1},
            )
            self.assertEqual(
                summary["default_package_count"],
                1,
            )

            self.assertEqual(
                summary["source_form_classifications"][
                    "qualified_type"
                ]["capsule_release"],
                {"javac_resolves_exact_class": 1},
            )
            self.assertEqual(
                summary["source_form_classifications"][
                    "same_package_simple"
                ]["capsule_release"],
                {"javac_resolves_exact_class": 1},
            )
            self.assertNotEqual(
                summary["source_form_classifications"][
                    "import_simple"
                ]["capsule_release"],
                {"javac_resolves_exact_class": 1},
            )
            self.assertEqual(
                summary["source_form_target_loaded_counts"][
                    "qualified_type"
                ]["capsule_release"],
                1,
            )
            self.assertEqual(
                summary["source_form_target_loaded_counts"][
                    "same_package_simple"
                ]["capsule_release"],
                1,
            )
            self.assertEqual(
                summary["source_form_target_loaded_counts"][
                    "import_simple"
                ]["capsule_release"],
                0,
            )
            import_keys = summary[
                "source_form_diagnostic_keys"
            ]["import_simple"]["capsule_release"]
            self.assertTrue(import_keys)
            self.assertTrue(
                all(
                    key.startswith("compiler.err.")
                    for key in import_keys
                )
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
                "package dep; public class Fallback "
                "extends missing.Missing {}\n",
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
            self.assertEqual(
                first["summary"][
                    "capsule_release_classifications"
                ],
                second["summary"][
                    "capsule_release_classifications"
                ],
            )
            self.assertEqual(
                first["summary"][
                    "capsule_default_classifications"
                ],
                second["summary"][
                    "capsule_default_classifications"
                ],
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
