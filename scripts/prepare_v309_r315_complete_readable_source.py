"""R352: stage the complete private R315 v309 source, optionally readability-renamed.

This intentionally does NOT publish private Java, dependency JARs, cache or
original client binaries to GitHub/CI. Actual R315 source is SHA-pinned; the
optional inferred class rename is NOT accepted original-v309 bytecode identity.
"""
from __future__ import annotations
import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import stat
import sys
from zipfile import ZipFile, BadZipFile

if __package__:
    from .apply_v309_r351_readable_packet_handler_candidate import transform
else:
    from apply_v309_r351_readable_packet_handler_candidate import transform

R315_ARCHIVE_SHA = "e46a213ba949dc0a2f420a040b5c9d38451c0923e3ea39917a5d2eb3c9b2fa28"
R315_JAVA_COUNT = 1277
R315_REBUILT_JAR_SHA = "b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721"
DEPENDENCIES = ("dependencies/R218.jar","dependencies/R239_filtered.jar")

class R315IntakeRefused(ValueError):
    pass

def digest(data):
    return hashlib.sha256(data).hexdigest()

def checked_archive(archive,*,expected_archive_sha=R315_ARCHIVE_SHA,
                    expected_java_count=R315_JAVA_COUNT,
                    check_dependency_jars=True):
    archive=Path(archive)
    if archive.is_symlink() or not archive.is_file():
        raise R315IntakeRefused("R315_ARCHIVE_NOT_REGULAR")
    h=hashlib.sha256()
    with archive.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    if h.hexdigest()!=expected_archive_sha:
        raise R315IntakeRefused("R315_ARCHIVE_SHA_MISMATCH")
    with ZipFile(archive) as z:
        infos=z.infolist()
        if len(infos)>1800:
            raise R315IntakeRefused("R315_MEMBER_COUNT_BUDGET")
        names=[x.filename for x in infos]
        if len(names)!=len(set(names)) or len(names)!=len(set(s.casefold() for s in names)):
            raise R315IntakeRefused("R315_DUPLICATE_OR_WINDOWS_COLLISION")
        for info in infos:
            name=info.filename
            parts=name.split("/")
            if (not name or name.startswith("/") or "\\" in name or
                any(part in ("", ".", "..") for part in parts) or
                info.is_dir() or stat.S_IFMT(info.external_attr>>16)==stat.S_IFLNK):
                raise R315IntakeRefused("R315_UNSAFE_ARCHIVE_ENTRY")
            if info.file_size>13_000_000 or info.flag_bits & 1:
                raise R315IntakeRefused("R315_ARCHIVE_MEMBER_UNSAFE")
        r315=json.loads(z.read("R315_MANIFEST.json"))
        build=json.loads(z.read("MANIFEST.json"))
        files=r315.get("source_file_sha256")
        if (r315.get("source_count")!=expected_java_count or
            not isinstance(files,dict) or len(files)!=expected_java_count or
            len(build.get("source_sha256",{}))!=expected_java_count):
            raise R315IntakeRefused("R315_SOURCE_MANIFEST_COUNT_MISMATCH")
        candidates={name for name in names if name.startswith("source/") and name.endswith(".java")}
        if candidates!=set(files):
            raise R315IntakeRefused("R315_SOURCE_FILE_SET_MISMATCH")
        output={}
        total=0
        for path in sorted(candidates):
            info=z.getinfo(path)
            if info.file_size>4_000_000:
                raise R315IntakeRefused("R315_SOURCE_MEMBER_BUDGET")
            data=z.read(path)
            total+=len(data)
            if total>24_000_000:
                raise R315IntakeRefused("R315_SOURCE_TREE_BUDGET")
            name=path[7:]
            if (digest(data)!=files[path] or
                digest(data)!=build["source_sha256"].get(name)):
                raise R315IntakeRefused("R315_SOURCE_SHA_MISMATCH")
            data.decode("utf-8")
            output[name]=data
        if (expected_java_count==R315_JAVA_COUNT and
            build.get("jar_sha256")!=R315_REBUILT_JAR_SHA):
            raise R315IntakeRefused("R315_REBUILD_PIN_MISMATCH")
        if check_dependency_jars:
            hashes=build.get("dependency_sha256",{})
            for name in DEPENDENCIES:
                if name not in names:
                    raise R315IntakeRefused("R315_MISSING_DEPENDENCY")
                data=z.read(name)
                if digest(data)!=hashes.get(name.split("/")[-1]):
                    raise R315IntakeRefused("R315_DEPENDENCY_SHA_MISMATCH")
                with ZipFile(BytesIO(data)) as dep:
                    if any(item.filename.startswith("rs/") and
                           item.filename.endswith(".class") for item in dep.infolist()):
                        raise R315IntakeRefused("PROJECT_BINARY_FALLBACK_IN_DEPENDENCY")
        return output

def stage(archive,output,mode="readable",**kwargs):
    output=Path(output)
    if output.exists() or output.is_symlink():
        raise R315IntakeRefused("R315_OUTPUT_MUST_BE_NEW")
    sources=checked_archive(archive,**kwargs)
    if mode=="readable":
        sources,rename=transform(sources,expected_files=len(sources),
            expected_touches=71,expected_occurrences=144)
    elif mode=="baseline":
        rename=None
    else:
        raise R315IntakeRefused("R315_UNKNOWN_MODE")
    report={
        "status":"R315_COMPLETE_PRIVATE_SOURCE_CANDIDATE_STAGED",
        "base_archive_sha256":R315_ARCHIVE_SHA,
        "source_count":len(sources),
        "mode":mode,
        "semantic_rename_candidate":rename,
        "original_r315_rebuild_sha256":R315_REBUILT_JAR_SHA,
        "this_staging_run_performed_java_compile":False,
        "recovered_original_v309_bytecode_semantic_parity":"NOT_CERTIFIED",
        "source_milestone_publishable":False,
        "source_file_sha256":{n:digest(b) for n,b in sorted(sources.items())}
    }
    output.mkdir(parents=True,exist_ok=False)
    for name,data in sorted(sources.items()):
        dest=output/"source"/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(data)
    (output/"PRIVATE_R315_SOURCE_CANDIDATE.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--r315-archive",type=Path,required=True)
    p.add_argument("--new-private-output",type=Path,required=True)
    p.add_argument("--mode",choices=("baseline","readable"),default="readable")
    a=p.parse_args(argv)
    try:
        result=stage(a.r315_archive,a.new_private_output,mode=a.mode)
    except (R315IntakeRefused,OSError,ValueError,BadZipFile,KeyError) as exc:
        print(json.dumps({"status":"R315_SOURCE_STAGE_BLOCKED","reason":str(exc)}))
        return 2
    print(json.dumps({k:v for k,v in result.items() if k!="source_file_sha256"},
                     indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
