#!/usr/bin/env python3
"""R397 public-safe read-only verifier for the private clean-stop fast path.

No extraction, plugin execution, user histories, game network or GUI.
Accepts SHA-pinned R381 originals, two *disposable* private candidate trees,
and emits no Java bodies or confidential files.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re

_PARENT = Path(__file__).resolve().parents[1] / "r396" / "audit_shutdown_merge_candidate.py"
if not _PARENT.is_file():
    raise RuntimeError("Missing R396 inherited static verifier")
spec = importlib.util.spec_from_file_location("r397_inherit_r396", _PARENT)
r396 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r396)
r395, r394, r393 = r396.r395, r396.r394, r396.r393
Refused = r395.Refused

PLUGIN_SOURCE = r396.PLUGIN
PLUGIN_CLASS = PLUGIN_SOURCE[:-5] + ".class"


def guard_flags(java_source: bytes) -> dict:
    try:
        masked = r393.mask_java(java_source.decode("utf-8"))
    except UnicodeDecodeError as e:
        raise Refused("NON_UTF8_PRIVATE_SOURCE") from e
    method = r394.method_body(masked, "r396FinishStopMerge")
    # Count direct guard occurrences; avoid merely matching string literals
    # or comments and do not interpret any later helper code as validation.
    guard = re.search(
        r"synchronized\s*\(\s*r395HistoryGate\s*\)\s*\{\s*"
        r"if\s*\(\s*r396PreloadRecords\s*\.\s*isEmpty\s*\(\s*\)\s*&&"
        r"\s*pendingRecords\s*\.\s*isEmpty\s*\(\s*\)\s*&&"
        r"\s*panel\s*\.\s*getRecordsOffEdt\s*\(\s*\)\s*"
        r"\.\s*isEmpty\s*\(\s*\)\s*\)\s*\{\s*return\s+true\s*;"
        r"\s*\}\s*\}",
        method
    )
    if guard is None:
        raise Refused("CLEAN_STOP_TRIPLE_EMPTY_GUARD_MISSING")
    load_index = method.find("historyStore.loadForMerge(")
    if load_index < 0 or guard.end() >= load_index:
        raise Refused("CLEAN_STOP_GUARD_NOT_BEFORE_DISK_IO")
    if method.count("historyStore.loadForMerge(") != 1:
        raise Refused("STRICT_MERGE_READ_SCOPE_DRIFT")
    if method.count("historyStore.saveWithReceipt(") != 1:
        raise Refused("STRICT_MERGE_SAVE_SCOPE_DRIFT")
    if "combined.addAll(r396PreloadRecords)" not in method:
        raise Refused("DIRTY_MERGE_PATH_MISSING")
    return {
        "fastpath_requires_all_three_buffers_empty": True,
        "fastpath_returns_before_strict_disk_read": True,
        "dirty_shutdown_merge_retained": True,
        "fastpath_actual_runtime_latency_measured": False,
    }


def audit(kit: Path, kit_sha: str, reference: Path, reference_sha: str,
          previous_sources: Path, previous_classes: Path,
          candidate_sources: Path, candidate_classes: Path,
          expected_sources: int, expected_classes: int) -> dict:
    inherited = r396.audit(
        kit=kit, kit_sha=kit_sha,
        reference=reference, reference_sha=reference_sha,
        sources=candidate_sources, classes=candidate_classes,
        expected_sources=expected_sources, expected_classes=expected_classes)
    old_sources = r395.read_tree_bytes(previous_sources, ".java")
    new_sources = r395.read_tree_bytes(candidate_sources, ".java")
    if (len(old_sources) != expected_sources or old_sources.keys() != new_sources.keys()):
        raise Refused("PREVIOUS_SOURCE_SET_DRIFT")
    changed_sources = sorted(path for path in old_sources
                             if old_sources[path] != new_sources[path])
    if changed_sources != [PLUGIN_SOURCE]:
        raise Refused("PREVIOUS_SOURCE_DELTA_SCOPE_DRIFT")
    old_classes = r395.read_tree_bytes(previous_classes, ".class")
    new_classes = r395.read_tree_bytes(candidate_classes, ".class")
    if (len(old_classes) != expected_classes or old_classes.keys() != new_classes.keys()):
        raise Refused("PREVIOUS_CLASS_SET_DRIFT")
    changed_classes = sorted(path for path in old_classes
                             if old_classes[path] != new_classes[path])
    if changed_classes != [PLUGIN_CLASS]:
        raise Refused("PREVIOUS_CLASS_DELTA_SCOPE_DRIFT")
    fastpath = guard_flags(new_sources[PLUGIN_SOURCE])
    inherited.pop("status", None)
    return {
        "status": "R397_PRIVATE_CLEAN_STOP_STATIC_GATE_PASS",
        **inherited,
        **fastpath,
        "change_vs_r396_source_count": len(changed_sources),
        "change_vs_r396_class_count": len(changed_classes),
        "changed_class_vs_r396": PLUGIN_CLASS,
        "actual_clean_stop_noop_observed": False,
        "actual_client_executed": False,
        "journal_integrated_with_game": False,
        "real_crash_recovery_durability_proven": False,
        "journal_recovery_across_original_game_versions_proven": False,
        "normal_host_launch_authorized": False,
        "merge_approved": False,
        "private_source_release_approved": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kit", required=True, type=Path)
    p.add_argument("--kit-sha256", required=True)
    p.add_argument("--reference", required=True, type=Path)
    p.add_argument("--reference-sha256", required=True)
    p.add_argument("--previous-sources", required=True, type=Path)
    p.add_argument("--previous-classes", required=True, type=Path)
    p.add_argument("--candidate-sources", required=True, type=Path)
    p.add_argument("--candidate-classes", required=True, type=Path)
    p.add_argument("--expected-sources", type=int, default=1277)
    p.add_argument("--expected-classes", type=int, default=1388)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    try:
        if a.out and (a.out.is_symlink() or a.out.exists()):
            raise Refused("REFUSE_EXISTING_OUTPUT")
        report = audit(a.kit, a.kit_sha256, a.reference, a.reference_sha256,
                       a.previous_sources, a.previous_classes,
                       a.candidate_sources, a.candidate_classes,
                       a.expected_sources, a.expected_classes)
        rendered = json.dumps(report, sort_keys=True, indent=2) + "\n"
        if a.out:
            with a.out.open("x", encoding="utf8") as stream:
                stream.write(rendered)
        else:
            print(rendered, end="")
        return 0
    except (Refused, OSError, ValueError) as exc:
        reason = str(exc) if isinstance(exc, Refused) else "INPUT_OR_FILESYSTEM_FAILURE"
        print(json.dumps({"status":"R397_REFUSED","reason":reason}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
