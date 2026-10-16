"""Attest private R203 source-only Java 11 build. No external jars or client-JAR fallback."""
import argparse,hashlib,json,subprocess,tempfile,zipfile
from pathlib import Path
def sha(b):return hashlib.sha256(b).hexdigest()
def attest(source_zip,output):
 with zipfile.ZipFile(source_zip) as z:
  names=z.namelist()
  if len(names)!=len(set(names)):raise ValueError("Duplicate entries")
  m=json.loads(z.read("PRIVATE_R203_MANIFEST.json"))
  files=m["subset_filenames"]
  if len(files)!=379 or len(set(files))!=379:raise ValueError("Source count mismatch")
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);paths=[];source_hash={}
   for rel in files:
    if rel.startswith("/") or "\\" in rel or ".." in Path(rel).parts:raise ValueError("Unsafe path")
    blob=z.read("src/"+rel);p=root/"src"/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob)
    paths.append(str(p));source_hash[rel]=sha(blob)
   p=subprocess.run(["javac","--release","11","-proc:none","-g:none","-encoding","UTF-8",
                     "-d",str(root/"classes"),*paths],capture_output=True,text=True)
   if p.returncode:raise RuntimeError("Failed private Java 11 compilation: "+p.stderr[-800:])
   binaries={x.relative_to(root/"classes").as_posix():sha(x.read_bytes()) for x in sorted((root/"classes").rglob("*.class"))}
   if not binaries:raise ValueError("No class files")
   result={"source_count":len(files),"classfile_count":len(binaries),"input_sha256":sha(source_zip.read_bytes()),
     "source_sha256":source_hash,"classfile_sha256":binaries,
     "scope":"Independent source-only Java 11 candidate compilation, NOT original-v309 bytecode equivalence"}
   with zipfile.ZipFile(output,"x",zipfile.ZIP_DEFLATED) as out:
    out.writestr("PRIVATE_ATTESTATION.json",json.dumps(result,indent=2))
    for rel in binaries:out.write(root/"classes"/rel,"classes/"+rel)
 return {"sources":len(files),"classfiles":len(binaries)}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--source-zip",required=True,type=Path);p.add_argument("--out-zip",required=True,type=Path);a=p.parse_args()
 print(json.dumps(attest(a.source_zip,a.out_zip)))
