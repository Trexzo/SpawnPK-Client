"""R95: four exact original v309 nested enum classes and InnerClasses metadata.

R49 allows limited explicitly controlled generated enum-member aliases. This
new all-four gate adds exact symbolic InnerClasses metadata, where the known
flattened collision workaround MUST fail. It is not runtime equivalence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from .bytecode_profile import (
    BytecodeProfileError, _Reader, _constant_pool, _utf8, _class_name,
    profile_jar_class,
)
from .nested_enum_source_parity import (
    NestedEnumSourceParityError, compare_nested_enum_source,
)

class FourNestedEnumAcceptanceError(ValueError):
    pass

def need(test,code):
    if not test:raise FourNestedEnumAcceptanceError(code)

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):
            h.update(part)
    return h.hexdigest()

def symbolic_innerclasses_table(data:bytes):
    """Parse actual class-level InnerClasses attribute, resolving CP indices."""
    r=_Reader(data)
    need(r.u4()==0xCAFEBABE,"INVALID_CLASSFILE_MAGIC")
    r.u2();r.u2()
    cp=_constant_pool(r)
    r.u2();r.u2();r.u2() # access,this,super
    r.take(2*r.u2()) # interfaces
    for _ in range(2): # fields, methods
        count=r.u2()
        for __ in range(count):
            r.take(6) # access,name,descriptor
            for ___ in range(r.u2()):
                r.u2();r.take(r.u4())
    results=[]
    found=False
    for _ in range(r.u2()):
        name=_utf8(cp,r.u2())
        raw=r.take(r.u4())
        if name!="InnerClasses":continue
        need(not found,"DUPLICATE_INNERCLASSES_ATTRIBUTE")
        found=True
        a=_Reader(raw)
        for __ in range(a.u2()):
            inner,outer,simple,flags=a.u2(),a.u2(),a.u2(),a.u2()
            need(inner!=0,"INNERCLASSES_INNER_CLASS_INDEX_ZERO")
            results.append((
                _class_name(cp,inner),
                _class_name(cp,outer) if outer else None,
                _utf8(cp,simple) if simple else None,
                flags,
            ))
        need(a.offset==len(raw),"INNERCLASSES_ATTRIBUTE_TRAILING_BYTES")
    need(r.offset==len(data),"CLASSFILE_ATTRIBUTE_TAIL_NOT_EXACT")
    return tuple(results)

def nested_entries(names,owner_entry):
    need(isinstance(owner_entry,str) and owner_entry.endswith(".class")
         and not owner_entry.startswith("/")
         and "\\" not in owner_entry
         and all(part not in ("",".","..") and ":" not in part
                 for part in owner_entry.split("/")),
         "ORIGINAL_NESTED_OWNER_ENTRY_UNSAFE")
    prefix=owner_entry[:-6]+"$"
    entries=sorted(x for x in names if x.startswith(prefix)
                   and x.endswith(".class"))
    need(len(entries)==4 and len(set(entries))==4,
         "EXPECTED_FOUR_ORIGINAL_NESTED_ENUM_CLASSES")
    return entries

def check_four_nested_enums(
    original_profiles,candidate_profiles,original_tables,candidate_tables,
    original_sha256,
):
    keys=set(original_profiles)
    need(len(keys)==4 and keys==set(candidate_profiles)
         and keys==set(original_tables)==set(candidate_tables),
         "FOUR_NESTED_ENUM_INPUT_IDENTITIES_NOT_EXACT")
    count=0
    methods=0
    for entry in sorted(keys):
        original=original_profiles[entry]
        candidate=candidate_profiles[entry]
        need(original.get("internal_name")==candidate.get("internal_name")
             and entry==original.get("internal_name")+".class",
             "NESTED_ENUM_BINARY_OWNER_NOT_EXACT")
        need(original_tables[entry]
             and original_tables[entry]==candidate_tables[entry],
             "NESTED_ENUM_ORIGINAL_INNERCLASSES_METADATA_DIFFER")
        try:
            proof=compare_nested_enum_source(
                original,candidate,original_jar_sha256=original_sha256)
        except (NestedEnumSourceParityError,ValueError,KeyError,TypeError) as e:
            raise FourNestedEnumAcceptanceError(
                "R49_ONE_OR_MORE_ORIGINAL_NESTED_ENUM_METHODS_NOT_ACCEPTED") from e
        count+=proof["enum_constant_count"]
        methods+=proof["method_instruction_parity_after_aliases"]
    return {
        "original_nested_enum_classes_verified":4,
        "original_nested_enum_constants_with_alias_review":count,
        "original_nested_enum_method_bodies_compared":methods,
        "symbolic_InnerClasses_tables_identical_all_four":True,
        "original_nested_enum_compiler_generated_aliases_permitted":True,
        "canonical_alias_free_obfuscated_enum_field_identity_proven":False,
        "original_external_helper_behavior_proven":False,
        "whole_client_runtime_equivalence_certified":False,
    }

def replay_private_four_enum_gate(
    original_jar,candidate_jar,owner_entry,out,*,
    original_sha256,candidate_sha256,
):
    original_jar,candidate_jar,out=map(Path,(original_jar,candidate_jar,out))
    need(not out.exists() and not out.is_symlink(),"OUTPUT_ALREADY_EXISTS")
    for jar,pin in ((original_jar,original_sha256),
                    (candidate_jar,candidate_sha256)):
        need(jar.is_file() and not jar.is_symlink()
             and isinstance(pin,str) and len(pin)==64
             and digest(jar)==pin.lower(),
             "ORIGINAL_OR_CANDIDATE_JAR_SHA256_MISMATCH")
    try:
        with ZipFile(original_jar) as a,ZipFile(candidate_jar) as b:
            entries=nested_entries(a.namelist(),owner_entry)
            need(b.namelist().count(owner_entry)==1
                 and a.namelist().count(owner_entry)==1,
                 "ORIGINAL_OR_CANDIDATE_OWNER_MISSING")
            candidates=nested_entries(b.namelist(),owner_entry)
            need(entries==candidates
                 and all(a.namelist().count(k)==1 and b.namelist().count(k)==1
                         for k in entries),
                 "ORIGINAL_FOUR_NESTED_CLASSES_NOT_REPRESENTED_EXACTLY")
            profiles_a={k:profile_jar_class(original_jar,k) for k in entries}
            profiles_b={k:profile_jar_class(candidate_jar,k) for k in entries}
            attrs_a={k:symbolic_innerclasses_table(a.read(k)) for k in entries}
            attrs_b={k:symbolic_innerclasses_table(b.read(k)) for k in entries}
        proof=check_four_nested_enums(
            profiles_a,profiles_b,attrs_a,attrs_b,original_sha256)
    except (BytecodeProfileError,ValueError,KeyError,IndexError,
            TypeError,EOFError) as e:
        if isinstance(e,FourNestedEnumAcceptanceError):raise
        raise FourNestedEnumAcceptanceError(
            "ORIGINAL_NESTED_ENUM_JVM_EVIDENCE_NOT_REPLAYABLE") from e
    need(digest(original_jar)==original_sha256.lower()
         and digest(candidate_jar)==candidate_sha256.lower(),
         "PINNED_JARS_CHANGED_DURING_NESTED_CLASS_PROOF")
    report={
        "schema_version":1,
        "kind":"v309_private_all_four_nested_enums_and_InnerClasses_parity",
        "research_only":True,
        "original_complete_jar_sha256":original_sha256.lower(),
        "candidate_complete_jar_sha256":candidate_sha256.lower(),
        **proof}
    out.mkdir(parents=True,exist_ok=False)
    with (out/"all-four-nested-enums.aggregate.json").open(
            "x",encoding="utf-8",newline="\n") as f:
        json.dump(report,f,indent=2,sort_keys=True);f.write("\n")
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("original_jar","candidate_jar","owner_class_entry",
                "new_private_output"):p.add_argument(arg)
    p.add_argument("--original-sha256",required=True)
    p.add_argument("--candidate-sha256",required=True)
    a=p.parse_args(argv)
    try:
        print(json.dumps(replay_private_four_enum_gate(
            a.original_jar,a.candidate_jar,a.owner_class_entry,
            a.new_private_output,original_sha256=a.original_sha256,
            candidate_sha256=a.candidate_sha256),sort_keys=True))
    except FourNestedEnumAcceptanceError as e:p.error(str(e))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
