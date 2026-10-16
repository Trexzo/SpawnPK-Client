"""R210 — verify an EXISTING readable Java deobf Widget against original v309.

Unlike compiler-only declarations, this stage compiles the actual existing
private rs/interfaces/widgets/Widget.java donor from the recovered deobf
source tree. It independently checks EVERY original rs/n/c JVM method,
field, constructor, superclass reference, and instruction, under an
EXPLICIT original->readable class/member name map.

The original and new JVM owner names are intentionally different. This is
source-semantic mapping evidence, NOT identical original classfile bytes,
runtime acceptance, or permission to distribute original-derived Java.
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
from .source_method_parity import _normalized_instructions

ORIGINAL_OWNER="rs/n/c"
READABLE_OWNER="rs/interfaces/widgets/Widget"
ORIGINAL_CLASS_SHA256=(
    "65b1517e3630da9dcc79b8e53c28fa1622c000ff0825b33880ca3262d4d2b2a0"
)
PINNED_PRIVATE_SOURCE_TREE_SHA256=(
    "cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d"
)
DONOR_SOURCE_ENTRY=(
    "recovered-source/v309/src/rs/interfaces/widgets/Widget.java"
)
DONOR_SOURCE_SHA256=(
    "b3f77f45537ce65772e066f4bd27b9c3df99ca767479b5704927fb51df60985a"
)
OWNER_MAP={
    "rs/n/c":"rs/interfaces/widgets/Widget",
    "rs/n/e":"rs/interfaces/WidgetComponent",
    "rs/l/K":"rs/graphics/HitsplatFont",
}
FIELD_MAP={
    ("a","[Lrs/l/K;"):("fonts","[Lrs/graphics/HitsplatFont;"),
    ("b","Z"):("field3371","Z"),
}
METHOD_MAP={
    ("<init>","([Lrs/l/K;)V"):
        ("<init>","([Lrs/graphics/HitsplatFont;)V"),
    ("a","()V"):("register","()V"),
    ("a","(ILjava/lang/String;)V"):
        ("onMenuAction","(ILjava/lang/String;)V"),
    ("a","(I)V"):("onOptionClick","(I)V"),
    ("b","()V"):("close","()V"),
    ("c","()Z"):("isEnabled","()Z"),
}
# The following TWO files are compiler-only dependency DECLARATIONS.
# They are never accepted as recovered original classes or copied into
# the private whole-client Java tree.
COMPILER_STUBS={
    "rs/interfaces/WidgetComponent.java":(
        "package rs.interfaces;\n"
        "public abstract class WidgetComponent {\n"
        "  protected WidgetComponent(){}\n"
        "}\n"
    ),
    "rs/graphics/HitsplatFont.java":(
        "package rs.graphics;\n"
        "public class HitsplatFont {}\n"
    ),
}

class R210OriginalReadableWidgetError(ValueError):
    pass


def need(ok,message):
    if not ok:
        raise R210OriginalReadableWidgetError(message)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):
            h.update(block)
    return h.hexdigest()


def rewrite_descriptor(desc, owner_map):
    text=desc
    # JVM field and method descriptors are explicit Lowner; references.
    # Order by length avoids prefixes taking precedence for nested names.
    for before in sorted(owner_map,key=lambda x:(-len(x),x)):
        text=text.replace("L"+before+";","L"+owner_map[before]+";")
    return text


def exact_methods(profile):
    entries={}
    for m in profile["methods"]:
        key=(m["name"],m["descriptor"])
        need(key not in entries,"R210_DUPLICATE_JVM_METHOD")
        entries[key]=m
    return entries


def map_instruction(old, *, owner_map, field_map, method_map):
    row=dict(old)
    if "owner" in row:
        prior_owner=row["owner"]
        row["owner"]=owner_map.get(prior_owner,prior_owner)
        if prior_owner==ORIGINAL_OWNER and row["opcode"] in (
                "0xb2","0xb3","0xb4","0xb5"):
            old_id=(row["name"],row["descriptor"])
            need(old_id in field_map,
                 "R210_UNMAPPED_ORIGINAL_WIDGET_FIELD_ACCESS")
            row["name"]=field_map[old_id][0]
        if prior_owner==ORIGINAL_OWNER and row["opcode"] in (
                "0xb6","0xb7","0xb8","0xb9"):
            old_id=(row["name"],row["descriptor"])
            need(old_id in method_map,
                 "R210_UNMAPPED_ORIGINAL_WIDGET_METHOD_INVOKE")
            row["name"]=method_map[old_id][0]
    if "descriptor" in row:
        row["descriptor"]=rewrite_descriptor(row["descriptor"],owner_map)
    if "type" in row:
        row["type"]=owner_map.get(row["type"],row["type"])
    return row


def audit_readable_widget_classfiles(
        original_bytes,candidate_bytes, *,
        owner_map=OWNER_MAP,field_map=FIELD_MAP,method_map=METHOD_MAP,
        original_owner=ORIGINAL_OWNER,readable_owner=READABLE_OWNER,
        expected_methods=6,expected_fields=2,expected_instructions=11,
        expected_original_sha256=None):
    """Fail-closed full-owner deobfuscated Java semantic proof.

    No opcode, offsets, exception range, stack/locals limits, member
    reference or declaration can drift outside the explicit mapping.
    """
    need(type(original_bytes) is bytes and
         type(candidate_bytes) is bytes,
         "R210_JVM_CLASSFILE_BYTES_REQUIRED")
    if expected_original_sha256 is not None:
        need(sha_bytes(original_bytes)==expected_original_sha256,
             "R210_ORIGINAL_WIDGET_CLASS_SHA256_CHANGED")
    old=parse_class(original_bytes)
    new=parse_class(candidate_bytes)
    need(old.name==original_owner and new.name==readable_owner
         and owner_map.get(original_owner)==readable_owner
         and old.major==new.major==53
         and old.minor==new.minor==0
         and old.access==new.access
         and [owner_map.get(x,x) for x in old.interfaces]==new.interfaces
         and owner_map.get(old.super_name)==new.super_name,
         "R210_ORIGINAL_WIDGET_READABLE_HEADER_SUPER_EDGE_DIFFER")
    need(len(old.fields)==len(new.fields)==expected_fields
         and len(old.methods)==len(new.methods)==expected_methods,
         "R210_WIDGET_FULL_FIELD_METHOD_INVENTORY_CHANGED")
    declared_fields_old={
        (f["name"],f["descriptor"],f["access"])
        for f in old.fields}
    declared_fields_new={
        (f["name"],f["descriptor"],f["access"])
        for f in new.fields}
    need(len(declared_fields_old)==expected_fields and
         len(declared_fields_new)==expected_fields
         and set(field_map)=={(n,d) for n,d,_ in declared_fields_old}
         and { (field_map[(n,d)][0],
                rewrite_descriptor(d,owner_map),access)
                for n,d,access in declared_fields_old}==declared_fields_new,
         "R210_READABLE_WIDGET_FIELD_DECLARATION_ABI_MISMATCH")
    original=profile_class_field_accesses(original_bytes)
    candidate=profile_class_field_accesses(candidate_bytes)
    left=exact_methods(original)
    right=exact_methods(candidate)
    need(set(method_map)==set(left)
         and set(method_map.values())==set(right)
         and len(set(method_map.values()))==expected_methods,
         "R210_ALL_ORIGINAL_WIDGET_METHODS_MUST_HAVE_EXACT_MAP")
    count=0
    source_only_methods=0
    for method_id,from_method in sorted(left.items()):
        target_id=method_map[method_id]
        to_method=right[target_id]
        need(from_method["access"]==to_method["access"] and
             from_method.get("signature")==to_method.get("signature"),
             "R210_METHOD_ACCESS_OR_GENERIC_SIGNATURE_MISMATCH")
        if from_method["code_length"] is None:
            need(to_method["code_length"] is None and
                 (from_method["access"]&0x0400)!=0,
                 "R210_ABSTRACT_WIDGET_METHOD_CHANGED")
            continue
        need(from_method["code_length"]==to_method["code_length"]
             and from_method["max_stack"]==to_method["max_stack"]
             and from_method["max_locals"]==to_method["max_locals"]
             and from_method["exception_handlers"]==
                 to_method["exception_handlers"]
             and from_method["stackmap_table_present"]==
                 to_method["stackmap_table_present"],
             "R210_ORIGINAL_WIDGET_CODE_LIMITS_OR_EXCEPTIONS_CHANGED")
        a=_normalized_instructions(original,from_method)
        b=_normalized_instructions(candidate,to_method)
        rewritten=[map_instruction(
            row,owner_map=owner_map,
            field_map=field_map,method_map=method_map)
            for row in a]
        need(rewritten==b,
             "R210_READABLE_WIDGET_JVM_CODE_OR_OPERAND_MISMATCH")
        count+=len(a)
        source_only_methods+=1
    need(count==expected_instructions
         and source_only_methods==expected_methods-1,
         "R210_ORIGINAL_JVM_INSTRUCTION_OR_CONCRETE_METHOD_COUNT_DRIFT")
    return {
        "schema_version":1,
        "kind":"v309_original_to_existing_readable_widget_java_r210",
        "original_owner":old.name,
        "existing_readable_source_owner":new.name,
        "original_complete_methods_mapped":expected_methods,
        "original_concrete_methods_jvm_code_matched":source_only_methods,
        "matched_original_decoded_jvm_instructions":count,
        "original_to_readable_declared_fields":expected_fields,
        "original_and_readable_superclass_edges_mapped":True,
        "exact_instruction_code_offsets_and_core_limits_matched":True,
        "existing_decompiled_widget_source_semantics_match_original":True,
        "classfile_identity_or_original_symbol_names_proven":False,
        "full_superclass_implementation_recovered_in_this_test":False,
        "original_game_code_executed":False,
        "full_original_client_compiled":False,
        "source_redistribution_authorized":False,
    }


def verify_pinned_existing_decompiled_widget_source(
        original_jar,private_source_tree_zip, *,
        original_jar_sha256=CANONICAL_V309,
        source_tree_sha256=PINNED_PRIVATE_SOURCE_TREE_SHA256,
        donor_java_sha256=DONOR_SOURCE_SHA256,
        original_class_sha256=ORIGINAL_CLASS_SHA256):
    """Compile the ACTUAL deobfuscated Widget.java, not invented replacement.

    All existing donor bytes come from the SHA-pinned private 1,295-file
    original-decompiled source tree; only TWO dependency signatures are
    handwritten, plainly compiler-only, and excluded from proof outputs.
    """
    need(sha_file(original_jar)==original_jar_sha256
         and sha_file(private_source_tree_zip)==source_tree_sha256,
         "R210_EXACT_ORIGINAL_BINARY_AND_READABLE_SOURCE_TREE_PINS_REQUIRED")
    with ZipFile(original_jar) as original:
        name=ORIGINAL_OWNER+".class"
        need(original.namelist().count(name)==1,
             "R210_ORIGINAL_CLASS_ENTRY_NOT_UNIQUE")
        old_bytes=original.read(name)
    need(sha_bytes(old_bytes)==original_class_sha256,
         "R210_ORIGINAL_CLASS_BINARY_HASH_CHANGED")
    with ZipFile(private_source_tree_zip) as sources:
        need(sources.namelist().count(DONOR_SOURCE_ENTRY)==1,
             "R210_EXISTING_READABLE_WIDGET_JAVA_NOT_UNIQUE")
        donor=sources.read(DONOR_SOURCE_ENTRY)
    need(sha_bytes(donor)==donor_java_sha256,
         "R210_EXISTING_READABLE_WIDGET_JAVA_HASH_CHANGED")
    java=shutil.which("javac")
    need(java is not None,"R210_JDK_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r210-read-widget-") as tmp:
        root=Path(tmp)
        files={}
        for rel,data in {
            READABLE_OWNER+".java":donor,
            **{name:text.encode("utf-8")
               for name,text in COMPILER_STUBS.items()}
        }.items():
            path=root/"sources"/rel
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
            files[rel]=str(path)
        out=root/"classes"
        empty=root/"empty"
        out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            result=subprocess.run(
                [java,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),*files.values()],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R210OriginalReadableWidgetError(
                "R210_SOURCE_ONLY_JAVA9_COMPILATION_ABORTED") from exc
        emitted={x.relative_to(out).as_posix()
                 for x in out.rglob("*.class")}
        expected={READABLE_OWNER+".class"} | {
            name.replace(".java",".class") for name in COMPILER_STUBS}
        need(result.returncode==0 and emitted==expected,
             "R210_ONE_REAL_READABLE_OWNER_PLUS_TWO_DECLARATION_HELPERS")
        generated=(out/(READABLE_OWNER+".class")).read_bytes()
    proof=audit_readable_widget_classfiles(
        old_bytes,generated,
        expected_original_sha256=original_class_sha256)
    need(sha_file(original_jar)==original_jar_sha256 and
         sha_file(private_source_tree_zip)==source_tree_sha256,
         "R210_ORIGINAL_OR_DONOR_SOURCE_CHANGED_DURING_REPLAY")
    return {
        **proof,
        "original_binary_SHA256":original_class_sha256,
        "readable_java_source_sha256":donor_java_sha256,
        "readable_source_tree_sha256":source_tree_sha256,
        "real_decompiled_source_compiled":True,
        "compiler_only_dependency_declarations_used":2,
        "compiler_helpers_accepted_as_original_source":False,
        "private_java_source_uploaded_to_GitHub":False,
    }
