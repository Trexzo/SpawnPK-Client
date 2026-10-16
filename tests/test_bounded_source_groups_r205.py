import json,sys,tempfile,unittest,zipfile,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from bounded_source_groups_r205 import main
class BoundedTest(unittest.TestCase):
 def test_group_accepts_linked_sources_and_rejects_missing_symbol(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);src=root/"src.zip";accepted=root/"accepted.json";out=root/"out.json"
   with zipfile.ZipFile(src,"w") as z:
    z.writestr("src/demo/A.java","package demo; class A {}")
    z.writestr("src/extra/B.java","package extra; class B { C c; }")
    z.writestr("src/extra/C.java","package extra; class C {}")
    z.writestr("src/broken/D.java","package broken; class D { Missing m; }")
   accepted.write_text(json.dumps(["demo/A.java"]))
   args=["tool","--source-zip",str(src),"--accepted-manifest",str(accepted),
        "--output",str(out),"--group-limit","20"]
   before=sys.argv
   try:
    sys.argv=args;main()
   finally:sys.argv=before
   result=json.loads(out.read_text())
   self.assertEqual(3,result["accepted_sources"])
   self.assertEqual(2,result["newly_compiling_sources"])
   self.assertIn("extra/B.java",result["verified_sources"])
   self.assertNotIn("broken/D.java",result["verified_sources"])
if __name__=="__main__":unittest.main()
