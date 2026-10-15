"""R206 — original v309 spellbook parent FIVE exact recovered JVM method bodies.

Partial original-named source rs/n/c/ap.java implements h(),i(),j(),m(int),
k() with 210 exact JVM instructions. It compiles with REAL recovered enum
sources ap$a and ap$c, and six separately inventoried NONORIGINAL helper
declarations for missing surrounding game types.

Other 9 original parent JVM methods are NOT recovered/accepted. In
particular a(ap$c) is an EMPTY NONORIGINAL placeholder in the partial
candidate. No fake declarations are inserted into full client source.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file,source_members
from .private_v309_matrix_source_method_parity_r150 import _strict_inspections
from .private_v309_spellbook_parent_three_methods_r205 import (
    ORIGINAL_OWNER, ORIGINAL_CLASS_SHA256,ORIGINAL_JVM_METHOD_COUNT,
)
from .private_v309_spellbook_two_enum_source_r204 import (
    PREVIOUS_OWNER,PREVIOUS_SOURCE_SHA256,MODE_OWNER,MODE_SOURCE_SHA256,
)

SOURCE_ZIP_SHA256=(
    "34a149d80c5c8b1b6f4614697a65c9f59618d444bd42f5661a1b9525669c0df7"
)
NONORIGINAL_SUPPORT_ZIP_SHA256=(
    "c75db592f6c9e5d8b734f226055314c7080ae90eb670eed7f871e60c98ace7ef"
)
NONORIGINAL_SUPPORT_OWNERS=(
    "rs/n/c/c","rs/n/e","rs/f/a","rs/n/c/V","rs/l/F","rs/Client"
)
SELECTED_METHODS=(
    ("h","()V"),("i","()V"),("j","()V"),
    ("m","(I)V"),("k","()V"),
)
INSTRUCTION_COUNTS={
    ("h","()V"):10,("i","()V"):62,("j","()V"):19,
    ("m","(I)V"):76,("k","()V"):43,
}
TOTAL_ORIGINAL_INSTRUCTIONS=210


class R206OriginalSpellbookPartialError(ValueError):
    pass


def need(ok,why):
    if not ok:
        raise R206OriginalSpellbookPartialError(why)


def verify_pinned_spellbook_parent_five_methods(
        original_jar, partial_parent_source_zip,
        real_category_source_zip,real_mode_source_zip,
        compiler_helpers_zip, *,
        original_jar_sha256=CANONICAL_V309,
        original_owner=ORIGINAL_OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        original_method_count=ORIGINAL_JVM_METHOD_COUNT,
        parent_source_sha256=SOURCE_ZIP_SHA256,
        category_owner=PREVIOUS_OWNER,
        category_source_sha256=PREVIOUS_SOURCE_SHA256,
        mode_owner=MODE_OWNER,
        mode_source_sha256=MODE_SOURCE_SHA256,
        compiler_helpers_sha256=NONORIGINAL_SUPPORT_ZIP_SHA256,
        helper_owners=NONORIGINAL_SUPPORT_OWNERS,
        selected_method_counts=INSTRUCTION_COUNTS):
    pins=(
        (original_jar,original_jar_sha256),
        (partial_parent_source_zip,parent_source_sha256),
        (real_category_source_zip,category_source_sha256),
        (real_mode_source_zip,mode_source_sha256),
        (compiler_helpers_zip,compiler_helpers_sha256),
    )
    need(all(sha_file(path)==sha for path,sha in pins),
         "R206_ORIGINAL_CLIENT_OR_PRIVATE_JAVA_SOURCE_SHA256_DRIFT")
    named={}
    for owner,(path,digest) in zip(
            (original_owner,category_owner,mode_owner),pins[1:4]):
        members=source_members(path,digest)
        need(len(members)==1 and members[0][0]==owner+".java"
             and 0<len(members[0][1])<=150000,
             "R206_EXPECTED_EXACT_REAL_SOURCE_OWNER_REQUIRED")
        named[owner]=members[0][1]
    fake=source_members(compiler_helpers_zip,compiler_helpers_sha256)
    need(len(fake)==len(helper_owners) and
         {name for name,_ in fake}==
             {owner+".java" for owner in helper_owners} and
         len(set((*named,*helper_owners)))==len(named)+len(helper_owners),
         "R206_ONLY_EXPLICIT_NONORIGINAL_DECLARATIONS_ALLOWED")
    with ZipFile(original_jar) as jar:
        path=original_owner+".class"
        need(jar.namelist().count(path)==1,
             "R206_ORIGINAL_SPELLBOOK_CLASSFILE_MISSING_OR_DUPLICATE")
        original_binary=jar.read(path)
    need(hashlib.sha256(original_binary).hexdigest()==original_class_sha256,
         "R206_ORIGINAL_PARENT_JVM_BINARY_SHA256_CHANGED")
    parsed=parse_class(original_binary)
    need(parsed.name==original_owner and parsed.major==53
         and len(parsed.methods)==original_method_count,
         "R206_ORIGINAL_PARENT_CLASS_ABI_INVENTORY_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R206_JAVA_COMPILER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r206-private-") as temp:
        root=Path(temp)
        paths=[]
        for relative,data in [
                *((owner+".java",body) for owner,body in named.items()),
                *fake]:
            src=root/"src"/relative
            src.parent.mkdir(parents=True,exist_ok=True)
            src.write_bytes(data)
            paths.append(str(src))
        out=root/"classes"
        empty=root/"empty"
        out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            result=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,check=False,timeout=120)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R206OriginalSpellbookPartialError(
                "R206_ISOLATED_JAVA9_SOURCE_BUILD_ABORTED") from exc
        emitted={p.relative_to(out).as_posix()
                 for p in out.rglob("*.class")}
        need(result.returncode==0 and
             emitted=={x+".class" for x in (*named,*helper_owners)},
             "R206_EXACT_THREE_REAL_ENUM_PARENT_AND_SIX_DECLARATIONS_REQUIRED")
        generated=(out/(original_owner+".class")).read_bytes()
    rebuilt=parse_class(generated)
    need((parsed.name,parsed.super_name,parsed.major,parsed.minor,
          parsed.access,parsed.interfaces)==
         (rebuilt.name,rebuilt.super_name,rebuilt.major,
          rebuilt.minor,rebuilt.access,rebuilt.interfaces),
         "R206_ORIGINAL_PARENT_CLASS_HEADER_CHANGED")
    before=profile_class_field_accesses(original_binary)
    after=profile_class_field_accesses(generated)
    actual_selected=set(selected_method_counts)
    need(actual_selected==set(SELECTED_METHODS)
         and sum(selected_method_counts.values())>0,
         "R206_ONLY_SELECTED_FIVE_ORIGINAL_JVM_IDENTITIES_ALLOWED")
    try:
        parity=_strict_inspections(
            before,after,selected=sorted(actual_selected))
    except ValueError as exc:
        raise R206OriginalSpellbookPartialError(
            "R206_ORIGINAL_FIVE_SELECTED_METHOD_JVM_CODE_CHANGED") from exc
    need(parity["verified_selected_method_count"]==len(actual_selected)
         and parity["matched_opcode_count"]==
             sum(selected_method_counts.values())
         and parity["all_selected_core_method_code_equal"],
         "R206_NOT_ALL_SELECTED_ORIGINAL_METHOD_CODE_MATCH")
    need(all(sha_file(path)==digest for path,digest in pins),
         "R206_INPUT_JAVA_SOURCE_OR_BINARY_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_original_spellbook_parent_five_partial_java_methods_r206",
        "original_parent_owner":original_owner,
        "original_method_count":original_method_count,
        "fully_matched_original_selected_method_bodies":
            len(selected_method_counts),
        "original_jvm_instructions_exactly_verified":
            parity["matched_opcode_count"],
        "original_method_abi_offsets_and_symbols_preserved":True,
        "original_parent_other_methods_unverified":
            original_method_count-len(selected_method_counts),
        "original_parent_full_field_inventory_verified":False,
        "placeholder_original_methods_accepted":False,
        "compiler_only_helper_sources_original":False,
        "original_client_jar_on_compiler_classpath":False,
        "original_game_code_executed":False,
        "experimental_full_client_source_tree_modified":False,
        "whole_original_client_compiles":False,
        "source_redistribution_authorized":False,
    }
