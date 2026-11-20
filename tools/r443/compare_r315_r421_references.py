#!/usr/bin/env python3
"""R443 owner-private READ-ONLY R315 -> R421 source-inventory reconciliation.

Does not generate, approve, or modify a baseline. An earlier R315 source-only
snapshot is NOT an R421 approval and cannot establish class lineage. Both raw
manifest SHA references must be trusted independently of the bytes under test.

CLI reports only aggregate counts and boolean gates; never names, file hashes,
recovered Java, class bytes, local paths, loot history or account information.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r442 import verify_prior_r421_manifest as r442

MAX_BYTES = 4 * 1024 * 1024
R315_STORE_PATH = "source/" + r425.STORE.as_posix()
R315_DEPENDENCIES = {
    "dependencies/R239_filtered.jar": "R239_filtered.jar",
    "dependencies/R218.jar": "R218.jar",
}


class Refused(RuntimeError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def digest_string(value: str) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def read_sha_pinned_regular_json(path: Path, reference_sha: str,
                                 prefix: str) -> tuple[dict, bytes]:
    need(digest_string(reference_sha), prefix + "_APPROVED_SHA_REQUIRED")
    try:
        meta = path.lstat()
    except OSError:
        raise Refused(prefix + "_MISSING_REFERENCE") from None
    need(stat.S_ISREG(meta.st_mode) and not path.is_symlink()
         and not getattr(path, "is_junction", lambda: False)(),
         prefix + "_NONREGULAR_REFERENCE_REFUSED")
    need(0 < meta.st_size <= MAX_BYTES, prefix + "_REFERENCE_SIZE_REFUSED")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    need(0 < len(raw) <= MAX_BYTES, prefix + "_REFERENCE_SIZE_REFUSED")
    need(sha256(raw).hexdigest() == reference_sha,
         prefix + "_REFERENCE_SHA_MISMATCH")
    try:
        payload = json.loads(raw.decode("utf-8"),
                             object_pairs_hook=r442.unique_pairs)
    except r442.Refused:
        raise Refused(prefix + "_DUPLICATE_JSON_KEY") from None
    except (ValueError, UnicodeError):
        raise Refused(prefix + "_INVALID_REFERENCE_JSON") from None
    need(type(payload) is dict, prefix + "_INVALID_REFERENCE_SHAPE")
    return payload, raw


def relative_source(path: str) -> str:
    need(type(path) is str and path.startswith("source/"),
         "R443_R315_SOURCE_PREFIX_CHANGED")
    relative = path[len("source/"):]
    need(relative.endswith(".java") and "\\" not in relative
         and "\x00" not in relative
         and all(token not in ("", ".", "..") for token in relative.split("/")),
         "R443_R315_SOURCE_PATH_INVALID")
    return relative


def read_r315_source_manifest(path: Path, approved_sha: str) -> dict:
    """Read original R315 format; never infer that it is a compiled-class map."""
    payload, original_bytes = read_sha_pinned_regular_json(
        path, approved_sha, "R443_R315")
    need(payload.get("classification") ==
         "owner-private; do not publish to public repository",
         "R443_R315_PRIVATE_CLASSIFICATION_REQUIRED")
    need(type(payload.get("java_count")) is int
         and payload["java_count"] == r425.BASELINE_SOURCE_COUNT,
         "R443_R315_SOURCE_COUNT_DRIFT")
    need(digest_string(payload.get("archive_sha256"))
         and digest_string(payload.get("java_tree_sha256")),
         "R443_R315_ARCHIVE_METADATA_MALFORMED")
    need("class_files" not in payload and "class_inventory" not in payload,
         "R443_R315_UNEXPECTED_CLASS_INVENTORY_REVIEW_REQUIRED")
    files = payload.get("source_files")
    need(type(files) is dict and len(files) == r425.BASELINE_SOURCE_COUNT,
         "R443_R315_SOURCE_INVENTORY_INCOMPLETE")

    sources = {}
    casefolded = set()
    for original_path, record in files.items():
        relative = relative_source(original_path)
        key = relative.casefold()
        need(key not in casefolded, "R443_R315_SOURCE_CASE_COLLISION")
        casefolded.add(key)
        need(type(record) is dict and set(record) == {"sha256", "size"}
             and digest_string(record["sha256"])
             and type(record["size"]) is int and record["size"] >= 0,
             "R443_R315_INVALID_SOURCE_RECORD")
        sources[relative] = record["sha256"]
    need(r425.STORE.as_posix() in sources,
         "R443_R315_SOURCE_STORE_MISSING")

    jar_files = payload.get("jar_files")
    need(type(jar_files) is dict
         and all(name in jar_files for name in R315_DEPENDENCIES),
         "R443_R315_DEPENDENCY_REFERENCES_MISSING")
    dependencies = {}
    for old_name, canonical_name in R315_DEPENDENCIES.items():
        record = jar_files[old_name]
        need(type(record) is dict and set(record) == {"sha256", "size"}
             and digest_string(record["sha256"])
             and type(record["size"]) is int and record["size"] >= 0,
             "R443_R315_INVALID_DEPENDENCY_RECORD")
        dependencies[canonical_name] = record["sha256"]

    # Retain an internal inventory only for comparison. Never emit it in
    # stdout/CI, commit it, or infer a later class fingerprint from it.
    return {
        "sources": sources, "dependencies": dependencies,
        "source_store_matches_r421_pin":
            sources[r425.STORE.as_posix()] == r425.PINNED_R421_STORE_SHA,
        "raw_sha": sha256(original_bytes).hexdigest(),
        "r315_has_verified_compiled_class_inventory": False,
    }


def compare_r315_to_approved_r421(r315_path: Path, r315_sha: str,
                                  r421_path: Path | None = None,
                                  r421_sha: str | None = None) -> dict:
    """A comparison, not proof of historical authorship or safe deployment."""
    old = read_r315_source_manifest(r315_path, r315_sha)
    safe = {
        "r315_raw_manifest_matches_supplied_reference": True,
        "r315_source_count": len(old["sources"]),
        "r315_store_matches_pinned_r421_source":
            old["source_store_matches_r421_pin"],
        "r315_compiled_class_inventory_available": False,
        "r421_original_class_history_proven_by_r315": False,
        "independent_manifest_custody_proven_by_tool": False,
        "owner_private_r425_r432_executed": False,
        "actual_client_started": False,
        "player_history_opened": False,
        "ready_for_private_compile": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    need((r421_path is None) == (r421_sha is None),
         "R443_R421_MANIFEST_AND_APPROVED_SHA_BOTH_REQUIRED")
    if r421_path is None:
        return {
            **safe, "status": "R443_R315_ONLY_R421_REFERENCE_STILL_MISSING",
            "r421_reference_present": False,
            "r315_to_r421_source_diff_computed": False,
        }

    try:
        proof = r442.read_approved_manifest(r421_path, r421_sha)
    except r442.Refused:
        raise Refused("R443_R421_REFERENCE_NOT_ACCEPTED") from None
    # Read again ONLY after R442's exact byte-pinned validation. Re-hash to
    # reject file replacement between verification and private comparison.
    data, _ = read_sha_pinned_regular_json(
        r421_path, r421_sha, "R443_R421")
    current = data["source_inventory"]
    previous = old["sources"]

    old_names = set(previous)
    new_names = set(current)
    common = old_names & new_names
    changed = sum(previous[name] != current[name] for name in common)
    retained = len(common) - changed
    added = len(new_names - old_names)
    removed = len(old_names - new_names)

    need(changed + retained + removed == len(previous),
         "R443_SOURCE_DIFF_ARITHMETIC_INVALID")
    need(changed + retained + added == len(current),
         "R443_SOURCE_DIFF_ARITHMETIC_INVALID")
    new_deps = data["dependency_sha256"]
    matching_deps = (old["dependencies"] == new_deps)

    return {
        **safe,
        "status": "R443_APPROVED_REFERENCE_SOURCE_DIFF_ONLY",
        "r421_reference_present": True,
        "r421_reference_bytes_match_supplied_sha": True,
        "r315_to_r421_source_diff_computed": True,
        "source_unchanged_path_count": retained,
        "source_changed_path_count": changed,
        "source_added_path_count": added,
        "source_removed_path_count": removed,
        "dependency_hashes_match_between_snapshots": matching_deps,
        "r421_source_count": proof["baseline_java_sources"],
        "r421_compiled_class_count": proof["baseline_compiled_classes"],
        "r421_original_compiled_store_pin_present": True,
        # Even with two hash-pinned manifests R315 lacks class inventory,
        # and neither SHA proves the independent custody of either snapshot.
        "r315_to_r421_compiled_class_diff_computed": False,
        "ready_for_private_compile": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r315-manifest", type=Path, required=True)
    parser.add_argument("--approved-r315-manifest-sha256", required=True)
    parser.add_argument("--r421-manifest", type=Path)
    parser.add_argument("--approved-r421-manifest-sha256")
    args = parser.parse_args(argv)
    try:
        result = compare_r315_to_approved_r421(
            args.r315_manifest, args.approved_r315_manifest_sha256,
            args.r421_manifest, args.approved_r421_manifest_sha256)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, OSError, ValueError, TypeError, UnicodeError) as error:
        detail = str(error) if isinstance(error, Refused) else (
            "R443_INVALID_OR_UNREADABLE_PRIVATE_REFERENCE")
        print(json.dumps({
            "status": "R443_PRIVATE_SOURCE_LINEAGE_REFUSED",
            "reason": detail[:160],
            "ready_for_private_compile": False,
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
