#!/usr/bin/env python3
"""R383 isolated full v309 Java build. PRIVATE source is never uploaded or launched.

Input is the SHA-pinned private R381 build kit or the user's R382 delivery ZIP.
All outputs are local to the supplied directory. No connection to the game is made.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

R382_ZIP_SHA = "9f21f71d070ab67ea50baed259bb13a8ae477eb2cee75236809128240a1169b3"
R381_PACKAGE_SHA = "67cf1940f1332d445d9e485424b85ceff3cafd76dbbafddcca16b4f1019c52db"
R381_BUILD_KIT_SHA = "902e3b583840073c095ea51c5fe5bee4034340ab92bd19dc7c36f3173f092f96"
EXPECTED_JAR_SHA = "ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3"
SOURCE_COUNT = 1277
CLASS_COUNT = 1388
MAX_ARCHIVE_SIZE = 30_000_000

class Refused(ValueError): pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def hash_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def safe_member(info: zipfile.ZipInfo) -> bool:
    n=info.filename
    parts=n.split("/")
    return (n and not n.startswith(("/","\\")) and "\\" not in n
        and ":" not in n and all(x not in ("", ".", "..") for x in parts)
        and not info.is_dir() and not (info.flag_bits & 1)
        and stat.S_IFMT(info.external_attr >> 16)!=stat.S_IFLNK
        and info.file_size<=16_000_000)

def load_private_kit(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink() or path.stat().st_size>MAX_ARCHIVE_SIZE:
        raise Refused("PRIVATE_INPUT_MISSING_OR_UNSAFE")
    digest=hash_file(path)
    if digest==R381_BUILD_KIT_SHA:
        return path.read_bytes()
    if digest!=R382_ZIP_SHA:
        raise Refused("UNRECOGNIZED_PRIVATE_INPUT_SHA256")
    with zipfile.ZipFile(path) as outer:
        if len(outer.infolist()) != 10:
            raise Refused("R382_PACKAGE_MEMBERS_CHANGED")
        nested=outer.read("R381-Complete-Private-Source-And-Build.zip")
    if sha(nested)!=R381_PACKAGE_SHA: raise Refused("R381_NESTED_PACKAGE_SHA256_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(nested)) as package:
        kit=package.read("R381-Reproducible-Build-Kit.zip")
    if sha(kit)!=R381_BUILD_KIT_SHA: raise Refused("R381_KIT_SHA256_MISMATCH")
    return kit

def extract_checked_kit(kit_bytes: bytes, destination: Path) -> dict:
    if sha(kit_bytes)!=R381_BUILD_KIT_SHA:raise Refused("BUILD_KIT_SHA256_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(kit_bytes)) as z:
        infos=z.infolist()
        names=[x.filename for x in infos]
        if len(names)!=len(set(names)) or len(names)!=len(set(n.casefold() for n in names)):
            raise Refused("DUPLICATE_OR_CASE_COLLISION")
        if any(not safe_member(x) for x in infos):raise Refused("UNSAFE_PRIVATE_ARCHIVE_MEMBER")
        if sum(x.file_size for x in infos)>60_000_000:raise Refused("ZIP_EXPANSION_BUDGET_EXCEEDED")
        if "MANIFEST.json" not in names:raise Refused("PRIVATE_MANIFEST_MISSING")
        m=json.loads(z.read("MANIFEST.json"))
        if (m.get("source_count")!=SOURCE_COUNT or
             m.get("build_compiled_class_expected")!=CLASS_COUNT or
             m.get("jar_sha256")!=EXPECTED_JAR_SHA or
             m.get("private_source_release_approved") is not False):
            raise Refused("PRIVATE_MANIFEST_AUTHORITY_CHANGED")
        pins=m.get("source_sha256")
        if not isinstance(pins,dict) or len(pins)!=SOURCE_COUNT:
            raise Refused("SOURCE_MANIFEST_SET_CHANGED")
        paths=set("source/"+x for x in pins)
        if {n for n in names if n.startswith("source/")}!=paths:
            raise Refused("SOURCE_PATH_SET_CHANGED")
        dest_paths=set()
        for info in infos:
            path=destination.joinpath(*info.filename.split("/"))
            if str(path).casefold() in dest_paths:raise Refused("COLLIDING_DESTINATION")
            dest_paths.add(str(path).casefold())
            path.parent.mkdir(parents=True,exist_ok=True)
            contents=z.read(info)
            if (info.filename.startswith("source/") and
                sha(contents)!=pins.get(info.filename[7:])):
                raise Refused("SOURCE_SHA256_DRIFT")
            if info.filename.startswith("dependencies/"):
                basename=info.filename[len("dependencies/"):]
                if sha(contents)!=m.get("dependency_sha256",{}).get(basename):
                    raise Refused("DEPENDENCY_SHA256_DRIFT")
            path.write_bytes(contents)
    return m

def javac_arg_path(p: Path)->str:
    # Normalize Windows separators and quote paths containing spaces for javac @argfiles.
    s=str(p.resolve()).replace("\\","/")
    if '\"' in s or '\n' in s or '\r' in s:raise Refused("UNSAFE_SOURCE_PATH")
    return '"'+s+'"'

def build(kit_dir: Path, result_dir: Path, compiler: Path, expected_manifest: dict, work: Path):
    sources=sorted((kit_dir/"source").rglob("*.java"))
    if len(sources)!=SOURCE_COUNT:raise Refused("SOURCE_COUNT_CHANGED")
    version=subprocess.run([str(compiler),"-version"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                           encoding="utf-8",errors="replace",timeout=15,check=True).stdout.strip()
    if not re.search(r"\bjavac\s+21(?:\.|\b)",version):raise Refused("JDK_21_REQUIRED: "+version)
    classes=work/"classes";classes.mkdir()
    args=work/"sources.arg"
    args.write_text("\n".join(javac_arg_path(x) for x in sources)+"\n",encoding="utf-8",newline="\n")
    cp=os.pathsep.join(str(kit_dir/"dependencies"/n) for n in ("R239_filtered.jar","R218.jar"))
    cmd=[str(compiler),"-J-Xmx2200m","--release","11","-proc:none","-g:none",
         "-encoding","UTF-8","-sourcepath",str(work/"no-extra-sourcepath"),
         "-cp",cp,"-d",str(classes),"@"+str(args)]
    log=result_dir/"javac-r383.log"
    with log.open("w",encoding="utf-8",errors="replace") as f:
        p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=240,check=False)
    if p.returncode:raise Refused("JAVAC_FAILED_RETURN_CODE_"+str(p.returncode))
    classfiles=sorted(classes.rglob("*.class"))
    if len(classfiles)!=CLASS_COUNT:raise Refused("GENERATED_CLASS_COUNT_DRIFT: "+str(len(classfiles)))
    jar=result_dir/"R383-Source-Built-From-Private-Kit.jar"
    if jar.exists():raise Refused("REFUSE_EXISTING_JAR_OUTPUT")
    with zipfile.ZipFile(jar,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for file in classfiles:
            info=zipfile.ZipInfo(file.relative_to(classes).as_posix(),(2026,10,18,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            z.writestr(info,file.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    observed=hash_file(jar)
    if observed!=EXPECTED_JAR_SHA:
        raise Refused("JAR_SHA256_DIFFERENCE: "+observed)
    return version,observed,len(classfiles)

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-bundle",type=Path,required=True,help="SHA-pinned R382 complete package or private R381 build kit")
    p.add_argument("--javac",type=Path,required=True,help="Path to trusted local JDK 21 javac (not default Java 8)")
    p.add_argument("--out-dir",type=Path,required=True,help="New output directory for compiled JAR/JSON/log")
    p.add_argument("--keep-extracted",action="store_true")
    args=p.parse_args(argv)
    out=args.out_dir.resolve()
    if out.exists():print("R383_REFUSED: output directory already exists",file=sys.stderr);return 2
    out.mkdir(parents=True)
    observed_os="windows" if os.name=="nt" else "non-windows"
    report={"status":"R383_NOT_VERIFIED","platform":observed_os,"sources_expected":SOURCE_COUNT,
            "classes_expected":CLASS_COUNT,"jar_sha256_expected":EXPECTED_JAR_SHA,
            "private_source_release_approved":False,"original_game_runtime_tested":False,
            "windows_full_compile_tested":False,"power_loss_durability_tested":False}
    try:
        kit=load_private_kit(args.private_bundle)
        report["private_kit_sha256"]=sha(kit)
        with tempfile.TemporaryDirectory(prefix="r383isolated-") as d:
            temp=Path(d);kitroot=temp/"kit";kitroot.mkdir()
            manifest=extract_checked_kit(kit,kitroot)
            report["source_sha256_verified"]=len(manifest["source_sha256"])
            report["dependency_sha256_verified"]=sorted(manifest["dependency_sha256"])
            version,digest,count=build(kitroot,out,args.javac,manifest,temp)
            report.update(javac=version,generated_classfiles=count,jar_sha256=digest,
                windows_full_compile_tested=(os.name=="nt"),
                status="R383_WINDOWS_PRIVATE_FULL_BUILD_PASS" if os.name=="nt" else "R383_LINUX_REFERENCE_REBUILD_PASS")
            if args.keep_extracted:
                # Only with explicit opt-in. Never publish this directory or add it to GitHub.
                target=out/"PRIVATE_EXTRACTED_BUILD_KIT_DO_NOT_PUBLISH"
                shutil.copytree(kitroot,target)
    except (OSError,Refused,subprocess.SubprocessError,zipfile.BadZipFile,ValueError,KeyError) as e:
        report.update(status="R383_REFUSED_OR_FAILED",reason=str(e))
    (out/"R383-Verification-Report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0 if report["status"].endswith("_PASS") else 2

if __name__=="__main__":raise SystemExit(main())
