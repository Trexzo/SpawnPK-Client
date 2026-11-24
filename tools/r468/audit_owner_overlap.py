#!/usr/bin/env python3
"""R468 optional owner-side exact member-overlap census.

The R459 inspector still performs complete before/after R446 SHA inventories,
pinned v309 archive checks, bounded nofollow class reads, dependency admission,
cross-parser parity and final original archive re-read before this function
returns anything. The temporary census is computed inside the optional R459
hierarchy-selector callback from precisely its admitted in-memory records.

Public output is NUMERIC AGGREGATE ONLY. No owner details, names, paths, hashes,
source text, class bytecode, private worklists or cached inventory are exported.
This does not approve historical R421 custody or real game performance.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r459 import audit_consolidated_inspection as r459
from tools.r461 import shared_constant_pool as cp
from tools.r462 import shared_instruction_stream as instructions
from tools.r463 import reuse_validated_metadata as metadata
from tools.r464 import shared_hierarchy as hierarchy
from tools.r468 import overlap_census as census

SCHEMA = "SpawnPK-R468-aggregate-overlap-census-UNAPPROVED-v1"


class Refused(RuntimeError):
    pass


def inspect(original: Path, companion: Path | None = None,
            *, threshold: int = 8):
    captures = []

    def selector(rebuilt, selected, sites):
        selected_cache, metrics = census.compare_with_gate(
            rebuilt, selected, sites, threshold=threshold)
        captures.append(metrics)
        return selected_cache

    summary, detail = r459.inspect(
        original, companion,
        shared_pool_factory=cp.decode,
        shared_instruction_factory=instructions.Index,
        descriptor_cache_factory=metadata.DescriptorShapes,
        reuse_opcode_summary=True,
        hierarchy_factory=hierarchy.Index,
        hierarchy_selector=selector)

    if len(captures) != 1 or not captures[0].complete_reference_enumeration:
        raise Refused("R468_CENSUS_NOT_COMPLETED_EXACTLY_ONCE")
    if (summary["full_R446_inventory_observations"] != 2
            or summary["isolated_r421_compiled_classes"] !=
            captures[0].rebuilt_class_records
            or summary["selected_preferred_dependency_classes"] !=
            captures[0].selected_dependency_records
            or summary["R456_actual_member_instruction_sites"] !=
            captures[0].decoded_member_opcode_sites
            or not summary["pinned_original_archive_re_read_after_evidence_pass"]
            or not summary["entire_current_inventory_consistent_after_evidence_pass"]):
        raise Refused("R468_ADMITTED_CENSUS_AUDIT_SUMMARY_MISMATCH")
    return summary, detail, captures[0]


def public_result(summary: dict, evidence: census.Census,
                  *, threshold: int = 8) -> dict:
    """Hardcoded allowlist: never materialize private detail or hash maps."""
    if (type(threshold) is not int or not 1 <= threshold <= 256
            or not summary["original_v309_pinned_sha_matched"]
            or not summary["entire_current_inventory_consistent_after_evidence_pass"]
            or not summary["pinned_original_archive_re_read_after_evidence_pass"]
            or summary["full_R446_inventory_observations"] != 2
            or not evidence.complete_reference_enumeration):
        raise Refused("R468_PUBLIC_SUMMARY_NOT_FULLY_ADMITTED")
    return {
        "schema": SCHEMA,
        "status": "R468_OWNER_CURRENT_STATE_CENSUS_UNAPPROVED",
        "census": asdict(evidence),
        "threshold_examined": threshold,
        "sha_observation_count": 2,
        "original_v309_exact_pin_verified": True,
        "final_current_inventory_consistent": True,
        "original_v309_reread_verified": True,
        "current_owner_source_class_counts_only": {
            "source_files": summary["isolated_r421_java_sources"],
            "class_files": summary["isolated_r421_compiled_classes"],
            "selected_dependency_classes":
                summary["selected_preferred_dependency_classes"],
        },
        "exact_recovered_source_inventory_historically_approved": False,
        "candidate_worklist_exported": False,
        "per_class_names_or_hashes_exported": False,
        "source_class_or_jar_bytes_exported": False,
        "production_history_or_journal_accessed": False,
        "client_runtime_measured": False,
        "full_original_source_reconstruction_proven": False,
        "release_authorized": False,
        "merge_authorized": False,
    }


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--original-v309-jar", type=Path, required=True)
    cli.add_argument("--threshold", type=int, choices=range(1, 257),
                     default=8)
    args = cli.parse_args(argv)
    try:
        summary, _private, overlap = inspect(
            args.original_v309_jar, threshold=args.threshold)
        print(json.dumps(public_result(
            summary, overlap, threshold=args.threshold),
            sort_keys=True, separators=(",", ":")))
        return 0
    except Exception:
        # Never disclose owner-specific exceptions, paths or private names.
        print(json.dumps({
            "status": "R468_OWNER_OVERLAP_CENSUS_REFUSED",
            "reason": "R468_PRIVATE_INPUT_OR_CUSTODY_NOT_ADMITTED",
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
