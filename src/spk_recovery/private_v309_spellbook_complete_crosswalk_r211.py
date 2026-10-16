"""R211: exhaustive original v309 spellbook -> readable Class179 member crosswalk.

The genuine v309 rs/n/c/ap.class has 14 methods and 14 fields. The pinned
decompiled Class179.java donor contains 13 Java method declarations and
source static field initializers for <clinit>. This inventory audit is a
STRICT FIRST STAGE for later source/bytecode proof, NOT method-Code parity.

Method-order and stable callsite fingerprints are correspondence EVIDENCE;
none establishes all 14 complete method bodies or client runtime closure.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from zipfile import ZipFile

from .classfile import parse_class
from .bytecode_profile import profile_class_field_accesses
from .private_client_namespace_legalizer_r125 import CANONICAL_V309

ORIGINAL_OWNER="rs/n/c/ap"
ORIGINAL_CLASS_SHA256=(
    "b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4"
)
SOURCE_TREE_SHA256=(
    "cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d"
)
DONOR_JAVA_ENTRY=(
    "recovered-source/v309/src/rs/interfaces/widgets/Class179.java"
)
DONOR_JAVA_SHA256=(
    "8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2"
)
READABLE_OWNER="rs/interfaces/widgets/Class179"

# Original binary member order, not guessed from an alphabetized name list.
# Source member names are also confirmed independently against donor Java.
FIELD_PAIR_ORDER=(
    ("g","field3643"),("bI","field3644"),
    ("c","field3645"),("d","field3646"),
    ("e","field3647"),("f","field3648"),
    ("bJ","field3649"),("bK","field3650"),
    ("bL","field3651"),("bM","field3652"),
    ("bN","field3653"),("bO","field3654"),
    ("bP","field3655"),("bQ","field3656"),
)

METHOD_PAIR_ORDER=(
    (("h","()V"),("method1966","")),
    (("i","()V"),("method3153","")),
    (("j","()V"),("method236","")),
    (("a","(Lrs/n/c/ap$c;)V"),("method2689","Class178")),
    (("<init>","([Lrs/l/K;)V"),("Class179","HitsplatFont[]")),
    (("a","()V"),("register","")),
    (("m","(I)V"),("method640","int")),
    (("k","()V"),("method1241","")),
    (("l","()V"),("method1592","")),
    (("m","()V"),("method2352","")),
    (("n","()V"),("method3532","")),
    (("o","()V"),("method892","")),
    (("p","()V"),("method1712","")),
    (("<clinit>","()V"),("<clinit>","")),
)
# Only contextually specific source fingerprints. The validator does NOT
# assert that these fingerprints alone prove bytecode method equality.
DONOR_ANCHORS={
    "method1966":("field3646 = !field3646","method236();",
                  "method3153();","Configuration.saveSettings();"),
    "method3153":("widgetTable[1151]","Arrays.copyOf",
                  "widgetTable[12424]"),
    "method236":("Class178.values()","method2689"),
    "method2689":("skillLevels[6]","field3648","7455"),
    "register":("new Sprite(\"icons/pktele\")",
                "this.method1592();","this.method2352();"),
    "method640":("41910","41913","Configuration.saveSettings();"),
    "method1241":("field3648.contains","Class170.field3533"),
    "method1592":("41902","createPanelWidget"),
    "method2352":("1151","createContainerWidget"),
}
# Original runtime field descriptors and decompiled-source field types.
DESCRIPTOR_TO_SOURCE_TYPE={
    "[I":"int[]","I":"int","Z":"boolean",
    "Ljava/util/List;":"List<Class176>",
    "Lrs/l/F;":"Sprite",
}
SOURCE_FIELD_PATTERN=re.compile(
    r"(?m)^\s*(?P<visibility>public|protected|private)\s+"
    r"(?:(?:static|final)\s+){1,2}"
    r"(?P<type>int\[\]|int|boolean|List<Class176>|Sprite)\s+"
    r"(?P<name>field\d+)\b"
)
SOURCE_MEMBER_PATTERN=re.compile(
    r"(?m)^\s*(?:public|private|protected)\s+"
    r"(?:(?:static|final|synchronized)\s+)*"
    r"(?:(?:void|boolean|int|Class179|String|List<[^>]+>)\s+)?"
    r"(?P<name>\w+)\s*\((?P<args>[^)]*)\)\s*\{"
)


class R211SpellbookCompleteCrosswalkError(ValueError):
    pass


def need(ok,reason):
    if not ok:
        raise R211SpellbookCompleteCrosswalkError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inspect_readable_members(source, *, expected_fields=FIELD_PAIR_ORDER,
                             expected_methods=METHOD_PAIR_ORDER):
    """Compare complete source member order, types, and known callsite anchors."""
    need(isinstance(source,str)
         and re.search(r"\bclass\s+Class179\s+extends\s+Widget\b",
                       source) is not None,
         "R211_READABLE_WIDGET_PARENT_DECLARATION_MISSING")
    fields=[
        (x.group("name"),x.group("type"),x.group("visibility"))
        for x in SOURCE_FIELD_PATTERN.finditer(source)]
    need(len(fields)==len(expected_fields) and
         tuple(x[0] for x in fields)==
         tuple(b for _,b in expected_fields),
         "R211_READABLE_CLASS179_FULL_FIELD_ORDER_CHANGED")
    methods=[
        (x.group("name"),x.group("args").strip(),x.start())
        for x in SOURCE_MEMBER_PATTERN.finditer(source)]
    need(len(methods)==len(expected_methods)-1 and
         tuple(x[0] for x in methods)==
         tuple(b for (_,desc),(b,params) in expected_methods
               if b!="<clinit>"),
         "R211_READABLE_CLASS179_FULL_METHOD_ORDER_CHANGED")
    # Method arguments are checked separately from declaration names.
    for (key,(candidate,argument)),(name,args,_) in zip(
            [x for x in expected_methods if x[1][0]!="<clinit>"],
            methods):
        if argument:
            need(args.startswith(argument),
                 "R211_DONOR_METHOD_PARAMETER_TYPE_CHANGED")
        else:
            need(args=="",
                 "R211_UNEXPECTED_DONOR_METHOD_PARAMETER")
    # The donor has no explicit static {} block. Its field initializers
    # produce a Java9 <clinit> when javac compiles the whole owner.
    need("field3645 = 0;" in source and
         "field3646 = true;" in source and
         "field3647 = true;" in source and
         "new ArrayList()" in source and
         "field3656 = -1;" in source,
         "R211_DONOR_STATIC_INITIALIZER_ANCHORS_CHANGED")

    # Extract each Java method body using balanced source curly braces.
    # The original pinned donor has no comment/string literal with braces
    # in the specific anchors; exact full-method parsing is NOT asserted.
    blocks={}
    for idx,(name,args,start) in enumerate(methods):
        limit=(methods[idx+1][2] if idx+1<len(methods) else len(source))
        snippet=source[start:limit]
        blocks[name]=snippet
    for method,anchors in DONOR_ANCHORS.items():
        need(method in blocks and
             all(token in blocks[method] for token in anchors),
             "R211_CRITICAL_DECOMPILED_METHOD_FINGERPRINT_CHANGED")
    return {
        "readable_member_field_count":len(fields),
        "readable_member_method_count_including_initializer":
            len(methods)+1,
        "readable_member_declared_method_names":
            [m[0] for m in methods],
        "original_to_deobf_method_candidate_count":len(expected_methods),
        "critical_method_source_fingerprint_checks":len(DONOR_ANCHORS),
        "code_semantic_equivalence_proved":False,
    }


def verify_pinned_original_spellbook_complete_crosswalk(
        original_jar,private_source_tree_zip, *,
        original_jar_sha256=CANONICAL_V309,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        source_tree_sha256=SOURCE_TREE_SHA256,
        donor_source_sha256=DONOR_JAVA_SHA256):
    original_data=Path(original_jar).read_bytes()
    source_data=Path(private_source_tree_zip).read_bytes()
    need(sha(original_data)==original_jar_sha256 and
         sha(source_data)==source_tree_sha256,
         "R211_PINNED_ORIGINAL_BINARY_OR_DECOMPILED_SOURCE_ZIP_DRIFT")
    with ZipFile(original_jar) as jar:
        path=ORIGINAL_OWNER+".class"
        need(jar.namelist().count(path)==1,
             "R211_ORIGINAL_PARENT_JVM_CLASSFILE_NOT_UNIQUE")
        original=jar.read(path)
    need(sha(original)==original_class_sha256,
         "R211_ORIGINAL_SPELLBOOK_BINARY_SHA_CHANGED")
    with ZipFile(private_source_tree_zip) as z:
        need(z.namelist().count(DONOR_JAVA_ENTRY)==1,
             "R211_DECOMPILED_CLASS179_SOURCE_NOT_UNIQUE")
        donor=z.read(DONOR_JAVA_ENTRY)
    need(sha(donor)==donor_source_sha256,
         "R211_DECOMPILED_CLASS179_SOURCE_SHA_CHANGED")
    old=parse_class(original)
    need(old.name==ORIGINAL_OWNER
         and old.super_name=="rs/n/c"
         and old.major==53
         and len(old.fields)==len(FIELD_PAIR_ORDER)
         and len(old.methods)==len(METHOD_PAIR_ORDER),
         "R211_ORIGINAL_SPELLBOOK_JVM_CLASS_HEADER_CHANGED")
    field_order=tuple(f["name"] for f in old.fields)
    method_order=tuple((m["name"],m["descriptor"]) for m in old.methods)
    need(field_order==tuple(x[0] for x in FIELD_PAIR_ORDER)
         and method_order==tuple(x[0] for x in METHOD_PAIR_ORDER),
         "R211_ORIGINAL_14_FIELD_OR_14_METHOD_IDENTITY_ORDER_CHANGED")
    readable=inspect_readable_members(donor.decode("utf-8"))
    sourcefields={
        x.group("name"):x.group("type")
        for x in SOURCE_FIELD_PATTERN.finditer(donor.decode("utf-8"))
    }
    for (original_name,new_name),field in zip(FIELD_PAIR_ORDER,old.fields):
        need(original_name==field["name"] and
             sourcefields[new_name]==
                 DESCRIPTOR_TO_SOURCE_TYPE[field["descriptor"]],
             "R211_ORIGINAL_FIELD_DESCRIPTOR_VS_READABLE_TYPE_MISMATCH")
    instructions=sum(len(m["instructions"]) for m in
                     profile_class_field_accesses(original)["methods"])
    need(sha(original_data)==original_jar_sha256 and
         sha(source_data)==source_tree_sha256,
         "R211_PRIVATE_EVIDENCE_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_original_spellbook_full_member_order_crosswalk_r211",
        "original_class_sha256":original_class_sha256,
        "original_parent_owner":ORIGINAL_OWNER,
        "readable_candidate_owner":READABLE_OWNER,
        "original_field_candidates_mapped":len(FIELD_PAIR_ORDER),
        "original_method_candidates_mapped":len(METHOD_PAIR_ORDER),
        "original_decoded_jvm_instructions_only_inventoried":instructions,
        "source_anchor_evidence":readable,
        "all_original_method_jvm_code_parity_accepted":False,
        "all_original_field_to_donor_semantics_accepted":False,
        "original_class_superclass_readable_mapping_certified":False,
        "original_game_code_executed":False,
        "whole_original_client_compiles":False,
        "source_publication_authorized":False,
    }
