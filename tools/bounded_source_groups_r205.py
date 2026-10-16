"""R205: bounded package-batch Java 11 source expansion, zero placeholder classes.

Compiles grouped Java candidates against an already clean owner-built baseline.
Accepts only classes recompiled in a final *combined* source-only build.
No candidate may inherit stale classfiles from previous probe attempts.
"""
import argparse, hashlib, json, re, subprocess, tempfile, zipfile
from collections import defaultdict
from pathlib import Path

ERR = re.compile(r"(?m)^(.+?\.java):\d+: error:")
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip",type=Path,required=True)
    p.add_argument("--accepted-manifest",type=Path,required=True,
                   help="JSON source-relative strings, previously compiler-accepted")
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--group-limit",type=int,default=30)
    p.add_argument("--round-limit",type=int,default=6)
    args = p.parse_args()
    if not 0 < args.group_limit <= 300 or not 0 < args.round_limit <= 15:
        raise ValueError("Bounded positive limits required")
    accepted = set(json.loads(args.accepted_manifest.read_text()))
    if not accepted: raise ValueError("No previously accepted sources")
    with zipfile.ZipFile(args.source_zip) as src:
        entries={n[4:]:src.read(n) for n in src.namelist()
                 if n.startswith("src/") and n.endswith(".java")}
        if len(entries)!=len([n for n in src.namelist()
                 if n.startswith("src/") and n.endswith(".java")]):
            raise ValueError("Duplicate source ZIP paths")
    if not accepted <= entries.keys(): raise ValueError("Accepted source absent")
    if any(".." in Path(n).parts or "\\" in n or n.startswith("/") for n in entries):
        raise ValueError("Unsafe ZIP member")
    packages=defaultdict(list)
    for rel in entries:
        if rel not in accepted:
            packages[str(Path(rel).parent)].append(rel)
    package_keys=sorted(packages, key=lambda k:(len(packages[k]),k))
    accepted_initial=len(accepted); reports=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/"src"
        for rel, blob in entries.items():
            path=root/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
        def compile_files(files):
            out=Path(td)/"classes"
            if out.exists():
                import shutil;shutil.rmtree(out)
            cmd=["javac","--release","11","-proc:none","-g:none","-encoding","UTF-8",
                 "-Xmaxerrs","3000","-d",str(out)]+[str(root/n) for n in sorted(files)]
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=150)
            owners=set()
            for item in ERR.findall(result.stderr):
                try:owners.add(Path(item).relative_to(root).as_posix())
                except ValueError:raise ValueError("Compiler produced unexpected path")
            return result.returncode,owners,result.stderr.count("error:")
        for package in package_keys[:args.group_limit]:
            trial=accepted|set(packages[package])
            iterations=[]
            for _ in range(args.round_limit):
                status,errors,num=compile_files(trial)
                iterations.append({"sources":len(trial),"errors":num,
                                   "failed_owners":len(errors)})
                if status==0:
                    accepted=trial;break
                # No source acceptance on an incomplete/ambiguous diagnostic.
                if not errors or not errors<=trial:break
                rejected=errors-accepted
                if not rejected:break
                trial-=rejected
            reports.append({"package":package,"candidate_sources":len(packages[package]),
                            "accepted_additions":len(accepted)-accepted_initial-
                              sum(x["accepted_additions"] for x in reports),
                            "rounds":iterations})
        status,errors,num=compile_files(accepted)
        if status!=0:raise RuntimeError("Final closed compilation failed")
        output={"schema":"spk.r205.bounded-source-groups.v1",
          "source_archive_sha256":hashlib.sha256(args.source_zip.read_bytes()).hexdigest(),
          "baseline_sources":accepted_initial,"accepted_sources":len(accepted),
          "newly_compiling_sources":len(accepted)-accepted_initial,
          "verified_sources":sorted(accepted),"groups":reports,
          "interpretation":"Existing candidate Java only; no original-bytecode parity"}
        with args.output.open("x",encoding="utf-8") as f:
            json.dump(output,f,indent=2);f.write("\n")
if __name__=="__main__":
    main()
