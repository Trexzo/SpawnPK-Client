#!/usr/bin/env python3
"""R452 owner-private acyclic JVM branch resource-argument evidence.

The R451 straight-line model skips methods containing branches. R452
explores a narrow forward-only conditional/goto CFG, requiring consensus of
all abstract paths at each resource method call site. Original v309 and R421
source/class/dependency SHA admission from R451/R446 is mandatory.

No game execution, classloading, history read, private source publication,
client installation or historic manifest self-approval is performed.
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
from tools.r450 import classfile_signature_resource as signatures
from tools.r451 import audit_resource_operand_arguments as r451
from tools.r452 import forward_branch_resource_operands as cfg

SCHEMA = "SpawnPK-R452-acyclic-branch-resource-evidence-UNAPPROVED-v1"
PREFIX = "SpawnPK-R452-Private-CFG-Resource-"
NAME = "R452-UNAPPROVED-BRANCH-RESOURCE-WORKLIST.json"
MAX_BYTES = 700 * 1024 * 1024
MAX_CLASS_STATES = 150000
MAX_PRIVATE = 5 * 1024 * 1024


class Refused(RuntimeError):
    pass


def need(value: bool, code: str) -> None:
    if not value:
        raise Refused(code)


def observed_cfg(observed: dict) -> tuple[
        dict[str, list[tuple[str, int, str]]], dict[str, dict[str, int]]]:
    """Per-class, per-SHA bounded static Code analysis; no Java execution."""
    _, _, class_root, _, _ = r446.roots()
    need(scanner.directory(class_root), "R452_COMPILED_ROOT_NOT_SAFE")
    evidence: dict[str, list[tuple[str, int, str]]] = {}
    summaries: dict[str, dict[str, int]] = {}
    total = 0
    states_total = 0
    for cls, fingerprint in sorted(observed["class_inventory"].items()):
        r447.zip_path(cls)
        need(cls.endswith(".class"), "R452_NON_CLASS_IN_R421_MAP")
        raw = scanner.read_bounded_regular(
            class_root.joinpath(*cls.split("/")), r448.MAX_CLASS_BYTES,
            "R452_COMPILED_CLASS_FILE_OVER_BUDGET")
        need(raw is not None and sha256(raw).hexdigest() == fingerprint,
             "R452_COMPILED_MEMBER_CHANGED_DURING_SCAN")
        total += len(raw)
        need(total <= MAX_BYTES, "R452_TOTAL_CLASS_SCAN_BYTES_EXCEEDED")
        collector = cfg.Collector()
        # Reuse R450's exact Java11 CP and method Code parser.
        # Callback visits methods once; CFG worklist stays bounded.
        signatures.classfile_evidence(
            raw, r449.resource_literal, code_observer=collector)
        evidence[cls] = collector.literal_argument_sites
        summaries[cls] = {
            "methods_seen": collector.methods_seen,
            "methods_modeled": collector.methods_modeled,
            "methods_skipped": collector.methods_skipped,
            "branch_methods_modeled":
                collector.methods_with_forward_branches_modeled,
            "resource_call_sites": collector.resource_call_sites,
            "ambiguous_sites": collector.ambiguous_resource_call_sites,
            "states_explored": collector.states_explored,
        }
        states_total += collector.states_explored
        need(states_total <= MAX_CLASS_STATES,
             "R452_TOTAL_GRAPH_STATE_BUDGET")
    return evidence, summaries


def aggregate(
        evidence: dict[str, list[tuple[str, int, str]]],
        stats: dict[str, dict[str, int]],
        original_resources: set[str],
        previous_private: dict,
) -> tuple[dict, dict]:
    need(evidence.keys() == stats.keys(),
         "R452_CLASS_EVIDENCE_STAT_KEY_MISMATCH")
    methods = sum(v["methods_seen"] for v in stats.values())
    modeled = sum(v["methods_modeled"] for v in stats.values())
    skipped = sum(v["methods_skipped"] for v in stats.values())
    branch_modeled = sum(v["branch_methods_modeled"] for v in stats.values())
    sites = sum(v["resource_call_sites"] for v in stats.values())
    ambiguous = sum(v["ambiguous_sites"] for v in stats.values())
    states = sum(v["states_explored"] for v in stats.values())
    need(methods == modeled + skipped and branch_modeled <= modeled
         and ambiguous <= sites, "R452_COUNTER_INVARIANT_FAILED")
    sites_found: set[tuple[str, str, int, str]] = set()
    for cls, list_of_sites in evidence.items():
        for method, pc, path in list_of_sites:
            sites_found.add((cls, method, pc, path))
    values_by_resource: dict[str, set[str]] = defaultdict(set)
    for cls, method, pc, path in sites_found:
        values_by_resource[path].add(cls + "#" + method)

    prior = previous_private[
        "owner_private_resource_argument_worklist"][
        "modeled_static_literal_call_arguments"]
    prior_signals = {
        (caller, item["possible_resource_path"])
        for item in prior
        for caller in item["rebuilt_method_referencers"]
    }
    next_signals = {
        (cls + "#" + method, path)
        for cls, method, pc, path in sites_found
    }
    novel = next_signals - prior_signals
    previously_modeled = next_signals & prior_signals

    summary = {
        "reconstructed_classfiles_examined": len(evidence),
        "bytecode_methods_inspected": methods,
        "fully_modeled_acyclic_methods": modeled,
        "forward_branch_methods_fully_modeled": branch_modeled,
        "unsupported_or_cyclic_methods_excluded": skipped,
        "total_bounded_graph_states_explored": states,
        "resource_call_sites_in_modeled_methods": sites,
        "ambiguous_or_unknown_literal_resource_call_sites": ambiguous,
        "all_path_consensus_resource_call_site_candidates":
            len(sites_found),
        "unique_all_path_literal_resource_candidates":
            len(values_by_resource),
        "all_path_literal_candidate_names_in_original_v309":
            len(set(values_by_resource) & original_resources),
        "all_path_literal_candidate_names_not_in_original_v309":
            len(set(values_by_resource) - original_resources),
        "new_class_method_resource_candidates_beyond_R451":
            len(novel),
        "class_method_resource_candidates_also_seen_by_R451":
            len(previously_modeled),
        "all_conditional_branch_outcomes_explored_conservatively": True,
        "backward_loops_switches_exceptions_and_unknown_opcodes_excluded": True,
        "actual_code_path_execution_proven": False,
        "resource_loading_success_proven": False,
        "client_runtime_linkage_proven": False,
    }
    private = {
        "all_path_consensus_static_resource_arguments": [
            {
                "possible_resource_name": resource,
                "source_class_and_method_signals":
                    sorted(values_by_resource[resource]),
                "name_present_in_original_v309_resources":
                    resource in original_resources,
                "actual_resource_loaded": False,
            }
            for resource in sorted(values_by_resource)
        ],
        "new_class_method_resource_signals_beyond_R451": [
            {
                "class_and_method": location,
                "possible_resource_name": name,
            }
            for location, name in sorted(novel)
        ],
        "all_path_consensus_is_static_not_runtime": True,
        "historical_R421_source_class_custody_approved": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return summary, private


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    previous, previous_details = r451.inspect(original, companion)
    observed, _ = r446.observe()
    evidence, stats = observed_cfg(observed)
    original_bytes = r447.read_pinned_original(original)
    _original_classes, resources, _ = r447.archive(
        original_bytes, "original")
    totals, detailed = aggregate(
        evidence, stats, resources,
        previous_details["owner_private_resource_argument_worklist"])
    need(totals["reconstructed_classfiles_examined"] ==
         previous["isolated_r421_compiled_classes"],
         "R452_R421_CLASS_COUNT_DRIFT")
    need(totals["bytecode_methods_inspected"] ==
         previous["bytecode_methods_inspected"],
         "R452_JAVA11_METHOD_COUNT_DRIFT")
    next_snapshot, _ = r446.observe()
    need(next_snapshot == observed,
         "R452_R421_CHANGED_DURING_ANALYSIS")
    need(sha256(r447.read_pinned_original(original)).hexdigest() ==
         r447.ORIGINAL_SHA, "R452_V309_ORIGINAL_CHANGED_DURING_ANALYSIS")
    result = {
        "status": "R452_ACYCLIC_JAVA_RESOURCE_ARGUMENT_EVIDENCE_UNAPPROVED",
        "original_v309_sha_matched": previous["original_v309_exact_sha_matched"],
        "original_class_count": previous["original_v309_classes"],
        "original_resource_count": previous["original_v309_resources"],
        "R421_java_sources": previous["isolated_r421_java_sources"],
        "R421_compiled_classes": previous["isolated_r421_compiled_classes"],
        "resource_companion_checked": companion is not None,
        "owner_game_client_launched": False,
        "actual_private_source_executed": False,
        "historical_R421_manifest_approved": False,
        "full_client_reconstruction_verified": False,
        "runnable_client_proven": False,
        "resource_packaging_verified": False,
        "persistent_game_history_accessed": False,
        "build_authorized": False,
        "merge_authorized": False,
        "release_authorized": False,
        **totals,
    }
    if companion is not None:
        for key in ("companion_resource_byte_matches",
                    "companion_resource_missing",
                    "companion_resource_mismatches"):
            result[key] = previous[key]
    private = {
        "schema": SCHEMA,
        "status": "UNAPPROVED_CURRENT_STATIC_FORWARD_ONLY_CFG_ANALYSIS",
        "details": detailed,
        "historical_R421_manifest_approved": False,
        "runtime_resource_load_proven": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return result, private


def save_private(contents: dict) -> str:
    root, *_ = r446.roots()
    need(scanner.directory(root), "R452_PRIVATE_TEMP_MISSING")
    raw = (json.dumps(contents, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")) + "\n").encode("ascii")
    need(0 < len(raw) <= MAX_PRIVATE, "R452_PRIVATE_REPORT_BUDGET")
    directory = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(root)))
    need(directory.parent == root and scanner.directory(directory),
         "R452_PRIVATE_DIRECTORY_INVALID")
    out = directory / NAME
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0) |
                 getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return directory.name


def run(original: Path, companion: Path | None = None,
        private: bool = False) -> dict:
    # Preserve whole current inventory before scans so equal aggregates
    # cannot hide an unrelated source/class/dependency change.
    baseline = r446.observe()[0] if private else None
    result, details = inspect(original, companion)
    if private:
        repeated, repeated_details = inspect(original, companion)
        need(repeated == result and repeated_details == details
             and r446.observe()[0] == baseline,
             "R452_INPUTS_CHANGED_BEFORE_PRIVATE_REPORT")
        result["private_output_directory"] = save_private(details)
        result["private_report_created"] = True
    else:
        result["private_report_created"] = False
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-v309-jar", type=Path, required=True)
    parser.add_argument("--resource-companion-root", type=Path)
    parser.add_argument("--save-private-unapproved-worklist",
                        action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run(
            args.original_v309_jar, args.resource_companion_root,
            args.save_private_unapproved_worklist), sort_keys=True))
        return 0
    except (Refused, cfg.Refused, r451.Refused, signatures.Refused,
            r450.Refused, r449.Refused, r448.Refused, r447.Refused,
            r446.Refused, r440.Refused, scanner.Refused, OSError,
            ValueError, TypeError, UnicodeError) as err:
        if isinstance(err, (Refused, cfg.Refused, r451.Refused,
                            signatures.Refused, r450.Refused, r449.Refused,
                            r448.Refused, r447.Refused, r446.Refused,
                            r440.Refused, scanner.Refused)):
            reason = str(err)[:120]
        else:
            reason = "R452_OWNER_PRIVATE_STATIC_FLOW_REFUSED"
        print(json.dumps({
            "status": "R452_ACYCLIC_RESOURCE_AUDIT_REFUSED",
            "reason": reason,
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
