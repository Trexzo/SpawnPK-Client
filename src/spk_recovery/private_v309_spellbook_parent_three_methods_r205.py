"""R205: recover 3 exact original v309 spellbook parent JVM method bodies.

Partial ORIGINAL-NAMED Java source rs/n/c/ap.java contains ONLY verified static
h()/i()/j() implementations, plus a clearly UNVERIFIED a(ap$c) placeholder.
Three other compiled source owners are NONORIGINAL method/field declarations
for original superclass, widget and configuration. The authentic ap$c Java
source is included and all original binary inputs are SHA-pinned.

The verifier compares all 91 original selected JVM instructions including
byte offsets, resolved field/method symbols, exception regions, and stack/
local maxima. Other 11 original methods, true full field/parent ABI, runtime
and whole-client compilation are NOT accepted. No game code is executed.
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
from .private_v309_spellbook_two_enum_source_r204 import (
    MODE_OWNER,MODE_SOURCE_SHA256,
)

ORIGINAL_OWNER="rs/n/c/ap"
ORIGINAL_CLASS_SHA256=(
    "b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4"
)
PARTIAL_JAVA_SHA256=(
    "74fef7ede24f9f704895c9a55d3ab44b0737b5e1267b010a55c4121bf3f07eea"
)
NONORIGINAL_HELPERS_SHA256=(
    "da2a513d6acae160ba440190651da6717a090ca62a981731ba45bb4e7971961d"
)
NONORIGINAL_HELPER_OWNERS=("rs/n/c/c","rs/n/e","rs/f/a")
ORIGINAL_JVM_METHOD_COUNT=14
SELECTED_METHODS=(("h","()V"),("i","()V"),("j","()V"))
SELECTED_JVM_INSTRUCTIONS=91


class R205OriginalSpellbookPartialError(ValueError):
    pass


def need(ok,why):
    if not ok:
        raise R205OriginalSpellbookPartialError(why)


def verify_pinned_original_spellbook_parent_methods(
        original_jar,partial_original_java_zip,real_mode_enum_zip,
        compiler_declarations_zip, *,
        original_sha256=CANONICAL_V309,
        original_owner=ORIGINAL_OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        partial_source_sha256=PARTIAL_JAVA_SHA256,
        mode_owner=MODE_OWNER,
        mode_source_sha256=MODE_SOURCE_SHA256,
        compiler_helpers_sha256=NONORIGINAL_HELPERS_SHA256,
        helper_owners=NONORIGINAL_HELPER_OWNERS,
        original_method_count=ORIGINAL_JVM_METHOD_COUNT,
        selected_methods=SELECTED_METHODS,
        expected_instructions=SELECTED_JVM_INSTRUCTIONS):
    pins=(
        (original_jar,original_sha256),
        (partial_original_java_zip,partial_source_sha256),
        (real_mode_enum_zip,mode_source_sha256),
        (compiler_declarations_zip,compiler_helpers_sha256),
    )
    need(all(sha_file(path)==digest for path,digest in pins),
         "R205_ORIGINAL_CLIENT_OR_PRIVATE_JAVA_SHA256_MISMATCH")
    partial=source_members(partial_original_java_zip,partial_source_sha256)
    mode=source_members(real_mode_enum_zip,mode_source_sha256)
    helpers=source_members(compiler_declarations_zip,compiler_helpers_sha256)
    need(len(partial)==len(mode)==1 and
         partial[0][0]==original_owner+".java" and
         mode[0][0]==mode_owner+".java" and
         len(helpers)==len(helper_owners) and
         {name for name,_ in helpers}==
             {owner+".java" for owner in helper_owners} and
         len(set((original_owner,mode_owner,*helper_owners)))==
             len(helper_owners)+2,
         "R205_ONE_PARTIAL_PARENT_REAL_ENUM_AND_EXACT_HELPERS")
    need(all(0<len(data)<150000
             for _,data in [*partial,*mode,*helpers]),
         "R205_UNEXPECTED_JAVA_SOURCE_SIZE")
    with ZipFile(original_jar) as archive:
        path=original_owner+".class"
        need(archive.namelist().count(path)==1,
             "R205_ORIGINAL_OWNER_CLASSFILE_MISSING_OR_DUPLICATE")
        original_bytes=archive.read(path)
    need(hashlib.sha256(original_bytes).hexdigest()==original_class_sha256,
         "R205_ORIGINAL_PARENT_CLASSFILE_SHA256_CHANGED")
    original=parse_class(original_bytes)
    need(original.name==original_owner and original.major==53 and
         len(original.methods)==original_method_count,
         "R205_ORIGINAL_CLASS_VERSION_OR_METHOD_INVENTORY_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R205_JDK_COMPILER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r205-partial-") as temp:
        root=Path(temp)
        files=[]
        for relative,body in [*partial,*mode,*helpers]:
            src=root/"src"/relative
            src.parent.mkdir(parents=True,exist_ok=True)
            src.write_bytes(body)
            files.append(str(src))
        out=root/"classes"
        empty=root/"empty"
        out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            compiled=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),*files],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=120,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R205OriginalSpellbookPartialError(
                "R205_JAVA9_SOURCE_ONLY_COMPILATION_ABORTED") from exc
        emitted={p.relative_to(out).as_posix()
                 for p in out.rglob("*.class")}
        need(compiled.returncode==0 and
             emitted=={owner+".class" for owner in
                      (original_owner,mode_owner,*helper_owners)},
             "R205_EXACT_FIVE_EMITTED_SOURCE_CLASSES_REQUIRED")
        rebuilt_bytes=(out/(original_owner+".class")).read_bytes()
    rebuilt=parse_class(rebuilt_bytes)
    need((original.name,original.access,original.major,
          original.minor,original.interfaces)==
         (rebuilt.name,rebuilt.access,rebuilt.major,
          rebuilt.minor,rebuilt.interfaces),
         "R205_ORIGINAL_PARENT_NON_SUPER_CLASS_HEADER_CHANGED")
    superclass_is_exact=original.super_name==rebuilt.super_name
    if not superclass_is_exact:
        need(original_owner=="rs/n/c/ap" and
             original.super_name=="rs/n/c" and
             rebuilt.super_name=="rs/n/c/c",
             "R205_UNAUTHORIZED_ORIGINAL_SUPERCLASS_BINARY_NAME_CHANGE")
    before=profile_class_field_accesses(original_bytes)
    after=profile_class_field_accesses(rebuilt_bytes)
    all_old={(m["name"],m["descriptor"]) for m in before["methods"]}
    all_new={(m["name"],m["descriptor"]) for m in after["methods"]}
    need(set(selected_methods).issubset(all_old&all_new),
         "R205_ONE_OF_THREE_ORIGINAL_METHODS_MISSING")
    try:
        parity=_strict_inspections(
            before,after,selected=sorted(selected_methods))
    except ValueError as exc:
        raise R205OriginalSpellbookPartialError(
            "R205_SELECTED_ORIGINAL_SPELLBOOK_METHOD_CODE_MISMATCH") from exc
    need(parity["verified_selected_method_count"]==len(selected_methods) and
         parity["matched_opcode_count"]==expected_instructions and
         parity["all_selected_core_method_code_equal"],
         "R205_ORIGINAL_SELECTED_JVM_CODE_NOT_EXACT")
    need(all(sha_file(path)==digest for path,digest in pins),
         "R205_SOURCE_ORIGINAL_BINARY_CHANGED_DURING_AUDIT")
    return {
        "schema_version":1,
        "kind":"v309_original_spellbook_parent_three_partial_java_methods_r205",
        "original_parent":original_owner,
        "original_method_count":original_method_count,
        "verified_selected_methods":[
            {"name":name,"descriptor":descriptor}
            for name,descriptor in selected_methods],
        "original_selected_method_count_verified":len(selected_methods),
        "original_selected_instructions_verified":expected_instructions,
        "original_method_code_offsets_and_symbolic_refs_match":True,
        "original_superclass_binary_name_identical":superclass_is_exact,
        "compiler_only_superclass_name_mapping_explicit":
            not superclass_is_exact,
        "original_full_parent_method_set_rebuilt":False,
        "original_parent_all_fields_and_attributes_verified":False,
        "other_methods_remaining_unverified":
            original_method_count-len(selected_methods),
        "placeholder_original_parent_methods_accepted":False,
        "compiler_only_support_java_original":False,
        "original_client_code_executed":False,
        "experimental_whole_client_overlay_modified":False,
        "entire_v309_client_compiles":False,
        "original_source_publication_authorized":False,
    }
