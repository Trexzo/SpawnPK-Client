#!/usr/bin/env python3
"""R461 bounded static cProfile comparison of R459 with/without decode cache.

The profiling run is deliberately separate from R460 wall-clock benchmarking:
Python cProfile overhead distorts timings. Only public Python source symbol
names (allowlisted tools/rNNN modules) and aggregate statistics leave the
process. No method/class names, original/JAR bytes or file paths are printed.

Same current-state pinned source/class/dependency SHA gates and exact
original v309 archive as R459; no JVM, client launch, disk cache, history
access, journal writes, or historical R421 custody promotion.
"""
from __future__ import annotations

import argparse
import cProfile
from hashlib import sha256
import json
from pathlib import Path
import pstats
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r446 import observe_owner_private_inventory as r446
from tools.r447 import audit_original_class_asset_coverage as r447
from tools.r450 import classfile_signature_resource as r450
from tools.r459 import audit_consolidated_inspection as r459

SCHEMA = "SpawnPK-R461-scoped-instruction-decode-profile-UNAPPROVED-v1"
MAX_HOT_FUNCTIONS = 12
ALLOWLIST = frozenset({
    "classfile_signature_resource.py", "straightline_resource_operands.py",
    "forward_branch_resource_operands.py",
    "classfile_member_reference.py", "bootstrap_callsite_evidence.py",
    "member_opcode_evidence.py", "jvm_callsite_constraints.py",
    "member_ancestry_evidence.py", "dependency_member_access.py",
    "audit_consolidated_inspection.py", "audit_bootstrap_evidence.py",
    "audit_descriptor_resource_gaps.py",
    "audit_original_class_asset_coverage.py",
    "observe_owner_private_inventory.py", "scan_owner_r421_artifacts.py",
    "audit_rebuilt_class_linkage.py", "audit_member_reference_coverage.py",
})
EVIDENCE_KEYS = (
    "original_v309_class_count",
    "original_v309_resource_count",
    "isolated_r421_java_sources",
    "isolated_r421_compiled_classes",
    "classfile_evidence_pass_reads",
    "R453_unique_member_references",
    "R454_possible_inherited_signature_count",
    "R455_exact_dependency_declarations",
    "R456_actual_member_instruction_sites",
    "R456_possible_static_instance_disagreements",
    "R457_callsite_syntactic_findings",
    "R458_invokedynamic_bytecode_sites",
    "R458_constant_dynamic_ldc_sites",
    "R451_likely_resource_literal_arguments",
    "R452_resource_literal_argument_sites",
)


class Refused(RuntimeError):
    pass


def need(value: bool, code: str) -> None:
    if not value:
        raise Refused(code)


def safe_stat_names(name: str) -> bool:
    """Allow public repository function symbols only, never private paths."""
    return (type(name) is str and name and len(name) <= 160
            and all(c.isascii() and (c.isalnum() or c in "_<>")
                    for c in name))


def profile_one(fn, original: Path) -> tuple[dict, list[dict], dict]:
    profile = cProfile.Profile()
    try:
        profile.enable()
        summary, detail = fn(original)
    finally:
        profile.disable()
    entries = []
    total_self = 0
    for (file_name, line_number, function_name), (primitive, calls,
             internal_seconds, cumulative_seconds, _callers) in (
                 pstats.Stats(profile).stats.items()):
        # Treat profiler's paths as untrusted and do not output them.
        base = Path(file_name).name
        if base not in ALLOWLIST or not safe_stat_names(function_name):
            continue
        if not (0 <= internal_seconds <= 60 * 60
                and 0 <= cumulative_seconds <= 60 * 60):
            continue
        total_self += internal_seconds
        entries.append({
            "module": base,
            "symbol": function_name,
            "calls": calls,
            "primitive_calls": primitive,
            "python_self_ms": round(internal_seconds * 1000, 4),
            "cumulative_ms": round(cumulative_seconds * 1000, 4),
        })
    entries.sort(key=lambda e: (-e["python_self_ms"],
                                e["module"], e["symbol"]))
    return summary, entries[:MAX_HOT_FUNCTIONS], {
        "allowlisted_repo_python_self_ms":
            round(total_self * 1000, 4),
        "allowlisted_function_symbols_examined": len(entries),
        "all_reported_symbols_are_public_module_functions": True,
    }


def require_parity(before: dict, after: dict, b_detail: dict,
                   a_detail: dict) -> None:
    for key in EVIDENCE_KEYS:
        need(key in before and key in after and before[key] == after[key],
             "R461_UNCACHED_VS_SCOPED_EVIDENCE_DRIFT")
    need(b_detail == a_detail, "R461_PRIVATE_EVIDENCE_DRIFT")
    for report in (before, after):
        need(report.get("historical_R421_full_inventory_independently_approved")
             is False and report.get("release_authorized") is False
             and report.get("merge_authorized") is False,
             "R461_CUSTODY_RELEASE_OR_MERGE_IMPROPERLY_ENABLED")


