#!/usr/bin/env python3
"""R432: opt-in, owner-only R425 -> R422 ACTUAL private-class gate chain.

Run AFTER a successful R425/R426 owner-private isolated TEMP compilation,
never on the live client. Requires the exact R421 private source/class SHA
pins and the exact R425 source/class inventories. Executes the existing R422
public Java harness against that SAME newly compiled private Store SHA.

No source, class, JAR, or game modification; R422 only creates fabricated
TEMP evidence. This program writes a new local receipt on success, but
NEVER authorizes a release, installation, cleanup, or history write.

Not usable in hosted CI without owner's private files. Public tests MUST
use invented data and mocked runner output; that is not private acceptance.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r424 import prepare_private_legacy_cleanup_patch as r424

R422_PROGRAM = REPO_ROOT / "tools/r422/run_private_store_acceptance.py"
R422_HARNESS = REPO_ROOT / "tests/fixtures/r422/R422ActualStoreAcceptance.java"
R425_HARNESS = REPO_ROOT / "tests/fixtures/r425/R425ActualPrivateOverlayAcceptance.java"
R424_HELPER = REPO_ROOT / "tests/fixtures/r424/LootLegacyCleanupR424.java"
R425_RECEIPT = "R425-Final-Private-Acceptance-Receipt.json"
R432_RECEIPT = "R432-Final-Private-CrossProcess-Receipt.json"

REQUIRED_R422_CHECKS = frozenset({
    "actual_private_store_73_assertions",
    "actual_store_first_process_acquired",
    "actual_store_second_process_refused",
    "actual_store_contender_did_not_create_history",
    "owner_release_terminates_normally",
    "owner_release_receipt",
    "actual_store_reacquire_after_shutdown",
    "real_os_lock_path_persists_after_release",
    "actual_store_crash_exit",
    "crash_keeps_inert_lock_file",
    "actual_store_reacquire_after_jvm_halt",
    "new_leaf_absent_before",
    "actual_store_first_run_creates_leaf_and_acquires",
    "first_run_does_not_create_history",
    "lease_try_does_not_repair_unresolved_marker",
    "pinned_real_class_unchanged_by_acceptance",
    "non_synthetic_temp_root_is_rejected",
})


class Refused(RuntimeError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise Refused(code)


def regular_nofollow(path: Path) -> bool:
    try:
        info = path.lstat()
        return stat.S_ISREG(info.st_mode) and not path.is_symlink()
    except OSError:
        return False


def validate_fresh_candidate(root: Path) -> Path:
    """Only exact fresh R425 owner TEMP children. No existing R432 receipt."""
    tmp = Path(tempfile.gettempdir()).resolve()
    raw = root.absolute()
    need(".." not in raw.parts, "R432_REFUSE_TRAVERSAL_PATH")
    need(raw.parent == tmp and
         raw.name.startswith("R424-Private-Candidate-R425-"),
         "R432_REFUSE_NONISOLATED_CANDIDATE")
    for ancestor in (raw, *raw.parents):
        try:
            mode = ancestor.lstat().st_mode
        except OSError:
            raise Refused("R432_MISSING_OR_UNREADABLE_ANCESTOR")
        need(stat.S_ISDIR(mode) and not stat.S_ISLNK(mode),
             "R432_SYMLINK_OR_NON_DIRECTORY_ANCESTOR")
    for path in raw.rglob("*"):
        need(not path.is_symlink(), "R432_SYMLINK_INSIDE_CANDIDATE")
    need(not (raw / R432_RECEIPT).exists() and
         not (raw / R432_RECEIPT).is_symlink(),
         "R432_REFUSE_ALREADY_ACCEPTED_OR_FOREIGN_RECEIPT")
    return raw


def validate_owner_references(args) -> SimpleNamespace:
    validated = SimpleNamespace(
        prior_source_root=args.prior_source_root,
        prior_classes_root=args.prior_classes_root,
        public_helper_source=R424_HELPER,
        public_acceptance_source=R425_HARNESS,
        dependency_a=args.dependency_a,
        dependency_b=args.dependency_b,
        dependency_a_sha256=args.dependency_a_sha256,
        dependency_b_sha256=args.dependency_b_sha256,
        javac=args.javac,
        java=args.java,
    )
    r425.validate_inputs(validated)
    for path in (R422_PROGRAM, R422_HARNESS, R425_HARNESS, R424_HELPER):
        need(regular_nofollow(path), "R432_MISSING_PUBLIC_ACCEPTANCE_SOURCE")
    return validated


def gate_existing_r425_receipt(
    receipt: dict[str, Any], source_scope: dict,
    class_scope: dict
) -> None:
    need(isinstance(receipt, dict), "R432_INVALID_R425_RECEIPT")
    need(receipt.get("status") ==
         "R425_PRIVATE_OVERLAY_COMPILE_AND_ACTUAL_STORE_PASS",
         "R432_R425_COMPILE_AND_TEST_NOT_PROVEN")
    need(receipt.get("private_source_patch") ==
         "R424_PRIVATE_DRY_RUN_LEGACY_CLEANUP_PATCH_PREPARED_NOT_COMPILED",
         "R432_R424_PREPARATION_IDENTITY_DRIFT")
    need(receipt.get("source_scope") == source_scope,
         "R432_R425_SOURCE_SCOPE_MISMATCH")
    need(receipt.get("class_scope") == class_scope,
         "R432_R425_COMPILED_CLASS_SCOPE_MISMATCH")
    real = receipt.get("actual_private_store")
    need(isinstance(real, dict) and
         real.get("status") == "R425_ACTUAL_PRIVATE_STORE_DRY_RUN_TEMP_PASS" and
         type(real.get("real_class_assertions")) is int and
         real.get("real_class_assertions") >= 39,
         "R432_R425_ACTUAL_STORE_RECEIPT_NOT_PROVEN")
    for field, expected in (
        ("legacy_deletion_enabled", False),
        ("real_history_read_or_changed", False),
        ("private_game_launched", False),
        ("release_authorized", False),
        ("merge_authorized", False),
    ):
        need(receipt.get(field) is expected, "R432_R425_UNSAFE_RECEIPT_" + field)


def gate_r422_process_receipt(
    receipt: dict[str, Any], exact_compiled_sha: str
) -> dict:
    need(isinstance(receipt, dict), "R432_R422_INVALID_RECEIPT")
    need(receipt.get("status") ==
         "R422_OWNER_PRIVATE_ACTUAL_STORE_PROCESS_ACCEPTANCE_PASS",
         "R432_R422_CROSS_PROCESS_NOT_PASSED")
    need(receipt.get("class_sha256_verified") == exact_compiled_sha,
         "R432_R422_DIFFERENT_PRIVATE_CLASS_BYTES")
    need(type(receipt.get("real_store_assertions")) is int and
         receipt.get("real_store_assertions") >= 73,
         "R432_R422_INSUFFICIENT_REAL_STORE_ASSERTIONS")
    items = receipt.get("cases")
    need(isinstance(items, list) and
         len(items) == len(REQUIRED_R422_CHECKS) and
         len(set(items)) == len(items) and
         set(items) == REQUIRED_R422_CHECKS,
         "R432_R422_MISSING_OR_DUPLICATE_PROCESS_CHECK")
    need(receipt.get("checks") == len(REQUIRED_R422_CHECKS),
         "R432_R422_CHECK_COUNT_DRIFT")
    for field in ("original_game_started", "production_history_opened",
                  "private_release_authorized"):
        need(receipt.get(field) is False, "R432_R422_UNSAFE_" + field)
    return {
        "status": receipt["status"],
        "checks": len(REQUIRED_R422_CHECKS),
        "real_store_assertions": receipt["real_store_assertions"],
        "tested_exact_class_sha256": exact_compiled_sha,
        "game_started": False,
        "real_history_opened": False,
        "private_release_authorized": False,
    }


def fresh_snapshots(args, candidate: Path) -> dict:
    return {
        "source": r425.sha_inventory(candidate / "source", ".java"),
        "class": r425.sha_inventory(candidate / "R425-Compiled-Classes",
                                    ".class"),
        "baseline_source": r425.sha_inventory(args.prior_source_root, ".java"),
        "baseline_class": r425.sha_inventory(args.prior_classes_root, ".class"),
        "dep_a": r425.hash_file(args.dependency_a),
        "dep_b": r425.hash_file(args.dependency_b),
        "r425_receipt": r425.hash_file(candidate / R425_RECEIPT),
    }


def run(args) -> dict:
    candidate = validate_fresh_candidate(args.candidate_temp_root)
    validate_owner_references(args)
    existing = candidate / R425_RECEIPT
    need(regular_nofollow(existing), "R432_MISSING_R425_FINAL_RECEIPT")
    need(regular_nofollow(candidate / "source" / r425.STORE),
         "R432_CANDIDATE_STORE_SOURCE_ABSENT")
    need(regular_nofollow(candidate / "source" / r425.HELPER),
         "R432_R424_HELPER_SOURCE_ABSENT")
    need(r425.hash_file(candidate / "source" / r425.HELPER) ==
         r424.PINNED_PUBLIC_HELPER_SHA,
         "R432_R424_HELPER_SHA_DRIFT")
    need(existing.stat().st_size < 128 * 1024,
         "R432_OVERSIZE_ACCEPTANCE_RECEIPT")
    original_receipt = json.loads(existing.read_text("utf-8"))
    before = fresh_snapshots(args, candidate)
    s = r425.gate_source_inventory(
        before["baseline_source"], before["source"])
    c = r425.gate_class_inventory(
        before["baseline_class"], before["class"])
    gate_existing_r425_receipt(original_receipt, s, c)
    need(before["dep_a"] == args.dependency_a_sha256 and
         before["dep_b"] == args.dependency_b_sha256,
         "R432_DEPENDENCIES_CHANGED_BEFORE_TEST")
    new_store_hash = before["class"][r425.EXPECTED_CHANGED_EXISTING_CLASS]
    need(re.fullmatch(r"[0-9a-f]{64}", new_store_hash) is not None,
         "R432_INVALID_NEW_STORE_DIGEST")
    need(new_store_hash != r425.PINNED_R421_STORE_CLASS,
         "R432_TEST_CANDIDATE_IDENTICAL_TO_UNPATCHED_STORE")

    command = [
        sys.executable, str(R422_PROGRAM),
        "--java", str(args.java),
        "--javac", str(args.javac),
        "--private-classes", str(candidate / "R425-Compiled-Classes"),
        "--dependency-a", str(args.dependency_a),
        "--dependency-b", str(args.dependency_b),
        "--public-java-source", str(R422_HARNESS),
        "--expected-store-class-sha256", new_store_hash,
    ]
    process = subprocess.run(
        command, capture_output=True, text=True, timeout=180, check=False)
    # Preserve full R422 output in isolated owner TEMP, not GitHub. This file
    # does not contain original private sources or class bytes.
    log = candidate / "R432-R422-CrossProcess-Acceptance.log"
    need(not log.exists() and not log.is_symlink(),
         "R432_REFUSE_EXISTING_OWNER_LOG")
    log.write_text(
        "EXIT=" + str(process.returncode) +
        "\nSTDOUT:\n" + process.stdout + "\nSTDERR:\n" + process.stderr,
        encoding="utf-8")
    need(process.returncode == 0,
         "R432_R422_TEST_FAILED_SEE_OWNER_TEMP_LOG")
    try:
        process_receipt = json.loads(process.stdout)
    except (ValueError, TypeError) as malformed:
        raise Refused("R432_R422_NON_JSON_OR_MULTIPLE_OUTPUT") from malformed
    checked = gate_r422_process_receipt(process_receipt, new_store_hash)

    # Rehash every source, class, dependency and original R425 receipt after
    # all separate JVMs exited; do not grant a pass for source/class drift.
    after = fresh_snapshots(args, candidate)
    need(before == after, "R432_INPUT_OR_CANDIDATE_CHANGED_DURING_PROCESS_TESTS")
    need(r425.hash_file(args.prior_source_root / r425.STORE) ==
         r425.PINNED_R421_STORE_SHA,
         "R432_ORIGINAL_PRIVATE_SOURCE_SHA_CHANGED")
    need(r425.hash_file(
            args.prior_classes_root / r425.EXPECTED_CHANGED_EXISTING_CLASS)
         == r425.PINNED_R421_STORE_CLASS,
         "R432_ORIGINAL_PRIVATE_CLASS_SHA_CHANGED")
    result = {
        "status": "R432_OWNER_PRIVATE_CROSS_PROCESS_CHAIN_PASS",
        "r425_private_receipt_confirmed": True,
        "r422_process_acceptance": checked,
        "candidate_store_sha256": new_store_hash,
        "source_scope": s,
        "class_scope": c,
        "files_checked_before_and_after": True,
        "legacy_deletion_enabled": False,
        "real_history_read_or_changed": False,
        "client_started": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    output = candidate / R432_RECEIPT
    # The candidate is owner TEMP only, and the receipt is create-only.
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-temp-root", type=Path, required=True)
    parser.add_argument("--prior-source-root", type=Path, required=True)
    parser.add_argument("--prior-classes-root", type=Path, required=True)
    parser.add_argument("--dependency-a", type=Path, required=True)
    parser.add_argument("--dependency-b", type=Path, required=True)
    parser.add_argument("--dependency-a-sha256", required=True)
    parser.add_argument("--dependency-b-sha256", required=True)
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--javac", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, OSError, ValueError, RuntimeError, KeyError, TypeError,
            subprocess.TimeoutExpired) as error:
        print(json.dumps({
            "status": "R432_PRIVATE_CROSS_PROCESS_CHAIN_REFUSED",
            "reason": str(error)[:200] if isinstance(error, Refused)
                      else "R432_INVALID_OR_UNVERIFIED_PRIVATE_ACCEPTANCE",
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
