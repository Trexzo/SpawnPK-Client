"""Synthetic-only source/JAR import coverage tests."""
import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from source_dependency_coverage_r197 import compare

class SourceCoverageTests(unittest.TestCase):
    def test_exact_sample_cover_and_uncovered_import(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "source.zip"
            with zipfile.ZipFile(source, "w") as z:
                z.writestr("src/example/A.java",
                           "package example;\nimport outside.api.Foo;\n"
                           "import missing.api.Other;\nclass A {}")
            jar = root / "lib.jar"
            with zipfile.ZipFile(jar, "w") as z:
                z.writestr("outside/api/Foo.class", b"synthetic fixture")
            pin = hashlib.sha256(jar.read_bytes()).hexdigest()
            result = compare(source, [jar], {"lib.jar": pin})
            rows = {r["package"]: r for r in result["sampled_groups"]}
            self.assertEqual(1, rows["outside.api"]["sampled_import_matches"])
            self.assertEqual(0, rows["missing.api"]["sampled_import_matches"])
            self.assertFalse(rows["outside.api"]["complete_package_coverage_proven"])
            with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                compare(source, [jar], {"lib.jar": "0" * 64})

if __name__ == "__main__":
    unittest.main()
