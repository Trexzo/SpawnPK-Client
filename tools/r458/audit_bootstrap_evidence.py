#!/usr/bin/env python3
"""R458 owner-only SHA-pinned invokedynamic/condy method-handle worklist.

Read-only extension to R457. Never executes Java or bootstrap methods,
loads the client, modifies player histories, unlocks LootTracker writes,
approves historical R421 provenance or publishes private class names.
"""
from __future__ import annotations

import argparse
from collections import Counter
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
from tools.r453 import audit_member_reference_coverage as r453
from tools.r454 import audit_inherited_member_ancestry as r454
from tools.r455 import audit_dependency_member_access as r455
from tools.r456 import audit_member_opcode_staticness as r456
from tools.r457 import audit_jvm_callsite_constraints as r457
from tools.r458 import bootstrap_callsite_evidence as bootstrap

SCHEMA = "SpawnPK-R458-invokedynamic-bootstrap-UNAPPROVED-v1"
PREFIX = "SpawnPK-R458-Private-Bootstrap-"
NAME = "R458-UNAPPROVED-INVOKEDYNAMIC-BOOTSTRAP.json"
MAX_TOTAL_CLASS_BYTES = 700 * 1024 * 1024
MAX_TOTAL_SITES = 250000
MAX_PRIVATE_BYTES = 5 * 1024 * 1024