def run(original: Path, *, synthetic: bool) -> dict:
    # R459's undecorated implementation is the explicit comparison target.
    # No global patching or disable switch is required.
    legacy_fn = r459.inspect.__wrapped__
    start, _ = r446.observe()
    original_bytes = r447.read_pinned_original(original)
    need(sha256(original_bytes).hexdigest() == r447.ORIGINAL_SHA,
         "R461_PINNED_ORIGINAL_NOT_VERIFIED")
    baseline, baseline_hot, baseline_totals = profile_one(
        legacy_fn, original)
    scoped, scoped_hot, scoped_totals = profile_one(
        r459.inspect, original)
    # Private worklist objects stay in RAM and never leave stdout.
    b_result, b_detail = legacy_fn(original)
    a_result, a_detail = r459.inspect(original)
    require_parity(baseline, scoped, b_detail, a_detail)
    require_parity(b_result, a_result, b_detail, a_detail)
    finish, _ = r446.observe()
    need(start == finish, "R461_OWNER_INVENTORY_CHANGED_DURING_PROFILE")
    need(sha256(r447.read_pinned_original(original)).hexdigest() ==
         r447.ORIGINAL_SHA, "R461_ORIGINAL_CHANGED_DURING_PROFILE")
    need(scoped["R461_scoped_instruction_decode_hits"] > 0,
         "R461_SCOPED_CACHE_NOT_ACTUALLY_USED")
    return {
        "schema": SCHEMA,
        "status": "R461_SYNTHETIC_PARSER_PROFILE_UNAPPROVED" if synthetic else
                  "R461_OWNER_PRIVATE_STATIC_PARSER_PROFILE_UNAPPROVED",
        "data_origin": "invented_public_fixture" if synthetic else
                       "pinned_owner_private_current_source",
        "original_v309_exact_SHA_verified": True,
        "source_classes_and_dependencies_unchanged": True,
        "rebuilt_class_count": a_result["isolated_r421_compiled_classes"],
        "shared_static_evidence_and_private_worklists_exactly_match": True,
        "uncached_R459": {
            "profile": baseline_totals,
            "hottest_public_symbols_by_Python_self_time": baseline_hot,
        },
        "scoped_R459": {
            "profile": scoped_totals,
            "hottest_public_symbols_by_Python_self_time": scoped_hot,
            "instruction_decode_hits":
                scoped["R461_scoped_instruction_decode_hits"],
            "instruction_decode_misses":
                scoped["R461_scoped_instruction_decode_misses"],
            "cached_method_bodies_at_exit":
                scoped["R461_cached_method_bodies_at_exit"],
            "instruction_decode_evictions":
                scoped["R461_instruction_decode_evictions"],
            "oversize_method_cache_skips":
                scoped["R461_oversize_method_cache_skips"],
        },
        "cProfile_measures_instrumented_Python_functions_not_wall_speedup": True,
        "real_owner_speedup_measured": False,
        "runtime_client_network_latency_or_FPS_measured": False,
        "class_or_source_names_from_owner_in_report": False,
        "source_or_class_bytes_uploaded": False,
        "historical_R421_full_inventory_independently_approved": False,
        "player_history_or_R415_R417_journals_accessed": False,
        "merge_authorized": False,
        "release_authorized": False,
    }


def run_synthetic() -> dict:
    tests = ROOT / "tests"
    if str(tests) not in sys.path:
        sys.path.insert(0, str(tests))
    from test_v309_r458_bootstrap_callsite import R458OwnerInventedOffline
    fixture = R458OwnerInventedOffline(
        "test_31_all_inherited_pinned_owner_inputs_required")
    try:
        fixture.setUp()
        return run(fixture.original_jar, synthetic=True)
    finally:
        fixture.doCleanups()


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("--synthetic", action="store_true")
    mode.add_argument("--owner-original-v309-jar", type=Path)
    args = cli.parse_args(argv)
    try:
        result = (run_synthetic() if args.synthetic else
                  run(args.owner_original_v309_jar, synthetic=False))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, r446.Refused, r447.Refused, r459.Refused,
            r450.Refused, ValueError, OSError, TypeError) as exc:
        reason = str(exc)[:120] if isinstance(
            exc, (Refused, r446.Refused, r447.Refused, r459.Refused,
                  r450.Refused)) else "R461_PRIVATE_PROFILE_INPUT_REFUSED"
        print(json.dumps({
            "status": "R461_STATIC_PARSER_PROFILE_REFUSED",
            "reason": reason,
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
