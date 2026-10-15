"""Synthetic R198 tests: complete imports, internal ownership, and JAR verification."""
import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from source_import_coverage_r198 import analyze_coverage

class ImportCoverageTests(unittest.TestCase):
    def test_all_imports_not_only_six_samples(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / "src.zip"
            names = ["A", "B", "C", "D", "E", "F", "G", "H"]
            imports = "".join("import external.api.%s;\n" % n for n in names)
            imports += "import local.Internal;\nimport java.util.List;\n"
            imports += "import unknown.misc.Absent;\nimport static external.api.A.VALUE;\n"
            with zipfile.ZipFile(src,"w") as z:
                z.writestr("src/local/Thing.java","package local;\n"+imports+"class Thing {}")
                z.writestr("src/local/Internal.java","package local; class Internal {}")
            jar = root / "dep.jar"
            with zipfile.ZipFile(jar,"w") as z:
                for n in names:
                    z.writestr("external/api/%s.class" % n,b"synthetic")
            pin = hashlib.sha256(jar.read_bytes()).hexdigest()
            report = analyze_coverage(src,[jar],{"dep.jar":pin})
            c = report["direct_import_counts"]
            self.assertEqual(8,c["approved_dependency"])
            self.assertEqual(1,c["internal_source"])
            self.assertEqual(1,c["jdk_namespace_candidate"])
            self.assertEqual(1,c["unresolved"])
            self.assertEqual(1,report["ambiguous_imports"]["static_or_wildcard"])
            self.assertEqual("unknown.misc",report["unresolved_by_package"][0]["package"])

    def test_missing_pin_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            src=root/"src.zip"
            with zipfile.ZipFile(src,"w") as z:
                z.writestr("src/X.java","class X {}")
            jar=root/"bad.jar"
            with zipfile.ZipFile(jar,"w") as z:
                z.writestr("other/Y.class",b"synthetic")
            with self.assertRaisesRegex(ValueError,"SHA approved"):
                analyze_coverage(src,[jar],{})

if __name__=="__main__":
    unittest.main()
