"""Synthetic fixtures only; no original SpawnPK Java is public."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from private_sneakythrows_rewrite_r194 import rewrite_java, main


class SourceRewriteTests(unittest.TestCase):
    def test_converts_multiple_methods_with_original_throws_identity(self):
        text = """package example;
import lombok.SneakyThrows;
public class Example {
    @SneakyThrows public static int get(boolean fail) {
        if (fail) { throw new java.io.IOException("original"); }
        return 42;
    }
    @SneakyThrows public static void noop() { }
}
"""
        modified, count = rewrite_java(text)
        self.assertEqual(2, count)
        self.assertNotIn("import lombok.", modified)
        self.assertIn("throw spkRecoverySneaky", modified)
        self.assertEqual(modified, rewrite_java(modified)[0])
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "Example.java"
            src.write_text(modified, encoding="utf-8")
            harness = Path(d) / "Check.java"
            harness.write_text("""import example.Example;
class Check {
 public static void main(String[] args) {
   if (Example.get(false) != 42) throw new AssertionError();
   try { Example.get(true); throw new AssertionError(); }
   catch (Throwable e) {
     if (!(e instanceof java.io.IOException) || !"original".equals(e.getMessage()))
       throw new AssertionError(e);
   }
 }
}""", encoding="utf-8")
            Path(d, "example").mkdir()
            src.rename(Path(d, "example", "Example.java"))
            subprocess.run(["javac", "--release", "9", "-d", d,
                            str(Path(d, "example", "Example.java")), str(harness)],
                           check=True, capture_output=True)
            subprocess.run(["java", "-cp", d, "Check"], check=True, capture_output=True)

    def test_rejects_unsupported_or_already_rewritten(self):
        with self.assertRaisesRegex(ValueError, "Helper"):
            rewrite_java("class X { void spkRecoverySneaky(){} }")
        with self.assertRaisesRegex(ValueError, "No method body"):
            rewrite_java("@SneakyThrows interface A { void call(); }")

    def test_preserves_braces_in_strings_and_comments(self):
        src = """class S {
 @SneakyThrows static String go() { // } misleading
   return "not a } bracket";
 }
}"""
        rewritten, count = rewrite_java(src)
        self.assertEqual(1, count)
        self.assertIn('return "not a } bracket";', rewritten)


if __name__ == "__main__":
    unittest.main()
