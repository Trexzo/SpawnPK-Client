#!/usr/bin/env python3
"""R442 owner-only verification of a previously approved R421 baseline manifest.

Reads a single separately preserved JSON reference whose RAW SHA256 must
already have been approved out-of-band. It NEVER generates or approves a
manifest from today's source/class files. No client, Java, private bytecode
execution, player history, journals, or output files are touched.

A matching SHA pins the supplied manifest's bytes, NOT the historical origin
of the reference digest; independent custody review remains mandatory.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import stat
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r441.approved_full_inventory import (
    Refused as InventoryRefused, inventory_digest,
)

SCHEMA = "SpawnPK-R442-previously-reviewed-R421-inventory-v1"
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
SOURCE_PATH = r425.STORE.as_posix()
CLASS_PATH = r425.EXPECTED_CHANGED_EXISTING_CLASS


class Refused(RuntimeError):
    pass


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise Refused(reason)


def unique_pairs(pairs):
    """JSON object duplicate keys are ambiguous even if values match."""
    obj = {}
    for key, value in pairs:
        need(key not in obj, "R442_DUPLICATE_MANIFEST_JSON_KEY")
        obj[key] = value
    return obj


def valid_file_map(value, suffix: str, count: int) -> dict[str, str]:
    need(type(value) is dict and len(value) == count,
         "R442_REFERENCE_" + suffix.upper() + "_COUNT_MISMATCH")
    names = set()
    for path, digest in value.items():
        need(type(path) is str and path.endswith("." + suffix)
             and not path.startswith("/") and not path.startswith("./")
             and "\\" not in path and "\x00" not in path
             and all(part not in ("", ".", "..") for part in path.split("/")),
             "R442_INVALID_REFERENCE_RELATIVE_PATH")
        normalized = path.casefold()
        need(normalized not in names, "R442_REFERENCE_CASE_COLLISION")
        names.add(normalized)
        need(type(digest) is str and
             re.fullmatch("[0-9a-f]{64}", digest) is not None,
             "R442_INVALID_REFERENCE_FILE_SHA")
    return value


def read_approved_manifest(path: Path, approved_sha: str) -> dict:
    """Hash full file before parse; no user/source paths in refusal output."""
    need(type(approved_sha) is str
         and re.fullmatch("[0-9a-f]{64}", approved_sha) is not None,
         "R442_APPROVED_MANIFEST_SHA_REQUIRED")
    try:
        meta = path.lstat()
    except OSError:
        raise Refused("R442_REFERENCE_MANIFEST_MISSING") from None
    need(stat.S_ISREG(meta.st_mode) and not path.is_symlink()
         and not getattr(path, "is_junction", lambda: False)(),
         "R442_REFERENCE_MANIFEST_NOT_REGULAR")
    need(0 < meta.st_size <= MAX_MANIFEST_BYTES,
         "R442_REFERENCE_MANIFEST_SIZE_REFUSED")
    with path.open("rb") as stream:
        data = stream.read(MAX_MANIFEST_BYTES + 1)
    need(0 < len(data) <= MAX_MANIFEST_BYTES,
         "R442_REFERENCE_MANIFEST_SIZE_REFUSED")
    need(sha256(data).hexdigest() == approved_sha,
         "R442_APPROVED_MANIFEST_SHA_MISMATCH")
    try:
        manifest = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                Refused("R442_NONFINITE_JSON_VALUE")),
        )
    except (ValueError, UnicodeError):
        raise Refused("R442_REFERENCE_MANIFEST_INVALID_JSON") from None
    need(type(manifest) is dict and set(manifest) == {
        "schema", "source_inventory", "class_inventory",
        "dependency_sha256", "archive_id",
    }, "R442_REFERENCE_MANIFEST_SCHEMA_MISMATCH")
    need(manifest["schema"] == SCHEMA,
         "R442_REFERENCE_MANIFEST_VERSION_MISMATCH")
    archive_id = manifest["archive_id"]
    need(type(archive_id) is str and
         re.fullmatch("[A-Za-z0-9][A-Za-z0-9._-]{3,119}", archive_id) is not None,
         "R442_INVALID_ARCHIVE_REFERENCE_ID")

    source = valid_file_map(
        manifest["source_inventory"], "java", r425.BASELINE_SOURCE_COUNT)
    classes = valid_file_map(
        manifest["class_inventory"], "class", r425.BASELINE_CLASS_COUNT)
    need(source.get(SOURCE_PATH) == r425.PINNED_R421_STORE_SHA,
         "R442_PINNED_R421_SOURCE_MISSING_OR_DIFFERENT")
    need(classes.get(CLASS_PATH) == r425.PINNED_R421_STORE_CLASS,
         "R442_PINNED_R421_CLASS_MISSING_OR_DIFFERENT")
    dependencies = manifest["dependency_sha256"]
    need(type(dependencies) is dict and set(dependencies) ==
         {"R239_filtered.jar", "R218.jar"},
         "R442_DEPENDENCY_REFERENCE_SET_MISMATCH")
    for digest in dependencies.values():
        need(type(digest) is str and
             re.fullmatch("[0-9a-f]{64}", digest) is not None,
             "R442_INVALID_DEPENDENCY_REFERENCE_SHA")
    need(dependencies["R239_filtered.jar"] != dependencies["R218.jar"],
         "R442_IDENTICAL_DEPENDENCIES_REQUIRE_REVIEW")

    try:
        source_digest = inventory_digest(source, "java")
        class_digest = inventory_digest(classes, "class")
    except InventoryRefused:
        raise Refused("R442_REFERENCE_MANIFEST_INVENTORY_INVALID") from None

    return {
        "status": "R442_PRIOR_R421_REFERENCE_BYTES_VERIFIED",
        "approved_manifest_sha256": approved_sha,
        "approved_source_inventory_sha256": source_digest,
        "approved_class_inventory_sha256": class_digest,
        "approved_dependency_a_sha256": dependencies["R239_filtered.jar"],
        "approved_dependency_b_sha256": dependencies["R218.jar"],
        "baseline_java_sources": len(source),
        "baseline_compiled_classes": len(classes),
        "reference_origin_independently_verified": False,
        "client_started": False,
        "private_java_compiled": False,
        "player_history_accessed": False,
        "release_authorized": False,
        "merge_authorized": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument("--approved-manifest-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = read_approved_manifest(
            args.manifest_path, args.approved_manifest_sha256)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, OSError, ValueError, TypeError, UnicodeError) as error:
        reason = str(error) if isinstance(error, Refused) else (
            "R442_REFERENCE_MANIFEST_UNREADABLE_OR_INVALID")
        print(json.dumps({
            "status": "R442_REFERENCE_BASELINE_REFUSED",
            "reason": reason[:140],
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
