#!/usr/bin/env python3
"""R459 single evidence-read owner-private Java11 class inspection coordinator.

Alternative to deeply nested R447..R458 audit invocations: obtain one R446
*current-state* full source/class/dependency SHA observation, validate pinned
v309 JAR/dependency ZIP bytes, then read every rebuilt .class ONCE in the
evidence pass and feed its immutable bytes to the existing independent
R449/R450/R451/R452/R453/R456/R458 parsers. Reuse parsed objects in memory
for R453/R454/R455/R456/R457/R458 aggregate analysis. Finish with a separate
full R446 observation + pinned original JAR re-read for TOCTOU protection.

No disk cache, source/JAR byte export, Java execution, runtime installation,
historical R421 custody approval or persistent history/journal modification.
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

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r440 import read_only_private_acceptance_preflight as r440
from tools.r444 import scan_owner_r421_artifacts as scanner
from tools.r446 import observe_owner_private_inventory as r446
from tools.r447 import audit_original_class_asset_coverage as r447
from tools.r448 import audit_rebuilt_class_linkage as r448
from tools.r449 import audit_descriptor_resource_gaps as r449
from tools.r450 import classfile_signature_resource as r450
from tools.r451 import straightline_resource_operands as r451
from tools.r452 import forward_branch_resource_operands as r452
from tools.r453 import classfile_member_reference as r453
from tools.r453 import audit_member_reference_coverage as r453_audit
from tools.r454 import member_ancestry_evidence as r454
from tools.r455 import dependency_member_access as r455
from tools.r456 import member_opcode_evidence as r456
from tools.r457 import jvm_callsite_constraints as r457
from tools.r458 import bootstrap_callsite_evidence as r458
from tools.r458 import audit_bootstrap_evidence as r458_audit

SCHEMA = "SpawnPK-R459-consolidated-evidence-UNAPPROVED-v1"
PREFIX = "SpawnPK-R459-Private-Consolidated-"
NAME = "R459-UNAPPROVED-RECONSTRUCTION-WORKLIST.json"
MAX_EVIDENCE_CLASS_BYTES = 700 * 1024 * 1024
MAX_EVIDENCE_MEMBER_SITES = 250000
MAX_EVIDENCE_DYNAMIC_SITES = 250000
MAX_PRIVATE_REPORT_BYTES = 16 * 1024 * 1024


class Refused(RuntimeError):
    pass


def need(condition: bool, code: str) -> None:
    if not condition:
        raise Refused(code)


@r450.scoped_instruction_cache
def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    # R446.observe always checks exact OS TEMP roots (no aliases),
    # fixed source/class counts, per-file SHA maps and pinned Store files.
    # This observation is never an independently approved R421 history.
    snapshot, _receipt = r446.observe()
    original_raw = r447.read_pinned_original(original)
    original_classes, resources, _ = r447.archive(original_raw, "original")
    need(len(original_classes) == r447.ORIGINAL_CLASSES and
         len(resources) == r447.ORIGINAL_RESOURCES,
         "R459_PINNED_ORIGINAL_CLASS_RESOURCE_COUNT_DRIFT")

    temporary, src_root, class_root, preferred_path, alternate_path = r446.roots()
    need(scanner.directory(class_root), "R459_COMPILED_ROOT_UNSAFE")
    preferred_raw = scanner.read_bounded_regular(
        preferred_path, r447.MAX_DEPENDENCY_BYTES,
        "R459_PREFERRED_DEPENDENCY_TOO_LARGE")
    alternate_raw = scanner.read_bounded_regular(
        alternate_path, r447.MAX_DEPENDENCY_BYTES,
        "R459_ALTERNATE_DEPENDENCY_TOO_LARGE")
    need(preferred_raw is not None and alternate_raw is not None,
         "R459_DEPENDENCY_MISSING_OR_UNSAFE")
    dep_hashes = snapshot["dependency_sha256"]
    need(sha256(preferred_raw).hexdigest() ==
         dep_hashes["R239_filtered.jar"] and
         sha256(alternate_raw).hexdigest() ==
         dep_hashes["R218.jar"],
         "R459_DEPENDENCY_CHANGED_DURING_EVIDENCE_PASS")
    preferred_names, _, _ = r447.archive(preferred_raw, "dependency")
    alternate_names, _, _ = r447.archive(alternate_raw, "dependency")

    class_records: dict[str, r453.ClassMembers] = {}
    dynamic_records: dict[str, r458.Evidence] = {}
    member_sites: list[r456.Site] = []
    straightline_details: list[tuple[str, str, str]] = []
    branch_details: list[tuple[str, str, int, str]] = []
    class_file_reads = 0
    class_bytes_read = 0
    methods = Counter()

    for path, expected_sha in sorted(snapshot["class_inventory"].items()):
        r447.zip_path(path)
        need(path.endswith(".class"), "R459_NONCLASS_IN_COMPILED_INVENTORY")
        data = scanner.read_bounded_regular(
            class_root.joinpath(*path.split("/")),
            r448.MAX_CLASS_BYTES, "R459_CLASS_BYTES_OVER_BUDGET")
        need(data is not None and sha256(data).hexdigest() == expected_sha,
             "R459_COMPILED_CLASS_CHANGED_DURING_EVIDENCE_PASS")
        class_file_reads += 1
        class_bytes_read += len(data)
        need(class_bytes_read <= MAX_EVIDENCE_CLASS_BYTES,
             "R459_COMPILED_TREE_TOO_LARGE")

        # The same immutable byte string is passed to each existing parser.
        # None reopens source/class files or invokes another full audit.
        record = r453.parse_class(data)
        need(record.class_name == path,
             "R459_REBUILT_CLASS_INTERNAL_NAME_MISMATCH")
        class_records[path] = record
        dynamic = r458.scan_class(data)
        need(dynamic.class_name == path,
             "R459_BOOTSTRAP_CLASS_INTERNAL_NAME_MISMATCH")
        dynamic_records[path] = dynamic
        opcode = r456.Collector(path)
        straight = r451.Collector()
        branch = r452.Collector()

        def resource_callback(method, code, max_stack, max_locals,
                              exceptions, literal, methodref, filter_resource):
            straight(method, code, max_stack, max_locals, exceptions,
                     literal, methodref, filter_resource)
            branch(method, code, max_stack, max_locals, exceptions,
                   literal, methodref, filter_resource)

        generic, proximity, api_count = r450.classfile_evidence(
            data, r449.resource_literal, code_observer=resource_callback,
            member_observer=opcode)
        methods["generic_signature_class_refs"] += len(generic)
        methods["resource_proximity_pairs"] += len(proximity)
        methods["known_resource_api_invokes"] += api_count
        methods["straightline_modeled_methods"] += straight.methods_straightline_analyzed
        methods["straightline_literal_arguments"] += len(straight.matched_arguments)
        methods["forward_cfg_modeled_methods"] += branch.methods_modeled
        methods["forward_cfg_literal_sites"] += len(branch.literal_argument_sites)
        methods["forward_cfg_ambiguous_sites"] += branch.ambiguous_resource_call_sites
        methods["forward_cfg_states_explored"] += branch.states_explored
        methods["methods_with_code"] += opcode.methods_with_code
        methods["invokedynamic_sites_in_R456_decoder"] += opcode.dynamic_sites
        methods["dynamic_sites_in_R458_parser"] += len(dynamic.invokedynamic_sites)
        need(methods["invokedynamic_sites_in_R456_decoder"] ==
             methods["dynamic_sites_in_R458_parser"],
             "R459_INVOKEDYNAMIC_DECODER_COUNT_DISAGREEMENT")
        member_sites.extend(opcode.sites)
        need(len(member_sites) <= MAX_EVIDENCE_MEMBER_SITES,
             "R459_MEMBER_SITE_LIMIT")
        straightline_details.extend(
            (path, method, value)
            for method, value in straight.matched_arguments)
        branch_details.extend(
            (path, method, pc, value)
            for method, pc, value in branch.literal_argument_sites)
        need(len(straightline_details) + len(branch_details)
             <= MAX_EVIDENCE_DYNAMIC_SITES,
             "R459_RESOURCE_SITE_LIMIT")

    need(class_file_reads == len(snapshot["class_inventory"]) ==
         r425.BASELINE_CLASS_COUNT,
         "R459_CLASS_SCAN_COUNT_MISMATCH")

    # Reuse all metadata and bytes already admitted above; never call
    # R453..R458 owner inspect() recursively in this fast path.
    chosen_dependencies = r455.selected_dependencies(
        preferred_raw, dep_hashes["R239_filtered.jar"],
        preferred_names, class_records)

    member_summary, member_private = r453_audit.classify(
        class_records, preferred_names, alternate_names, original_classes)
    ancestry_summary, ancestry_private = r454.analyze(
        class_records, preferred_names, alternate_names, original_classes)
    dependency_summary, dependency_private = r455.analyze(
        class_records, chosen_dependencies, original_classes, alternate_names)
    opcode_summary, opcode_private = r456.analyze(
        class_records, chosen_dependencies, member_sites,
        methods["invokedynamic_sites_in_R456_decoder"])
    callsite_summary, callsite_private = r457.analyze(
        class_records, chosen_dependencies, member_sites,
        methods["invokedynamic_sites_in_R456_decoder"])
    dynamic_summary, dynamic_private = r458_audit.aggregate(
        dynamic_records, set(class_records), preferred_names,
        alternate_names, original_classes)

    need(dynamic_summary["invokedynamic_bytecode_sites"] ==
         opcode_summary["invokedynamic_sites_without_static_owner_resolution"] ==
         callsite_summary["invokedynamic_sites_not_resolved"],
         "R459_CROSS_PARSER_INVOKEDYNAMIC_COUNT_DRIFT")
    need(member_summary["unique_constant_pool_member_references"] ==
         ancestry_summary["unique_rebuilt_constant_pool_member_references"],
         "R459_CROSS_PARSER_MEMBER_REFERENCE_COUNT_DRIFT")
    need(len(class_records) ==
         dependency_summary["rebuilt_classfiles_examined"] ==
         callsite_summary["rebuilt_classfiles_checked"],
         "R459_CROSS_PARSER_REBUILT_CLASS_COUNT_DRIFT")

    # Owner TEMP current-state re-hash proves no intervening source/class/
    # dependency change on disk. The original archive is also re-read.
    final, _ = r446.observe()
    need(final == snapshot,
         "R459_CURRENT_FULL_SOURCE_CLASS_DEPENDENCY_INVENTORY_CHANGED")
    need(sha256(r447.read_pinned_original(original)).hexdigest() ==
         r447.ORIGINAL_SHA, "R459_PINNED_ORIGINAL_CHANGED_DURING_EVIDENCE_PASS")

    report = {
        "status": "R459_CONSOLIDATED_OWNER_EVIDENCE_UNAPPROVED",
        "original_v309_pinned_sha_matched": True,
        "original_v309_class_count": len(original_classes),
        "original_v309_resource_count": len(resources),
        "isolated_r421_java_sources": len(snapshot["source_inventory"]),
        "isolated_r421_compiled_classes": len(snapshot["class_inventory"]),
        "preferred_dependency_class_names": len(preferred_names),
        "alternate_dependency_class_names": len(alternate_names),
        "selected_preferred_dependency_classes": len(chosen_dependencies),
        "classfile_evidence_pass_reads": class_file_reads,
        "classfile_evidence_pass_bytes": class_bytes_read,
        "full_R446_inventory_observations": 2,
        "recursive_legacy_owner_audits_invoked": 0,
        "entire_current_inventory_consistent_after_evidence_pass": True,
        "pinned_original_archive_re_read_after_evidence_pass": True,
        "resource_companion_checked": companion is not None,
        "R453_unique_member_references":
            member_summary["unique_constant_pool_member_references"],
        "R454_possible_inherited_signature_count":
            ancestry_summary["possible_inherited_declaration_signatures"],
        "R455_exact_dependency_declarations":
            dependency_summary[
                "reference_owners_preferred_dependency_direct_exact_declaration"],
        "R456_actual_member_instruction_sites":
            opcode_summary["field_and_method_bytecode_sites_inspected"],
        "R456_possible_static_instance_disagreements":
            opcode_summary["static_instance_opcode_declaration_conflicts"],
        "R457_callsite_syntactic_findings":
            callsite_summary["sites_with_one_or_more_syntactic_findings"],
        "R458_invokedynamic_bytecode_sites":
            dynamic_summary["invokedynamic_bytecode_sites"],
        "R458_constant_dynamic_ldc_sites":
            dynamic_summary["constant_dynamic_ldc_bytecode_sites"],
        "R458_bootstrap_method_handle_argument_sites":
            dynamic_summary[
                "bootstrap_method_handle_arguments_at_instruction_sites"],
        "R450_generic_signature_class_refs_sum":
            methods["generic_signature_class_refs"],
        "R450_resource_string_proximity_pairs":
            methods["resource_proximity_pairs"],
        "R451_modeled_straightline_methods":
            methods["straightline_modeled_methods"],
        "R451_likely_resource_literal_arguments":
            methods["straightline_literal_arguments"],
        "R452_modeled_forward_control_flow_methods":
            methods["forward_cfg_modeled_methods"],
        "R452_resource_literal_argument_sites":
            methods["forward_cfg_literal_sites"],
        "R452_ambiguous_resource_call_sites":
            methods["forward_cfg_ambiguous_sites"],
        "R452_CFG_states_explored":
            methods["forward_cfg_states_explored"],
        "java_method_Code_attributes_observed": methods["methods_with_code"],
        "source_or_class_bytes_exported": False,
        "historical_R421_full_inventory_independently_approved": False,
        "client_executed": False,
        "client_compilation_performed": False,
        "complete_original_source_or_asset_parity_proven": False,
        "jvm_linkage_verified": False,
        "production_history_or_deletion_journal_accessed": False,
        "merge_authorized": False,
        "release_authorized": False,
    }

    if companion is not None:
        companion_counts, _, _ = r447.resource_companion(
            companion, original_raw, resources)
        report.update(companion_counts)

    private = {
        "schema": SCHEMA,
        "status": "UNAPPROVED_CURRENT_OWNER_ONLY_CONSOLIDATED_EVIDENCE",
        "R451_resource_literals": straightline_details,
        "R452_acyclic_control_flow_literals": branch_details,
        "R453_member_reference_candidates": member_private,
        "R454_member_ancestry_candidates": ancestry_private,
        "R455_selected_dependency_candidates": dependency_private,
        "R456_real_member_opcode_candidates": opcode_private,
        "R457_invocation_constraint_candidates": callsite_private,
        "R458_bootstrap_method_handle_candidates": dynamic_private,
        "source_or_JAR_bytes_included": False,
        "historical_R421_approval_created": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return report, private


def save_private(detail: dict) -> str:
    root, *_ = r446.roots()
    need(scanner.directory(root), "R459_PRIVATE_ROOT_UNSAFE")
    raw = (json.dumps(detail, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":")) + "\n").encode("ascii")
    need(0 < len(raw) <= MAX_PRIVATE_REPORT_BYTES,
         "R459_PRIVATE_OUTPUT_SIZE_LIMIT")
    folder = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(root)))
    need(folder.parent == root and scanner.directory(folder),
         "R459_PRIVATE_REPORT_FOLDER_INVALID")
    fd = os.open(folder / NAME, os.O_WRONLY | os.O_EXCL | os.O_CREAT
                 | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return folder.name


def run(original: Path, companion: Path | None = None,
        save: bool = False) -> dict:
    baseline, _ = r446.observe() if save else (None, None)
    summary, details = inspect(original, companion)
    if save:
        repeated, again_details = inspect(original, companion)
        need(repeated == summary and details == again_details
             and baseline == r446.observe()[0],
             "R459_PRIVATE_REPORT_FULL_INPUT_CHANGED_BETWEEN_PASSES")
        summary["private_quarantine_directory"] = save_private(details)
        summary["private_report_created"] = True
    else:
        summary["private_report_created"] = False
    return summary


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--original-v309-jar", type=Path, required=True)
    cli.add_argument("--resource-companion-root", type=Path)
    cli.add_argument("--save-private-unapproved-worklist",
                     action="store_true")
    args = cli.parse_args(argv)
    try:
        print(json.dumps(run(args.original_v309_jar,
                             args.resource_companion_root,
                             args.save_private_unapproved_worklist),
                         sort_keys=True))
        return 0
    except (Refused, r446.Refused, r447.Refused, r448.Refused,
            r449.Refused, r450.Refused, r451.Refused, r452.Refused,
            r453.Refused, r454.Refused, r455.Refused, r456.Refused,
            r457.Refused, r458.Refused, r458_audit.Refused,
            r453_audit.Refused, scanner.Refused, r440.Refused,
            OSError, ValueError, TypeError, UnicodeError) as e:
        if isinstance(e, (Refused, r446.Refused, r447.Refused,
                          r448.Refused, r449.Refused, r450.Refused,
                          r451.Refused, r452.Refused, r453.Refused,
                          r454.Refused, r455.Refused, r456.Refused,
                          r457.Refused, r458.Refused, r458_audit.Refused,
                          r453_audit.Refused, scanner.Refused,
                          r440.Refused)):
            code = str(e)[:120]
        else:
            code = "R459_CONSOLIDATED_PRIVATE_INPUT_REFUSED"
        print(json.dumps({
            "status": "R459_CONSOLIDATED_AUDIT_REFUSED",
            "reason": code,
            "historical_R421_approved": False,
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
