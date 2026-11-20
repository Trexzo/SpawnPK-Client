#!/usr/bin/env python3
"""R446 isolated owner-only R421 full inventory OBSERVATION, never approval.

By default read-only, no output files. With an explicit opt-in, creates a NEW
private quarantine directory under OS TEMP containing an unapproved observation
file of path -> SHA256 maps, not source/class bytes. Such a file is deliberately
INCOMPATIBLE with R442's approved historical reference schema. It cannot unlock
R440/R425/R432 compilation, journal writes, history deletion or release.

Never upload the private observation to public GitHub. Run python -B.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r440 import read_only_private_acceptance_preflight as r440
from tools.r441.approved_full_inventory import (
    Refused as InventoryRefused, inventory_digest,
)
from tools.r444 import scan_owner_r421_artifacts as scanner

SCHEMA = "SpawnPK-R446-current-observation-UNAPPROVED-v1"
STATUS = "UNAPPROVED_CURRENT_OBSERVATION_NOT_HISTORICAL_EVIDENCE"
OUTPUT_NAME = "R446-UNAPPROVED-CURRENT-SOURCE-CLASS-INVENTORY.json"
OUTPUT_PREFIX = "SpawnPK-R446-Owner-Private-Unapproved-"
MAX_MEMBERS = 9500
MAX_DIRECTORIES = 2200
MAX_DEPTH = 40
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 700 * 1024 * 1024
MAX_DEP_BYTES = 48 * 1024 * 1024
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_OUTPUT_NAME_BYTES = 200


class Refused(RuntimeError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise Refused(code)


def roots() -> tuple[Path, Path, Path, Path, Path]:
    """Exact existing R421 isolated TEMP paths, never an arbitrary input."""
    temporary = Path(tempfile.gettempdir()).absolute()
    workspace = (temporary / "SpawnPK-R386-Isolated-Acceptance" /
                 "R421-Private-NoFollow-Cache-Directory-Preflight")
    candidate = workspace / "Source-Candidate-R421"
    src = candidate / "source"
    cls = workspace / "R421-Compiled-Classes"
    dep_a = candidate / "dependencies" / "R239_filtered.jar"
    dep_b = candidate / "dependencies" / "R218.jar"
    return temporary, src, cls, dep_a, dep_b


def inventory(root: Path, suffix: str, expected: int) -> tuple[dict[str, str], int]:
    """Non-following, bounded digest of all expected code files."""
    need(scanner.directory(root), "R446_SOURCE_OR_CLASS_ROOT_MISSING")
    result: dict[str, str] = {}
    folded: set[str] = set()
    visited = 0
    dirs_seen = 0
    bytes_hashed = 0
    stack = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        dirs_seen += 1
        need(dirs_seen <= MAX_DIRECTORIES, "R446_DIRECTORY_BUDGET_EXCEEDED")
        need(depth <= MAX_DEPTH and scanner.directory(current),
             "R446_DEPTH_OR_DIRECTORY_LINK_REFUSED")
        children = scanner.bounded_children(
            current, MAX_MEMBERS, "R446_DIRECTORY_ENTRY_LIMIT")
        for child in children:
            visited += 1
            need(visited <= MAX_MEMBERS, "R446_TREE_ENTRY_LIMIT")
            if scanner.directory(child):
                stack.append((child, depth + 1))
                continue
            need(scanner.regular(child), "R446_TREE_LINK_OR_SPECIAL_MEMBER_REFUSED")
            if child.suffix != suffix:
                continue
            rel = child.relative_to(root).as_posix()
            need(rel and not rel.startswith("/") and not rel.startswith("./")
                 and all(token not in ("", ".", "..") for token in rel.split("/"))
                 and "\\" not in rel and "\x00" not in rel,
                 "R446_INVALID_RELATIVE_CODE_PATH")
            key = rel.casefold()
            need(key not in folded, "R446_SOURCE_OR_CLASS_CASE_COLLISION")
            folded.add(key)
            raw = scanner.read_bounded_regular(
                child, MAX_FILE_BYTES, "R446_CODE_FILE_TOO_LARGE")
            need(raw is not None, "R446_CODE_FILE_CHANGED_DURING_SCAN")
            bytes_hashed += len(raw)
            need(bytes_hashed <= MAX_TOTAL_BYTES, "R446_CODE_TOTAL_BYTES_EXCEEDED")
            result[rel] = sha256(raw).hexdigest()
    need(len(result) == expected, "R446_ORIGINAL_INVENTORY_COUNT_MISMATCH")
    return result, bytes_hashed


def dependency(path: Path) -> str:
    raw = scanner.read_bounded_regular(
        path, MAX_DEP_BYTES, "R446_DEPENDENCY_TOO_LARGE")
    need(raw is not None, "R446_DEPENDENCY_MISSING_OR_CHANGED")
    return sha256(raw).hexdigest()


def observe() -> tuple[dict, dict]:
    temporary, src, cls, dep_a, dep_b = roots()
    # Lexically exact paths, no symlink/junction in parents or at roots.
    r440.exact_owner_isolated_roots(src, cls)
    for p in (dep_a.parent, dep_a, dep_b):
        need(not r440.path_is_link(p), "R446_DEPENDENCY_ALIAS_REFUSED")
    source, source_bytes = inventory(src, ".java", r425.BASELINE_SOURCE_COUNT)
    classes, class_bytes = inventory(cls, ".class", r425.BASELINE_CLASS_COUNT)
    store = r425.STORE.as_posix()
    store_class = r425.EXPECTED_CHANGED_EXISTING_CLASS
    need(source.get(store) == r425.PINNED_R421_STORE_SHA,
         "R446_ORIGINAL_R421_STORE_SOURCE_PIN_MISMATCH")
    need(classes.get(store_class) == r425.PINNED_R421_STORE_CLASS,
         "R446_ORIGINAL_R421_STORE_CLASS_PIN_MISMATCH")
    dep_hashes = {
        "R239_filtered.jar": dependency(dep_a),
        "R218.jar": dependency(dep_b),
    }
    need(dep_hashes["R239_filtered.jar"] != dep_hashes["R218.jar"],
         "R446_IDENTICAL_JARS_REQUIRE_REVIEW")
    try:
        java_digest = inventory_digest(source, "java")
        class_digest = inventory_digest(classes, "class")
    except InventoryRefused:
        raise Refused("R446_UNSAFE_CODE_INVENTORY") from None
    candidate = {
        "schema": SCHEMA,
        "observation_status": STATUS,
        "source_inventory": source,
        "class_inventory": classes,
        "dependency_sha256": dep_hashes,
        "observed_source_inventory_sha256": java_digest,
        "observed_class_inventory_sha256": class_digest,
        "store_source_sha_pinned_to_R421": True,
        "store_class_sha_pinned_to_R421": True,
        "independent_prior_manifest_custody_approved": False,
        "historical_R421_reference_proven": False,
        "compilation_authorized": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    receipt = {
        "status": "R446_CURRENT_R421_INVENTORY_OBSERVED_UNAPPROVED",
        "java_sources_observed": len(source),
        "compiled_classes_observed": len(classes),
        "store_java_sha_matched_R421_pin": True,
        "store_class_sha_matched_R421_pin": True,
        "dependency_jars_observed": len(dep_hashes),
        "total_java_bytes_hashed": source_bytes,
        "total_class_bytes_hashed": class_bytes,
        "independent_prior_manifest_custody_approved": False,
        "historical_R421_reference_proven": False,
        "private_observation_file_created": False,
        "private_javac_executed": False,
        "client_started": False,
        "loot_history_accessed": False,
        "compiled_candidate_created": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return candidate, receipt


def emit_quarantined(candidate: dict) -> str:
    """Opt-in NEW private TEMP output, never installed or self-approved."""
    temp, *_ = roots()
    need(scanner.directory(temp), "R446_PRIVATE_TEMP_UNAVAILABLE")
    raw = (json.dumps(candidate, sort_keys=True,
                      ensure_ascii=True, separators=(",", ":")) + "\n").encode("ascii")
    need(0 < len(raw) <= MAX_MANIFEST_BYTES,
         "R446_OBSERVED_MANIFEST_TOO_LARGE")
    directory = Path(tempfile.mkdtemp(prefix=OUTPUT_PREFIX, dir=str(temp)))
    # Prefix and generated suffix contain no private path components.
    need(directory.parent == temp and directory.name.startswith(OUTPUT_PREFIX)
         and len(directory.name.encode("utf-8")) < MAX_OUTPUT_NAME_BYTES,
         "R446_PRIVATE_QUARANTINE_DIRECTORY_REFUSED")
    need(scanner.directory(directory), "R446_PRIVATE_QUARANTINE_ALIAS_REFUSED")
    final_path = directory / OUTPUT_NAME
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(final_path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        # Intentionally do not silently delete evidence after a failed write.
        raise
    return directory.name


def run(emit: bool = False) -> dict:
    candidate, receipt = observe()
    if emit:
        # Re-read all original inputs before any new output file is created.
        # Prevent accidental promotion of a moving observed state.
        second, _ = observe()
        need(second == candidate, "R446_ORIGINAL_INPUT_CHANGED_BETWEEN_SCANS")
        receipt["private_quarantine_directory_name"] = emit_quarantined(candidate)
        receipt["private_observation_file_created"] = True
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observe-isolated-r421", action="store_true",
                        required=True)
    parser.add_argument("--emit-owner-private-unapproved-candidate",
                        action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run(emit=args.emit_owner_private_unapproved_candidate)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, r440.Refused, scanner.Refused, OSError, ValueError,
            UnicodeError, TypeError) as error:
        reason = str(error) if isinstance(
            error, (Refused, r440.Refused, scanner.Refused)) else (
                "R446_PRIVATE_OBSERVATION_FAILED")
        print(json.dumps({
            "status": "R446_PRIVATE_OBSERVATION_REFUSED",
            "reason": reason[:140],
            "independent_prior_manifest_custody_approved": False,
            "compilation_authorized": False,
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
