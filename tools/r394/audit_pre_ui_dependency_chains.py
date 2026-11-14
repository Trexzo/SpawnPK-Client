#!/usr/bin/env python3
"""R394: nonexecuting startup dependency/EDT/file-I/O path witness.

Reads an owner-private SHA-pinned Java source ZIP in memory without extraction.
The output reports narrowly grounded path indicators. It never launches the
client, loads plugins, reads the user's histories or touches production files.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re

_R393 = Path(__file__).resolve().parents[1] / "r393" / "audit_plugin_startup.py"
if not _R393.is_file():
    raise RuntimeError("Missing inherited R393 source-only verifier")
_spec = importlib.util.spec_from_file_location("r394_import_r393", _R393)
_r393 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_r393)
Refused = _r393.Refused

PATHS = {
    "bootstrap": "source/rs/pkg42/Class255.java",
    "plugin_manager": "source/rs/plugins/PluginManager.java",
    "client_ui": "source/rs/ui/ClientUI.java",
    "loadouts_plugin": "source/rs/plugins/loadouts/LoadoutsPlugin.java",
    "loadouts_panel": "source/rs/gui/loadouts/LoadoutsPanel.java",
    "image_loader": "source/rs/gui/loadouts/ImageLoader.java",
    "icon_worker": "source/rs/gui/loadouts/io/LoadoutIconWorker.java",
    "loadout_store": "source/rs/gui/loadouts/io/LoadoutStore.java",
    "loot_plugin": "source/rs/plugins/loottracker/LootTrackerPlugin.java",
    "loot_history_store": "source/rs/plugins/loottracker/LootHistoryStore.java",
}


def method_body(source: str, name: str) -> str:
    """Conservative method-body extraction after masking literals/comments."""
    if not re.fullmatch(r"[a-zA-Z_$][\w$]*", name):
        raise Refused("INVALID_METHOD_NAME")
    if name == "LoadoutsPanel":
        expression = _r393.constructor_pattern(name)
    else:
        # Require a declaration's return type. Calls in conditions (such as
        # 'if (deleteTree(...)) {') must not masquerade as method bodies.
        expression = re.compile(
            r"(?m)(?:^[ \t]*|(?<=[;{}])[ \t]*)"
            r"(?:(?:public|private|protected|static|final|synchronized)\s+)*"
            r"[\w$<>?,\[\]]+\s+" + re.escape(name)
            + r"\s*\([^;{}]*\)\s*(?:throws\s+[\w\s,.]+)?\s*\{"
        )
    matches = list(expression.finditer(source))
    if len(matches) != 1:
        raise Refused("METHOD_NOT_UNIQUELY_DEFINED")
    match = matches[0]
    opening = source.find("{", match.start(), match.end())
    return _r393.braced_body(source, opening)


def require_chain(text: str, *pieces: str) -> None:
    positions = [text.find(x) for x in pieces]
    if any(v < 0 for v in positions) or positions != sorted(positions) or len(set(positions)) != len(positions):
        raise Refused("STARTUP_CHAIN_MISSING_OR_REORDERED")


def report_from_sources(sources: dict[str, str]) -> dict:
    if any(path not in sources for path in PATHS.values()):
        raise Refused("REQUIRED_SOURCE_MISSING")
    a = {key: sources[p] for key, p in PATHS.items()}
    bootstrap = method_body(a["bootstrap"], "method3355")
    require_chain(bootstrap, ".loadPlugins(", ".startPlugins(", ".show(")
    manager = method_body(a["plugin_manager"], "startPlugins")
    require_chain(manager, "SwingUtilities.invokeAndWait(", "this.startPlugin(")
    start_plugin = method_body(a["plugin_manager"], "startPlugin")
    if ".startUp(" not in start_plugin:
        raise Refused("PLUGIN_STARTUP_DISPATCH_NOT_FOUND")
    client_show = method_body(a["client_ui"], "show")
    if "SwingUtilities.invokeLater(" not in client_show:
        raise Refused("UI_SHOW_ENQUEUE_MISSING")

    loot_start = method_body(a["loot_plugin"], "startUp")
    require_chain(loot_start, "new LootHistoryStore(", "historyStore.deleteStale(", "loadHistory(")
    history_request = method_body(a["loot_plugin"], "loadHistory")
    require_chain(history_request, "SwingUtilities.invokeLater(", "historyStore.load(")
    loot_load = method_body(a["loot_history_store"], "load")
    if "Files.newInputStream(" not in loot_load:
        raise Refused("LOOT_HISTORY_READ_NOT_FOUND")
    if "MAX_HISTORY_BYTES" not in loot_load or "GSON.a(" not in loot_load:
        raise Refused("LOOT_HISTORY_BOUNDS_OR_PARSE_MISSING")
    if not re.search(
        r"\bMAX_HISTORY_BYTES\s*=\s*64L\s*\*\s*1024L\s*\*\s*1024L\s*;",
        a["loot_history_store"],
    ):
        raise Refused("LOOT_HISTORY_BYTE_LIMIT_CHANGED")
    cleanup = method_body(a["loot_history_store"], "deleteStale")
    recursive = method_body(a["loot_history_store"], "deleteTree")
    if not ("deleteTree(" in cleanup and ".delete(" in cleanup
            and "Files.deleteIfExists(" in recursive):
        raise Refused("LOOT_CLEANUP_PATH_CHANGED")

    loadouts_start = method_body(a["loadouts_plugin"], "startUp")
    if "new LoadoutsPanel(" not in loadouts_start:
        raise Refused("LOADOUTS_PANEL_INIT_MISSING")
    panel_ctor = method_body(a["loadouts_panel"], "LoadoutsPanel")
    require_chain(
        panel_ctor, "ImageLoader.start(", "new LoadoutStore(",
        ".store.loadFolder(", ".store.writeFolderOrderSettings(",
    )
    panel_delete_calls = len(re.findall(r"\.delete\s*\(", panel_ctor))
    if panel_delete_calls < 1:
        raise Refused("LOADOUTS_CONSTRUCTOR_DELETE_PATH_MISSING")
    store_load = method_body(a["loadout_store"], "loadFolder")
    if not re.search(
        r"if\s*\(\s*!var5\.exists\(\)\s*&&\s*var2\s*\)"
        r"\s*\{\s*var4\.delete\s*\(\s*\)\s*;",
        store_load,
    ):
        raise Refused("LOADOUTS_LEGACY_DELETE_BRANCH_CHANGED")
    store_order_write = method_body(a["loadout_store"], "writeFolderOrderSettings")
    # The public entrypoint takes a file lock then delegates the actual
    # temporary-write + atomic-move path to a private helper.
    if "this.writeFolderOrderSettingsWithLock(" not in store_order_write:
        raise Refused("LOADOUTS_ORDER_WRITE_DELEGATION_CHANGED")
    store_order_helper = method_body(a["loadout_store"], "writeFolderOrderSettingsWithLock")
    if "Files.newBufferedWriter(" not in store_order_helper or "Files.move(" not in store_order_helper:
        raise Refused("LOADOUTS_ORDER_WRITE_PATH_CHANGED")
    loader = a["image_loader"]
    loader_start = method_body(loader, "start")
    if not (re.search(r"\bExecutors\s*\.\s*newFixedThreadPool\s*\(\s*5\s*\)", loader)
            and "field3284.submit(" in loader_start and "new LoadoutIconWorker(" in loader_start):
        raise Refused("LOADOUTS_EXECUTOR_PATH_CHANGED")
    worker_run = method_body(a["icon_worker"], "run")
    # Empty run() is evidence about the current body, not proof of quiescence
    # or that these pooled threads have a bounded lifetime.
    no_worker_body = not worker_run.strip()
    if not no_worker_body:
        raise Refused("ICON_WORKER_RUN_NO_LONGER_EMPTY")
    references_to_pool_shutdown = sum(
        len(re.findall(r"(?:ImageLoader\s*\.\s*)?field3284\s*\.\s*shutdown(?:Now)?\s*\(", text))
        for text in sources.values()
    )
    return {
        "status": "R394_STATIC_PRE_UI_EDT_IO_WITNESS",
        "source_count": len(sources),
        "bootstrap_plugin_start_precedes_ui_show": True,
        "plugin_start_dispatches_on_edt_invoke_and_wait": True,
        "loot_history_callback_enqueued_on_edt": True,
        "ui_show_callback_enqueued_on_edt": True,
        "loot_history_file_read_and_json_parse_in_callback": True,
        "loot_history_read_max_bytes": 64 * 1024 * 1024,
        "loot_history_retired_layout_recursive_cleanup_path": True,
        "loadouts_panel_initialized_in_plugin_startup": True,
        "loadouts_panel_constructor_explicit_delete_invocations": panel_delete_calls,
        "loadouts_panel_load_folder_before_order_write": True,
        "loadouts_folder_load_contains_conditional_legacy_delete": True,
        "loadouts_order_write_uses_buffered_write_and_move": True,
        "loadouts_fixed_executor_workers": 5,
        "loadouts_executor_worker_runnable_body_empty": True,
        "source_references_to_executor_shutdown": references_to_pool_shutdown,
        "source_reference_search_is_not_lifecycle_proof": True,
        "runtime_EDT_queue_order_verified": False,
        "runtime_plugin_enablement_verified": False,
        "runtime_freeze_root_cause_proven": False,
        "source_parser_semantic_equivalence_proven": False,
        "client_executed": False,
        "real_user_data_accessed": False,
        "isolated_guest_verified": False,
        "launch_authorized": False,
        "private_source_release_approved": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--kit-sha256", required=True)
    parser.add_argument("--expected-sources", type=int, default=1277)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        _r393.pinned_archive(args.kit, args.kit_sha256)
        if args.out and (args.out.exists() or args.out.is_symlink()):
            raise Refused("OUTPUT_ALREADY_EXISTS")
        sources = _r393.load_sources(args.kit, args.expected_sources)
        report = report_from_sources(sources)
        report["private_kit_sha256"] = args.kit_sha256
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.out:
            with args.out.open("x", encoding="utf-8") as target:
                target.write(rendered)
        else:
            print(rendered, end="")
        return 0
    except (Refused, OSError) as exc:
        reason = str(exc) if isinstance(exc, Refused) else "FILESYSTEM_FAILURE"
        print(json.dumps({"status": "R394_REFUSED", "reason": reason}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
