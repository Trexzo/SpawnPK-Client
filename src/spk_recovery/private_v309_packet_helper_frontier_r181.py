"""R181: original-v309 Packet compiler-only helper class recovery worklist.

Read-only; the original JAR is SHA pinned. The four helpers from R179 are
NOT restored by this scan. Member references identify investigation targets,
not proven source equivalence or even full Java type-checking dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file
from .private_v309_packet_complete_source_r179 import (
    COMPILER_ONLY_HELPERS, ORIGINAL_PACKET_SHA,
)


class R181HelperFrontierError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise R181HelperFrontierError(reason)


_OWNER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*(?:/[A-Za-z_$][A-Za-z0-9_$]*)+")
_HEX64 = re.compile(r"[0-9a-f]{64}")


def _digest_json(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _candidate_source_paths(candidate, expected_sha):
    """Check canonical recovered-source ZIP paths; do not load or run Java."""
    p=Path(candidate)
    require(p.is_file() and not p.is_symlink() and
            sha_file(p)==expected_sha,
            "R181_CANDIDATE_SOURCE_ARCHIVE_NOT_PINNED")
    prefix="recovered-source/v309/src/"
    with ZipFile(p) as archive:
        infos=archive.infolist()
        require(1<=len(infos)<=50000,
                "R181_CANDIDATE_ZIP_ENTRY_COUNT_INVALID")
        names=[i.filename for i in infos]
        require(len(names)==len(set(names)),
                "R181_CANDIDATE_ZIP_DUPLICATE_FILE")
        chosen=[]
        total=0
        for item in infos:
            name=item.filename
            require(not name.startswith("/") and "\\" not in name and
                    all(x not in ("", ".", "..")
                        for x in name.rstrip("/").split("/")) and
                    ((item.external_attr >> 16) & 0o170000) != 0o120000,
                    "R181_CANDIDATE_ZIP_UNSAFE_FILE")
            if item.is_dir() or not name.endswith(".java"):
                continue
            require(name.startswith(prefix) and
                    len(name)<400 and item.file_size<=2_000_000,
                    "R181_CANDIDATE_JAVA_FILE_OUTSIDE_CANONICAL_TREE")
            total+=item.file_size
            require(total<=50_000_000,
                    "R181_CANDIDATE_JAVA_SIZE_EXCEEDS_LIMIT")
            chosen.append(name)
    require(chosen and len(chosen)==len({x.casefold() for x in chosen}),
            "R181_CANDIDATE_DUPLICATE_OR_EMPTY_JAVA_PATH_SET")
    return set(chosen)


def audit_packet_helper_frontier(
        original_jar, *,
        original_sha256=CANONICAL_V309,
        packet_owner="rs/x/e",
        packet_class_sha256=ORIGINAL_PACKET_SHA,
        helper_owners=COMPILER_ONLY_HELPERS,
        expected_helper_class_sha256=None,
        private_source_candidate_zip=None,
        candidate_source_sha256=None,
        include_private_names=False):
    """Audit exact original helper ABI, uses, and unverified source coverage.

    This does NOT accept a reconstruction. Calls to inherited members and
    reflective/dynamic references are not proven by this direct-call census.
    """
    owners=tuple(helper_owners)
    require(_OWNER.fullmatch(packet_owner) is not None
            and len(owners)==4
            and len(set(owners))==4
            and all(_OWNER.fullmatch(x) is not None for x in owners)
            and packet_owner not in owners,
            "R181_FOUR_UNIQUE_JVM_HELPER_OWNERS_REQUIRED")
    require(_HEX64.fullmatch(original_sha256) is not None and
            _HEX64.fullmatch(packet_class_sha256) is not None and
            sha_file(original_jar)==original_sha256,
            "R181_ORIGINAL_JAR_SHA256_NOT_PINNED")
    if expected_helper_class_sha256 is not None:
        require(isinstance(expected_helper_class_sha256, dict)
                and set(expected_helper_class_sha256)==set(owners)
                and all(isinstance(x, str) and _HEX64.fullmatch(x)
                        for x in expected_helper_class_sha256.values()),
                "R181_HELPER_CLASS_SHA256_MANIFEST_INVALID")
    have_source=private_source_candidate_zip is not None
    require(have_source==(candidate_source_sha256 is not None),
            "R181_SOURCE_ZIP_AND_SHA_MUST_BE_TOGETHER")
    sources=None
    if have_source:
        require(_HEX64.fullmatch(candidate_source_sha256) is not None,
                "R181_CANDIDATE_SHA_INVALID")
        sources=_candidate_source_paths(private_source_candidate_zip,
                                        candidate_source_sha256)
    with ZipFile(original_jar) as jar:
        paths=[packet_owner+".class",*(o+".class" for o in owners)]
        listing=jar.namelist()
        require(all(listing.count(p)==1 for p in paths),
                "R181_ONE_OR_MORE_ORIGINAL_CLASSES_MISSING_OR_DUPLICATE")
        require(all(jar.getinfo(p).file_size<=5_000_000 for p in paths),
                "R181_CLASSFILE_SIZE_EXCEEDS_AUDIT_BOUND")
        original={p[:-6]:jar.read(p) for p in paths}
    require(hashlib.sha256(original[packet_owner]).hexdigest()==
            packet_class_sha256,
            "R181_ORIGINAL_PACKET_CLASS_CHANGED")
    packet=parse_class(original[packet_owner])
    require(packet.name==packet_owner,
            "R181_PACKET_INTERNAL_OWNER_MISMATCH")
    packet_profile=profile_class_field_accesses(original[packet_owner])
    require(packet_profile["internal_name"]==packet_owner,
            "R181_PACKET_PROFILE_OWNER_MISMATCH")
    all_details=[]
    public_rows=[]
    for owner in sorted(owners):
        data=original[owner]
        class_sha=hashlib.sha256(data).hexdigest()
        if expected_helper_class_sha256 is not None:
            require(class_sha==expected_helper_class_sha256[owner],
                    "R181_HELPER_CLASS_SHA256_NOT_MATCHED")
        parsed=parse_class(data)
        profile=profile_class_field_accesses(data)
        require(parsed.name==owner and profile["internal_name"]==owner,
                "R181_HELPER_INTERNAL_OWNER_MISMATCH")
        calls=sorted({
            (method["name"],method["descriptor"],
             call["operation"],call["name"],call["descriptor"])
            for method in packet_profile["methods"]
            for call in method["method_invocations"]
            if call["owner"]==owner
        })
        field_uses=sorted({
            (method["name"],method["descriptor"],
             access["operation"],access["name"],access["descriptor"])
            for method in packet_profile["methods"]
            for access in method["field_accesses"]
            if access["owner"]==owner
        })
        descriptor_mark="L"+owner+";"
        descriptor_refs=sorted({
            (kind,name,descriptor)
            for kind,values in (("packet_method",packet_profile["methods"]),
                                ("packet_field",packet_profile["fields"]))
            for x in values
            for name,descriptor in [(x["name"],x["descriptor"])]
            if descriptor_mark in descriptor
        })
        defined_methods={(m["name"],m["descriptor"])
                         for m in profile["methods"]}
        defined_fields={(f["name"],f["descriptor"])
                        for f in profile["fields"]}
        direct_call_declared=sum(
            (name,desc) in defined_methods
            for _,_,_,name,desc in calls)
        direct_field_declared=sum(
            (name,desc) in defined_fields
            for _,_,_,name,desc in field_uses)
        path="recovered-source/v309/src/"+owner+".java"
        source_present=(path in sources) if have_source else None
        detail={
            "owner":owner,"class_sha256":class_sha,
            "super_name":parsed.super_name,
            "interfaces":parsed.interfaces,
            "fields":sorted((f["name"],f["descriptor"],f["access"])
                            for f in parsed.fields),
            "methods":sorted((m["name"],m["descriptor"],m["access"],
                              m["code_length"]) for m in parsed.methods),
            "packet_invocations":calls,
            "packet_field_accesses":field_uses,
            "packet_type_descriptors":descriptor_refs,
            "candidate_java_path":path if source_present else None,
        }
        all_details.append(detail)
        public_rows.append({
            "owner":owner,
            "original_class_sha256":class_sha,
            "classfile_major":parsed.major,
            "declared_fields":len(parsed.fields),
            "declared_methods_including_initializers":len(parsed.methods),
            "original_jvm_instructions":sum(
                len(x["instructions"]) for x in profile["methods"]),
            "distinct_packet_method_calls":len(calls),
            "packet_calls_to_directly_declared_members":direct_call_declared,
            "distinct_packet_field_accesses":len(field_uses),
            "packet_fields_directly_declared":direct_field_declared,
            "packet_signature_type_references":len(descriptor_refs),
            "candidate_source_path_present_unverified":source_present,
            "full_original_helper_java_recovered":False,
        })
    require(sha_file(original_jar)==original_sha256,
            "R181_ORIGINAL_ARCHIVE_CHANGED_DURING_READ")
    if have_source:
        require(sha_file(private_source_candidate_zip)==
                candidate_source_sha256,
                "R181_CANDIDATE_SOURCE_CHANGED_DURING_READ")
    report={
        "schema_version":1,
        "kind":"v309_original_packet_four_helper_abi_frontier_r181",
        "original_client_sha256":original_sha256,
        "original_packet_class_sha256":packet_class_sha256,
        "four_original_helper_classes_present":True,
        "helper_class_sha256_separately_pinned":
            expected_helper_class_sha256 is not None,
        "source_candidate_checked":have_source,
        "helpers":public_rows,
        "private_member_worklist_sha256":_digest_json(all_details),
        "original_helper_method_bodies_reconstructed_by_this_audit":0,
        "helper_java_source_equivalence_verified":False,
        "complete_runtime_or_reflection_dependency_closure":False,
        "full_v309_client_compilation_proven":False,
        "original_game_code_executed":False,
    }
    if include_private_names:
        report["private_original_helper_member_worklist"]=all_details
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_v309_jar")
    p.add_argument("fresh_private_report_json")
    p.add_argument("--original-sha256",default=CANONICAL_V309)
    p.add_argument("--source-candidate-zip")
    p.add_argument("--source-sha256")
    p.add_argument("--private-names",action="store_true")
    a=p.parse_args(argv)
    out=Path(a.fresh_private_report_json)
    try:
        require(not out.exists() and not out.is_symlink()
                and out.parent.is_dir() and not out.parent.is_symlink(),
                "R181_FRESH_PRIVATE_OUTPUT_REQUIRED")
        report=audit_packet_helper_frontier(
            a.private_original_v309_jar,
            original_sha256=a.original_sha256,
            private_source_candidate_zip=a.source_candidate_zip,
            candidate_source_sha256=a.source_sha256,
            include_private_names=a.private_names)
        out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",
                       encoding="utf-8")
        print(json.dumps({k:v for k,v in report.items()
                          if k!="private_original_helper_member_worklist"},
                         sort_keys=True))
    except (OSError,ValueError) as exc:
        p.error("R181_PRIVATE_HELPER_FRONTIER_REJECTED: "+str(exc))


if __name__=="__main__":
    main()
