"""R207: recover COMPLETE original v309 abstract widget base Java class.

Original rs/n/c.class (rs.n.c) is a six-method, two-field abstract widget
base. All five Code-bearing methods must independently compile from real
original-named Java9 source and exactly reproduce 11 original JVM operations.
Its abstract a():void declaration, superclass and both protected field
ABIs are independently checked. The original class bytecode is never run.

CRITICAL: rs.n.c (class) collides with rs.n.c (package of rs.n.c.ap).
Thus original-named rs/n/c.java CANNOT be installed alongside original-named
rs/n/c/ap.java in one vanilla Java source tree. It must be namespace-
legalized (deobfuscated) before full tree integration. Do not invent a
different superclass owner and claim JVM class-header identity.
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

OWNER="rs/n/c"
CLASS_SHA256=(
    "65b1517e3630da9dcc79b8e53c28fa1622c000ff0825b33880ca3262d4d2b2a0"
)
SOURCE_SHA256=(
    "2a69da84230573377795311331eb30196aff132f8bc55f18853d841bba57d148"
)
NONORIGINAL_HELPER_SHA256=(
    "c43928dad50b7dbfa828c6f0a7c2b7f17ecf4ce4abb8a4fb5781b4f287855dc0"
)
NONORIGINAL_HELPERS=("rs/n/e","rs/l/K")
EXPECTED_FIELDS=2
EXPECTED_METHODS=6
EXPECTED_CONCRETE_METHODS=5
EXPECTED_ORIGINAL_JVM_INSTRUCTIONS=11
ORIGINAL_ABSTRACT=("a","()V")


class R207OriginalWidgetBaseError(ValueError):
    pass


def need(ok,message):
    if not ok:
        raise R207OriginalWidgetBaseError(message)


def _fields(parsed):
    return sorted(
        (f["name"],f["descriptor"],f["access"],f.get("signature"),
         repr(f.get("constant_value"))) for f in parsed.fields)


def _methods(parsed):
    return sorted(
        (m["name"],m["descriptor"],m["access"],m.get("signature"))
        for m in parsed.methods)


def verify_original_widget_base_source(
        original_jar,real_base_source_zip,compiler_helpers_zip, *,
        original_jar_sha256=CANONICAL_V309,
        original_owner=OWNER,original_class_sha256=CLASS_SHA256,
        source_sha256=SOURCE_SHA256,
        helper_source_sha256=NONORIGINAL_HELPER_SHA256,
        helper_owners=NONORIGINAL_HELPERS,
        expected_fields=EXPECTED_FIELDS,
        expected_methods=EXPECTED_METHODS,
        expected_selected_methods=EXPECTED_CONCRETE_METHODS,
        expected_instructions=EXPECTED_ORIGINAL_JVM_INSTRUCTIONS,
        expected_abstract=ORIGINAL_ABSTRACT):
    pins=(
        (original_jar,original_jar_sha256),
        (real_base_source_zip,source_sha256),
        (compiler_helpers_zip,helper_source_sha256),
    )
    need(all(sha_file(path)==digest for path,digest in pins),
         "R207_ORIGINAL_JAR_OR_JAVA_SOURCE_SHA256_CHANGED")
    java=source_members(real_base_source_zip,source_sha256)
    helpers=source_members(compiler_helpers_zip,helper_source_sha256)
    need(len(java)==1 and java[0][0]==original_owner+".java" and
         len(helpers)==len(helper_owners) and
         {name for name,_ in helpers}==
             {owner+".java" for owner in helper_owners} and
         len(set((original_owner,*helper_owners)))==len(helper_owners)+1,
         "R207_EXACT_ONE_REAL_OWNER_AND_TWO_NONORIGINAL_HELPERS")
    with ZipFile(original_jar) as archive:
        path=original_owner+".class"
        need(archive.namelist().count(path)==1,
             "R207_ORIGINAL_SUPERCLASS_OWNER_MISSING_OR_DUPLICATE")
        original_bytes=archive.read(path)
    need(hashlib.sha256(original_bytes).hexdigest()==original_class_sha256,
         "R207_ORIGINAL_SUPERCLASS_BINARY_SHA_CHANGED")
    old=parse_class(original_bytes)
    need(old.name==original_owner and old.super_name is not None and
         old.major==53 and (old.access&0x0400)!=0 and
         len(old.fields)==expected_fields and
         len(old.methods)==expected_methods,
         "R207_ORIGINAL_ABSTRACT_WIDGET_BASE_ABI_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R207_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r207-base-") as td:
        root=Path(td)
        paths=[]
        for relative,body in [*java,*helpers]:
            path=root/"src"/relative
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(body)
            paths.append(str(path))
        out=root/"classes"
        empty=root/"empty"
        out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            p=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R207OriginalWidgetBaseError(
                "R207_SOURCE_ONLY_JAVA9_COMPILATION_ABORTED") from exc
        emitted={p.relative_to(out).as_posix()
                 for p in out.rglob("*.class")}
        need(p.returncode==0 and
             emitted=={owner+".class" for owner in
                      (original_owner,*helper_owners)},
             "R207_NO_ORIGINAL_BINARY_FALLBACK_OR_EXTRA_CLASSES")
        compiled=(out/(original_owner+".class")).read_bytes()
    new=parse_class(compiled)
    need((old.name,old.super_name,old.major,old.minor,
          old.access,old.interfaces)==
         (new.name,new.super_name,new.major,new.minor,
          new.access,new.interfaces),
         "R207_ORIGINAL_SUPERCLASS_BINARY_NAME_OR_FLAGS_CHANGED")
    need(_fields(old)==_fields(new) and
         _methods(old)==_methods(new),
         "R207_FULL_TWO_FIELDS_SIX_METHODS_OR_ABSTRACT_FLAGS_DIFFER")
    abstract=[m for m in old.methods
              if (m["name"],m["descriptor"])==expected_abstract]
    need(len(abstract)==1 and (abstract[0]["access"]&0x0400)!=0
         and abstract[0]["code_length"] is None,
         "R207_ORIGINAL_ABSTRACT_METHOD_CODE_OR_FLAGS_CHANGED")
    original_profile=profile_class_field_accesses(original_bytes)
    rebuilt_profile=profile_class_field_accesses(compiled)
    all_selected=sorted(
        (m["name"],m["descriptor"]) for m in old.methods
        if (m["name"],m["descriptor"])!=expected_abstract)
    need(len(all_selected)==expected_selected_methods,
         "R207_ORIGINAL_CONCRETE_METHOD_IDENTITY_DRIFT")
    try:
        comparison=_strict_inspections(
            original_profile,rebuilt_profile,selected=all_selected)
    except ValueError as exc:
        raise R207OriginalWidgetBaseError(
            "R207_ORIGINAL_ABSTRACT_WIDGET_BASE_JVM_CODE_CHANGED") from exc
    need(comparison["verified_selected_method_count"]==
         expected_selected_methods and
         comparison["matched_opcode_count"]==expected_instructions and
         comparison["all_selected_core_method_code_equal"],
         "R207_NOT_ALL_ORIGINAL_SUPERCLASS_JVM_INSTRUCTIONS_MATCH")
    need(all(sha_file(path)==digest for path,digest in pins),
         "R207_PRIVATE_ORIGINAL_SOURCE_CHANGED_DURING_AUDIT")
    return {
        "schema_version":1,
        "kind":"v309_original_widget_base_full_java_source_r207",
        "original_owner":original_owner,
        "original_class_sha256":original_class_sha256,
        "full_original_member_abi_verified":True,
        "complete_original_six_method_inventory_verified":True,
        "original_abstract_method_signature_verified":True,
        "original_concrete_method_code_verified":expected_selected_methods,
        "all_original_jvm_instructions_compared":expected_instructions,
        "original_superclass_binary_name_matches":True,
        "original_external_support_java_recovered":False,
        "compiler_only_support_owners":list(helper_owners),
        "original_named_package_class_collision_unresolved":True,
        "safe_to_insert_original_named_source_alongside_rs_n_c_ap":False,
        "original_game_code_executed":False,
        "full_original_client_compiles":False,
        "source_publication_authorized":False,
    }
