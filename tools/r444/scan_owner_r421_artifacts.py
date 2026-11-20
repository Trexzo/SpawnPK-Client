#!/usr/bin/env python3
"""R444 owner-only, READ-ONLY discovery of older R421 artifacts in known TEMP roots.

No writes, commands, self-approved SHA pins, original client launch, history,
deletion-journal or credential access. Report only aggregates and booleans;
never emit private filenames, local paths, per-file digests or source code.
Run with Python -B. A discovered file is NOT an approved R442 reference.
"""
from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path
import stat
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r442 import verify_prior_r421_manifest as r442

PARENT = "SpawnPK-R386-Isolated-Acceptance"
R421 = "R421-Private-NoFollow-Cache-Directory-Preflight"
STORE_CLASS = r425.EXPECTED_CHANGED_EXISTING_CLASS
RECEIPT_NAMES = {
    "R425-Final-Private-Acceptance-Receipt.json": "r425_receipts_found",
    "R432-Final-Private-CrossProcess-Receipt.json": "r432_receipts_found",
}
MAX_JSON_BYTES = r442.MAX_MANIFEST_BYTES
MAX_CANDIDATE_DIRS = 24
MAX_SCANNED_ENTRIES = 600
MAX_DEPTH = 4
# R445: independent enumeration and stable-file-read budgets. The R444
# MAX_SCANNED_ENTRIES limit alone did not bound the initial TEMP listing or
# the os.walk() source/class directory enumeration.
MAX_TEMP_TOP_LEVEL_ENTRIES = 6000
MAX_SOURCE_CLASS_TREE_ENTRIES = 7500
MAX_SOURCE_CLASS_DIRECTORIES = 1800
MAX_SOURCE_CLASS_DEPTH = 36
MAX_STORE_BYTES = 2 * 1024 * 1024
KEYWORDS = ("r421", "inventory", "manifest", "receipt", "acceptance",
            "baseline", "sha256")
SKIP_FOLDERS = {"source", "dependencies", "R421-Compiled-Classes",
                ".git", "__pycache__", "node_modules"}


class Refused(RuntimeError):
    pass


