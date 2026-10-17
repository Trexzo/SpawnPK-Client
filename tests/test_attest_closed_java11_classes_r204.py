import hashlib,json,sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from attest_closed_java11_classes_r204 import attest
class AttestationTests(unittest.TestCase):
 def test_clean_java11_build_with_hashes_and_no_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/"in.zip";output=root/"out.zip"
   names=["demo/C%03d.java"%i for i in range(379)]
   with zipfile.ZipFile(source,"w") as z:
    for i,n in enumerate(names):
     z.writestr("src/"+n,"package demo; public class C%03d {}"%i)
    z.writestr("PRIVATE_R203_MANIFEST.json",json.dumps({"subset_filenames":names}))
   result=attest(source,output)
   self.assertEqual(379,result["sources"])
   self.assertEqual(379,result["classfiles"])
   with zipfile.ZipFile(output) as z:
    meta=json.loads(z.read("PRIVATE_ATTESTATION.json"))
    self.assertEqual(379,len(meta["classfile_sha256"]))
    first=z.read("classes/demo/C000.class")
    self.assertEqual(hashlib.sha256(first).hexdigest(),meta["classfile_sha256"]["demo/C000.class"])
   with self.assertRaises(FileExistsError):attest(source,output)
if __name__=="__main__":unittest.main()