class Refused(RuntimeError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def observed_bootstrap(snapshot: dict) -> dict[str, bootstrap.Evidence]:
    _, _, class_root, _, _ = r446.roots()
    need(scanner.directory(class_root), "R458_COMPILED_ROOT_UNSAFE")
    observed = {}
    bytes_seen = 0
    sites_seen = 0
    for path, fingerprint in sorted(snapshot["class_inventory"].items()):
        r447.zip_path(path)
        need(path.endswith(".class"),
             "R458_NON_CLASS_ENTRY_IN_COMPILED_INVENTORY")
        data = scanner.read_bounded_regular(
            class_root.joinpath(*path.split("/")), r448.MAX_CLASS_BYTES,
            "R458_CLASS_FILE_TOO_LARGE")
        need(data is not None and sha256(data).hexdigest() == fingerprint,
             "R458_REBUILT_CLASS_CHANGED_DURING_SCAN")
        bytes_seen += len(data)
        need(bytes_seen <= MAX_TOTAL_CLASS_BYTES,
             "R458_REBUILT_CLASS_TOTAL_BYTES_EXCEEDED")
        record = bootstrap.scan_class(data)
        need(record.class_name == path,
             "R458_REBUILT_CLASS_INTERNAL_NAME_MISMATCH")
        observed[path] = record
        sites_seen += (
            len(record.invokedynamic_sites) +
            len(record.constant_dynamic_load_sites))
        need(sites_seen <= MAX_TOTAL_SITES,
             "R458_TOTAL_DYNAMIC_CODE_SITES_EXCEEDED")
    return observed


def aggregate(
    observed: dict[str, bootstrap.Evidence],
    rebuilt_names: set[str],
    preferred_names: set[str],
    alternate_names: set[str],
    original_names: set[str],
) -> tuple[dict, dict]:
    need(set(observed) == rebuilt_names,
         "R458_REBUILT_INVENTORY_CLASS_KEY_DRIFT")
    counters = Counter()
    bootstrap_owner = Counter()
    argument_owner = Counter()
    private_sites = []

    def where(owner: str) -> str:
        if owner.startswith(r388.PLATFORM_ROOTS):
            return "platform_uninspected"
        if owner in rebuilt_names:
            return "rebuilt_class_name"
        if owner in preferred_names:
            return "preferred_dependency_class_name"
        if owner in alternate_names:
            return "alternate_dependency_only_class_name"
        if owner in original_names:
            return "original_v309_only_class_name"
        return "owner_missing_from_known_static_classpaths"

    def handle_dict(handle: bootstrap.Handle) -> dict:
        return {
            "owner_class": handle.owner,
            "method_or_field_name": handle.name,
            "descriptor": handle.descriptor,
            "method_handle_kind": bootstrap.HANDLE_NAMES[handle.kind],
            "target_member_CP_tag": handle.target_cp_tag,
            "owner_location": where(handle.owner),
            "method_handle_executed_or_linked": False,
        }

    for path, record in sorted(observed.items()):
        for name, value in (
            ("class_method_handle_cp_entries", record.method_handle_entries),
            ("class_method_type_cp_entries", record.method_type_entries),
            ("class_bootstrap_table_entries", record.bootstrap_entries),
            ("class_bootstrap_argument_entries",
             record.bootstrap_argument_entries),
            ("class_bootstrap_condy_argument_entries",
             record.bootstrap_dynamic_arguments),
            ("class_invokedynamic_cp_entries",
             record.constant_pool_invokedynamic),
            ("class_constant_dynamic_cp_entries",
             record.constant_pool_dynamic),
            ("unused_invokedynamic_cp_entries",
             record.unused_invokedynamic_cp_entries),
            ("unused_condy_cp_entries",
             record.unused_dynamic_cp_entries),
            ("unreferenced_bootstrap_table_entries",
             record.unreferenced_bootstrap_entries),
        ):
            counters[name] += value
        for call in (
            *record.invokedynamic_sites,
            *record.constant_dynamic_load_sites,
        ):
            counters[call.nature+"_instruction_sites"] += 1
            location = where(call.bootstrap.owner)
            bootstrap_owner[location] += 1
            counters["bootstrap_method_handle_arguments_at_sites"] += len(
                call.bootstrap_handle_arguments)
            for argument in call.bootstrap_handle_arguments:
                argument_owner[where(argument.owner)] += 1
            if (call.bootstrap.owner.endswith(
                    "/LambdaMetafactory.class")
                    and call.bootstrap.name in ("metafactory", "altMetafactory")):
                counters["lambda_metafactory_named_bootstrap_sites"] += 1
            elif (call.bootstrap.owner.endswith(
                    "/StringConcatFactory.class")):
                counters["string_concat_factory_named_bootstrap_sites"] += 1
            private_sites.append({
                "source_class": path,
                "source_method": call.source_method,
                "bytecode_pc": call.pc,
                "constant_pool_index": call.cp_index,
                "kind": call.nature,
                "dynamic_name": call.name,
                "dynamic_descriptor": call.descriptor,
                "bootstrap_table_index": call.bootstrap_index,
                "bootstrap_method_handle": handle_dict(call.bootstrap),
                "argument_constant_pool_tags": list(call.argument_tags),
                "argument_method_handles": [
                    handle_dict(h) for h in call.bootstrap_handle_arguments
                ],
                "bootstrap_or_dynamic_target_resolved": False,
                "instruction_executed": False,
            })

    summary = {
        "rebuilt_java11_classfiles_scanned": len(observed),
        "invokedynamic_bytecode_sites": counters[
            "invokedynamic_instruction_sites"],
        "constant_dynamic_ldc_bytecode_sites": counters[
            "constant_dynamic_instruction_sites"],
        "unique_invokedynamic_cp_entries_sum":
            counters["class_invokedynamic_cp_entries"],
        "unique_condy_cp_entries_sum":
            counters["class_constant_dynamic_cp_entries"],
        "bootstrap_methods_table_entries_sum":
            counters["class_bootstrap_table_entries"],
        "bootstrap_argument_constants_sum":
            counters["class_bootstrap_argument_entries"],
        "bootstrap_constant_dynamic_arguments_sum":
            counters["class_bootstrap_condy_argument_entries"],
        "method_handle_cp_entries_sum":
            counters["class_method_handle_cp_entries"],
        "method_type_cp_entries_sum":
            counters["class_method_type_cp_entries"],
        "bootstrap_method_handle_arguments_at_instruction_sites":
            counters["bootstrap_method_handle_arguments_at_sites"],
        "unused_invokedynamic_cp_entries_sum":
            counters["unused_invokedynamic_cp_entries"],
        "unused_constant_dynamic_cp_entries_sum":
            counters["unused_condy_cp_entries"],
        "unreferenced_bootstrap_methods_table_entries_sum":
            counters["unreferenced_bootstrap_table_entries"],
        "named_lambda_metafactory_bootstrap_sites":
            counters["lambda_metafactory_named_bootstrap_sites"],
        "named_string_concat_factory_bootstrap_sites":
            counters["string_concat_factory_named_bootstrap_sites"],
        "bootstrap_target_platform_name_only_sites":
            bootstrap_owner["platform_uninspected"],
        "bootstrap_target_rebuilt_owner_name_only_sites":
            bootstrap_owner["rebuilt_class_name"],
        "bootstrap_target_preferred_dependency_name_only_sites":
            bootstrap_owner["preferred_dependency_class_name"],
        "bootstrap_target_alternate_only_name_sites":
            bootstrap_owner["alternate_dependency_only_class_name"],
        "bootstrap_target_original_v309_only_name_sites":
            bootstrap_owner["original_v309_only_class_name"],
        "bootstrap_target_name_absent_from_known_classpaths_sites":
            bootstrap_owner["owner_missing_from_known_static_classpaths"],
        "bootstrap_argument_handle_target_name_absent_sites":
            argument_owner["owner_missing_from_known_static_classpaths"],
        "bootstrap_method_execution_proven": False,
        "invokedynamic_callsite_resolution_proven": False,
        "dynamic_constant_resolution_proven": False,
        "lambda_runtime_functionality_proven": False,
        "method_handle_member_access_proven": False,
        "unreachable_bytecode_excluded": False,
    }
    return summary, {
        "owner_only_bootstrap_callsite_and_handle_worklist": private_sites,
        "bootstrap_handle_targets_are_static_name_leads_only": True,
        "bootstrap_calls_or_condy_constants_executed": False,
        "historical_R421_full_inventory_independently_approved": False,
        "release_authorized": False,
        "merge_authorized": False,
    }


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    previous, _ = r457.inspect(original, companion)
    snapshot, _ = r446.observe()
    evidence = observed_bootstrap(snapshot)
    pinned_original = r447.read_pinned_original(original)
    original_names, _, _ = r447.archive(pinned_original, "original")

    _, _, _, preferred_path, alternate_path = r446.roots()
    preferred = scanner.read_bounded_regular(
        preferred_path, r447.MAX_DEPENDENCY_BYTES,
        "R458_PREFERRED_JAR_BUDGET")
    alternate = scanner.read_bounded_regular(
        alternate_path, r447.MAX_DEPENDENCY_BYTES,
        "R458_ALTERNATE_JAR_BUDGET")
    need(preferred is not None and alternate is not None,
         "R458_DEPENDENCY_UNAVAILABLE")
    need(sha256(preferred).hexdigest() ==
         snapshot["dependency_sha256"]["R239_filtered.jar"]
         and sha256(alternate).hexdigest() ==
         snapshot["dependency_sha256"]["R218.jar"],
         "R458_DEPENDENCY_CHANGED_DURING_ANALYSIS")
    preferred_names, _, _ = r447.archive(preferred, "dependency")
    alternate_names, _, _ = r447.archive(alternate, "dependency")

    stats, private = aggregate(
        evidence, set(snapshot["class_inventory"]), preferred_names,
        alternate_names, original_names)
    need(stats["rebuilt_java11_classfiles_scanned"] ==
         previous["isolated_r421_compiled_classes"],
         "R458_REBUILT_CLASS_COUNT_DISAGREEMENT")
    need(stats["invokedynamic_bytecode_sites"] ==
         previous["invokedynamic_sites_not_resolved"],
         "R458_R457_INVOKEDYNAMIC_OPCODE_COUNT_DISAGREEMENT")
    need(r446.observe()[0] == snapshot
         and sha256(r447.read_pinned_original(original)).hexdigest() ==
         r447.ORIGINAL_SHA,
         "R458_INPUTS_CHANGED_DURING_AUDIT")

    result = {
        "status": "R458_STATIC_BOOTSTRAP_METHOD_HANDLE_EVIDENCE_UNAPPROVED",
        "original_v309_exact_sha_verified": previous[
            "original_v309_SHA_verified"],
        "original_v309_class_count": previous["original_v309_classes"],
        "original_v309_resource_count": previous["original_v309_resources"],
        "isolated_r421_java_sources": previous["isolated_r421_sources"],
        "isolated_r421_compiled_classfiles":
            previous["isolated_r421_compiled_classes"],
        "resource_companion_checked": companion is not None,
        "historical_R421_full_inventory_independently_approved": False,
        "client_started": False,
        "private_classfiles_executed": False,
        "source_completeness_proven": False,
        "asset_packaging_proven": False,
        "live_v312_compatibility_proven": False,
        "persistent_player_history_or_deletion_journal_accessed": False,
        "release_authorized": False,
        "merge_authorized": False,
        **stats,
    }
    if companion is not None:
        for name in ("companion_resource_byte_matches",
                     "companion_resource_missing",
                     "companion_resource_mismatches"):
            result[name] = previous[name]
    details = {
        "schema": SCHEMA,
        "status": "UNAPPROVED_CURRENT_STATIC_JAVA11_BOOTSTRAP_EVIDENCE",
        "owner_private_worklist": private,
        "original_v309_or_R421_executed": False,
        "historical_R421_inventory_approved": False,
        "merge_authorized": False,
        "release_authorized": False,
    }
    return result, details


def save_private(details: dict) -> str:
    root, *_ = r446.roots()
    need(scanner.directory(root), "R458_OWNER_TEMP_UNSAFE")
    data = (json.dumps(details, sort_keys=True, ensure_ascii=True,
                       separators=(",", ":")) + "\n").encode("ascii")
    need(0 < len(data) <= MAX_PRIVATE_BYTES,
         "R458_PRIVATE_REPORT_TOO_LARGE")
    folder = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(root)))
    need(folder.parent == root and scanner.directory(folder),
         "R458_PRIVATE_REPORT_LOCATION_INVALID")
    path = folder / NAME
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0) |
                 getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return folder.name


