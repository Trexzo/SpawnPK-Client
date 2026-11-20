#!/usr/bin/env python3
"""R451 offline SHA-pinned v309/R421 resource API literal-argument audit.

Only a narrow, conservative straight-line subset of Java 11 method Code is
symbolically interpreted to associate an LDC String with the actual argument
operand at an allowlisted Class/ClassLoader resource call. Unsupported flow
is *excluded*, not inferred. This does NOT execute a client, prove dynamic
loading, inspect private history, or approve release/build/provenance.
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

from tools.r440 import read_only_private_acceptance_preflight as r440
from tools.r444 import scan_owner_r421_artifacts as scanner
from tools.r446 import observe_owner_private_inventory as r446
from tools.r447 import audit_original_class_asset_coverage as r447
from tools.r448 import audit_rebuilt_class_linkage as r448
from tools.r449 import audit_descriptor_resource_gaps as r449
from tools.r450 import audit_generic_resource_proximity as r450
from tools.r450 import classfile_signature_resource as signature
from tools.r451 import straightline_resource_operands as stacktrace

SCHEMA = "SpawnPK-R451-static-straightline-resource-arguments-UNAPPROVED-v1"
PREFIX = "SpawnPK-R451-Private-StackArguments-"
NAME = "R451-UNAPPROVED-RESOURCE-ARGUMENT-WORKLIST.json"
MAX_CLASS_TOTAL_BYTES = 700 * 1024 * 1024
MAX_MATCHED_SITES = 50000
MAX_PROXIMITY_SITES = 50000
MAX_PRIVATE_REPORT_BYTES = 5 * 1024 * 1024


class Refused(RuntimeError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise Refused(code)


def owner_metadata(observed: dict) -> tuple[
        dict[str, list[tuple[str, str]]],
        dict[str, list[tuple[str, str]]],
        dict[str, dict[str, int]],
]:
    """Strict per-file SHA recheck, static Code parse, no class execution."""
    _, _, root, _, _ = r446.roots()
    need(scanner.directory(root), "R451_COMPILED_ROOT_UNAVAILABLE")
    attributed: dict[str, list[tuple[str, str]]] = {}
    proximity: dict[str, list[tuple[str, str]]] = {}
    stats: dict[str, dict[str, int]] = {}
    total = 0
    seen_matches = 0
    seen_nearby = 0
    for name, pinned_current_sha in sorted(observed["class_inventory"].items()):
        r447.zip_path(name)
        need(name.endswith(".class"), "R451_INVALID_R421_CLASS_MEMBER")
        raw = scanner.read_bounded_regular(
            root.joinpath(*name.split("/")), r448.MAX_CLASS_BYTES,
            "R451_CLASS_FILE_TOO_LARGE")
        need(raw is not None and sha256(raw).hexdigest() == pinned_current_sha,
             "R451_R421_CLASS_CHANGED_OR_UNSAFE")
        total += len(raw)
        need(total <= MAX_CLASS_TOTAL_BYTES,
             "R451_TOTAL_R421_CLASS_BYTES_EXCEEDED")
        collector = stacktrace.Collector()
        _generic_refs, candidate_sites, total_resource_calls = (
            signature.classfile_evidence(
                raw, r449.resource_literal, code_observer=collector))
        attributed[name] = collector.matched_arguments
        proximity[name] = candidate_sites
        stats[name] = {
            "methods_observed": collector.methods_observed,
            "methods_analyzed": collector.methods_straightline_analyzed,
            "methods_skipped": collector.methods_unsupported_or_control_flow,
            "resource_api_calls_in_class": total_resource_calls,
            "resource_api_calls_in_modeled_methods":
                collector.resource_calls_analyzed,
            "literal_arguments_in_modeled_methods":
                len(collector.matched_arguments),
        }
        need(collector.resource_calls_analyzed <= total_resource_calls,
             "R451_STACK_MODEL_CALL_COUNT_INCONSISTENT")
        seen_matches += len(collector.matched_arguments)
        seen_nearby += len(candidate_sites)
        need(seen_matches <= MAX_MATCHED_SITES,
             "R451_MATCHED_ARGUMENT_BUDGET_EXCEEDED")
        need(seen_nearby <= MAX_PROXIMITY_SITES,
             "R451_PROXIMITY_BUDGET_EXCEEDED")
    return attributed, proximity, stats


def compare(
        attributed: dict[str, list[tuple[str, str]]],
        nearby: dict[str, list[tuple[str, str]]],
        stats: dict[str, dict[str, int]],
        original_resources: set[str],
) -> tuple[dict, dict]:
    need(attributed.keys() == nearby.keys() == stats.keys(),
         "R451_RESOURCE_GRAPH_KEYS_MISMATCH")
    methods = sum(x["methods_observed"] for x in stats.values())
    analyzed = sum(x["methods_analyzed"] for x in stats.values())
    skipped = sum(x["methods_skipped"] for x in stats.values())
    total_calls = sum(x["resource_api_calls_in_class"] for x in stats.values())
    tracked_calls = sum(
        x["resource_api_calls_in_modeled_methods"] for x in stats.values())
    need(analyzed + skipped == methods and tracked_calls <= total_calls,
         "R451_METHOD_AND_CALL_COUNTS_INCONSISTENT")
    all_confirmed: set[tuple[str, str, str]] = set()
    all_nearby: set[tuple[str, str, str]] = set()
    observations = 0
    for cls, occurrences in attributed.items():
        for method, resource in occurrences:
            all_confirmed.add((cls, method, resource))
            observations += 1
    for cls, occurrences in nearby.items():
        for method, resource in occurrences:
            all_nearby.add((cls, method, resource))
    resolved = {name for _, _, name in all_confirmed}
    near_names = {name for _, _, name in all_nearby}
    false_proximity = all_nearby - all_confirmed

    use_sites: dict[str, set[str]] = defaultdict(set)
    for owner, method, resource in all_confirmed:
        use_sites[resource].add(owner + "#" + method)

    summary = {
        "rebuilt_java11_classfiles_examined": len(attributed),
        "bytecode_methods_inspected": methods,
        "straightline_methods_fully_modeled": analyzed,
        "methods_skipped_due_to_uncertain_bytecode_or_control_flow": skipped,
        "allowlisted_resource_api_calls_total": total_calls,
        "allowlisted_resource_api_calls_in_fully_modeled_methods": tracked_calls,
        "allowlisted_resource_api_calls_not_fully_modeled":
            total_calls - tracked_calls,
        "literal_argument_occurrences_in_modeled_resource_calls": observations,
        "unique_literal_resource_arguments_modeled": len(resolved),
        "modeled_literal_resource_argument_names_in_original":
            len(resolved & original_resources),
        "modeled_literal_resource_argument_names_absent_from_original":
            len(resolved - original_resources),
        "prior_R450_unique_method_proximity_names": len(near_names),
        "proximity_site_pairs_not_attributed_as_literal_arguments":
            len(false_proximity),
        "model_is_straightline_only": True,
        "branch_exception_and_unsupported_methods_excluded": True,
        "literal_reaches_actual_call_at_runtime_proven": False,
        "resource_successfully_loaded_proven": False,
        "classloader_runtime_resolution_proven": False,
        "complete_resource_manifest_proven": False,
    }
    private = {
        "modeled_static_literal_call_arguments": [
            {
                "possible_resource_path": resource,
                "rebuilt_method_referencers": sorted(use_sites[resource]),
                "present_in_exact_original_v309_resource_archive":
                    resource in original_resources,
                "proven_runtime_load": False,
                "operand_symbolically_tracked_only_in_straightline_code": True,
            }
            for resource in sorted(resolved)
        ],
        "R450_proximity_pairs_without_modeled_literal_argument": [
            {
                "class_name": cls,
                "method": method,
                "resource_path": resource,
                "why_not_proven": "not modeled as a literal argument",
            }
            for cls, method, resource in sorted(false_proximity)
        ],
        "total_unmodeled_known_resource_calls": total_calls - tracked_calls,
        "history_or_production_client_accessed": False,
        "historical_R421_reference_custody_approved": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return summary, private


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    previous, _ = r450.inspect(original, companion)
    observed, _ = r446.observe()
    attributed, nearby, stats = owner_metadata(observed)
    original_bytes = r447.read_pinned_original(original)
    _original_classes, original_resources, _ = r447.archive(
        original_bytes, "original")
    counts, private = compare(attributed, nearby, stats, original_resources)
    need(counts["allowlisted_resource_api_calls_total"] ==
         previous["known_resource_api_invocations_in_rebuilt_bytecode"],
         "R451_PRIOR_RESOURCE_CALL_COUNT_DRIFT")
    need(counts["rebuilt_java11_classfiles_examined"] ==
         previous["isolated_r421_classfiles"],
         "R451_R421_REBUILT_CLASS_COUNT_DRIFT")
    fresh, _ = r446.observe()
    need(fresh == observed, "R451_INPUT_CHANGED_DURING_ANALYSIS")
    need(sha256(r447.read_pinned_original(original)).hexdigest() ==
         r447.ORIGINAL_SHA, "R451_ORIGINAL_V309_CHANGED_DURING_ANALYSIS")
    summary = {
        "status": "R451_STRAIGHTLINE_STATIC_RESOURCE_OPERAND_AUDIT_UNAPPROVED",
        "original_v309_exact_sha_matched": previous["pinned_original_v309_verified"],
        "original_v309_classes": previous["original_v309_class_count"],
        "original_v309_resources": previous["original_v309_resource_count"],
        "isolated_r421_java_sources": previous["isolated_r421_java_sources"],
        "isolated_r421_compiled_classes": previous["isolated_r421_classfiles"],
        "optional_resource_companion_checked": companion is not None,
        "private_client_executed": False,
        "bytecode_behavioural_parity_proven": False,
        "full_deobfuscated_source_verified": False,
        "assets_repackaged_or_installed": False,
        "historical_R421_inventory_approved": False,
        "compile_authorized": False,
        "release_authorized": False,
        "merge_authorized": False,
        **counts,
    }
    if companion is not None:
        for key in ("companion_resource_byte_matches",
                    "companion_resource_missing",
                    "companion_resource_mismatches"):
            summary[key] = previous[key]
    details = {
        "schema": SCHEMA,
        "status": "UNAPPROVED_STATIC_STRAIGHTLINE_OPERAND_CANDIDATES",
        "owner_private_resource_argument_worklist": private,
        "historical_R421_inventory_approved": False,
        "runtime_tested": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return summary, details


def write_private(detail: dict) -> str:
    temporary, *_ = r446.roots()
    need(scanner.directory(temporary), "R451_OWNER_TEMP_UNAVAILABLE")
    raw = (json.dumps(detail, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")) + "\n").encode("ascii")
    need(0 < len(raw) <= MAX_PRIVATE_REPORT_BYTES,
         "R451_PRIVATE_WORKLIST_TOO_LARGE")
    folder = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(temporary)))
    need(scanner.directory(folder) and folder.parent == temporary,
         "R451_PRIVATE_REPORT_FOLDER_INVALID")
    destination = folder / NAME
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0) |
                 getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    return folder.name


def run(original: Path, companion: Path | None = None,
        save: bool = False) -> dict:
    # An aggregate result could remain equal even if an unrelated class
    # changes between scans. Capture exact per-member source/class/dependency
    # SHA evidence before the first pass, and require identity afterward.
    baseline = r446.observe()[0] if save else None
    report, details = inspect(original, companion)
    if save:
        after, rechecked = inspect(original, companion)
        need(after == report and rechecked == details,
             "R451_INPUT_CHANGED_BEFORE_PRIVATE_WORKLIST")
        need(r446.observe()[0] == baseline,
             "R451_ORIGINAL_INVENTORY_CHANGED_BETWEEN_PRIVATE_SCANS")
        report["owner_private_report_directory"] = write_private(details)
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
        print(json.dumps(
            run(args.original_v309_jar, args.resource_companion_root,
                args.save_private_unapproved_worklist), sort_keys=True))
        return 0
    except (Refused, stacktrace.Refused, signature.Refused, r450.Refused,
            r449.Refused, r448.Refused, r447.Refused, r446.Refused,
            r440.Refused, scanner.Refused, ValueError, TypeError,
            UnicodeError, OSError) as error:
        if isinstance(error, (
                Refused, stacktrace.Refused, signature.Refused, r450.Refused,
                r449.Refused, r448.Refused, r447.Refused, r446.Refused,
                r440.Refused, scanner.Refused)):
            reason = str(error)[:120]
        else:
            reason = "R451_OWNER_PRIVATE_STACK_AUDIT_REFUSED"
        print(json.dumps({
            "status": "R451_RESOURCE_OPERAND_AUDIT_REFUSED",
            "reason": reason,
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
