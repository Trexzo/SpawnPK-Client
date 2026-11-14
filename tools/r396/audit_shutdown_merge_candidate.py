#!/usr/bin/env python3
"""R396: source-only fail-closed two-class async-shutdown merge candidate gate.

This never runs or loads the private game, opens user histories, executes a
plugin, launches a GUI, or publishes original/recovered source. It verifies
a SHA-pinned, disposable private source/class candidate against the archived
source reference; all actual file changes stay owner-local.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path

_R395 = Path(__file__).resolve().parents[1] / "r395" / "audit_private_candidate_delta.py"
if not _R395.is_file():
    raise RuntimeError("Inherited R395 static source scope gate missing")
spec = importlib.util.spec_from_file_location("r396_inherit_r395", _R395)
r395 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r395)
Refused = r395.Refused
r394 = r395.r394
r393 = r395.r393

PLUGIN = "rs/plugins/loottracker/LootTrackerPlugin.java"
STORE = "rs/plugins/loottracker/LootHistoryStore.java"
EXPECTED_SOURCES = {PLUGIN, STORE}
EXPECTED_CLASSES = {n[:-5] + ".class" for n in EXPECTED_SOURCES}


def require(source: str, needle: str, reason: str) -> None:
    if needle not in source:
        raise Refused(reason)


def check_structure(plugin: bytes, store: bytes) -> dict:
    # The inherited R395 gate expects the earlier lenient read spelling.
    # Normalize that *one token in memory* for inherited barrier checks;
    # the new strict method is checked separately below.
    if plugin.count(b"restoreStore.loadForMerge(") != 1:
        raise Refused("ASYNC_STRICT_SOURCE_CALL_COUNT_DRIFT")
    inherited_source = plugin.replace(b"restoreStore.loadForMerge(",
                                      b"restoreStore.load(")
    flags = r395.static_assertions(inherited_source)
    try:
        p = r393.mask_java(plugin.decode("utf-8"))
        s = r393.mask_java(store.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise Refused("PRIVATE_CANDIDATE_NON_UTF8") from exc

    strict = r394.method_body(s, "loadForMerge")
    relaxed = r394.method_body(s, "load")
    receipt_save = r394.method_body(s, "saveWithReceipt")
    old_save = r394.method_body(s, "save")
    fallback = r394.method_body(p, "r396FinishStopMerge")
    shutdown = r394.method_body(p, "shutDown")
    persist = r394.method_body(p, "persistHistory")
    clear = r394.method_body(p, "clearHistory")
    startup = r394.method_body(p, "startUp")
    load = r394.method_body(p, "loadHistory")
    requires = (
        (strict, "return null;", "STRICT_HISTORY_INVALID_RETURNS_MISSING"),
        (strict, "if (record == null)", "STRICT_DTO_VALIDATION_MISSING"),
        (relaxed, "loadForMerge(", "LEGACY_LOAD_WRAPPER_MISSING"),
        (receipt_save, "AtomicFileReplace.move(", "RECEIPT_ATOMIC_MOVE_MISSING"),
        (receipt_save, "return true;", "RECEIPT_SUCCESS_MISSING"),
        (receipt_save, "return false;", "RECEIPT_FAILURE_MISSING"),
        (old_save, "saveWithReceipt(", "LEGACY_SAVE_WRAPPER_MISSING"),
        (fallback, "historyStore.loadForMerge(", "STOP_STRICT_HISTORY_READ_MISSING"),
        (fallback, "historyStore.saveWithReceipt(", "STOP_VERIFIED_COMMIT_MISSING"),
        (fallback, "if (!committed)", "STOP_COMMIT_FAILURE_CHECK_MISSING"),
        (fallback, "r396PreloadRecords.clear(", "STOP_PRELOAD_DRAIN_MISSING"),
        (shutdown, "r396FinishStopMerge(", "SHUTDOWN_MERGE_DISPATCH_MISSING"),
        (persist, "historyStore.saveWithReceipt(", "RUNTIME_SAVE_RECEIPT_MISSING"),
        (clear, "r396PreloadRecords.clear(", "CLEAR_PRELOAD_INVALIDATION_MISSING"),
        (startup, "r396PanelResetAfterVerifiedStop", "STARTUP_PANEL_RECONCILIATION_MISSING"),
        (load, "restoreStore.loadForMerge(", "ASYNC_STRICT_READ_MISSING"),
        (p, "r396PreloadRecords.add(record)", "LIVE_DROP_REPLAY_CAPTURE_MISSING"),
        (p, "r396LastCommitSucceeded = false", "DIRTY_COMMIT_GUARD_MISSING"),
    )
    for body, needle, reason in requires:
        require(body, needle, reason)
    if not r395.ordered(fallback,
                        "historyStore.loadForMerge(", "new ArrayList<>(original)",
                        "combined.addAll(r396PreloadRecords)",
                        "historyStore.saveWithReceipt(", "if (!committed)",
                        "r396PreloadRecords.clear(", "return true;"):
        raise Refused("STOP_TRANSACTION_ORDER_DRIFT")
    if not r395.ordered(shutdown, "r396FinishStopMerge(", "if (!r396MergedBeforeStop)",
                        "persistHistory("):
        raise Refused("SHUTDOWN_FALLBACK_ORDER_DRIFT")
    if not r395.ordered(receipt_save, "AtomicFileReplace.move(", "return true;"):
        raise Refused("STORE_ACK_BEFORE_COMMIT")
    if not r395.ordered(persist, "if (!historyLoaded)", "panel.getRecordsOffEdt(",
                        "historyStore.saveWithReceipt(", "r396LastCommitSucceeded = true"):
        raise Refused("LIVE_SAVE_GUARD_ORDER_DRIFT")
    if not r395.ordered(load, "restoreStore.loadForMerge(", "stored == null",
                        "SwingUtilities.invokeLater("):
        raise Refused("ASYNC_UNREADABLE_SOURCE_GUARD_MISSING")
    if not r395.ordered(clear, "++r395HistoryGeneration",
                        "r396PreloadRecords.clear(", "pendingRecords.clear("):
        raise Refused("CLEAR_GENERATION_ORDER_DRIFT")
    if "r396PreloadRecords.clear(" in load:
        raise Refused("INFLIGHT_DROPS_CLEARED_DURING_RESTORE")
    return {
        **flags,
        "strict_history_load_failure_distinguishable": True,
        "strict_invalid_record_refusal_present": True,
        "verified_save_receipt_source_structure": True,
        "shutdown_original_then_preload_then_commit_order": True,
        "clear_invalidates_preload_queue": True,
        "restart_panel_reset_guard_present": True,
        "no_automatic_source_release": True,
    }


def audit(*, kit: Path, reference: Path, sources: Path, classes: Path,
          kit_sha: str, reference_sha: str,
          expected_sources: int = 1277, expected_classes: int = 1388) -> dict:
    r395.require_pin(kit, kit_sha)
    r395.require_pin(reference, reference_sha)
    base_sources = r395.read_zip_bytes(kit, "source/", ".java")
    new_sources = r395.read_tree_bytes(sources, ".java")
    if (len(base_sources) != expected_sources or
            len(new_sources) != expected_sources or
            base_sources.keys() != new_sources.keys()):
        raise Refused("SOURCE_SET_DRIFT")
    changed_sources = {k for k in base_sources if base_sources[k] != new_sources[k]}
    if changed_sources != EXPECTED_SOURCES:
        raise Refused("SOURCE_CHANGE_SCOPE_DRIFT")
    base_classes = r395.read_zip_bytes(reference, "", ".class")
    new_classes = r395.read_tree_bytes(classes, ".class")
    if (len(base_classes) != expected_classes or
            len(new_classes) != expected_classes or
            base_classes.keys() != new_classes.keys()):
        raise Refused("CLASS_SET_DRIFT")
    changed_classes = {k for k in base_classes if base_classes[k] != new_classes[k]}
    if changed_classes != EXPECTED_CLASSES:
        raise Refused("COMPILED_CHANGE_SCOPE_DRIFT")
    checks = check_structure(new_sources[PLUGIN], new_sources[STORE])
    return {
        "status": "R396_PRIVATE_SHUTDOWN_MERGE_STATIC_GATE_PASS",
        "java_source_count": len(new_sources),
        "compiled_class_count": len(new_classes),
        "changed_private_source_count": len(changed_sources),
        "changed_private_class_count": len(changed_classes),
        "changed_classes": sorted(changed_classes),
        **checks,
        "client_executed": False,
        "private_runtime_integration_tested": False,
        "normal_host_execution_authorized": False,
        "power_loss_durability_proven": False,
        "concurrent_writer_isolation_proven": False,
        "shutdown_failure_zero_loss_proven": False,
        "ui_shutdown_latency_bounded": False,
        "original_v309_behavioral_parity_proven": False,
        "merge_approved": False,
        "private_source_release_approved": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kit", type=Path, required=True)
    p.add_argument("--kit-sha256", required=True)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--reference-sha256", required=True)
    p.add_argument("--candidate-sources", type=Path, required=True)
    p.add_argument("--candidate-classes", type=Path, required=True)
    p.add_argument("--expected-sources", type=int, default=1277)
    p.add_argument("--expected-classes", type=int, default=1388)
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    try:
        if args.out and (args.out.exists() or args.out.is_symlink()):
            raise Refused("REFUSE_EXISTING_OUTPUT")
        result = audit(kit=args.kit, kit_sha=args.kit_sha256,
                       reference=args.reference, reference_sha=args.reference_sha256,
                       sources=args.candidate_sources, classes=args.candidate_classes,
                       expected_sources=args.expected_sources,
                       expected_classes=args.expected_classes)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.out:
            with args.out.open("x", encoding="utf-8") as f:
                f.write(rendered)
        else:
            print(rendered, end="")
        return 0
    except (Refused, OSError, ValueError) as exc:
        reason = str(exc) if isinstance(exc, Refused) else "FILESYSTEM_OR_INPUT_ERROR"
        print(json.dumps({"status": "R396_REFUSED", "reason": reason}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