def run(original: Path, companion: Path | None = None,
        save: bool = False) -> dict:
    initial = r446.observe()[0] if save else None
    summary, details = inspect(original, companion)
    if save:
        repeated, detail_again = inspect(original, companion)
        need(summary == repeated and details == detail_again
             and r446.observe()[0] == initial,
             "R458_CURRENT_INPUTS_CHANGED_BEFORE_PRIVATE_SAVE")
        summary["private_quarantine_directory"] = save_private(details)
        summary["private_report_created"] = True
    else:
        summary["private_report_created"] = False
    return summary


def main(argv=None) -> int:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--original-v309-jar", type=Path, required=True)
    command.add_argument("--resource-companion-root", type=Path)
    command.add_argument("--save-private-unapproved-worklist",
                         action="store_true")
    args = command.parse_args(argv)
    try:
        print(json.dumps(run(args.original_v309_jar,
                             args.resource_companion_root,
                             args.save_private_unapproved_worklist),
                         sort_keys=True))
        return 0
    except (Refused, bootstrap.Refused, r457.Refused, r456.Refused,
            r455.Refused, r454.Refused, r453.Refused, r452.Refused,
            r451.Refused, r450.Refused, r449.Refused, r448.Refused,
            r447.Refused, r446.Refused, r440.Refused, scanner.Refused,
            OSError, ValueError, TypeError, UnicodeError) as error:
        if isinstance(error, (Refused, bootstrap.Refused, r457.Refused,
                              r456.Refused, r455.Refused, r454.Refused,
                              r453.Refused, r452.Refused, r451.Refused,
                              r450.Refused, r449.Refused, r448.Refused,
                              r447.Refused, r446.Refused, r440.Refused,
                              scanner.Refused)):
            reason = str(error)[:120]
        else:
            reason = "R458_STATIC_OWNER_INPUT_REFUSED"
        print(json.dumps({
            "status": "R458_BOOTSTRAP_AUDIT_REFUSED",
            "reason": reason,
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
