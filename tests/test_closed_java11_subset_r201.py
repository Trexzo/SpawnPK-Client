"""R201 synthetic Java 11 subset compilation acceptance."""
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from closed_java11_subset_r201 import recover_subset

class ClosedJava11SubsetTests(unittest.TestCase):
    def test_compiling_subset_and_rejected_owner(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d);source=path/"input.zip";output=path/"subset.zip"
            with zipfile.ZipFile(source,"w") as z:
                z.writestr("src/demo/A.java","package demo; class A { int add(int x) { return x+1; } }")
                z.writestr("src/demo/B.java","package demo; class B { Unknown missing; }")
                z.writestr("src/demo/C.java","package demo; import external.Api; class C {}")
            history=recover_subset(source,output)
            self.assertEqual(2,history[0]["sources"])
            self.assertEqual(1,history[-1]["sources"])
            with zipfile.ZipFile(output) as z:
                self.assertIn("src/demo/A.java",z.namelist())
                self.assertNotIn("src/demo/B.java",z.namelist())
                self.assertEqual(1,json.loads(z.read("PRIVATE_SUBSET_MANIFEST.json"))["count"])
    def test_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d);source=path/"a.zip";output=path/"out.zip"
            with zipfile.ZipFile(source,"w") as z:
                z.writestr("src/A.java","class A {}")
            recover_subset(source,output)
            with self.assertRaises(FileExistsError):
                recover_subset(source,output)

if __name__=="__main__":
    unittest.main()
