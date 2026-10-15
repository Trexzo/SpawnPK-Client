"""R204: independently audit v309 spellbook parent and decompiled donor.

Research-only crosswalk. It does NOT rename classfiles, inject sources,
execute game code, or accept Class179 as bytecode-identical to rs/n/c/ap.
All reported anchors are verified against the SHA-pinned original class
and the actual pinned decompiled source ZIP, not assumed from prior notes.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile
from .classfile import parse_class
from .bytecode_profile import profile_class_field_accesses

ORIGINAL_OWNER="rs/n/c/ap"
ORIGINAL_SHA256="b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4"
ORIGINAL_CLIENT_SHA256="ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
DONOR_PATH="recovered-source/v309/src/rs/interfaces/widgets/Class179.java"
DONOR_ENUM_PATH="recovered-source/v309/src/rs/interfaces/widgets/Class176.java"
PRIVATE_ENUM_OWNER="rs/n/c/ap$a"
PRIVATE_ENUM_SHA256="884186742e7d92489d6634e8cb6d0012ee5e8ba71bcc272c339bed4a8a9ee7df"

# Distinct original-vs-decompiled anchors, not automatic member mappings.
ANCHORS=(
 ("filter_toggle",("method1966","field3646","method3153","Configuration.saveSettings"),
  ("()V","rs/f/a")),
 ("widget_relayout",("method3153","widgetTable[1151]","12424","Arrays.copyOf"),
  ("()V","java/util/Arrays")),
 ("filtered_spell_categories",("Class176","field3648","field3647","skillLevels[6]"),
  ("()V","java/util/ArrayList")),
 ("settings_save_action",("Configuration.saveSettings","field3648","Class176"),
  ("(I)V","rs/f/a")),
)

class R204SpellbookCrosswalkError(ValueError):
    pass

def require(ok,reason):
    if not ok:
        raise R204SpellbookCrosswalkError(reason)

def _sha(data):
    return hashlib.sha256(data).hexdigest()

def audit_spellbook_parent(original_jar, source_tree_zip, *,
                           original_jar_sha256=ORIGINAL_CLIENT_SHA256,
                           original_class_sha256=ORIGINAL_SHA256,
                           donor_path=DONOR_PATH,
                           donor_enum_path=DONOR_ENUM_PATH,
                           expected_original_owner=ORIGINAL_OWNER):
    jar_bytes=Path(original_jar).read_bytes()
    require(_sha(jar_bytes)==original_jar_sha256,
            "R204_ORIGINAL_JAR_SHA_PIN_FAILED")
    with ZipFile(original_jar) as jar:
        required=[expected_original_owner+".class",PRIVATE_ENUM_OWNER+".class"]
        require(all(jar.namelist().count(x)==1 for x in required),
                "R204_ORIGINAL_PARENT_OR_ENUM_MISSING_DUPLICATE")
        original=jar.read(required[0])
        enum=jar.read(required[1])
    require(_sha(original)==original_class_sha256 and
            _sha(enum)==PRIVATE_ENUM_SHA256,
            "R204_ORIGINAL_PARENT_OR_ENUM_HASH_CHANGED")
    parsed=parse_class(original)
    require(parsed.name==expected_original_owner and
            parsed.super_name=="rs/n/c" and parsed.major==53,
            "R204_ORIGINAL_PARENT_CLASS_HEADER_DRIFT")
    profile=profile_class_field_accesses(original)
    fieldset={(x["name"],x["descriptor"]) for x in parsed.fields}
    require({("d","Z"),("e","Z"),("c","I"),
             ("f","Ljava/util/List;")}.issubset(fieldset),
            "R204_ORIGINAL_SPELLBOOK_STATE_ABI_CHANGED")
    with ZipFile(source_tree_zip) as sources:
        names=sources.namelist()
        require(len(names)==len(set(names)) and
                names.count(donor_path)==1 and
                names.count(donor_enum_path)==1,
                "R204_EXACT_TWO_DECOMPILED_SOURCE_OWNERS_REQUIRED")
        donor=sources.read(donor_path).decode("utf-8")
        donor_enum=sources.read(donor_enum_path).decode("utf-8")
    require(re.search(r"\bclass\s+Class179\s+extends\s+Widget\b",donor)
            and re.search(r"\benum\s+Class176\b",donor_enum),
            "R204_DECOMPILED_DONOR_OWNER_MISMATCH")
    require(all(re.search(r"\b"+name+r"\b",donor_enum)
                for name in ("field3590","field3591","field3592")),
            "R204_DONOR_ENUM_THREE_VALUES_CHANGED")
    method_descriptors=[x["descriptor"] for x in parsed.methods]
    memberrefs=set()
    for m in profile["methods"]:
        for ins in m["instructions"]:
            owner=ins.get("owner")
            if owner:
                memberrefs.add(owner)
    grounded=[]
    for name,tokens,original_support in ANCHORS:
        missing=[tok for tok in tokens if tok not in donor]
        compatible_method=original_support[0] in method_descriptors
        owner=original_support[1]
        comparable_owner=(owner in memberrefs)
        grounded.append({
            "candidate":name,
            "donor_tokens_present":not missing,
            "missing_donor_tokens":missing,
            "original_method_descriptor_present":compatible_method,
            "original_symbolic_dependency_present":comparable_owner,
            "strong_crosswalk_anchor":not missing and compatible_method
              and comparable_owner,
            "exact_member_mapping_proved":False,
        })
    require(all(x["strong_crosswalk_anchor"] for x in grounded),
            "R204_CROSSWALK_ANCHOR_MISSING")
    return {
        "schema":1,
        "original_owner":parsed.name,
        "original_class_sha256":_sha(original),
        "source_decompiled_owner":"rs/interfaces/widgets/Class179",
        "source_decompiled_enum":"rs/interfaces/widgets/Class176",
        "original_field_count":len(parsed.fields),
        "original_method_count":len(parsed.methods),
        "original_instructions":sum(len(x["instructions"])
             for x in profile["methods"]),
        "original_nested_enum_hash_verified":True,
        "anchors":grounded,
        "full_original_source_reconstructed":False,
        "exact_obfuscated_member_to_decompiled_member_mapping_proven":False,
        "whole_client_compiles":False,
        "game_code_executed":False,
    }
