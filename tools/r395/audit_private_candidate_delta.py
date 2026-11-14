#!/usr/bin/env python3
"""R395 owner-private candidate gate: read-only SHA-pinned source/class delta.

Only reports counts, expected class names and failure categories. Never emits
recovered Java source, JAR contents, user data, original endpoints, or code.
Never executes the game or requires a runtime client. This is NOT permission
to merge, run, share private source, or release.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

_R394 = Path(__file__).resolve().parents[1] / "r394" / "audit_pre_ui_dependency_chains.py"
if not _R394.is_file():
    raise RuntimeError("Missing R394 static source-method helper")
_spec = importlib.util.spec_from_file_location("r395_import_r394", _R394)
r394 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r394)
r393 = r394._r393
Refused = r393.Refused
SOURCE_REL = "rs/plugins/loottracker/LootTrackerPlugin.java"
CLASS_REL = "rs/plugins/loottracker/LootTrackerPlugin.class"
MAX_JAR = 64 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for piece in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(piece)
    return digest.hexdigest()


def require_pin(path: Path, pin: str, *, limit: int = MAX_JAR) -> None:
    if not re.fullmatch(r"[a-f0-9]{64}", pin):
        raise Refused("INVALID_SHA_PIN")
    if not path.is_file() or path.is_symlink() or path.stat().st_size > limit:
        raise Refused("REFUSE_UNSAFE_ARCHIVE")
    if sha256(path) != pin:
        raise Refused("ARCHIVE_SHA_DRIFT")


def validate_zip_member(info: zipfile.ZipInfo) -> None:
    name = info.filename.rstrip("/") if info.is_dir() else info.filename
    if not name or "\\" in name or name.startswith("/") or ":" in name or "//" in name:
        raise Refused("UNSAFE_ZIP_MEMBER")
    if any(part in ("", ".", "..") for part in PurePosixPath(name).parts):
        raise Refused("UNSAFE_ZIP_MEMBER")
    if info.create_system == 3 and stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
        raise Refused("ZIP_SYMLINK")


def read_zip_bytes(path: Path, prefix: str, suffix: str) -> dict[str, bytes]:
    result = {}
    seen = set()
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                validate_zip_member(info)
                if info.filename in seen:
                    raise Refused("DUPLICATE_ZIP_ENTRY")
                seen.add(info.filename)
                if not info.filename.startswith(prefix) or not info.filename.endswith(suffix):
                    continue
                if info.file_size <= 0 or info.file_size > 5 * 1024 * 1024:
                    raise Refused("ZIP_MEMBER_SIZE_LIMIT")
                result[info.filename[len(prefix):]] = archive.read(info)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise Refused("ARCHIVE_READ_FAILED") from exc
    return result


def read_tree_bytes(directory: Path, suffix: str) -> dict[str, bytes]:
    if not directory.is_dir() or directory.is_symlink():
        raise Refused("UNSAFE_DIRECTORY")
    files = {}
    for p in directory.rglob("*"):
        if p.is_symlink():
            raise Refused("SYMLINK_IN_CANDIDATE")
        if not p.is_file() or p.suffix != suffix:
            continue
        if p.stat().st_size > 5 * 1024 * 1024:
            raise Refused("CANDIDATE_FILE_SIZE_LIMIT")
        rel = p.relative_to(directory).as_posix()
        if rel in files:
            raise Refused("DUPLICATE_CANDIDATE_PATH")
        files[rel] = p.read_bytes()
    return files


def ordered(source: str, *needles: str) -> bool:
    # Source methods can contain earlier 'return' in a guard. Match a
    # complete ordered subsequence, rather than comparing first occurrence.
    cursor = 0
    for needle in needles:
        index = source.find(needle, cursor)
        if index < 0:
            return False
        cursor = index + len(needle)
    return True


def static_assertions(source: bytes) -> dict:
    try:
        masked = r393.mask_java(source.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise Refused("NON_UTF8_CANDIDATE") from exc
    load = r394.method_body(masked, "loadHistory")
    start = r394.method_body(masked, "startUp")
    stop = r394.method_body(masked, "shutDown")
    persist = r394.method_body(masked, "persistHistory")
    clear = r394.method_body(masked, "clearHistory")
    expected_load = [
        "r395RestoreInFlight = true",
        "new Thread(",
        "restoreStore.load(",
        "SwingUtilities.invokeLater(",
        "restorePanel.addRecords(",
        "historyLoaded = true",
        "if (deferred)",
        "persistHistory(",
        "worker.setDaemon(true",
        "worker.start(",
    ]
    if not ordered(load, *expected_load):
        raise Refused("ASYNC_LOAD_STRUCTURE_DRIFT")
    if "pendingRecords.clear(" in load:
        raise Refused("PENDING_DROP_CLEAR_IN_RESTORE")
    # A recovery callback also resets the flight flag on read failure,
    # so inspect the successful-apply region rather than the first match.
    after_apply = load.split("restorePanel.addRecords(", 1)[-1]
    if "r395RestoreInFlight = false" not in after_apply:
        raise Refused("SUCCESSFUL_RESTORE_FLIGHT_RESET_MISSING")
    if not ordered(persist,
                   "if (!historyLoaded)", "r395WriteDeferred = true",
                   "return", "panel.getRecordsOffEdt("):
        raise Refused("PERSISTENCE_BARRIER_MISSING")
    if not ordered(clear, "++r395HistoryGeneration", "historyLoaded = true",
                   "pendingRecords.clear("):
        raise Refused("CLEAR_INVALIDATION_MISSING")
    if not ordered(stop, "instance = null", "++r395HistoryGeneration",
                   "persistHistory("):
        raise Refused("STOP_INVALIDATION_MISSING")
    if not ordered(start, "historyLoaded = false", "instance = this"):
        raise Refused("START_GENERATION_RESET_MISSING")
    if "generation != r395HistoryGeneration" not in load:
        raise Refused("STALE_GENERATION_GUARD_MISSING")
    return {
        "background_restore_source_structure_verified": True,
        "EDT_apply_guard_source_structure_verified": True,
        "pending_live_drops_not_cleared_in_restore": True,
        "save_deferral_source_structure_verified": True,
        "clear_stop_generation_invalidation_structure_verified": True,
        "source_only_not_runtime_behavior": True,
    }


def audit(*, kit: Path, reference: Path, sources: Path, classes: Path,
          kit_sha: str, reference_sha: str, expected_sources: int,
          expected_classes: int) -> dict:
    require_pin(kit, kit_sha)
    require_pin(reference, reference_sha)
    baseline_sources = read_zip_bytes(kit, "source/", ".java")
    candidate_sources = read_tree_bytes(sources, ".java")
    if (len(baseline_sources) != expected_sources or
            baseline_sources.keys() != candidate_sources.keys()):
        raise Refused("SOURCE_SET_DRIFT")
    changed_sources = sorted(name for name in baseline_sources
                             if baseline_sources[name] != candidate_sources[name])
    if changed_sources != [SOURCE_REL]:
        raise Refused("SOURCE_CHANGE_SCOPE_DRIFT")
    baseline_classes = read_zip_bytes(reference, "", ".class")
    candidate_classes = read_tree_bytes(classes, ".class")
    if (len(baseline_classes) != expected_classes or
            baseline_classes.keys() != candidate_classes.keys()):
        raise Refused("CLASS_SET_DRIFT")
    changed_classes = sorted(name for name in baseline_classes
                             if baseline_classes[name] != candidate_classes[name])
    if changed_classes != [CLASS_REL]:
        raise Refused("COMPILED_CHANGE_SCOPE_DRIFT")
    structure = static_assertions(candidate_sources[SOURCE_REL])
    return {
        "status": "R395_PRIVATE_CANDIDATE_CLASS_SCOPE_PASS",
        "java_source_count": len(candidate_sources),
        "class_file_count": len(candidate_classes),
        "modified_source_count": len(changed_sources),
        "modified_compiled_class_count": len(changed_classes),
        "modified_class": CLASS_REL,
        **structure,
        "client_initialized_or_executed": False,
        "real_user_data_read": False,
        "game_network_connected": False,
        "shutdown_during_restore_durability_proven": False,
        "real_runtime_race_acceptance_proven": False,
        "original_v309_behavioral_parity_proven": False,
        "launch_authorized": False,
        "private_source_release_approved": False,
        "merge_approved": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kit", required=True, type=Path)
    p.add_argument("--kit-sha256", required=True)
    p.add_argument("--reference", required=True, type=Path)
    p.add_argument("--reference-sha256", required=True)
    p.add_argument("--candidate-sources", required=True, type=Path)
    p.add_argument("--candidate-classes", required=True, type=Path)
    p.add_argument("--expected-sources", type=int, default=1277)
    p.add_argument("--expected-classes", type=int, default=1388)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    try:
        if a.out and (a.out.exists() or a.out.is_symlink()):
            raise Refused("REFUSE_EXISTING_OUTPUT")
        result = audit(
            kit=a.kit, reference=a.reference,
            sources=a.candidate_sources, classes=a.candidate_classes,
            kit_sha=a.kit_sha256, reference_sha=a.reference_sha256,
            expected_sources=a.expected_sources, expected_classes=a.expected_classes,
        )
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if a.out:
            with a.out.open("x", encoding="utf-8") as target:
                target.write(rendered)
        else:
            print(rendered, end="")
        return 0
    except (Refused, OSError, ValueError) as exc:
        reason = str(exc) if isinstance(exc, Refused) else "FILESYSTEM_OR_INPUT_FAILURE"
        print(json.dumps({"status": "R395_REFUSED", "reason": reason}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
