"""R44: JVM int-array micro-parity tested on synthetic Java classes only."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.array_initializer_microparity import (
    ArrayInitializerParityError, verify_array_initializer,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ExactJavacIntArrayInitializationTests(unittest.TestCase):
    def _jar(self, root: Path, stem: str, fields: str) -> Path:
        src = root / stem / "source" / "p"
        out = root / stem / "classes"
        src.mkdir(parents=True)
        out.mkdir(parents=True)
        java = src / "A.java"
        java.write_text(
            "package p; public class A {" + fields +
            " public static void other(){} }", encoding="utf-8",
        )
        proc = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(out), str(java)], capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        path = root / (stem + ".jar")
        with ZipFile(path, "w") as archive:
            archive.write(out / "p" / "A.class", "p/A.class")
        return path

    def _run(self, a, b, *, old_pin=None, new_pin=None):
        return verify_array_initializer(
            a, b, original_sha256=old_pin or _sha(a),
            candidate_sha256=new_pin or _sha(b),
            class_entry="p/A.class", field_name="values",
        )

    def test_equal_allocation_across_changed_class_initializer_offsets(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = self._jar(
                root, "original",
                'public static String unrelated = "private";'
                'public static final int[] values = new int[10];',
            )
            new = self._jar(
                root, "candidate",
                "public static final int[] values = new int[10];",
            )
            result = self._run(old, new)
            self.assertTrue(result["microparity_pass"])
            self.assertTrue(all(result["checks"].values()))
            self.assertEqual(result["original_allocation_length"], 10)
            self.assertEqual(result["candidate_allocation_length"], 10)
            self.assertNotEqual(result["original_allocation_start_pc"],
                                result["candidate_allocation_start_pc"])
            for name in ("source_equivalence_certified",
                         "full_clinit_equivalence_certified",
                         "original_class_identity_accepted",
                         "runtime_equivalence_certified"):
                self.assertFalse(result[name])
            self.assertNotIn("values", str(result))
            self.assertEqual(result, self._run(old, new))

    def test_different_length_is_detected_without_fake_acceptance(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = self._jar(root, "original",
                            "public static final int[] values = new int[10];")
            new = self._jar(root, "candidate",
                            "public static final int[] values = new int[9];")
            result = self._run(old, new)
            self.assertFalse(result["checks"]["exact_array_length"])
            self.assertFalse(result["microparity_pass"])

    def test_missing_final_modifier_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = self._jar(root, "original",
                            "public static final int[] values = new int[10];")
            new = self._jar(root, "candidate",
                            "public static int[] values = new int[10];")
            with self.assertRaises(ArrayInitializerParityError):
                self._run(old, new)

    def test_missing_initializer_or_wrong_array_type_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = self._jar(root, "original",
                            "public static final int[] values = new int[10];")
            new = self._jar(root, "candidate",
                            "public static final int[] values; "
                            "static { values = java.util.Arrays.copyOf(new int[5], 10); }")
            with self.assertRaises(ArrayInitializerParityError):
                self._run(old, new)

    def test_wrong_complete_jar_sha_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = self._jar(root, "original",
                            "public static final int[] values = new int[10];")
            new = self._jar(root, "candidate",
                            "public static final int[] values = new int[10];")
            with self.assertRaisesRegex(
                ArrayInitializerParityError, "WHOLE_JAR_SHA256_MISMATCH",
            ):
                self._run(old, new, new_pin="0" * 64)


if __name__ == "__main__":
    unittest.main()
