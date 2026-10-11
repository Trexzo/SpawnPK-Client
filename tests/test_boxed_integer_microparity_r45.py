"""R45: independently compiled Java int boxing initializer parity tests."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.boxed_integer_microparity import (
    BoxedIntegerInitializerError,
    verify_boxed_initializer,
)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class BoxedIntegerJava9Tests(unittest.TestCase):
    def _jar(self, root: Path, label: str, body: str) -> Path:
        java = root / label / "source" / "p" / "A.java"
        java.parent.mkdir(parents=True)
        classes = root / label / "classes"
        classes.mkdir(parents=True)
        java.write_text(
            "package p; public class A {" + body +
            " public static void keep(){} }",
            encoding="utf-8",
        )
        process = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(java)],
            capture_output=True, text=True,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as z:
            z.write(classes / "p" / "A.class", "p/A.class")
        return jar

    def _run(self, original: Path, candidate: Path, *, pin=None):
        return verify_boxed_initializer(
            original, candidate, original_sha256=_sha(original),
            candidate_sha256=pin or _sha(candidate),
            class_entry="p/A.class", field_name="boxed",
        )

    def test_equal_valueof_allocation_without_equal_clinit_offsets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._jar(
                root, "original",
                "public static int unrelated=3;"
                "public static final Integer boxed=Integer.valueOf(42000);",
            )
            candidate = self._jar(
                root, "candidate",
                "public static final Integer boxed=Integer.valueOf(42000);",
            )
            report = self._run(original, candidate)
            self.assertTrue(report["microparity_pass"])
            self.assertTrue(all(report["checks"].values()))
            self.assertNotEqual(report["original_init_start_offset"],
                                report["candidate_init_start_offset"])
            self.assertNotIn("boxed", str(report))
            self.assertNotIn("42000", str(report))
            for flag in ("full_clinit_equivalence_certified",
                         "whole_source_equivalence_certified",
                         "runtime_semantics_certified",
                         "canonical_identity_accepted"):
                self.assertFalse(report[flag])
            self.assertEqual(report, self._run(original, candidate))

    def test_changed_integer_literal_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._jar(
                root, "original",
                "public static final Integer boxed=Integer.valueOf(42000);",
            )
            candidate = self._jar(
                root, "candidate",
                "public static final Integer boxed=Integer.valueOf(42001);",
            )
            report = self._run(original, candidate)
            self.assertFalse(report["microparity_pass"])
            self.assertFalse(report["checks"]["exact_jvm_integer_constant_bits"])

    def test_new_object_constructor_is_not_valueof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._jar(
                root, "original",
                "public static final Integer boxed=Integer.valueOf(42000);",
            )
            candidate = self._jar(
                root, "candidate",
                "public static final Integer boxed=new Integer(42000);",
            )
            with self.assertRaises(BoxedIntegerInitializerError):
                self._run(original, candidate)

    def test_nonfinal_field_does_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._jar(
                root, "original",
                "public static final Integer boxed=Integer.valueOf(42000);",
            )
            candidate = self._jar(
                root, "candidate",
                "public static Integer boxed=Integer.valueOf(42000);",
            )
            with self.assertRaises(BoxedIntegerInitializerError):
                self._run(original, candidate)

    def test_sha_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._jar(
                root, "original",
                "public static final Integer boxed=Integer.valueOf(42000);",
            )
            candidate = self._jar(
                root, "candidate",
                "public static final Integer boxed=Integer.valueOf(42000);",
            )
            with self.assertRaisesRegex(
                BoxedIntegerInitializerError, "WHOLE_JAR_SHA256_MISMATCH",
            ):
                self._run(original, candidate, pin="0" * 64)


if __name__ == "__main__":
    unittest.main()
