"""R197: original v309 configuration NESTED enum source-only evidence.

Read-only SHA-pinned original client and FOUR original-named private Java
sources. Java 9 compiles all four enums together WITHOUT external/game
.class fallback. Compare all original JVM method Code after narrowly
mapping original obfuscated enum CONSTANT fields to genuine Enum.name()
labels, compiler-generated $values, and the required public obfuscated
field aliases. Alias writes are EXTRA; no byte-identical class claim.

DO NOT treat this as recovery of the large parent rs/f/a.class. No enum
methods or full game client are run, and no derived Java is published.
"""
from __future__ import annotations
from collections import OrderedDict
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
from .private_v309_signlink_whole_semantic_r189 import _semantic_method
from .private_v309_four_owner_javac_frontier_r192 import (
    build_private_four_owner_overlay,
    compare_pinned_private_four_owner_javac,
)

PARENT_OWNER="rs/f/a"
ENUM_SPECS=OrderedDict((
 ("rs/f/a$a",{
    "class_sha256":"a2b590461bcacc7bc287c9d8835a805a10e80c8626a2ac98b2bb05bd0a15e972",
    "source_zip_sha256":"394d1269c088d0a90479681868d6021e1d49981ea722ca10d57a0158304a1639",
    "constants":(("a","SPAWNPK"),("b","RUNEX")),
    "array_field":"e","array_method":"c",
    "other_fields":("c","d"),
    "method_count":9,"original_instruction_count":62,
    "source_derived_synthetic_accessors":(
        ("a","(Lrs/f/a$a;)Ljava/lang/String;"),
        ("b","(Lrs/f/a$a;)Ljava/lang/String;")),
 }),
 ("rs/f/a$b",{
    "class_sha256":"86ee7a024bade8de10ac00e18812919b9703925b6c5a6c89e74a489339ab800d",
    "source_zip_sha256":"4d8ba639924ce19ff9ae8a5d100cba96e143d137cad621bc09b6e3f5dd6817a5",
    "constants":(("a","NORMAL"),("b","WINTER"),
                 ("c","DARK_WINTER"),("d","HALLOWEEN"),("e","SUMMER")),
    "array_field":"g","array_method":"a",
    "other_fields":("f",),
    "method_count":5,"original_instruction_count":78,
    "source_derived_synthetic_accessors":(),
 }),
 ("rs/f/a$c",{
    "class_sha256":"7602671538d7d7e42139e93667f9b6134cdc70b1376b6536a52f69f67c64a29f",
    "source_zip_sha256":"f67ddbb08348facd63728def1b283081bd144c85677f7735cecab858ffd21160",
    "constants":(("a","FIXED"),("b","RESIZABLE"),("c","FULLSCREEN")),
    "array_field":"d","array_method":"a",
    "other_fields":(),
    "method_count":6,"original_instruction_count":75,
    "source_derived_synthetic_accessors":(),
 }),
 ("rs/f/a$d",{
    "class_sha256":"1049f7db1f6841a0720c11f0feba46c54d4b64d327ccef26c5dec5f514c23eef",
    "source_zip_sha256":"29650a87f128f06d44d80f40de62ebc1e885d58d00ce8d5e71b95d460b79da04",
    "constants":(("a","NONE"),("b","SPRING"),("c","SUMMER"),
                 ("d","HWEEN"),("e","DARK_WINTER"),("f","WINTER")),
    "array_field":"g","array_method":"a",
    "other_fields":(),
    "method_count":5,"original_instruction_count":80,
    "source_derived_synthetic_accessors":(),
 }),
))
TOTAL_ORIGINAL_ENUM_METHODS=25
TOTAL_ORIGINAL_JVM_INSTRUCTIONS=295
PREVIOUS_TREE_SHA256="f248c92c9bea9047a2282b826b8003095935093680f4ba25c6d3dee435a5b00f"
NEW_TREE_SHA256="e337def4eb1c4395f917e14ec2922c95e9ee0ff99461ec97b4a4ec8a78744bf01"


