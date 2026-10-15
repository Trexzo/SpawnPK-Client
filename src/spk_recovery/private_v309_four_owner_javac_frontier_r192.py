"""R192 — actual private v309 whole-source Javac frontier, four real Java owners.

Read-only, SHA-pinned experimental four-source overlay of the original
1,278-file private recovered v309 Java tree. Compiles BOTH original baseline
and overlay under IDENTICAL JDK-only Java9 conditions and reports a measured
compiler-error delta. Never accepts compiler-only fake helper classes,
original JAR fallback, or an unverified source ZIP as a real client build.

Hosted CI uses invented Java ZIPs only; original-derived source stays private.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile,ZIP_DEFLATED

from .private_client_source_ast_census_r126 import sha_file,source_members


BASELINE_SHA256=(
    "dd68b18a4e60e7d9b2431811a1531f4e33bfa75ac1adb9a4f07100a64e99d6da"
)
BASELINE_FILES=1278
CANONICAL_PREFIX="recovered-source/v309/src/"
ADDED_SOURCES=(
    ("rs/q/a.java",
     "09ad2bbf2a8fd83c26fb3a2c9c22de0a08ae77ab54ba5ad4c88f4d055f91d431"),
    ("rs/v/a.java",
     "a7172b3aae3a794bbd5a59f6de085a7ee7b68749a117671d5cf6b47a0fcd5288"),
    ("rs/v/a$a.java",
     "367c02a4e7fcc9ba9d7eb5bb99504751c6c17cd7d3eaf5717c7f2b32942dc766"),
    ("rs/k/j.java",
     "07d1e38deebe95ede0297d08ca2922bea33c4518af22af6ffe1d1ed1ba9ecfa2"),
)
KNOWN_UNRESTORED_DEPENDENCY_OWNERS=(
    "rs/f/a","rs/w/c","rs/secure/a","rs/secure/b","rs/secure/c",
)


class R192PrivateSourceFrontierError(ValueError):
    pass


def need(ok,message):
    if not ok:
        raise R192PrivateSourceFrontierError(message)


def source_bytes_from_pinned_baseline(
        baseline_zip, *, baseline_sha256=BASELINE_SHA256,
        expected_file_count=BASELINE_FILES, prefix=CANONICAL_PREFIX):
    need(sha_file(baseline_zip)==baseline_sha256,
         "R192_PRIVATE_BASELINE_SHA256_CHANGED")
    need(prefix.endswith("/") and ".." not in prefix,
         "R192_CANONICAL_SOURCE_PATH_INVALID")
    with ZipFile(baseline_zip) as archive:
        infos=archive.infolist()
        names=[x.filename for x in infos]
        need(len(infos)==expected_file_count and
             len(infos)==len(set(names)) and
             len(names)==len({x.casefold() for x in names}),
             "R192_ORIGINAL_BASELINE_COUNT_OR_DUPLICATE_DRIFT")
        output={}
        total=0
        for info in infos:
            path=info.filename
            need(path.startswith(prefix) and path.endswith(".java")
                 and "\\" not in path
                 and not path.startswith("/")
                 and all(part not in ("",".","..") for part in path.split("/"))
                 and not info.is_dir() and
                 ((info.external_attr>>16)&0o170000)!=0o120000,
                 "R192_NONCANONICAL_OR_UNSAFE_JAVA_SOURCE_ARCHIVE")
            need(info.file_size<=2_000_000,
                 "R192_OVERSIZED_JAVA_SOURCE_ENTRY")
            total+=info.file_size
            need(total<=45_000_000,
                 "R192_JAVA_SOURCE_ARCHIVE_EXCEEDS_BOUND")
            output[path]=archive.read(path)
    need(sha_file(baseline_zip)==baseline_sha256,
         "R192_BASELINE_SOURCE_CHANGED_DURING_READ")
    return output


def build_private_four_owner_overlay(
        baseline_zip, four_source_zips, output_zip, *,
        baseline_sha256=BASELINE_SHA256,
        source_identities=ADDED_SOURCES,
        expected_baseline_java=BASELINE_FILES,
        prefix=CANONICAL_PREFIX):
    """Preserves EVERY baseline Java source byte; never mutates input ZIPs."""
    need(len(four_source_zips)==len(source_identities) and
         len(set(rel for rel,_ in source_identities))==
             len(source_identities) and
         all(rel.endswith(".java") and
             all(x not in ("",".","..") for x in rel.split("/"))
             and "\\" not in rel for rel,_ in source_identities),
         "R192_EXACT_DECLARED_NEW_SOURCE_OWNERS_REQUIRED")
    target=Path(output_zip)
    need(target.parent.is_dir() and
         not target.exists() and not target.is_symlink() and
         not target.parent.is_symlink(),
         "R192_FRESH_PRIVATE_OUTPUT_ARCHIVE_REQUIRED")
    baseline=source_bytes_from_pinned_baseline(
        baseline_zip,baseline_sha256=baseline_sha256,
        expected_file_count=expected_baseline_java,prefix=prefix)
    additions={}
    for (owner,pin),private_zip in zip(source_identities,four_source_zips):
        need(sha_file(private_zip)==pin,
             "R192_EXACT_PRIVATE_NEW_SOURCE_ZIP_SHA_REQUIRED")
        sources=source_members(private_zip,pin)
        need(len(sources)==1 and sources[0][0]==owner,
             "R192_PRIVATE_SOURCE_OWNER_NAME_NOT_PINNED")
        name=prefix+owner
        need(name not in baseline and name not in additions,
             "R192_WOULD_OVERWRITE_RECOVERED_SOURCE")
        additions[name]=sources[0][1]
    merged={**baseline,**additions}
    need(len(merged)==len(baseline)+len(source_identities),
         "R192_PRIVATE_SOURCE_TREE_COUNT_INCONSISTENT")
    with ZipFile(target,"w",ZIP_DEFLATED,compresslevel=9) as archive:
        for name in sorted(merged):
            archive.writestr(name,merged[name])
    with ZipFile(target) as audit:
        need(len(audit.namelist())==len(merged) and
             all(audit.read(name)==data for name,data in baseline.items())
             and all(audit.read(name)==data for name,data in additions.items()),
             "R192_PREVIOUS_JAVA_FILES_NOT_BYTE_IDENTICAL")
    return {
        "schema_version":1,
        "original_baseline_zip_sha256":baseline_sha256,
        "new_overlay_zip_sha256":sha_file(target),
        "baseline_java_files_exactly_preserved":len(baseline),
        "added_independently_evidenced_java_files":len(additions),
        "candidate_java_source_file_count":len(merged),
        "invented_compiler_helpers_added":False,
        "original_client_jar_used_as_compiler_dependency":False,
        "original_full_client_compilation_passed":False,
    }


def _compile_private_zip(source_zip,root,label,*,javac):
    """No original game runtime, only Java9 compiler diagnostics."""
    src=root/(label+"-source")
    out=root/(label+"-classes")
    empty=root/"empty-classpath"
    src.mkdir();out.mkdir();empty.mkdir(exist_ok=True)
    sources=source_bytes_from_pinned_baseline(
        source_zip,baseline_sha256=sha_file(source_zip),
        expected_file_count=len(ZipFile(source_zip).namelist()))
    paths=[]
    for owner,content in sorted(sources.items()):
        name=owner[len(CANONICAL_PREFIX):]
        target=src/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(content)
        paths.append(str(target))
    argfile=root/(label+"-java-sources.args")
    argfile.write_text("\n".join(paths)+"\n",encoding="utf-8")
    env=os.environ.copy()
    for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
        env.pop(key,None)
    command=[
        javac,"-J-Xmx4g","--release","9","-g:none",
        "-proc:none","-implicit:none","-Xmaxerrs","10000",
        "-classpath",str(empty),"-sourcepath",str(empty),
        "-d",str(out),"@"+str(argfile),
    ]
    try:
        result=subprocess.run(
            command,cwd=root,env=env,stdin=subprocess.DEVNULL,
            capture_output=True,timeout=150,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise R192PrivateSourceFrontierError(
            "R192_SOURCE_ONLY_JAVA9_COMPILATION_ABORTED") from exc
    diagnostic=result.stderr.decode("utf-8",errors="replace")
    details=re.findall(r"(?m)^.*\.java:\d+: error: ([^\r\n]+)",diagnostic)
    summary=re.findall(r"(?m)^(\d+) errors?$",diagnostic)
    if result.returncode==0:
        need(len(details)==0,"R192_SUCCESS_WITH_ERROR_DIAGNOSTICS")
        count=0
    else:
        need(len(summary)==1 and
             int(summary[0])==len(details) and
             len(details)<10_000,
             "R192_COMPILER_DIAGNOSTICS_INCOMPLETE_OR_TRUNCATED")
        count=len(details)
    return {
        "java_file_count":len(paths),
        "javac_exit_code":result.returncode,
        "total_compiler_errors":count,
        "diagnostic_category_counts":dict(sorted(Counter(details).items())),
        "javac_stderr_sha256":hashlib.sha256(result.stderr).hexdigest(),
        "original_client_binary_on_compiler_classpath":False,
        "source_only_jdk9":True,
    }


def compare_pinned_private_four_owner_javac(
        original_baseline_zip, candidate_overlay_zip, *,
        original_sha256=BASELINE_SHA256,
        candidate_sha256,expected_original_count=BASELINE_FILES,
        expected_added_count=4):
    need(sha_file(original_baseline_zip)==original_sha256 and
         sha_file(candidate_overlay_zip)==candidate_sha256,
         "R192_JAVAC_COMPARISON_EXACT_SOURCE_INPUT_PINS_REQUIRED")
    original=source_bytes_from_pinned_baseline(
        original_baseline_zip,
        baseline_sha256=original_sha256,
        expected_file_count=expected_original_count)
    new=source_bytes_from_pinned_baseline(
        candidate_overlay_zip,
        baseline_sha256=candidate_sha256,
        expected_file_count=expected_original_count+expected_added_count)
    need(all(new.get(path)==body for path,body in original.items())
         and len(new)==len(original)+expected_added_count,
         "R192_CANDIDATE_DID_NOT_PRESERVE_BASELINE_BYTES")
    javac=shutil.which("javac")
    need(javac is not None,"R192_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r192-javac-") as temp:
        root=Path(temp)
        first=_compile_private_zip(original_baseline_zip,root,"baseline",
                                   javac=javac)
        second=_compile_private_zip(candidate_overlay_zip,root,"candidate",
                                    javac=javac)
    need(sha_file(original_baseline_zip)==original_sha256 and
         sha_file(candidate_overlay_zip)==candidate_sha256,
         "R192_ORIGINAL_SOURCE_TREE_CHANGED_DURING_COMPILE")
    return {
        "schema_version":1,
        "kind":"v309_private_four_original_java_owner_javac_frontier_r192",
        "baseline":first,
        "candidate":second,
        "compilation_error_delta":
            second["total_compiler_errors"]-
            first["total_compiler_errors"],
        "previous_source_files_byte_identical":True,
        "remaining_known_fake_dependency_owners_not_included":
            list(KNOWN_UNRESTORED_DEPENDENCY_OWNERS),
        "original_game_executed":False,
        "original_jar_on_compiler_classpath":False,
        "full_original_v309_client_compiles":
            second["javac_exit_code"]==0,
        "redistribution_authorized":False,
    }