def regular(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return (stat.S_ISREG(info.st_mode) and not path.is_symlink()
            and not getattr(path, "is_junction", lambda: False)())


def directory(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return (stat.S_ISDIR(info.st_mode) and not path.is_symlink()
            and not getattr(path, "is_junction", lambda: False)())


def bounded_children(root: Path, limit: int, refusal: str) -> list[Path]:
    """Bound iteration BEFORE sorting; do not materialize an unbounded TEMP."""
    children: list[Path] = []
    for child in root.iterdir():
        children.append(child)
        if len(children) > limit:
            raise Refused(refusal)
    return sorted(children, key=lambda item: item.name)


def source_class_count(root: Path, suffix: str, max_files: int = 2500) -> int | None:
    """Bound files, directories, depth and directory listing; never follow links."""
    if not directory(root):
        return None
    found = 0
    visited_entries = 0
    visited_directories = 0
    stack = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        visited_directories += 1
        if visited_directories > MAX_SOURCE_CLASS_DIRECTORIES:
            raise Refused("R445_SOURCE_CLASS_DIR_BUDGET_EXCEEDED")
        if depth > MAX_SOURCE_CLASS_DEPTH or not directory(current):
            raise Refused("R445_SOURCE_CLASS_DEPTH_OR_ALIAS_REFUSED")
        # Preserve R444's mandatory fail-closed link/special-member behavior.
        children = bounded_children(
            current, MAX_SOURCE_CLASS_TREE_ENTRIES,
            "R445_SOURCE_CLASS_DIRECTORY_ENTRY_LIMIT")
        for child in children:
            visited_entries += 1
            if visited_entries > MAX_SOURCE_CLASS_TREE_ENTRIES:
                raise Refused("R445_SOURCE_CLASS_TREE_ENTRY_LIMIT")
            if directory(child):
                stack.append((child, depth + 1))
                continue
            if not regular(child):
                raise Refused("R444_SOURCE_CLASS_TREE_NONREGULAR_REFUSED")
            if child.suffix == suffix:
                found += 1
                if found > max_files:
                    raise Refused("R444_SOURCE_CLASS_COUNT_TOO_LARGE")
    return found


def read_bounded_regular(path: Path, maximum: int,
                         oversize_reason: str | None = None) -> bytes | None:
    """Read an identity-stable, size-limited regular file without link follow.

    The opened fd is checked against lstat() before any content is read.
    O_NOFOLLOW is applied where the OS provides it. Report only safe error
    codes, not filenames, read bytes, or original private filesystem paths.
    """
    if not regular(path):
        return None
    before = path.lstat()
    if before.st_size > maximum:
        if oversize_reason:
            raise Refused(oversize_reason)
        return None
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        identity = lambda st: (st.st_dev, st.st_ino, st.st_size,
                               st.st_mtime_ns)
        if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(before):
            raise Refused("R445_FILE_IDENTITY_CHANGED_BEFORE_READ")
        data = bytearray()
        while True:
            chunk = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > maximum:
                raise Refused("R445_FILE_GREW_OVER_READ_LIMIT")
        after = path.lstat()
        if (not stat.S_ISREG(after.st_mode) or
                identity(after) != identity(before) or
                len(data) != before.st_size):
            raise Refused("R445_FILE_IDENTITY_CHANGED_DURING_READ")
        return bytes(data)
    finally:
        os.close(fd)


def exact_store_pin_matches(path: Path, expected: str) -> bool | None:
    """A bounded observed SHA, never evidence of independent approval."""
    raw = read_bounded_regular(path, MAX_STORE_BYTES,
                               "R445_STORE_PIN_FILE_TOO_LARGE")
    return None if raw is None else sha256(raw).hexdigest() == expected


def candidate_shape(path: Path) -> bool:
    """Recognize, never approve, a *possible* R442 full manifest."""
    try:
        raw = read_bounded_regular(path, MAX_JSON_BYTES)
        if not raw:
            return False
        payload = json.loads(raw.decode("utf-8"),
                             object_pairs_hook=r442.unique_pairs)
        if type(payload) is not dict or set(payload) != {
            "schema", "source_inventory", "class_inventory",
            "dependency_sha256", "archive_id",
        } or payload.get("schema") != r442.SCHEMA:
            return False
        src = payload.get("source_inventory")
        cls = payload.get("class_inventory")
        deps = payload.get("dependency_sha256")
        if (type(src) is not dict or type(cls) is not dict
                or type(deps) is not dict
                or len(src) != r425.BASELINE_SOURCE_COUNT
                or len(cls) != r425.BASELINE_CLASS_COUNT):
            return False
        if (src.get(r425.STORE.as_posix()) != r425.PINNED_R421_STORE_SHA
                or cls.get(STORE_CLASS) != r425.PINNED_R421_STORE_CLASS):
            return False
        return set(deps) == {"R239_filtered.jar", "R218.jar"}
    except (ValueError, UnicodeError, TypeError, r442.Refused):
        return False


def evidence_dirs(temp: Path):
    """Only historical R421/R425 scratch namespaces, never live client dirs."""
    if not directory(temp):
        raise Refused("R444_OWNER_TEMP_ROOT_UNAVAILABLE")
    base = temp / PARENT
    if directory(base):
        target = base / R421
        if directory(target):
            yield target
        # Adjacent known R421 evidence directories; never scan unrelated.
        for child in bounded_children(base, MAX_TEMP_TOP_LEVEL_ENTRIES,
                                      "R445_ISOLATED_ROOT_LISTING_TOO_LARGE"):
            if (child.name.startswith("R421-") and child != target
                    and directory(child)):
                yield child
    # R425 candidate receipts are saved under disposable TEMP roots.
    for child in bounded_children(temp, MAX_TEMP_TOP_LEVEL_ENTRIES,
                                  "R445_TEMP_TOP_LEVEL_LISTING_TOO_LARGE"):
        if (child.name.startswith("R424-Private-Candidate-R425-")
                and directory(child)):
            yield child


def scan_owner_temp(temp: Path) -> dict:
    """Inspect only bounded, historical candidate directories; no writes."""
    roots = list(evidence_dirs(temp))
    if len(roots) > MAX_CANDIDATE_DIRS:
        raise Refused("R444_TOO_MANY_HISTORICAL_CANDIDATES")
    preflight = temp / PARENT / R421
    base = preflight / "Source-Candidate-R421"
    source = base / "source"
    compiled = preflight / "R421-Compiled-Classes"
    result = {
        "status": "R444_OWNER_TEMP_EVIDENCE_SCAN_COMPLETE",
        "owner_isolated_r421_root_present": directory(preflight),
        "original_source_root_present": directory(source),
        "original_class_root_present": directory(compiled),
        "original_source_count_observed": source_class_count(source, ".java"),
        "original_class_count_observed": source_class_count(compiled, ".class"),
        "original_store_source_pin_matches": exact_store_pin_matches(
            source / r425.STORE, r425.PINNED_R421_STORE_SHA),
        "original_store_class_pin_matches": exact_store_pin_matches(
            compiled / STORE_CLASS, r425.PINNED_R421_STORE_CLASS),
        "historical_candidate_roots_scanned": len(roots),
        "reference_artifact_candidates_found": 0,
        "possible_r442_manifest_shapes_found": 0,
        "r425_receipts_found": 0,
        "r432_receipts_found": 0,
        "candidate_file_entries_inspected": 0,
        "possible_reference_sha_independently_approved": False,
        "source_class_inventory_independently_approved": False,
        "owner_private_compile_executed": False,
        "client_started": False,
        "history_accessed": False,
        "candidate_created": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    seen = set()
    inspected = 0
    for root in roots:
        stack = [(root, 0)]
        while stack:
            current, level = stack.pop()
            if level > MAX_DEPTH:
                continue
            if not directory(current):
                raise Refused("R444_HISTORICAL_CANDIDATE_LINK_REFUSED")
            for child in bounded_children(
                    current, MAX_SCANNED_ENTRIES,
                    "R445_HISTORICAL_DIRECTORY_LISTING_TOO_LARGE"):
                inspected += 1
                if inspected > MAX_SCANNED_ENTRIES:
                    raise Refused("R444_HISTORICAL_CANDIDATE_SCAN_TOO_LARGE")
                if directory(child):
                    if child.name not in SKIP_FOLDERS and level < MAX_DEPTH:
                        stack.append((child, level + 1))
                    continue
                if not regular(child):
                    raise Refused("R444_HISTORICAL_CANDIDATE_NONREGULAR_REFUSED")
                if child.name in RECEIPT_NAMES:
                    result[RECEIPT_NAMES[child.name]] += 1
                lowered = child.name.lower()
                if not any(tag in lowered for tag in KEYWORDS):
                    continue
                if child.suffix.lower() not in (".json", ".sha256", ".txt",
                                                 ".md"):
                    continue
                if child in seen:
                    continue
                seen.add(child)
                result["reference_artifact_candidates_found"] += 1
                if child.suffix.lower() == ".json" and candidate_shape(child):
                    result["possible_r442_manifest_shapes_found"] += 1
    result["candidate_file_entries_inspected"] = inspected
    # This scan cannot promote an observed file into trusted R421 custody.
    return result


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-read-only-evidence-audit",
                        action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        result = scan_owner_temp(Path(tempfile.gettempdir()).absolute())
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, OSError, UnicodeError, ValueError) as error:
        reason = str(error) if isinstance(error, Refused) else (
            "R444_HISTORICAL_EVIDENCE_UNREADABLE")
        print(json.dumps({
            "status": "R444_OWNER_TEMP_EVIDENCE_SCAN_REFUSED",
            "reason": reason[:120],
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
