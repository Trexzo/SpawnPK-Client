#!/usr/bin/env python3
"""R453 offline JVM member-signature linkage worklist for rebuilt v309.

Compares CONSTANT_{Field,Method,InterfaceMethod}ref owners/name/descriptors
in exact owner-isolated R421 Java11 classfiles to *directly declared*
members in the same reconstructed class tree. Preferred/alternate dependency
JARs are inventoried by class path only, not parsed for member declarations.

A missing direct declaration can be inherited; an owner on the classpath
can have binary-incompatible members. This is advisory, not JVM resolution,
real classloading, compilation, source parity, or runtime proof.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r388 import audit_offline_classpath as r388
from tools.r440 import read_only_private_acceptance_preflight as r440
from tools.r444 import scan_owner_r421_artifacts as scanner
from tools.r446 import observe_owner_private_inventory as r446
from tools.r447 import audit_original_class_asset_coverage as r447
from tools.r448 import audit_rebuilt_class_linkage as r448
from tools.r449 import audit_descriptor_resource_gaps as r449
from tools.r450 import audit_generic_resource_proximity as r450
from tools.r451 import audit_resource_operand_arguments as r451
from tools.r452 import audit_forward_branch_resource as r452
from tools.r453 import classfile_member_reference as parser

SCHEMA = "SpawnPK-R453-member-signature-worklist-UNAPPROVED-v1"
PREFIX = "SpawnPK-R453-Private-Member-"
NAME = "R453-UNAPPROVED-MEMBER-REFERENCE-WORKLIST.json"
MAX_CLASS_TOTAL = 700 * 1024 * 1024
MAX_REFERENCES = 220000
MAX_REPORT_BYTES = 5 * 1024 * 1024


class Refused(RuntimeError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise Refused(code)


def observed_members(observed: dict) -> dict[str, parser.ClassMembers]:
    """Independently read each R421 class with exact per-file SHA guards."""
    _, _, class_root, _, _ = r446.roots()
    need(scanner.directory(class_root), "R453_R421_CLASSES_ROOT_INVALID")
    files = observed["class_inventory"]
    need(type(files) is dict and files, "R453_EMPTY_R421_CLASS_MAP")
    result = {}
    total = 0
    refs = 0
    for path, expected_sha in sorted(files.items()):
        r447.zip_path(path)
        need(path.endswith(".class"), "R453_NON_CLASS_IN_R421_MAP")
        data = scanner.read_bounded_regular(
            class_root.joinpath(*path.split("/")), parser.MAX_CLASS_BYTES,
            "R453_CLASS_MEMBER_OVER_BUDGET")
        need(data is not None and sha256(data).hexdigest() == expected_sha,
             "R453_R421_CLASS_CHANGED_OR_UNSAFE")
        total += len(data)
        need(total <= MAX_CLASS_TOTAL, "R453_CLASS_TREE_BYTE_BUDGET")
        record = parser.parse_class(data)
        need(record.class_name == path,
             "R453_R421_CLASS_INTERNAL_NAME_AND_PATH_MISMATCH")
        refs += len(record.references)
        need(refs <= MAX_REFERENCES, "R453_MEMBER_REFERENCE_COUNT_BUDGET")
        result[path] = record
    return result


def classify(
    records: dict[str, parser.ClassMembers],
    preferred: set[str],
    alternate: set[str],
    original: set[str],
) -> tuple[dict, dict]:
    """Only direct declaration checks; inheritance remains UNKNOWN."""
    rebuilt = set(records)
    preferred_runtime = rebuilt | preferred
    all_refs = defaultdict(set)
    for referencer, record in records.items():
        for target in record.references:
            all_refs[target].add(referencer)

    labels = {}
    for target in all_refs:
        owner = target.owner
        if owner.startswith(r388.PLATFORM_ROOTS):
            kind = "platform_owner_unchecked"
        elif owner in records:
            declared = (
                records[owner].declared_fields if target.kind == "field"
                else records[owner].declared_methods
            )
            if (target.name, target.descriptor) in declared:
                kind = "rebuilt_owner_declares_exact_member"
            else:
                kind = "rebuilt_owner_member_not_directly_declared"
        elif owner in preferred:
            kind = "preferred_dependency_owner_member_not_inspected"
        else:
            kind = "missing_preferred_classpath_owner"
        labels[target] = kind

    unique = set(labels)
    counts = {
        kind: sum(1 for target in unique if labels[target] == kind)
        for kind in (
            "platform_owner_unchecked",
            "rebuilt_owner_declares_exact_member",
            "rebuilt_owner_member_not_directly_declared",
            "preferred_dependency_owner_member_not_inspected",
            "missing_preferred_classpath_owner",
        )
    }
    missing = {
        member for member in unique
        if labels[member] == "missing_preferred_classpath_owner"
    }
    not_direct = {
        member for member in unique
        if labels[member] == "rebuilt_owner_member_not_directly_declared"
    }
    owner_original = {member for member in missing
                      if member.owner in original}
    owner_alternate = {member for member in missing
                       if member.owner in alternate}
    count_sources = sum(len(sources) for sources in all_refs.values())
    report = {
        "rebuilt_classfiles_with_member_metadata": len(records),
        "unique_constant_pool_member_references": len(unique),
        "rebuilt_class_to_member_reference_pairs": count_sources,
        "field_reference_count": sum(m.kind == "field" for m in unique),
        "class_method_reference_count": sum(
            m.kind == "method" for m in unique),
        "interface_method_reference_count": sum(
            m.kind == "interface_method" for m in unique),
        "platform_owner_member_references_not_checked":
            counts["platform_owner_unchecked"],
        "rebuilt_class_owner_exact_member_directly_declared":
            counts["rebuilt_owner_declares_exact_member"],
        "rebuilt_class_owner_member_not_directly_declared":
            counts["rebuilt_owner_member_not_directly_declared"],
        "preferred_dependency_owner_member_declaration_not_inspected":
            counts["preferred_dependency_owner_member_not_inspected"],
        "missing_preferred_classpath_member_owners":
            counts["missing_preferred_classpath_owner"],
        "missing_preferred_classpath_owner_names_in_original_v309":
            len({x.owner for x in owner_original}),
        "missing_preferred_classpath_owner_names_in_alternate_dependency":
            len({x.owner for x in owner_alternate}),
        "unique_missing_preferred_classpath_member_owner_names":
            len({x.owner for x in missing}),
        "member_references_with_owner_present_but_no_direct_declaration":
            len(not_direct),
        "inherited_member_resolution_performed": False,
        "preferred_dependency_member_bytecode_inspected": False,
        "jvm_binary_linkage_verified": False,
        "actual_method_invocation_or_field_access_proven": False,
        "all_resources_packaged_verified": False,
    }

    def entry(member: parser.Member) -> dict:
        return {
            "owner_class_path": member.owner,
            "member_name": member.name,
            "member_descriptor": member.descriptor,
            "reference_kind": member.kind,
            "referencing_rebuilt_class_paths": sorted(all_refs[member]),
            "referencing_rebuilt_class_count": len(all_refs[member]),
            "owner_present_in_original_v309": member.owner in original,
            "owner_present_in_alternate_dependency": member.owner in alternate,
            "owner_on_preferred_classpath": member.owner in preferred_runtime,
            "direct_declaration_absence_may_be_inheritance": (
                labels[member] ==
                "rebuilt_owner_member_not_directly_declared"),
            "runtime_binary_resolution_proven": False,
        }

    def rank(item: parser.Member) -> tuple:
        return (-len(all_refs[item]), item.owner, item.name,
                item.descriptor, item.kind)

    private = {
        "missing_classpath_member_owner_references": [
            entry(x) for x in sorted(missing, key=rank)
        ],
        "rebuilt_owner_member_not_directly_declared": [
            entry(x) for x in sorted(not_direct, key=rank)
        ],
        "preferred_dependency_owner_member_declarations_unverified":
            sum(labels[x] == "preferred_dependency_owner_member_not_inspected"
                for x in unique),
        "no_inheritance_resolution_claimed": True,
        "historical_full_R421_inventory_approved": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return report, private


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    # Inherited pinned SHA-verified v309 original, source/class/dependency
    # R421 current inventory gates; no owner-private source is exported.
    previous, _ = r452.inspect(original, companion)
    observed, _ = r446.observe()
    records = observed_members(observed)
    original_bytes = r447.read_pinned_original(original)
    original_classes, _original_resources, _ = r447.archive(
        original_bytes, "original")
    _, _, _, preferred_jar, alternate_jar = r446.roots()
    dep_a = scanner.read_bounded_regular(
        preferred_jar, r447.MAX_DEPENDENCY_BYTES,
        "R453_PREFERRED_DEPENDENCY_TOO_LARGE")
    dep_b = scanner.read_bounded_regular(
        alternate_jar, r447.MAX_DEPENDENCY_BYTES,
        "R453_ALTERNATE_DEPENDENCY_TOO_LARGE")
    need(dep_a is not None and dep_b is not None,
         "R453_DEPENDENCIES_MISSING_OR_UNSAFE")
    need(sha256(dep_a).hexdigest() ==
         observed["dependency_sha256"]["R239_filtered.jar"]
         and sha256(dep_b).hexdigest() ==
         observed["dependency_sha256"]["R218.jar"],
         "R453_DEPENDENCY_CHANGED_DURING_AUDIT")
    preferred, _, _ = r447.archive(dep_a, "dependency")
    alternate, _, _ = r447.archive(dep_b, "dependency")
    summary, private = classify(
        records, preferred, alternate, original_classes)
    fresh, _ = r446.observe()
    need(fresh == observed, "R453_R421_INPUTS_CHANGED")
    need(sha256(r447.read_pinned_original(original)).hexdigest()
         == r447.ORIGINAL_SHA, "R453_ORIGINAL_CHANGED_DURING_AUDIT")
    result = {
        "status": "R453_R421_MEMBER_LINKAGE_INVENTORY_UNAPPROVED",
        "original_v309_exact_sha_matched": previous["original_v309_sha_matched"],
        "original_v309_class_count": previous["original_class_count"],
        "original_v309_resource_count": previous["original_resource_count"],
        "isolated_r421_java_sources": previous["R421_java_sources"],
        "isolated_r421_compiled_classfiles": previous["R421_compiled_classes"],
        "resource_companion_checked": companion is not None,
        "client_started": False,
        "private_client_code_executed": False,
        "original_v309_behavioural_parity_proven": False,
        "historical_R421_custody_approved": False,
        "complete_readable_source_proven": False,
        "compile_authorized": False,
        "release_authorized": False,
        "merge_authorized": False,
        **summary,
    }
    if companion is not None:
        for key in ("companion_resource_byte_matches",
                    "companion_resource_missing",
                    "companion_resource_mismatches"):
            result[key] = previous[key]
    detail = {
        "schema": SCHEMA,
        "status": "PRIVATE_MEMBER_OWNER_WORKLIST_UNAPPROVED",
        "owner_only_details": private,
        "client_execution_proven": False,
        "historical_R421_custody_approved": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return result, detail


def save_private(detail: dict) -> str:
    temporary, *_ = r446.roots()
    need(scanner.directory(temporary), "R453_OWNER_TEMP_UNAVAILABLE")
    encoded = (json.dumps(detail, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":")) + "\n").encode("ascii")
    need(0 < len(encoded) <= MAX_REPORT_BYTES,
         "R453_PRIVATE_REPORT_TOO_LARGE")
    folder = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(temporary)))
    need(folder.parent == temporary and scanner.directory(folder),
         "R453_PRIVATE_REPORT_LOCATION_INVALID")
    dest = folder / NAME
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0) |
                 getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(encoded)
        output.flush()
        os.fsync(output.fileno())
    return folder.name


def run(original: Path, companion: Path | None = None,
        save: bool = False) -> dict:
    baseline = r446.observe()[0] if save else None
    report, detail = inspect(original, companion)
    if save:
        repeated_report, repeated_detail = inspect(original, companion)
        need(report == repeated_report and detail == repeated_detail
             and baseline == r446.observe()[0],
             "R453_FULL_INVENTORY_CHANGED_BEFORE_PRIVATE_OUTPUT")
        report["private_output_directory_name"] = save_private(detail)
        report["private_worklist_saved"] = True
    else:
        report["private_worklist_saved"] = False
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-v309-jar", type=Path, required=True)
    p.add_argument("--resource-companion-root", type=Path)
    p.add_argument("--save-private-unapproved-worklist", action="store_true")
    args = p.parse_args(argv)
    try:
        print(json.dumps(run(
            args.original_v309_jar, args.resource_companion_root,
            args.save_private_unapproved_worklist), sort_keys=True))
        return 0
    except (Refused, parser.Refused, r452.Refused, r451.Refused,
            r450.Refused, r449.Refused, r448.Refused, r447.Refused,
            r446.Refused, r440.Refused, scanner.Refused, OSError,
            TypeError, ValueError, UnicodeError) as error:
        if isinstance(error, (Refused, parser.Refused, r452.Refused,
                              r451.Refused, r450.Refused, r449.Refused,
                              r448.Refused, r447.Refused, r446.Refused,
                              r440.Refused, scanner.Refused)):
            reason = str(error)[:120]
        else:
            reason = "R453_OWNER_PRIVATE_MEMBER_ANALYSIS_REFUSED"
        print(json.dumps({
            "status": "R453_MEMBER_REFERENCE_AUDIT_REFUSED",
            "reason": reason,
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
