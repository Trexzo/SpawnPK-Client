#!/usr/bin/env python3
"""R425 owner-only SHA-gated overlay compilation and actual-class acceptance.

Future opt-in use ONLY on the R421 owner TEMP isolated source tree. This file
does NOT publish recovered sources, start SpawnPK, use real history paths,
or install/distribute a JAR. Requires real private source access; public CI
only exercises fabricated acceptance/gate invariants.

The R424 private overlay permanently hardcodes commit=false. No real data
is deleted or journal evidence reconciled.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Iterable

# Support owner-local direct CLI invocation as well as python -m, without
# depending on a global PYTHONPATH or user site-packages installation.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.r424.prepare_private_legacy_cleanup_patch import (
    HELPER, STORE, PINNED_R421_STORE_SHA, stage as prepare_r424,
)
from tools.r441.approved_full_inventory import (
    Refused as InventoryRefused, require_approved_baselines,
)

PINNED_R421_STORE_CLASS = (
    "65272371272fdcf9142095880a042aa007a9a088f93c969a57878188fae37a09"
)
BASELINE_SOURCE_COUNT = 1277
BASELINE_CLASS_COUNT = 1394
EXPECTED_HELPER_CLASSES = {
    "rs/plugins/loottracker/LootLegacyCleanupR424.class",
    "rs/plugins/loottracker/LootLegacyCleanupR424$1.class",
    "rs/plugins/loottracker/LootLegacyCleanupR424$Entry.class",
    "rs/plugins/loottracker/LootLegacyCleanupR424$Receipt.class",
    "rs/plugins/loottracker/LootLegacyCleanupR424$Status.class",
}
EXPECTED_CHANGED_EXISTING_CLASS = "rs/plugins/loottracker/LootHistoryStore.class"
MAIN = "rs.plugins.loottracker.R425ActualPrivateOverlayAcceptance"


class Refused(RuntimeError):
    pass


def need(truth: bool, code: str) -> None:
    if not truth:
        raise Refused(code)


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for piece in iter(lambda: f.read(1 << 20), b""):
            h.update(piece)
    return h.hexdigest()


def sha_inventory(root: Path, suffix: str) -> dict[str, str]:
    need(root.is_dir() and not root.is_symlink(), "R425_INVALID_INVENTORY_ROOT")
    out: dict[str, str] = {}
    for p in root.rglob("*" + suffix):
        need(p.is_file() and not p.is_symlink(), "R425_NONREGULAR_INVENTORY_MEMBER")
        name = p.relative_to(root).as_posix()
        need(name not in out, "R425_DUPLICATE_INVENTORY_MEMBER")
        out[name] = hash_file(p)
    return out


def gate_source_inventory(
    prior: dict[str, str], candidate: dict[str, str],
    expected_base_count: int | None = None,
) -> dict:
    # Resolve the default at call-time, allowing invented test-only
    # mini-client baselines without exposing any owner CLI override.
    if expected_base_count is None:
        expected_base_count = BASELINE_SOURCE_COUNT
    helper = HELPER.as_posix()
    store = STORE.as_posix()
    need(len(prior) == expected_base_count,
         "R425_PARENT_SOURCE_COUNT_DRIFT")
    need(set(candidate) - set(prior) == {helper} and
         set(prior) - set(candidate) == set(),
         "R425_EXACT_ONE_ADDED_HELPER_SOURCE_REQUIRED")
    need({key for key in prior if prior[key] != candidate[key]} == {store},
         "R425_EXACT_ONE_MODIFIED_PRIVATE_SOURCE_REQUIRED")
    return {"parent_sources": len(prior),
            "candidate_sources": len(candidate),
            "modified_private_sources": [store],
            "added_public_helper_sources": [helper]}


def gate_class_inventory(
    prior: dict[str, str], candidate: dict[str, str],
    expected_base_count: int | None = None,
) -> dict:
    if expected_base_count is None:
        expected_base_count = BASELINE_CLASS_COUNT
    need(len(prior) == expected_base_count,
         "R425_PARENT_CLASS_COUNT_DRIFT")
    added = set(candidate) - set(prior)
    removed = set(prior) - set(candidate)
    changed = {name for name in prior if name in candidate and
               prior[name] != candidate[name]}
    need(not removed, "R425_NO_PRIVATE_CLASSES_MAY_DISAPPEAR")
    need(added == EXPECTED_HELPER_CLASSES,
         "R425_HELPER_CLASS_ADDITIONS_UNEXPECTED")
    need(changed == {EXPECTED_CHANGED_EXISTING_CLASS},
         "R425_EXISTING_PRIVATE_CLASS_DELTA_UNEXPECTED")
    need(len(candidate) == len(prior) + len(EXPECTED_HELPER_CLASSES),
         "R425_COMPILED_CLASS_INVENTORY_COUNT_DRIFT")
    return {"parent_classes": len(prior),
            "candidate_classes": len(candidate),
            "modified_existing_classes": sorted(changed),
            "added_helper_classes": sorted(added),
            "removed_classes": []}


def validate_inputs(args) -> None:
    for option in ("dependency_a_sha256", "dependency_b_sha256"):
        need(re.fullmatch(r"[0-9a-f]{64}", getattr(args, option)) is not None,
             "R425_INVALID_DEPENDENCY_DIGEST")
    for bin_path in (args.javac, args.java, args.dependency_a,
                     args.dependency_b, args.public_helper_source,
                     args.public_acceptance_source):
        need(bin_path.is_file() and not bin_path.is_symlink(),
             "R425_BAD_OR_SYMLINK_INPUT_FILE")
    need(hash_file(args.dependency_a) == args.dependency_a_sha256,
         "R425_DEPENDENCY_A_SHA_DRIFT")
    need(hash_file(args.dependency_b) == args.dependency_b_sha256,
         "R425_DEPENDENCY_B_SHA_DRIFT")

    prior_source = args.prior_source_root
    prior_classes = args.prior_classes_root
    need(prior_source.is_dir() and not prior_source.is_symlink() and
         prior_classes.is_dir() and not prior_classes.is_symlink(),
         "R425_PRIVATE_INPUT_TREE_MISSING")
    # Explicitly tie the operation to the isolated R421 acceptance tree.
    expected_fragment = (
        "SpawnPK-R386-Isolated-Acceptance",
        "R421-Private-NoFollow-Cache-Directory-Preflight",
    )
    for path in (prior_source, prior_classes):
        parts = path.resolve().parts
        need(all(part in parts for part in expected_fragment),
             "R425_REFUSE_NONISOLATED_PRIVATE_TREE")
    need(hash_file(prior_source / STORE) == PINNED_R421_STORE_SHA,
         "R425_PRIVATE_R421_SOURCE_PIN_DRIFT")
    need(hash_file(prior_classes / EXPECTED_CHANGED_EXISTING_CLASS) ==
         PINNED_R421_STORE_CLASS,
         "R425_R421_PRIVATE_CLASS_SHA_DRIFT")
    source = sha_inventory(prior_source, ".java")
    classes = sha_inventory(prior_classes, ".class")
    need(len(source) == BASELINE_SOURCE_COUNT and
         len(classes) == BASELINE_CLASS_COUNT,
         "R425_PRIVATE_INPUT_INVENTORY_DRIFT")
    # Counts plus Store SHA alone cannot identify the other 1,276 sources
    # and 1,393 classes. Require an independently reviewed full-tree pin.
    require_approved_baselines(args, source, classes)


def verify_unchanged_build_inputs(
    args, original_source_snapshot: dict[str, str],
    original_class_snapshot: dict[str, str],
    candidate_source_snapshot: dict[str, str],
    candidate_source_tree: Path,
) -> None:
    """Fail closed if owner-private or staged inputs changed since snapshot.

    Files are hashed again, not merely counted. This doesn't provide
    protection from a hostile process swapping files between the checks,
    but rejects accidental edits and most non-atomic concurrent changes.
    """
    need(sha_inventory(args.prior_source_root, ".java") ==
         original_source_snapshot,
         "R426_PRIOR_SOURCE_CHANGED_DURING_BUILD")
    require_approved_baselines(
        args, original_source_snapshot, original_class_snapshot)
    need(sha_inventory(args.prior_classes_root, ".class") ==
         original_class_snapshot,
         "R426_PRIOR_CLASSES_CHANGED_DURING_BUILD")
    need(sha_inventory(candidate_source_tree, ".java") ==
         candidate_source_snapshot,
         "R426_CANDIDATE_SOURCES_CHANGED_DURING_BUILD")
    need(hash_file(args.dependency_a) == args.dependency_a_sha256,
         "R426_DEPENDENCY_A_CHANGED_DURING_BUILD")
    need(hash_file(args.dependency_b) == args.dependency_b_sha256,
         "R426_DEPENDENCY_B_CHANGED_DURING_BUILD")


def java11_compiler(args, source_tree: Path, compiled: Path,
                    deps: str, log: Path) -> None:
    compiled.mkdir()
    sources = sorted(source_tree.rglob("*.java"))
    need(len(sources) == BASELINE_SOURCE_COUNT + 1,
         "R425_EXPECTED_1278_SOURCES")
    argfile = compiled.parent / "R425-javac-sources.txt"
    # JDK javac response file handles spaces using double quotes.
    argfile.write_text(
        "".join('"' + p.as_posix().replace('"', '\\"') + '"\n'
                for p in sources), encoding="utf-8")
    cmd = [str(args.javac), "--release", "11", "-proc:none",
           "-encoding", "UTF-8", "-Xlint:none",
           "-cp", deps, "-d", str(compiled), "@" + str(argfile)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    log.write_text("EXIT=" + str(p.returncode) +
                   "\nSTDOUT:\n" + p.stdout + "\nSTDERR:\n" + p.stderr,
                   encoding="utf-8")
    need(p.returncode == 0, "R425_PRIVATE_JAVAC_FAILED_SEE_OWNER_LOCAL_LOG")


def parse_r425_selftest_assertions(output: str) -> int | None:
    """Require the exact full R425 synthetic Store success receipt.

    Java may print exactly one optional symlink-unavailable warning. Accept
    that line only before a full, bounded numeric receipt; reject unrelated
    text, duplicate receipts, leading zeros and missing final terminators.
    """
    if type(output) is not str:
        return None
    for eol in ("\n", "\r\n"):
        match = re.fullmatch(
            r"(?:R425_OPTIONAL_SYMLINK_UNAVAILABLE" + re.escape(eol) + r")?"
            r"R425_ACTUAL_PATCHED_PRIVATE_STORE_PASS assertions=([1-9][0-9]{0,5})"
            + re.escape(eol),
            output,
        )
        if match is not None:
            return int(match.group(1))
    return None


def execute_actual_class_acceptance(args, compiled: Path,
                                    deps: str, dest: Path) -> dict:
    harness_classes = dest / "R425-Harness-Classes"
    harness_classes.mkdir()
    cp = os.pathsep.join((str(compiled), deps))
    build = subprocess.run(
        [str(args.javac), "--release", "11", "-proc:none",
         "-encoding", "UTF-8", "-cp", cp, "-d",
         str(harness_classes), str(args.public_acceptance_source)],
        capture_output=True, text=True, timeout=60)
    (dest / "R425-harness-javac.log").write_text(
        "EXIT=" + str(build.returncode) +
        "\nSTDOUT:\n" + build.stdout + "\nSTDERR:\n" + build.stderr,
        encoding="utf-8")
    need(build.returncode == 0, "R425_PRIVATE_HARNESS_JAVAC_FAILED_SEE_LOCAL_LOG")

    tmp = Path(tempfile.gettempdir()).resolve()
    scratch = Path(tempfile.mkdtemp(prefix="R425-Synthetic-", dir=str(tmp)))
    cp = os.pathsep.join((str(harness_classes), str(compiled), deps))
    proc = subprocess.run(
        [str(args.java), "-Xmx512m", "-Djava.awt.headless=true",
         "-Djava.io.tmpdir=" + str(tmp),
         "-Duser.home=" + str(scratch),
         "-cp", cp, MAIN, str(scratch)],
        capture_output=True, text=True, timeout=70)
    (dest / "R425-actual-store-acceptance.log").write_text(
        "EXIT=" + str(proc.returncode) +
        "\nSTDOUT:\n" + proc.stdout + "\nSTDERR:\n" + proc.stderr,
        encoding="utf-8")
    assertions = parse_r425_selftest_assertions(proc.stdout)
    need(proc.returncode == 0 and assertions is not None and assertions >= 39,
         "R425_REAL_PRIVATE_STORE_ACCEPTANCE_FAILED_SEE_LOCAL_LOG")
    return {"status": "R425_ACTUAL_PRIVATE_STORE_DRY_RUN_TEMP_PASS",
            "real_class_assertions": assertions,
            "scratch_directory": str(scratch),
            "real_game_client_started": False,
            "real_player_history_accessed": False}


def run(args) -> dict:
    validate_inputs(args)
    parent_src = sha_inventory(args.prior_source_root, ".java")
    parent_cls = sha_inventory(args.prior_classes_root, ".class")
    # prepare_r424 performs its own SHA and 1277-count validation and
    # refuses non-new, non-TEMP destinations. No source ever overwritten.
    prepared = prepare_r424(args.prior_source_root,
                            args.public_helper_source,
                            args.fresh_temp_destination)
    dest = args.fresh_temp_destination.resolve()
    source_tree = dest / "source"
    candidate_src = sha_inventory(source_tree, ".java")
    changed = gate_source_inventory(parent_src, candidate_src)
    verify_unchanged_build_inputs(
        args, parent_src, parent_cls, candidate_src, source_tree)
    compiled = dest / "R425-Compiled-Classes"
    deps = os.pathsep.join((str(args.dependency_a),
                            str(args.dependency_b)))
    java11_compiler(args, source_tree, compiled, deps,
                    dest / "R425-full-javac.log")
    verify_unchanged_build_inputs(
        args, parent_src, parent_cls, candidate_src, source_tree)
    compiled_snapshot = sha_inventory(compiled, ".class")
    class_delta = gate_class_inventory(parent_cls, compiled_snapshot)
    accepted = execute_actual_class_acceptance(args, compiled, deps, dest)
    verify_unchanged_build_inputs(
        args, parent_src, parent_cls, candidate_src, source_tree)
    need(sha_inventory(compiled, ".class") == compiled_snapshot,
         "R426_COMPILED_CLASSES_CHANGED_DURING_ACCEPTANCE")
    need(hash_file(args.prior_source_root / STORE) == PINNED_R421_STORE_SHA,
         "R425_PARENT_PRIVATE_SOURCE_CHANGED_DURING_ACCEPTANCE")
    need(hash_file(args.prior_classes_root / EXPECTED_CHANGED_EXISTING_CLASS)
         == PINNED_R421_STORE_CLASS,
         "R425_PARENT_COMPILED_CLASS_CHANGED_DURING_ACCEPTANCE")
    # Re-validate the class snapshot just before issuing the final receipt.
    # Ordinary class output rewrites cannot pass the same compiled SHA inventory.
    need(sha_inventory(compiled, ".class") == compiled_snapshot,
         "R426_COMPILED_CLASSES_CHANGED_BEFORE_RECEIPT")
    receipt = {
        "status": "R425_PRIVATE_OVERLAY_COMPILE_AND_ACTUAL_STORE_PASS",
        "source_scope": changed,
        "class_scope": class_delta,
        "actual_private_store": accepted,
        "private_source_patch": prepared["status"],
        "legacy_deletion_enabled": False,
        "real_history_read_or_changed": False,
        "private_game_launched": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    (dest / "R425-Final-Private-Acceptance-Receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-source-root", type=Path, required=True)
    parser.add_argument("--prior-classes-root", type=Path, required=True)
    parser.add_argument("--public-helper-source", type=Path, required=True)
    parser.add_argument("--public-acceptance-source", type=Path, required=True)
    parser.add_argument("--dependency-a", type=Path, required=True)
    parser.add_argument("--dependency-b", type=Path, required=True)
    parser.add_argument("--dependency-a-sha256", required=True)
    parser.add_argument("--dependency-b-sha256", required=True)
    parser.add_argument("--approved-source-inventory-sha256", required=True)
    parser.add_argument("--approved-class-inventory-sha256", required=True)
    parser.add_argument("--javac", type=Path, required=True)
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--fresh-temp-destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, InventoryRefused, OSError, subprocess.TimeoutExpired, ValueError,
            RuntimeError, UnicodeError, KeyError) as e:
        reason = str(e) if isinstance(e, (Refused, InventoryRefused)) else (
            "R425_ACCEPTANCE_FAILED_OR_INCOMPLETE_SEE_OWNER_TEMP_LOCAL_LOGS")
        print(json.dumps({"status": "R425_PRIVATE_ACCEPTANCE_REFUSED",
                          "reason": reason,
                          "release_authorized": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