class R197OriginalConfigEnumError(ValueError):
    pass


def need(ok,why):
    if not ok:
        raise R197OriginalConfigEnumError(why)


def _method_index(profile):
    result={}
    for method in profile["methods"]:
        id=(method["name"],method["descriptor"])
        need(id not in result,"R197_DUPLICATE_ORIGINAL_METHOD")
        result[id]=method
    return result


def _remap_original_instruction(operand,owner,field_map,array_method,
                                array_descriptor):
    row=dict(operand)
    if row.get("owner")==owner:
        opcode=row["opcode"]
        if opcode in ("0xb2","0xb3","0xb4","0xb5"):
            row["name"]=field_map.get(row.get("name"),row.get("name"))
        elif opcode in ("0xb6","0xb7","0xb8","0xb9") and (
                row.get("name")==array_method and
                row.get("descriptor")==array_descriptor):
            row["name"]="$values"
    return row


def _alias_initializers(actual,old,owner,aliases):
    """Remove ONLY the expected, nonoriginal alias field initialization."""
    need(len(actual)>=len(old)+2*len(aliases),
         "R197_ENUM_STATIC_INITIALIZER_LOST_ORIGINAL_CODE")
    need(actual[-1]["opcode"]=="0xb1" and
         old[-1]["opcode"]=="0xb1",
         "R197_STATIC_INITIALIZER_RETURN_CHANGED")
    start=len(actual)-1-2*len(aliases)
    expected=[]
    for obfuscated,label in aliases:
        expected.extend([("0xb2",label),("0xb3",obfuscated)])
    added=actual[start:-1]
    need(len(added)==len(expected) and
         [(i["opcode"],i.get("name")) for i in added]==expected and
         all(i.get("owner")==owner for i in added),
         "R197_ENUM_ALIAS_ASSIGNMENTS_NOT_EXACT")
    return actual[:start]+actual[-1:],len(added)


