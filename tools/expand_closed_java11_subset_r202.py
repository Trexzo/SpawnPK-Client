import argparse,json,re,subprocess,tempfile,zipfile,hashlib
from pathlib import Path
def build(src,out):
 with zipfile.ZipFile(src) as z:
  data={n[4:]:z.read(n) for n in z.namelist() if n.startswith("src/") and n.endswith(".java")}
 owners=set()
 for n,b in data.items():
  m=re.search(r"(?m)^\s*package\s+([\w.]+)\s*;",b.decode("utf-8-sig"))
  owners.add((m.group(1)+"." if m else "")+Path(n).stem)
 def covered(v):
  return v.startswith(("java.","javax.","com.apple.")) or v in owners or any(v.startswith(k+".") for k in owners)
 selected={n for n,b in data.items() if all(covered(x) for x in re.findall(r"(?m)^\s*import\s+(?:static\s+)?([\w.*]+)\s*;",b.decode("utf-8-sig")))}
 rounds=[]
 with tempfile.TemporaryDirectory() as d:
  root=Path(d)/"src"
  for n in selected:
   f=root/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data[n])
  for i in range(20):
   p=subprocess.run(["javac","--release","11","-proc:none","-g:none","-encoding","UTF-8","-Xmaxerrs","3000","-d",str(Path(d)/"classes"),*[str(root/n) for n in sorted(selected)]],capture_output=True,text=True)
   bad={Path(x).relative_to(root).as_posix() for x in re.findall(r"(?m)^(.+?\.java):\d+: error:",p.stderr)}
   rounds.append(dict(sources=len(selected),errors=p.stderr.count("error:"),failed=len(bad)))
   if p.returncode==0:break
   if not bad or not bad.issubset(selected):raise ValueError("Unclassified Java compile failure")
   selected-=bad
  else:raise ValueError("Iteration cap")
  with zipfile.ZipFile(out,"x",zipfile.ZIP_DEFLATED) as z:
   hashes={}
   for n in sorted(selected):
    z.writestr("src/"+n,data[n]);hashes[n]=hashlib.sha256(data[n]).hexdigest()
   z.writestr("PRIVATE_MANIFEST.json",json.dumps(dict(accepted=len(selected),sha256=hashes,rounds=rounds),indent=2))
 return rounds
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--source-zip",type=Path,required=True)
 p.add_argument("--out-zip",type=Path,required=True)
 a=p.parse_args()
 print(json.dumps(build(a.source_zip,a.out_zip),indent=2))
