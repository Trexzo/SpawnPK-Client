"""Synthetic import frontier tests, intentionally no original client source."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from source_import_frontier_r196 import analyze

class ImportFrontierTests(unittest.TestCase):
    def test_missing_import_is_not_claimed_as_root_cause(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tiny.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("src/example/Foo.java",
                           "package example;\nimport java.util.List;\n"
                           "import example.Bar;\nimport external.logging.Logger;\n"
                           "class Foo {}")
                z.writestr("src/example/Bar.java", "package example; class Bar {}")
            result = analyze(path)
            self.assertEqual(2, result["source_count"])
            self.assertEqual(1, result["unresolved_direct_import_count"])
            self.assertEqual("external.logging", result["unresolved_packages"][0]["package"])
            self.assertEqual(1, result["affected_source_count"])
            self.assertTrue(result["interpretation"])

    def test_duplicate_java_member_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tiny.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("src/Foo.java", "class Foo {}")
                z.writestr("src/Foo.java", "class Foo {}")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                analyze(path)

    def test_static_and_wildcard_remain_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tiny.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("src/Foo.java",
                    "import static third.party.Owner.METHOD;\n"
                    "import third.party.*;\nclass Foo {}")
            result = analyze(path)
            self.assertEqual(0, result["unresolved_direct_import_count"])
            self.assertEqual(2, result["ambiguous_imports"]["static_or_wildcard_import"])

if __name__ == "__main__":
    unittest.main()
