"""Source-only CI for exact original-vs-Java9 bytecode branch diagnostics."""
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from spk_recovery.source_parity_diagnostic import first_jvm_parity_difference
from spk_recovery.standalone_source_parity import _normalize_javap


@unittest.skipUnless(
    shutil.which("javac") and shutil.which("javap"), "Requires local JDK",
)
class SourceParityDiagnosticTests(unittest.TestCase):
    def build(self, root: Path, content: str):
        src = root / "src" / "demo" / "Clock.java"
        src.parent.mkdir(parents=True)
        src.write_text(content, encoding="utf-8")
        out = root / "classes"
        out.mkdir()
        built = subprocess.run([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-classpath", str(root / "no-classpath"),
            "-sourcepath", str(root / "no-sourcepath"),
            "-d", str(out), str(src),
        ], capture_output=True, text=True, timeout=30)
        self.assertEqual(built.returncode, 0, built.stderr)
        run = subprocess.run([
            "javap", "-classpath", str(out), "-c", "-p", "-s",
            "demo.Clock",
        ], capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        return _normalize_javap(run.stdout)[0]

    def test_java9_boolean_ternary_branch_inversion_is_detected(self):
        skeleton = """
package demo;
public final class Clock {
  public boolean active() { return System.currentTimeMillis() > 0L; }
  public long left() { return CONDITION ? 0L : 100L; }
}
"""
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            expected = self.build(
                parent / "expected", skeleton.replace("CONDITION", "!active()")
            )
            wrong = self.build(
                parent / "wrong", skeleton.replace("CONDITION", "active()")
            )
        self.assertNotEqual(expected, wrong)
        self.assertIsNone(first_jvm_parity_difference(expected, expected))
        summary = first_jvm_parity_difference(expected, wrong)
        self.assertIsNotNone(summary)
        self.assertIn("reason=instruction_opcode", summary)
        self.assertIn("original_offset=4", summary)
        self.assertIn("rebuilt_offset=4", summary)
        self.assertIn("original_opcode=ifne", summary)
        self.assertIn("rebuilt_opcode=ifeq", summary)
        self.assertNotIn("java/lang/System", summary)
        self.assertNotIn("Clock", summary)

    def test_javac_local_variable_slot_scope_diagnostic(self):
        # Original-source layout can depend on a local variable's lexical
        # lifetime even when the Java values and JVM opcode COUNT match.
        narrow = """
package demo;
public final class Clock {
  public int size(String text) {
    int width = 0;
    { String suffix = text.substring(0); width += suffix.length(); }
    int height = width;
    return height;
  }
}
"""
        broad = narrow.replace(
            "{ String suffix = text.substring(0); width += suffix.length(); }",
            "String suffix = text.substring(0); width += suffix.length();",
        )
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            expected = self.build(parent / "narrow", narrow)
            wrong = self.build(parent / "broad", broad)
        self.assertNotEqual(expected, wrong)
        left_instructions = sum(x[:1].isdigit() for x in expected)
        right_instructions = sum(x[:1].isdigit() for x in wrong)
        self.assertEqual(left_instructions, right_instructions)
        summary = first_jvm_parity_difference(expected, wrong)
        self.assertIsNotNone(summary)
        # Local slots 0..3 use dedicated JVM _n opcode forms, so this
        # test's first mismatch is the opcode encoding itself.
        self.assertIn("reason=instruction_opcode", summary)
        self.assertIn("original_opcode=istore_3", summary)
        self.assertIn("rebuilt_opcode=istore", summary)
        self.assertNotIn("suffix", summary)

    def test_operand_mismatch_is_reported_without_original_values(self):
        original = (
            "CLASS public class demo.Clock {",
            "DECL public long left();",
            "DESC ()J",
            "0: ldc #CP // Long 111111111",
            "2: lreturn",
        )
        other = (*original[:3], "0: ldc #CP // Long 222222222", original[-1])
        summary = first_jvm_parity_difference(original, other)
        self.assertIn("reason=instruction_operand_or_branch_target", summary)
        self.assertNotIn("111111111", summary)
        self.assertNotIn("222222222", summary)
        self.assertNotIn("Long", summary)

    def test_declaration_mismatch_and_missing_instructions(self):
        original = (
            "CLASS public class demo.Clock {", "DECL public long left();",
            "DESC ()J", "0: lconst_0", "1: lreturn",
        )
        other = (*original[:1], "DECL public int left();", *original[2:])
        detail = first_jvm_parity_difference(original, other)
        self.assertIn("reason=declaration_or_descriptor", detail)
        missing = first_jvm_parity_difference(original, original[:-1])
        self.assertIn("reason=instruction_or_declaration_shape", missing)
        self.assertIn("original_opcode=lreturn", missing)
        self.assertIn("rebuilt_opcode=none", missing)


if __name__ == "__main__":
    unittest.main(verbosity=2)