def audit_config_enum_classfiles(
        original_bytes,recompiled_bytes, *,
        owner,config,original_sha256=None):
    """Class-level symbolic Code evidence, with explicit Java enum deviations."""
    if original_sha256 is not None:
        need(hashlib.sha256(original_bytes).hexdigest()==original_sha256,
             "R197_ORIGINAL_CLASS_DIGEST_MISMATCH")
    original=parse_class(original_bytes)
    rebuilt=parse_class(recompiled_bytes)
    need((original.name,original.super_name,original.access,
          original.major,original.minor,original.interfaces)==
         (rebuilt.name,rebuilt.super_name,rebuilt.access,
          rebuilt.major,rebuilt.minor,rebuilt.interfaces)
         and original.name==owner
         and original.super_name=="java/lang/Enum" and
         original.major==53 and original.minor==0 and
         (original.access & 0x4000),
         "R197_ORIGINAL_JAVA9_ENUM_CLASS_HEADER_CHANGED")
    aliases=tuple(config.get("aliases",config["constants"]))
    field_map=dict(config["constants"])
    need(len(aliases)==len(config["constants"]) and
         set(label for _,label in aliases)==
             set(label for _,label in config["constants"]),
         "R197_ALIAS_LABELS_MUST_MATCH_ORIGINAL_ENUM_VALUES")
    field_map[config["array_field"]]="$VALUES"
    field_map.update({n:n for n in config["other_fields"]})
    old_fields={f["name"]:f for f in original.fields}
    new_fields={f["name"]:f for f in rebuilt.fields}
    need(set(old_fields)==set(field_map) and
         set(new_fields)==set(field_map.values()) |
             {name for name,_ in aliases} and
         len(rebuilt.fields)==len(original.fields)+len(aliases),
         "R197_ORIGINAL_ENUM_FIELD_IDENTITY_OR_ALIAS_INVENTORY_CHANGED")
    for key,target in field_map.items():
        old=old_fields[key];new=new_fields[target]
        need((old["descriptor"],old["access"])==
             (new["descriptor"],new["access"]),
             "R197_ORIGINAL_ENUM_FIELD_TYPE_OR_ACCESS_CHANGED")
    for field,_ in aliases:
        new=new_fields[field]
        need(new["descriptor"]=="L"+owner+";" and
             new["access"]==0x0019,
             "R197_NONORIGINAL_ALIAS_NOT_PUBLIC_STATIC_FINAL")

    left=profile_class_field_accesses(original_bytes)
    right=profile_class_field_accesses(recompiled_bytes)
    methods_old=_method_index(left)
    methods_new=_method_index(right)
    need(len(methods_old)==len(methods_new)==config["method_count"],
         "R197_ENUM_METHOD_COUNT_MISMATCH")
    array_method_id=(config["array_method"],"()[L"+owner+";")
    renamed=lambda id:("$values",id[1]) if id==array_method_id else id
    need({renamed(id) for id in methods_old}==set(methods_new),
         "R197_ENUM_ORIGINAL_METHOD_SET_CHANGED")
    compared=0
    extra_alias_instructions=0
    mapped_restrictions=config["source_derived_synthetic_accessors"]
    for id,original_method in sorted(methods_old.items()):
        target=renamed(id)
        next_method=methods_new[target]
        if id not in mapped_restrictions:
            need(original_method["access"]==next_method["access"],
                 "R197_ORIGINAL_METHOD_ACCESS_FLAGS_CHANGED")
        else:
            # Original synthetic nestmate accessors become explicit helper
            # methods in source-only Java; their JVM Code is still checked.
            need((original_method["access"]&~0x1000)==
                 next_method["access"],
                 "R197_ORIGINAL_SYNTHETIC_ACCESSOR_ACCESS_DIFFERS")
        a,ahandlers=_semantic_method(left,original_method)
        b,bhandlers=_semantic_method(right,next_method)
        a=[_remap_original_instruction(x,owner,field_map,
               config["array_method"],array_method_id[1]) for x in a]
        if id==("<clinit>","()V"):
            b,extra=_alias_initializers(b,a,owner,aliases)
            extra_alias_instructions+=extra
        need(a==b and ahandlers==bhandlers,
             "R197_ORIGINAL_JVM_ENUM_CODE_NOT_SEMANTICALLY_EQUAL")
        # Extra alias writes are not counted as original instructions.
        compared+=len(a)
    need(compared==config["original_instruction_count"] and
         extra_alias_instructions==2*len(aliases),
         "R197_ORIGINAL_ENUM_JVM_OPCODE_OR_ALIAS_COUNT_CHANGED")
    return {
        "owner":owner,
        "original_jvm_methods_compared":len(methods_old),
        "matched_original_semantic_jvm_instructions":compared,
        "original_enum_labels":[x[1] for x in aliases],
        "original_ordinals_in_label_order":True,
        "source_added_alias_fields":len(aliases),
        "extra_alias_initializer_instructions":extra_alias_instructions,
        "java9_source_only":True,
        "original_binary_classfile_identity_claimed":False,
        "original_nesting_and_stackmap_attributes_verified":False,
        "original_game_or_enum_methods_executed":False,
    }


