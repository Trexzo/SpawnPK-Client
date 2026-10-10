"""R41 synthetic JVM field-scaffold tests; no proprietary original code."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_field_scaffold import (
    FieldDeclarationScaffoldError,
    descriptor_java_type,
    plan_missing_field_declarations,
    scaffold_missing_fields,
)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ExactFieldScaffoldJavacTests(unittest.TestCase):
    def _jar(self, root: Path, name: str, fields: str) -> Path:
        src = root / name / "source" / "p"
        classes = root / name / "classes"
        src.mkdir(parents=True)
        classes.mkdir()
        java = src / "A.java"
        java.write_text(
            "package p; public class A { " + fields +
            " public int get(){return 1;} }",
            encoding="utf-8",
        )
        run = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(java)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        jar = root / f"{name}.jar"
        with ZipFile(jar, "w") as archive:
            archive.write(classes / "p" / "A.class", "p/A.class")
        return jar

    def _pair(self, root: Path, *, candidate_fields=None):
        original = self._jar(root, "original",
            "public static int same;"
            "public static final int PIN=7;"
            "public static boolean enabled;"
            "public static String text;"
            "public static int[] nums;"
        )
        candidate = self._jar(root, "candidate",
            candidate_fields if candidate_fields is not None else
            "public static int same; public static String text;"
            "public static boolean extra;"
        )
        return original, candidate

    def _run(self, old: Path, new: Path, dest: Path, old_pin=None, new_pin=None):
        return scaffold_missing_fields(
            old, new, dest, original_sha256=old_pin or _sha(old),
            candidate_sha256=new_pin or _sha(new),
            class_entry="p/A.class",
        )

    def test_scaffold_emits_exact_declarations_without_fake_initializers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old, new = self._pair(root)
            out = root / "private"
            report = self._run(old, new, out)
            self.assertEqual(report["original_field_count"], 5)
            self.assertEqual(report["candidate_field_count"], 3)
            self.assertEqual(report["declarations_staged"], 3)
            self.assertEqual(report["final_fields_needing_initializer_review"], 1)
            self.assertEqual(report["final_fields_with_exact_constant_value_evidence"], 1)
            self.assertEqual(report["final_fields_without_constant_value_evidence"], 0)
            self.assertEqual(report["static_fields_staged"], 3)
            self.assertEqual(report["java_type_counts"],
                             {"primitive": 2, "array": 1, "reference": 0})
            self.assertFalse(report["runtime_field_initialization_recovered"])
            self.assertFalse(report["source_compilation_certified"])
            self.assertFalse(report["canonical_identity_accepted"])
            snippet = (out / "missing-fields.fragment.txt").read_text()
            for line in ("public static final int PIN;",
                         "public static boolean enabled;",
                         "public static int[] nums;"):
                self.assertIn(line, snippet)
            self.assertNotIn("PIN =", snippet)
            self.assertNotIn("static int same;", snippet)
            self.assertNotIn("static String text;", snippet)
            self.assertNotIn("static boolean extra;", snippet)
            self.assertTrue("PRIVATE" in snippet)
            self.assertNotIn("PIN", json.dumps(report))
            self.assertNotIn("enabled", json.dumps(report))
            self.assertNotIn("p/A", json.dumps(report))
            self.assertEqual(_sha(out / "missing-fields.fragment.txt"),
                             report["snippet_sha256"])
            self.assertEqual(
                json.loads((out / "private-field-scaffold-manifest.json").read_text()),
                report,
            )

    def test_replay_is_deterministic_with_distinct_output_roots(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old, new = self._pair(root)
            one = self._run(old, new, root / "one")
            two = self._run(old, new, root / "two")
            self.assertEqual(one, two)
            self.assertEqual(
                (root / "one" / "missing-fields.fragment.txt").read_bytes(),
                (root / "two" / "missing-fields.fragment.txt").read_bytes(),
            )

    def test_modified_existing_field_is_not_duplicated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old, new = self._pair(root, candidate_fields=(
                "public static final int same=3;"
                "public static String text;"
            ))
            report = self._run(old, new, root / "scaffold")
            self.assertEqual(report["shared_metadata_differences_unmodified"], 1)
            snippet = (root / "scaffold" / "missing-fields.fragment.txt").read_text()
            self.assertNotIn("static int same;", snippet)
            self.assertEqual(report["declarations_staged"], 3)

    def test_wrong_sha_refused_without_any_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old, new = self._pair(root)
            out = root / "no-output"
            with self.assertRaisesRegex(
                FieldDeclarationScaffoldError, "PRIVATE_FIELD_EVIDENCE_UNEVALUABLE",
            ):
                self._run(old, new, out, old_pin="0" * 64)
            self.assertFalse(out.exists())

    def test_no_overwrite_even_if_output_contains_important_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old, new = self._pair(root)
            out = root / "occupied"
            out.mkdir()
            marker = out / "important.txt"
            marker.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(FieldDeclarationScaffoldError,
                                        "OUTPUT_ROOT_ALREADY_EXISTS"):
                self._run(old, new, out)
            self.assertEqual(marker.read_text(), "KEEP")

    def test_when_no_fields_missing_only_private_header_is_emitted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old, _ = self._pair(root)
            candidate = root / "identical-copy.jar"
            candidate.write_bytes(old.read_bytes())
            report = self._run(old, candidate, root / "output")
            self.assertEqual(report["declarations_staged"], 0)
            self.assertEqual(report["final_fields_needing_initializer_review"], 0)
            self.assertEqual(report["final_fields_with_exact_constant_value_evidence"], 0)
            self.assertEqual(report["final_fields_without_constant_value_evidence"], 0)
            self.assertFalse(report["source_compilation_certified"])


class FieldDescriptorAndModiferTests(unittest.TestCase):
    def test_safe_primitives_arrays_and_object_descriptors(self):
        self.assertEqual(descriptor_java_type("Z"), ("boolean", "primitive"))
        self.assertEqual(descriptor_java_type("[[I"), ("int[][]", "array"))
        self.assertEqual(descriptor_java_type("Ljava/lang/String;"),
                         ("java.lang.String", "reference"))
        self.assertEqual(descriptor_java_type("Ldemo/pkg/Outer$Nested;"),
                         ("demo.pkg.Outer$Nested", "reference"))
        self.assertEqual(descriptor_java_type("[Ldemo/pkg/Outer$Nested;"),
                         ("demo.pkg.Outer$Nested[]", "array"))

    def test_invalid_jvm_descriptors_refused_instead_of_guessed(self):
        for broken in ("", "V", "(I)V", "Lbad", "Lbad//Name;", "[[",
                       "Lpackage/class;", "Lrs/void;", "I;", "[V", "[" * 256 + "I"):
            with self.subTest(broken=broken):
                with self.assertRaises(FieldDeclarationScaffoldError):
                    descriptor_java_type(broken)

    def test_generic_signature_and_non_java_field_flag_veto(self):
        original = {
            "internal_name": "p/A",
            "fields": [
                {"name": "a", "descriptor": "Ljava/util/List;",
                 "access": 0x0008, "signature": "Ljava/util/List<Ljava/lang/String;>;",
                 "constant_value": None},
            ],
        }
        candidate = {"internal_name": "p/A", "fields": []}
        matrix = {
            "research_only": True, "source_equivalence_certified": False,
            "canonical_identity_accepted": False,
            "original_declared_field_count": 1,
            "candidate_declared_field_count": 0,
            "field_counts": {"missing_field": 1,
                             "shared_metadata_difference": 0},
        }
        with self.assertRaisesRegex(
            FieldDeclarationScaffoldError, "GENERIC_FIELD_SIGNATURE_NEEDS_MANUAL",
        ):
            plan_missing_field_declarations(original, candidate, matrix)
        original["fields"][0]["signature"] = None
        original["fields"][0]["access"] = 0x1008
        with self.assertRaisesRegex(
            FieldDeclarationScaffoldError, "FIELD_ACCESS_HAS_NON_JAVA_FLAGS",
        ):
            plan_missing_field_declarations(original, candidate, matrix)

    def test_name_collision_and_wrong_authority_refused(self):
        original = {"internal_name": "p/A", "fields": [
            {"name": "same", "descriptor": "I", "access": 0x0008,
             "signature": None, "constant_value": None},
        ]}
        candidate = {"internal_name": "p/A", "fields": [
            {"name": "same", "descriptor": "Z", "access": 0x0008,
             "signature": None, "constant_value": None},
        ]}
        matrix = {
            "research_only": True, "source_equivalence_certified": False,
            "canonical_identity_accepted": False,
            "original_declared_field_count": 1,
            "candidate_declared_field_count": 1,
            "field_counts": {"missing_field": 1,
                             "shared_metadata_difference": 0},
        }
        with self.assertRaisesRegex(
            FieldDeclarationScaffoldError,
            "JAVA_FIELD_NAME_COLLISION_WITH_DIFFERENT_DESCRIPTOR",
        ):
            plan_missing_field_declarations(original, candidate, matrix)
        matrix["source_equivalence_certified"] = True
        with self.assertRaisesRegex(
            FieldDeclarationScaffoldError, "STRICT_MATRIX_AUTHORITY_UNEXPECTED",
        ):
            plan_missing_field_declarations(original, candidate, matrix)


if __name__ == "__main__":
    unittest.main()
