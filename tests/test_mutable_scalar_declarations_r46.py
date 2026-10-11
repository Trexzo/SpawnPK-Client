"""R46 tests: exact mutable scalar Java declarations without guessed values."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_field_scaffold import (
    FieldDeclarationScaffoldError, scaffold_missing_fields,
)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class MutableScalarDeclarationJavacTests(unittest.TestCase):
    def _jar(self, root: Path, name: str, body: str) -> Path:
        src = root / name / "src" / "p"
        compiled = root / name / "classes"
        src.mkdir(parents=True)
        compiled.mkdir(parents=True)
        java = src / "A.java"
        java.write_text("package p; public class A {" + body + "}",
                        encoding="utf-8")
        process = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(compiled), str(java)],
            text=True, capture_output=True,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        jar = root / f"{name}.jar"
        with ZipFile(jar, "w") as archive:
            archive.write(compiled / "p" / "A.class", "p/A.class")
        return jar

    def _run(self, original, candidate, out, *,
             scalar_only=True, constants=False):
        return scaffold_missing_fields(
            original, candidate, out,
            original_sha256=_sha(original),
            candidate_sha256=_sha(candidate),
            class_entry="p/A.class",
            scalar_declarations_only=scalar_only,
            emit_verified_constants=constants,
        )

    def test_exact_original_boolean_int_string_recompiled_without_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = self._jar(root, "original",
                "public static boolean switchFlag;"
                "public static int count;"
                "public static String title;"
                "public static Object dependent;"
                "public static final int literal=42;")
            candidate = self._jar(root, "candidate", "")
            out = root / "fragment"
            report = self._run(original, candidate, out)
            self.assertEqual(report["selection_mode"],
                             "mutable_static_scalar_declarations_only")
            self.assertEqual(report["total_missing_field_declarations"], 5)
            self.assertEqual(report["declarations_staged"], 3)
            self.assertEqual(report["filtered_original_fields_not_staged"], 2)
            self.assertEqual(report["final_fields_needing_initializer_review"], 0)
            self.assertEqual(report["verified_literal_initializers_staged"], 0)
            self.assertFalse(report["mutable_scalar_initializer_semantics_recovered"])
            self.assertFalse(report["source_compilation_certified"])
            fragment = (out / "missing-fields.fragment.txt").read_text()
            for declaration in (
                "public static boolean switchFlag;",
                "public static int count;",
                "public static java.lang.String title;",
            ):
                self.assertIn(declaration, fragment)
            self.assertNotIn("dependent;", fragment)
            self.assertNotIn("literal;", fragment)
            self.assertNotIn("= false", fragment)
            self.assertNotIn("= 0", fragment)
            self.assertNotIn('"switchFlag"', json.dumps(report))
            self.assertNotIn('"title"', json.dumps(report))

            compiled = self._jar(root, "from-fragment", fragment)
            def fields(jar):
                with ZipFile(jar) as archive:
                    prof = profile_class_field_accesses(archive.read("p/A.class"))
                return {(f["name"], f["descriptor"]):
                        (f["access"], f["constant_value"], f["signature"])
                        for f in prof["fields"]}
            actual = fields(compiled)
            original_fields = fields(original)
            self.assertEqual(len(actual), 3)
            for key, value in actual.items():
                self.assertEqual(value, original_fields[key])

    def test_existing_scalar_fields_are_not_duplicated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = self._jar(root, "original",
                "public static boolean first; public static int second;")
            candidate = self._jar(root, "candidate", "public static boolean first;")
            report = self._run(original, candidate, root / "out")
            self.assertEqual(report["declarations_staged"], 1)
            fragment = (root / "out" / "missing-fields.fragment.txt").read_text()
            self.assertIn("public static int second;", fragment)
            self.assertNotIn("boolean first;", fragment)

    def test_modes_cannot_mix_and_existing_output_stays_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = self._jar(root, "original", "public static boolean first;")
            candidate = self._jar(root, "candidate", "")
            out = root / "private"
            with self.assertRaisesRegex(
                FieldDeclarationScaffoldError, "PRIVATE_FIELD_EVIDENCE_UNEVALUABLE",
            ):
                self._run(original, candidate, out, constants=True)
            self.assertFalse(out.exists())
            out.mkdir()
            marker = out / "keep.txt"
            marker.write_text("IMPORTANT", encoding="utf-8")
            with self.assertRaisesRegex(
                FieldDeclarationScaffoldError, "OUTPUT_ROOT_ALREADY_EXISTS",
            ):
                self._run(original, candidate, out)
            self.assertEqual(marker.read_text(), "IMPORTANT")

    def test_default_mode_preserves_unfiltered_original_behavior(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = self._jar(root, "original",
                "public static boolean first; public static Object objectField;")
            candidate = self._jar(root, "candidate", "")
            report = self._run(original, candidate, root / "normal",
                               scalar_only=False)
            self.assertEqual(report["selection_mode"], "all_missing_fields")
            self.assertEqual(report["declarations_staged"], 2)
            self.assertEqual(report["filtered_original_fields_not_staged"], 0)


if __name__ == "__main__":
    unittest.main()