def verify_pinned_config_enum_java(
        original_jar,private_original_source_zips, *,
        original_jar_sha256=CANONICAL_V309,
        source_sha256_overrides=None):
    """Exact original v309 replay: four owners and ZERO helper declarations."""
    need(len(private_original_source_zips)==4,
         "R197_EXACT_FOUR_CONFIG_ENUM_JAVA_SOURCE_ARCHIVES")
    need(sha_file(original_jar)==original_jar_sha256,
         "R197_ORIGINAL_V309_BINARY_SHA256_CHANGED")
    expected=tuple(ENUM_SPECS.items())
    paths=[]
    for (owner,spec),source_path in zip(expected,private_original_source_zips):
        sha=(source_sha256_overrides or {}).get(
            owner,spec["source_zip_sha256"])
        need(sha_file(source_path)==sha,
             "R197_ORIGINAL_ENUM_JAVA_SOURCE_SHA256_CHANGED")
        candidate=source_members(source_path,sha)
        need(len(candidate)==1 and
             candidate[0][0]==owner+".java" and
             0<len(candidate[0][1])<=50_000,
             "R197_PRIVATE_JAVA_SOURCE_OWNER_NOT_UNIQUE")
        paths.append((owner,candidate[0][1]))
    with ZipFile(original_jar) as jar:
        need(all(jar.namelist().count(o+".class")==1
                 for o in ENUM_SPECS),
             "R197_ORIGINAL_ENUM_CLASSFILE_NOT_UNIQUE")
        original={o:jar.read(o+".class") for o in ENUM_SPECS}
    need(all(hashlib.sha256(original[o]).hexdigest()==
             spec["class_sha256"]
             for o,spec in ENUM_SPECS.items()),
         "R197_ORIGINAL_ENUM_CLASSFILE_SHA256_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R197_JDK_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r197-config-enums-") as d:
        root=Path(d)
        java_sources=[]
        for owner,body in paths:
            src=root/"src"/(owner+".java")
            src.parent.mkdir(parents=True,exist_ok=True)
            src.write_bytes(body)
            java_sources.append(str(src))
        out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            p=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),
                *java_sources],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R197OriginalConfigEnumError(
                "R197_SOURCE_ONLY_JAVA9_COMPILATION_ABORTED") from exc
        emitted={x.relative_to(out).as_posix()
                 for x in out.rglob("*.class")}
        need(p.returncode==0 and
             emitted=={o+".class" for o in ENUM_SPECS},
             "R197_FOUR_AND_ONLY_FOUR_SOURCE_GENERATED_CLASSFILES")
        built={o:(out/(o+".class")).read_bytes()
               for o in ENUM_SPECS}
    proof=[audit_config_enum_classfiles(
        original[o],built[o],owner=o,config=spec,
        original_sha256=spec["class_sha256"])
        for o,spec in ENUM_SPECS.items()]
    need(sum(x["original_jvm_methods_compared"] for x in proof)==
             TOTAL_ORIGINAL_ENUM_METHODS and
         sum(x["matched_original_semantic_jvm_instructions"]
             for x in proof)==TOTAL_ORIGINAL_JVM_INSTRUCTIONS,
         "R197_ORIGINAL_FOUR_ENUM_METHOD_TOTALS_CHANGED")
    need(all(sha_file(path)==
         (source_sha256_overrides or {}).get(
             owner,spec["source_zip_sha256"])
         for (owner,spec),path in zip(expected,private_original_source_zips)),
         "R197_PRIVATE_JAVA_SOURCE_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_four_original_config_enum_semantic_java_r197",
        "original_class_count_verified":len(proof),
        "original_method_bodies_compared":TOTAL_ORIGINAL_ENUM_METHODS,
        "original_semantic_instructions_matched":
            TOTAL_ORIGINAL_JVM_INSTRUCTIONS,
        "classes":proof,
        "all_four_java_source_files_compile_without_helpers":True,
        "large_rs_f_a_parent_java_reconstructed":False,
        "binary_identical_original_enums_claimed":False,
        "original_client_compiles":False,
        "game_or_enum_runtime_executed":False,
        "original_source_publication_authorized":False,
    }


def build_pinned_private_config_enum_overlay(
        previous_1286_tree_zip,original_enum_zips,fresh_1290_tree_zip, *,
        old_tree_sha256=PREVIOUS_TREE_SHA256,
        expected_new_tree_sha256=NEW_TREE_SHA256,
        source_identities=None):
    identities=source_identities or tuple(
        (owner+".java",spec["source_zip_sha256"])
        for owner,spec in ENUM_SPECS.items())
    result=build_private_four_owner_overlay(
        previous_1286_tree_zip,original_enum_zips,fresh_1290_tree_zip,
        baseline_sha256=old_tree_sha256,
        source_identities=identities,
        expected_baseline_java=1286)
    need(result["new_overlay_zip_sha256"]==expected_new_tree_sha256,
         "R197_PRIVATE_1290_JAVA_OVERLAY_SHA256_DRIFT")
    return result
