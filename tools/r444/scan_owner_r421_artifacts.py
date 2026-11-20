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


def source_class_count(root: Path, suffix: str, max_files: int = 2500) -> int | None:
    """Count only regular members, never follow links into external trees."""
    if not directory(root):
        return None
    found = 0
    visited = 0
    for current, dirs, files in os.walk(root, followlinks=False):
        safe = []
        for name in dirs:
            path = Path(current) / name
            if not directory(path):
                raise Refused("R444_SOURCE_CLASS_TREE_LINK_OR_NONDIR_REFUSED")
            safe.append(name)
        dirs[:] = safe
        for name in files:
            file = Path(current) / name
            if not regular(file):
                raise Refused("R444_SOURCE_CLASS_TREE_NONREGULAR_REFUSED")
            visited += 1
            if visited > max_files * 3:
                raise Refused("R444_SOURCE_CLASS_TREE_TOO_LARGE")
            if file.suffix == suffix:
                found += 1
                if found > max_files:
                    raise Refused("R444_SOURCE_CLASS_COUNT_TOO_LARGE")
    return found


def exact_store_pin_matches(path: Path, expected: str) -> bool | None:
    """A checked SHA is an observation, NOT a signed source provenance proof."""
    if not regular(path):
        return None
    return r425.hash_file(path) == expected


def candidate_shape(path: Path) -> bool:
    """Recognize, never approve, a *possible* R442 full manifest."""
    try:
        if not regular(path):
            return False
        size = path.stat().st_size
        if size <= 0 or size > MAX_JSON_BYTES:
            return False
        with path.open("rb") as stream:
            raw = stream.read(MAX_JSON_BYTES + 1)
        if len(raw) != size:
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
    except (OSError, ValueError, UnicodeError, TypeError, r442.Refused):
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
        for child in sorted(base.iterdir()):
            if (child.name.startswith("R421-") and child != target
                    and directory(child)):
                yield child
    # R425 candidate receipts are saved under disposable TEMP roots.
    for child in sorted(temp.iterdir()):
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
            for child in current.iterdir():
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
