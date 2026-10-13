"""R120: privately compile a Java9 source tree and attest an R119 candidate.

R120 proves candidate provenance from actual Java sources; it does NOT prove
original-v309 behavior. That requires independent SHA-pinned R119 replay.
The original JAR is neither required nor supplied as a compiler classpath.
All private source paths, identifiers, classfiles and Java diagnostics remain
strictly local, never published into the public recovery repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from .bytecode_profile import profile_jar_class
from .private_original_fourth_enum_accessors import digest


class PrivateJava9BuildWitnessR120Error(ValueError):
    pass


def need(value, reason):
    if not value:
        raise PrivateJava9BuildWitnessR120Error(reason)


def original_like_source_files(root):
    need(root.is_dir() and not root.is_symlink(),
         "PRIVATE_SOURCE_TREE_DIRECTORY_REQUIRED")
    selected = []
    for path in sorted(root.rglob("*")):
        need(not path.is_symlink(),
             "SOURCE_TREE_SYMLINK_NOT_ALLOWED")
        if path.is_dir():
            continue
        need(path.is_file(), "SOURCE_TREE_SPECIAL_FILE_NOT_ALLOWED")
        if path.suffix != ".java":
            continue
        rel = path.relative_to(root).as_posix()
        need(path.stat().st_size <= 2_000_000,
             "SOURCE_FILE_TOO_LARGE")
        selected.append((rel, path))
    need(1 <= len(selected) <= 512,
         "PRIVATE_JAVA9_SOURCE_FILE_COUNT_OUTSIDE_LIMIT")
    need(sum(p.stat().st_size for _,p in selected) <= 12_000_000,
         "PRIVATE_JAVA9_SOURCE_TREE_TOO_LARGE")
    return selected


def compile_private_java9_owner(source_root, owner_entry, surrogate_simple,
                                new_private_output, *, javac="javac"):
    root = Path(source_root).resolve()
    output = Path(new_private_output)
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "FRESH_PRIVATE_OUTPUT_REQUIRED")
    need(type(owner_entry) is str and owner_entry.endswith(".class")
         and not owner_entry.startswith("/") and "\\" not in owner_entry
         and all(x not in ("", ".", "..") for x in owner_entry.split("/"))
         and type(surrogate_simple) is str
         and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*",
                          surrogate_simple) is not None,
         "UNSAFE_PRIVATE_OWNER_OR_SURROGATE")
    need(output.resolve() != root and root not in output.resolve().parents,
         "PRIVATE_OUTPUT_MUST_BE_OUTSIDE_SOURCE_TREE")
    sources = original_like_source_files(root)
    javac_bin = shutil.which(javac)
    need(javac_bin is not None, "JAVA_COMPILER_NOT_FOUND")
    source_manifest = [
        {"name": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for rel,path in sources
    ]
    manifest_sha = hashlib.sha256(
        json.dumps(source_manifest, sort_keys=True, separators=(",",":")).encode()
    ).hexdigest()

    with tempfile.TemporaryDirectory(prefix="v309-java9-source-r120-",
                                     dir=output.parent) as td:
        stage = Path(td)
        classes = stage / "classes"
        classes.mkdir()
        command = [
            javac_bin, "--release", "9", "-g:none", "-proc:none",
            "-encoding", "UTF-8", "-d", str(classes),
            *[str(path) for _,path in sources],
        ]
        try:
            result = subprocess.run(
                command, cwd=root, capture_output=True, timeout=180,
                check=False,
            )
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise PrivateJava9BuildWitnessR120Error(
                "JAVA9_SOURCE_COMPILE_NOT_COMPLETED") from exc
        need(result.returncode == 0, "JAVA9_SOURCE_COMPILE_FAILED")
        need(all(hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
                 for (_,path),item in zip(sources,source_manifest)),
             "SOURCE_INPUT_CHANGED_DURING_COMPILATION")
        classfiles = sorted(classes.rglob("*.class"))
        need(len(classfiles) > 0, "JAVA9_COMPILE_PRODUCED_NO_CLASSES")
        need(not any(p.is_symlink() for p in classfiles),
             "JAVA9_COMPILE_OUTPUT_SYMLINK_REJECTED")
        candidate = stage / "source-compiled.private.jar"
        with ZipFile(candidate,"w") as z:
            for path in classfiles:
                rel = path.relative_to(classes).as_posix()
                data = path.read_bytes()
                need(len(data) >= 8 and data[:4] == b"\xca\xfe\xba\xbe"
                     and int.from_bytes(data[6:8], "big") == 53,
                     "JAVA9_CLASSFILE_MAJOR_OR_MAGIC_CHANGED")
                info=ZipInfo(rel, date_time=(1980,1,1,0,0,0))
                info.compress_type=ZIP_DEFLATED
                info.external_attr=0o644 << 16
                z.writestr(info,data)
        with ZipFile(candidate) as z:
            entries=z.namelist()
            need(len(entries)==len(set(entries))
                 and entries.count(owner_entry)==1,
                 "EXACT_ONE_SOURCE_COMPILED_OWNER_REQUIRED")
            prefix=owner_entry[:-6]+"$"
            nested=[n for n in entries
                    if n.startswith(prefix) and n.endswith(".class")
                    and "$" not in n[len(prefix):-6]]
            need(len(nested)==4 and
                 prefix+surrogate_simple+".class" in nested,
                 "EXACT_FOUR_SOURCE_ENUM_IDENTITIES_REQUIRED")
        owner=profile_jar_class(candidate,owner_entry)
        need(owner.get("classfile_major")==53
             and len(owner.get("fields",[]))==126
             and len(owner.get("methods",[]))==10,
             "COMPLETE_126_FIELD_TEN_METHOD_JAVA9_OWNER_REQUIRED")
        for entry in nested:
            enumeration=profile_jar_class(candidate,entry)
            need(enumeration.get("classfile_major")==53
                 and (enumeration.get("class_access",0) & 0x4000)!=0,
                 "FOUR_JAVA9_NESTED_ENUMS_REQUIRED")
        sha=digest(candidate)
        report={
            "schema_version":1,
            "kind":"private_v309_java9_source_build_provenance_r120",
            "source_file_count":len(sources),
            "source_tree_sha256_manifest":manifest_sha,
            "generated_classfiles":len(classfiles),
            "original_like_owner_fields":126,
            "original_like_owner_methods":10,
            "source_nested_enum_count":4,
            "compiler_release":9,
            "candidate_sha256":sha,
            "candidate_from_separately_compiled_java_source":True,
            "original_v309_bytecode_parity_verified":False,
            "r119_original_acceptance_performed":False,
            "whole_client_runtime_equivalence_certified":False,
        }
        accepted=stage/"accepted"
        accepted.mkdir()
        final=accepted/"source-compiled.private.jar"
        shutil.copyfile(candidate,final)
        need(digest(final)==sha,
             "FINAL_SOURCE_COMPILED_CANDIDATE_COPY_HASH_MISMATCH")
        (accepted/"source-compiled.aggregate.json").write_text(
            json.dumps(report,sort_keys=True,indent=2)+"\n",
            encoding="utf-8")
        need(not output.exists(), "PRIVATE_BUILD_OUTPUT_OCCUPIED")
        os.rename(accepted,output)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for item in ("source_root","owner_entry","surrogate_simple",
                 "new_private_output"):
        p.add_argument(item)
    p.add_argument("--javac",default="javac")
    args=p.parse_args(argv)
    try:
        print(json.dumps(compile_private_java9_owner(
            args.source_root,args.owner_entry,args.surrogate_simple,
            args.new_private_output,javac=args.javac),sort_keys=True))
    except Exception:
        p.error("PRIVATE_V309_R120_JAVA9_SOURCE_CANDIDATE_NOT_ACCEPTED")


if __name__=="__main__":
    main()
