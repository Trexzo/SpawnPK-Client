"""R49: synthetic Java9 Boolean negation initializer micro-parity."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.boolean_negation_initializer_microparity import (
    BooleanNegationParityError,
    verify_boolean_negation_initializer,
)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class BooleanNegationSourceJavacTests(unittest.TestCase):
    def _jar(self, root: Path, name: str, body: str) -> Path:
        src = root / name / "source" / "p"
        classes = root / name / "classes"
        src.mkdir(parents=True)
        classes.mkdir(parents=True)
        java = src / "Example.java"
        java.write_text(
            "package p; public class Example {" + body + "}",
            encoding="utf-8",
        )
        proc = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(java)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        jar = root / (name + ".jar")
        with ZipFile(jar, "w") as archive:
            archive.write(classes / "p" / "Example.class", "p/Example.class")
        return jar

    def _verify(self, original: Path, candidate: Path, *, candidate_pin=None):
        return verify_boolean_negation_initializer(
            original, candidate,
            original_sha256=_sha(original),
            candidate_sha256=candidate_pin or _sha(candidate),
            class_entry="p/Example.class",
            source_field="flag", target_field="inverse",
        )

    def test_exact_six_instructions_even_when_initializer_pc_differs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._jar(
                root, "original",
                "public static boolean flag;"
                "public static boolean inverse=!flag;",
            )
            candidate = self._jar(
                root, "candidate",
                "public static boolean extra=true;"
                "public static boolean flag;"
                "public static boolean inverse=!flag;",
            )
            report = self._verify(original, candidate)
            self.assertTrue(report["microparity_pass"])
            self.assertEqual(report["original_slice_instruction_count"], 6)
            self.assertEqual(report["candidate_slice_instruction_count"], 6)
            self.assertNotEqual(
                report["original_slice_start_pc"],
                report["candidate_slice_start_pc"],
            )
            self.assertTrue(all(report["checks"].values()))
            for key in (
                "full_clinit_equivalence_certified",
                "enum_dependent_boolean_initializer_recovered",
                "original_runtime_semantics_certified",
                "complete_source_equivalence_certified",
                "canonical_identity_accepted",
            ):
                self.assertFalse(report[key])
            self.assertNotIn('"flag"', str(report))
            self.assertNotIn('"inverse"', str(report))
            self.assertEqual(report, self._verify(original, candidate))

    def test_no_false_parity_for_unnegated_boolean(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._jar(
                root, "original",
                "public static boolean flag; "
                "public static boolean inverse=!flag;",
            )
            candidate = self._jar(
                root, "candidate",
                "public static boolean flag;"
                "public static boolean inverse=flag;",
            )
            with self.assertRaisesRegex(
                BooleanNegationParityError,
                "NEGATION_SIX_OPCODE_PREFIX_MISSING|NOT_EXACT_BOOLEAN_NEGATION_OPCODE_PATTERN",
            ):
                self._verify(original, candidate)

    def test_boolean_source_field_mismatch_cannot_be_aliased(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._jar(
                root, "original",
                "public static boolean flag;"
                "public static boolean other;"
                "public static boolean inverse=!flag;",
            )
            candidate = self._jar(
                root, "candidate",
                "public static boolean flag;"
                "public static boolean other;"
                "public static boolean inverse=!other;",
            )
            with self.assertRaisesRegex(
                BooleanNegationParityError,
                "NEGATION_USES_DIFFERENT_SOURCE_FIELD",
            ):
                self._verify(original, candidate)

    def test_wrong_original_field_modifiers_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._jar(
                root, "original",
                "public static boolean flag;"
                "public static boolean inverse=!flag;",
            )
            candidate = self._jar(
                root, "candidate",
                "private static boolean flag;"
                "public static boolean inverse=!flag;",
            )
            with self.assertRaisesRegex(
                BooleanNegationParityError,
                "BOOLEAN_FIELD_DECLARATION_NOT_EXACT_MUTABLE_STATIC",
            ):
                self._verify(original, candidate)

    def test_complete_jar_sha256_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._jar(
                root, "original",
                "public static boolean flag;"
                "public static boolean inverse=!flag;",
            )
            candidate = self._jar(
                root, "candidate",
                "public static boolean flag;"
                "public static boolean inverse=!flag;",
            )
            with self.assertRaisesRegex(
                BooleanNegationParityError, "COMPLETE_JAR_SHA256_MISMATCH",
            ):
                self._verify(
                    original, candidate, candidate_pin="0" * 64,
                )


if __name__ == "__main__":
    unittest.main()
