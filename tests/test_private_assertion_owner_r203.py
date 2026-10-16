import hashlib,sys,tempfile,unittest,zipfile,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from private_assertion_owner_r203 import patch

class AssertionOwnerTests(unittest.TestCase):
 def test_single_exact_rewrite_compiles_three_linked_java_classes(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);source=root/"before.zip";out=root/"after.zip"
   parts={
    "src/demo/A.java":"package demo; class A extends Base { B child; static final boolean CHECK = !Missing.class.desiredAssertionStatus(); }",
    "src/demo/B.java":"package demo; class B { A node; C next; }",
    "src/demo/C.java":"package demo; class C { B prev; }",
    "src/demo/Base.java":"package demo; class Base {}"}
   with zipfile.ZipFile(source,"w") as z:
    for path,code in parts.items():z.writestr(path,code)
   approved=hashlib.sha256(parts["src/demo/A.java"].encode()).hexdigest()
   patch(source,out,"src/demo/A.java",approved,"Missing","A")
   with zipfile.ZipFile(out) as z:
    for name in z.namelist():
     p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
   java=sorted(str(p) for p in (root/"src").rglob("*.java"))
   subprocess.run(["javac","--release","11","-d",str(root/"classes"),*java],check=True,capture_output=True)
   with self.assertRaisesRegex(ValueError,"preflight"):
    patch(source,root/"wrong.zip","src/demo/A.java","0"*64,"Missing","A")
if __name__=="__main__":unittest.main()
