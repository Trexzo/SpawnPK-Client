"""R201: reproduce a *closed* standalone Java-11 compilation subset.

Candidate private Java ZIP is supplied locally. No library stubs are invented.
Every rejected compilation owner is recorded. This does not establish v309
original binary equivalence or a full-client build.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

def recover_subset(source_zip: Path, output: Path, release: int=11):
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "src"
        classes = Path(temp) / "classes"
        with zipfile.ZipFile(source_zip) as source:
            files = sorted(n for n in source.namelist()
                           if n.startswith("src/") and n.endswith(".java"))
            if len(files) != len(set(files)): raise ValueError("Duplicate source names")
            for name in files:
                rel=name[4:]
                if not rel or "\\" in rel or ".." in Path(rel).parts or rel.startswith("/"):
                    raise ValueError("Unsafe source path")
                body=source.read(name).decode("utf-8-sig")
                imports=re.findall(r"(?m)^\s*import\s+(?:static\s+)?([\w.*]+)\s*;",body)
                if not all(item.startswith(("java.","javax.","com.apple.")) for item in imports):
                    continue
                target=root/rel;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text(body,encoding="utf-8")
        candidates=set(root.rglob("*.java"))
        history=[]
        while candidates:
            command=["javac","--release",str(release),"-proc:none","-g:none",
                     "-encoding","UTF-8","-Xmaxerrs","3000","-d",str(classes)]
            result=subprocess.run(command+sorted(map(str,candidates)),capture_output=True,text=True)
            failures={Path(name) for name in re.findall(
                r"(?m)^(.+?\.java):\d+: error:",result.stderr)}
            history.append({"sources":len(candidates),"error_owners":len(failures),
                            "compiler_errors":result.stderr.count("error:")})
            if result.returncode == 0:
                break
            if not failures or not failures.issubset(candidates):
                raise ValueError("Unclassified compiler failure: "+result.stderr[-500:])
            candidates-=failures
        if not candidates or result.returncode:
            raise ValueError("No closed source subset")
        with zipfile.ZipFile(output,"x",zipfile.ZIP_DEFLATED) as archive:
            files_meta={}
            for path in sorted(candidates):
                rel=path.relative_to(root).as_posix()
                payload=path.read_bytes()
                archive.writestr("src/"+rel,payload)
                files_meta[rel]=hashlib.sha256(payload).hexdigest()
            archive.writestr("PRIVATE_SUBSET_MANIFEST.json",
                json.dumps({"release":release,"count":len(candidates),
                  "files_sha256":files_meta,"rounds":history,
                  "scope":"JDK-only private candidate subset, not original v309 parity"},indent=2))
        return history

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip",required=True,type=Path)
    p.add_argument("--out-zip",required=True,type=Path)
    args=p.parse_args()
    print(json.dumps(recover_subset(args.source_zip,args.out_zip),indent=2))
