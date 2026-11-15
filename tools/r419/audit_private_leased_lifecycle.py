#!/usr/bin/env python3
"""R419 read-only SHA-pinned private history-lease lifecycle admission gate.

Requires owner-explicit paths. Never emits Java/class bytes, opens player history,
launches a game, removes locks, or authorizes release. Structural checks are
necessary but NOT sufficient for deadlock freedom or original-client runtime.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

STORE = "rs/plugins/loottracker/LootHistoryStore.java"
PLUGIN = "rs/plugins/loottracker/LootTrackerPlugin.java"
CHANGED = {STORE, PLUGIN}
CLASS = lambda path: path[:-5] + ".class"


class Refused(Exception):
    pass


def need(condition: bool, code: str):
    if not condition:
        raise Refused(code)


def tree(root: Path, suffix: str) -> dict[str, str]:
    need(root.is_dir() and not root.is_symlink(), "R419_INVALID_TREE")
    result = {}
    for item in root.rglob("*" + suffix):
        need(item.is_file() and not item.is_symlink(), "R419_UNSAFE_TREE_ENTRY")
        key = item.relative_to(root).as_posix()
        need(key not in result, "R419_DUPLICATE_PATH")
        result[key] = sha256(item.read_bytes()).hexdigest()
    return result


def method_body(source: str, name: str) -> str:
    pattern = r"\b" + re.escape(name) + r"\s*\([^;{}]*\)\s*(?:throws\s+[\w, ]+\s*)?\{"
    match = re.search(pattern, source)
    need(match is not None, "R419_METHOD_MISSING_" + name)
    start = source.index("{", match.start())
    level = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            level += 1
        elif source[index] == "}":
            level -= 1
            if not level:
                return source[start + 1:index]
    raise Refused("R419_METHOD_UNBALANCED_" + name)


def ordered(source: str, *parts: str) -> bool:
    cursor = 0
    for part in parts:
        cursor = source.find(part, cursor)
        if cursor < 0:
            return False
        cursor += len(part)
    return True


def check_source(store: str, plugin: str) -> dict:
    # Comments are not evidence for the actual method contracts.
    store = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", " ", store)
    plugin = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", " ", plugin)
    activate = method_body(store, "r419ActivateOwner")
    close = method_body(store, "r419CloseOwner")
    stage = method_body(store, "r411StageState")
    with_owner = method_body(store, "r419WithOwner")
    cleanup = method_body(store, "deleteStale")
    load = method_body(store, "loadForMerge")
    save = method_body(store, "r415SaveWithReceipt")
    clear = method_body(store, "clearWithReceipt")
    worker = method_body(plugin, "loadHistory")
    start = method_body(plugin, "startUp")
    stop = method_body(plugin, "shutDown")
    persist = method_body(plugin, "persistHistory")
    panel_delete = method_body(plugin, "r402ApplyPanelDeletion")
    clear_panel = method_body(plugin, "clearHistory")

    need("volatile R418CooperativeLease r419Owner" in store,
         "R419_OWNER_NOT_VOLATILE")
    need(ordered(activate, "if (r419Owner != null)",
                 "r418TryAcquireCooperativeLease()", "r419Owner = admitted;"),
         "R419_ASYNC_LEASE_ADMISSION_DRIFT")
    need(ordered(close, "r419Owner = null;", "prior.close();"),
         "R419_CLOSE_MUST_REVOKE_FIRST")
    need("owner.withOwner(owner.sessionToken(), operation)" in with_owner,
         "R419_OS_LOCK_NOT_HELD_THROUGH_ACTION")
    need(ordered(stage, "if (!r419OwnsLease())",
                 "return R411StageState.UNSAFE;", "r417UnresolvedAckEvidence()"),
         "R419_ADMISSION_NOT_FENCED")
    need("r419WithOwner(this::r419DeleteStaleLeased)" in cleanup,
         "R419_CLEANUP_NOT_LEASED")
    need("r419WithOwner(() -> receipt.add(r419LoadForMergeLeased()))" in load,
         "R419_HISTORY_READ_NOT_LEASED")
    need("r419WithOwner(() ->" in save and
         "r419SaveWithReceiptLeased(records, confirmedDeletion)" in save and
         "R413WriteDisposition.FAILED_BEFORE_REPLACE" in save,
         "R419_HISTORY_SAVE_OR_PRE_REPLACE_RECEIPT_UNSAFE")
    need("r419WithOwner(() -> receipt[0] = r419ClearWithReceiptLeased())" in clear,
         "R419_CLEAR_NOT_LEASED")
    need("historyStore = new LootHistoryStore()" in start,
         "R419_STORE_START_MISSING")
    need("historyStore.deleteStale()" not in start,
         "R419_STARTUP_DISK_CLEANUP_BEFORE_LEASE")
    need(worker.count("restoreStore.r419ActivateOwner()") == 1 and
         worker.count("restoreStore.deleteStale()") == 1 and
         worker.count("restoreStore.loadForMerge()") == 1,
         "R419_DUPLICATE_OR_UNBOUNDED_RESTORE_IO")
    need("new Thread" in worker and
         ordered(worker, "restoreStore.r419ActivateOwner()",
                 "generation != r395HistoryGeneration",
                 "restoreStore.deleteStale()",
                 "restoreStore.loadForMerge()",
                 "SwingUtilities.invokeLater("),
         "R419_RESTORE_SESSION_ACQUIRE_ORDER_UNSAFE")
    need(ordered(stop, "r419ShutdownCommitThread = Thread.currentThread()",
                 "instance = null", "persistHistory()",
                 "r419ShutdownCommitThread = null",
                 "closingStore::r419CloseOwner"),
         "R419_SHUTDOWN_COMMIT_OR_RELEASE_ORDER_UNSAFE")
    need("if (!r399AcceptingDrops &&" in persist and
         "Thread.currentThread() != r419ShutdownCommitThread" in persist,
         "R419_STALE_CALLBACK_SAVE_NOT_FENCED")
    for body, name in ((panel_delete, "PANEL_DELETE"), (clear_panel, "CLEAR_ALL")):
        need("!r399AcceptingDrops || instance != this" in body,
             "R419_STALE_"+name+"_NOT_FENCED")
    for token in ("Files.delete", "Files.move", "Files.createLink"):
        need(token not in close and token not in activate and token not in with_owner,
             "R419_OWNER_LIFECYCLE_MUST_NOT_CLEAN_FILES")
    # Actual Game client remains unverified; diagnostics must not mark READY.
    return {
        "background_owner_acquisition_required": True,
        "startup_cleanup_moved_behind_owner": True,
        "all_four_history_entrypoint_wrappers": True,
        "r411_ack_and_lease_fence": True,
        "stale_session_saves_and_panel_edits_fenced": True,
        "shutdown_revoke_then_async_lease_release": True,
        "source_only_not_end_to_end_runtime": True,
    }


def audit(prior_sources: Path, candidate_sources: Path,
          prior_classes: Path, candidate_classes: Path,
          pins: dict[str, str]) -> dict:
    a, b = tree(prior_sources, ".java"), tree(candidate_sources, ".java")
    c, d = tree(prior_classes, ".class"), tree(candidate_classes, ".class")
    need(len(a) == len(b) == 1277 and a.keys() == b.keys(),
         "R419_SOURCE_INVENTORY_DRIFT")
    need(len(c) == len(d) == 1394 and c.keys() == d.keys(),
         "R419_COMPILED_INVENTORY_DRIFT")
    need({x for x in b if b[x] != a[x]} == CHANGED,
         "R419_EXACT_TWO_SOURCE_SCOPE_REQUIRED")
    need({x for x in d if d[x] != c[x]} == {CLASS(x) for x in CHANGED},
         "R419_EXACT_TWO_CLASS_SCOPE_REQUIRED")
    for target, actual in (
        ("prior-store", a[STORE]), ("candidate-store", b[STORE]),
        ("prior-plugin", a[PLUGIN]), ("candidate-plugin", b[PLUGIN]),
    ):
        pin = pins[target]
        need(re.fullmatch(r"[0-9a-f]{64}", pin) is not None and actual == pin,
             "R419_SOURCE_PIN_DRIFT_" + target)
    checks = check_source(
        (candidate_sources / STORE).read_text("utf8"),
        (candidate_sources / PLUGIN).read_text("utf8"))
    return {
        "status": "R419_PRIVATE_OWNER_LEASE_LIFECYCLE_STATIC_GATE_PASS",
        "source_count": 1277,
        "class_count": 1394,
        "changed_sources": 2,
        "changed_classes": 2,
        **checks,
        "original_client_executed": False,
        "production_history_opened": False,
        "merge_authorized": False,
        "private_release_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prior-sources", "candidate-sources", "prior-classes",
                 "candidate-classes"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("prior-store", "candidate-store", "prior-plugin", "candidate-plugin"):
        parser.add_argument("--" + name + "-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        pins = {name: getattr(args, name.replace("-", "_") + "_sha256") for name
                in ("prior-store", "candidate-store", "prior-plugin", "candidate-plugin")}
        result = audit(args.prior_sources, args.candidate_sources,
                       args.prior_classes, args.candidate_classes, pins)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, OSError, ValueError, UnicodeError, KeyError) as e:
        print(json.dumps({"status": "R419_REFUSED",
                          "reason": str(e) if isinstance(e, Refused) else "INVALID_INPUT"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
