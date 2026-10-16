import json,sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from expand_closed_java11_subset_r202 import build
class R202Tests(unittest.TestCase):
 def test_internal_source_owner_and_missing_external(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);s=p/"in.zip";o=p/"out.zip"
   with zipfile.ZipFile(s,"w") as z:
    z.writestr("src/demo/A.java","package demo;\nimport demo.B;\nclass A { B b; }")
    z.writestr("src/demo/B.java","package demo; class B {}")
    z.writestr("src/demo/C.java","package demo;\nimport external.Lib;\nclass C {}")
   rounds=build(s,o)
   self.assertTrue(rounds[-1]["errors"]==0)
   with zipfile.ZipFile(o) as z:
    self.assertIn("src/demo/A.java",z.namelist())
    self.assertIn("src/demo/B.java",z.namelist())
    self.assertNotIn("src/demo/C.java",z.namelist())
    self.assertEqual(2,json.loads(z.read("PRIVATE_MANIFEST.json"))["accepted"])
if __name__=="__main__": unittest.main()
