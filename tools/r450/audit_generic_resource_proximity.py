#!/usr/bin/env python3
"""R450 isolated R421 generic signature / resource-API proximity census.

Requires SHA-pinned original v309 JAR and the exact isolated reconstructed
R421 sources/classes/dependencies through R449/R446. The default is read-only
and prints aggregate counts only. Detailed class/resource names require
explicit NEW owner-private TEMP quarantine output. Never compiles, launches
client, reads user history, changes deletion journals or approves a release.
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
from tools.r450 import classfile_signature_resource as binary

SCHEMA = "SpawnPK-R450-generic-resource-proximity-UNAPPROVED-v1"
PREFIX = "SpawnPK-R450-Private-Generic-Resource-"
NAME = "R450-UNAPPROVED-GENERIC-RESOURCE-WORKLIST.json"
MAX_TOTAL_BYTES = 700 * 1024 * 1024
MAX_METADATA_REFS = 250000
MAX_API_CALLS = 50000
MAX_PROXIMITY_SITES = 50000
MAX_PRIVATE_REPORT_BYTES = 5 * 1024 * 1024


class Refused(RuntimeError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise Refused(code)


def observed_metadata(observed: dict) -> tuple[
        dict[str, set[str]], dict[str, set[str]],
        dict[str, set[str]], dict[str, list[tuple[str, str]]], int]:
    """Read bounded compiled class bytes, hash-check and parse pure metadata."""
    _, _, root, _, _ = r446.roots()
    need(scanner.directory(root), "R450_ORIGINAL_COMPILED_ROOT_MISSING")
    class_refs: dict[str, set[str]] = {}
    descriptor_refs: dict[str, set[str]] = {}
    signatures: dict[str, set[str]] = {}
    resource_sites: dict[str, list[tuple[str, str]]] = {}
    total = 0
    refs = 0
    calls = 0
    sites = 0
    for class_name, fingerprint in sorted(observed["class_inventory"].items()):
        r447.zip_path(class_name)
        need(class_name.endswith(".class"), "R450_BAD_COMPILED_MEMBER_NAME")
        raw = scanner.read_bounded_regular(
            root.joinpath(*class_name.split("/")), r448.MAX_CLASS_BYTES,
            "R450_COMPILED_CLASS_MEMBER_OVERSIZE")
        need(raw is not None and sha256(raw).hexdigest() == fingerprint,
             "R450_COMPILED_INPUT_CHANGED_OR_UNSAFE")
        total += len(raw)
        need(total <= MAX_TOTAL_BYTES, "R450_TOTAL_CLASS_BYTES_EXCEEDED")
        # R449 validates fields/methods and CP structure. R450 additionally
        # parses Signature attributes and method Code for API proximity.
        old, described, _possible = r449.class_metadata(raw)
        generic, nearby, resource_calls = binary.classfile_evidence(
            raw, r449.resource_literal)
        class_refs[class_name] = old
        descriptor_refs[class_name] = described
        signatures[class_name] = generic
        resource_sites[class_name] = nearby
        refs += len(old) + len(described) + len(generic)
        calls += resource_calls
        sites += len(nearby)
        need(refs <= MAX_METADATA_REFS, "R450_METADATA_REFERENCE_BUDGET")
        need(calls <= MAX_API_CALLS, "R450_RESOURCE_API_CALL_BUDGET")
        need(sites <= MAX_PROXIMITY_SITES,
             "R450_RESOURCE_PROXIMITY_BUDGET")
    return class_refs, descriptor_refs, signatures, resource_sites, calls


def analyze(
        class_refs: dict[str, set[str]],
        descriptor_refs: dict[str, set[str]],
        generic_refs: dict[str, set[str]],
        resource_sites: dict[str, list[tuple[str, str]]],
        resource_api_calls: int,
        original_classes: set[str],
        preferred_classes: set[str],
        alternate_classes: set[str],
        original_resources: set[str],
) -> tuple[dict, dict]:
    """Count new generic references beyond R449 and resource-call proximity."""
    need(class_refs.keys() == descriptor_refs.keys() ==
         generic_refs.keys() == resource_sites.keys(),
         "R450_GRAPH_KEYSET_MISMATCH")
    rebuilt = set(class_refs)
    known = (set().union(*class_refs.values(), *descriptor_refs.values())
             if rebuilt else set())
    generics = set().union(*generic_refs.values()) if rebuilt else set()
    newly_found = generics - known
    nonplatform = {
        x for x in newly_found if not x.startswith(r388.PLATFORM_ROOTS)
    }
    unresolved = nonplatform - (rebuilt | preferred_classes)
    previous_unresolved = {
        x for x in known if not x.startswith(r388.PLATFORM_ROOTS)
        and x not in (rebuilt | preferred_classes)
    }
    origins: dict[str, set[str]] = defaultdict(set)
    for src, refs in generic_refs.items():
        for item in refs & unresolved:
            origins[item].add(src)

    resource_users: dict[str, set[str]] = defaultdict(set)
    nearby_sites = 0
    for source, sites in resource_sites.items():
        for method, name in sites:
            resource_users[name].add(source + "#" + method)
            nearby_sites += 1
    near = set(resource_users)
    private = {
        "new_unresolved_generic_type_names": [
            {
                "class_name": name,
                "referencing_reconstructed_class_names": sorted(origins[name]),
                "referencer_count": len(origins[name]),
                "present_in_original_v309": name in original_classes,
                "available_in_alternate_dependency": name in alternate_classes,
                "runtime_linkage_verified": False,
            }
            for name in sorted(unresolved,
                               key=lambda value: (-len(origins[value]), value))
        ],
        "method_local_string_resource_api_proximity_candidates": [
            {
                "resource_name": name,
                "potential_referencing_methods": sorted(resource_users[name]),
                "present_in_original_resource_archive": name in original_resources,
                "resource_load_dataflow_verified": False,
            }
            for name in sorted(near)
        ],
        "complete_generic_metadata_coverage": False,
        "dynamic_resource_names_covered": False,
        "resource_load_dataflow_verified": False,
        "historical_R421_reference_approved": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    summary = {
        "parsed_reconstructed_classfiles": len(rebuilt),
        "unique_generic_signature_class_targets": len(generics),
        "new_generic_targets_absent_from_R449_class_and_descriptors":
            len(newly_found),
        "new_nonplatform_generic_class_targets": len(nonplatform),
        "new_unresolved_generic_class_targets": len(unresolved),
        "new_unresolved_generic_targets_present_in_original_v309":
            len(unresolved & original_classes),
        "new_unresolved_generic_targets_absent_from_original_v309":
            len(unresolved - original_classes),
        "new_unresolved_generic_targets_in_alternate_dependency":
            len(unresolved & alternate_classes),
        "prior_unresolved_class_or_descriptor_targets":
            len(previous_unresolved),
        "combined_unresolved_class_and_generic_targets":
            len(previous_unresolved | unresolved),
        "known_resource_api_invocations_in_rebuilt_bytecode":
            resource_api_calls,
        "resource_string_api_proximity_occurrences": nearby_sites,
        "unique_resource_strings_near_resource_API_calls": len(near),
        "nearby_resource_strings_named_in_original_archive":
            len(near & original_resources),
        "nearby_resource_strings_absent_from_original_archive":
            len(near - original_resources),
        "bytecode_proximity_not_argument_dataflow": True,
        "generic_annotations_and_kotlin_metadata_fully_parsed": False,
        "resource_loads_proven": False,
        "runtime_linkage_proven": False,
        "actual_client_assets_packaged": False,
    }
    return summary, private


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    previous, _ = r449.inspect(original, companion)
    current, _ = r446.observe()
    old, desc, generic, candidates, calls = observed_metadata(current)
    original_bytes = r447.read_pinned_original(original)
    original_classes, original_resources, _ = r447.archive(
        original_bytes, "original")
    _, _, _, primary, alternate = r446.roots()
    primary_bytes = scanner.read_bounded_regular(
        primary, r447.MAX_DEPENDENCY_BYTES, "R450_PRIMARY_JAR_TOO_LARGE")
    alternate_bytes = scanner.read_bounded_regular(
        alternate, r447.MAX_DEPENDENCY_BYTES, "R450_ALTERNATE_JAR_TOO_LARGE")
    need(primary_bytes is not None and alternate_bytes is not None,
         "R450_DEPENDENCY_MISSING_OR_UNSAFE")
    need(sha256(primary_bytes).hexdigest() ==
         current["dependency_sha256"]["R239_filtered.jar"]
         and sha256(alternate_bytes).hexdigest() ==
         current["dependency_sha256"]["R218.jar"],
         "R450_DEPENDENCIES_CHANGED")
    primary_names, _, _ = r447.archive(primary_bytes, "dependency")
    alternate_names, _, _ = r447.archive(alternate_bytes, "dependency")
    summary, private = analyze(
        old, desc, generic, candidates, calls, original_classes,
        primary_names, alternate_names, original_resources)

    # Independent fresh current-state check, never historical approval.
    again, _ = r446.observe()
    need(again == current, "R450_INPUT_CHANGED_DURING_SCAN")
    need(sha256(r447.read_pinned_original(original)).hexdigest()
         == r447.ORIGINAL_SHA, "R450_ORIGINAL_CHANGED_DURING_SCAN")
    report = {
        "status": "R450_GENERIC_AND_RESOURCE_CALL_PROXIMITY_UNAPPROVED",
        "pinned_original_v309_verified": previous["exact_original_v309_sha_matched"],
        "original_v309_class_count": previous["original_class_files"],
        "original_v309_resource_count": previous["original_resource_files"],
        "isolated_r421_java_sources": previous["rebuilt_java_sources"],
        "isolated_r421_classfiles": previous["rebuilt_compiled_class_files"],
        "resource_companion_checked": companion is not None,
        "private_client_executed": False,
        "full_deobfuscated_source_verified": False,
        "production_client_integrated": False,
        "historical_R421_custody_approved": False,
        "compile_authorized": False,
        "release_authorized": False,
        "merge_authorized": False,
        **summary,
    }
    if companion is not None:
        for key in ("companion_resource_byte_matches",
                    "companion_resource_missing",
                    "companion_resource_mismatches"):
            report[key] = previous[key]
    detail = {
        "schema": SCHEMA,
        "status": "UNAPPROVED_CURRENT_STATIC_RECONSTRUCTION_LEADS",
        "owner_private_details": private,
        "historical_R421_custody_approved": False,
        "runtime_tested": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return report, detail


def save_private(detail: dict) -> str:
    temp, *_ = r446.roots()
    need(scanner.directory(temp), "R450_OWNER_TEMP_UNAVAILABLE")
    content = (json.dumps(detail, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":")) + "\n").encode("ascii")
    need(0 < len(content) <= MAX_PRIVATE_REPORT_BYTES,
         "R450_PRIVATE_REPORT_TOO_LARGE")
    destination = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(temp)))
    need(destination.parent == temp and scanner.directory(destination),
         "R450_PRIVATE_REPORT_ROOT_INVALID")
    output = destination / NAME
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(output, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return destination.name


def run(original: Path, companion: Path | None = None,
        save: bool = False) -> dict:
    report, detail = inspect(original, companion)
    if save:
        second_report, second_detail = inspect(original, companion)
        need(report == second_report and detail == second_detail,
             "R450_INPUT_CHANGED_BEFORE_PRIVATE_REPORT")
        report["private_quarantine_directory_name"] = save_private(detail)
        report["private_worklist_saved"] = True
    else:
        report["private_worklist_saved"] = False
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-v309-jar", type=Path, required=True)
    parser.add_argument("--resource-companion-root", type=Path)
    parser.add_argument("--save-private-unapproved-worklist", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run(
            args.original_v309_jar, args.resource_companion_root,
            args.save_private_unapproved_worklist), sort_keys=True))
        return 0
    except (Refused, binary.Refused, r449.Refused, r448.Refused, r447.Refused,
            r446.Refused, r440.Refused, scanner.Refused, OSError,
            ValueError, UnicodeError, TypeError) as error:
        reason = str(error) if isinstance(error, (
            Refused, binary.Refused, r449.Refused, r448.Refused, r447.Refused,
            r446.Refused, r440.Refused, scanner.Refused)) else (
            "R450_OWNER_PRIVATE_METADATA_SCAN_REFUSED")
        print(json.dumps({
            "status": "R450_GENERIC_RESOURCE_AUDIT_REFUSED",
            "reason": reason[:120],
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
