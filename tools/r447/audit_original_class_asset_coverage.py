#!/usr/bin/env python3
"""R447 offline v309 original JAR vs isolated R421 class/asset coverage.

Only read an independently exact-SHA pinned *original v309 client.jar*, and
R446-validated owner-private R421 source/class trees & dependencies. No
decompilation, runtime execution, network, installed client, cache/history,
user settings or production writes. Mapping class names is NOT proof of code
or behavioral parity. Optional report is PRIVATE and explicitly UNAPPROVED.
Use Python -B.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r440 import read_only_private_acceptance_preflight as r440
from tools.r444 import scan_owner_r421_artifacts as scanner
from tools.r446 import observe_owner_private_inventory as r446

ORIGINAL_SHA = "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
ORIGINAL_CLASSES = 10502
ORIGINAL_RESOURCES = 419
MAX_ORIGINAL_JAR_BYTES = 256 * 1024 * 1024
MAX_DEPENDENCY_BYTES = 64 * 1024 * 1024
MAX_ZIP_ENTRIES = 25000
MAX_UNCOMPRESSED_ENTRY = 100 * 1024 * 1024
MAX_UNCOMPRESSED_TOTAL = 2 * 1024 * 1024 * 1024
MAX_COMPANION_ENTRIES = 5000
MAX_COMPANION_DEPTH = 45
MAX_REPORT_BYTES = 4 * 1024 * 1024
PRIVATE_PREFIX = "SpawnPK-R447-Private-Coverage-"
PRIVATE_NAME = "R447-UNAPPROVED-ORIGINAL-COVERAGE.json"
PRIVATE_SCHEMA = "SpawnPK-R447-private-original-coverage-UNAPPROVED-v1"


class Refused(RuntimeError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def zip_path(name: str, directory: bool = False) -> None:
    """Reject paths that would escape a companion root when investigated."""
    need(type(name) is str and 0 < len(name) <= 4096
         and "\\" not in name and "\x00" not in name
         and not name.startswith("/") and not name.startswith("./")
         and all(part not in ("", ".", "..")
                 for part in name.rstrip("/").split("/"))
         and (not name.endswith("/") or directory),
         "R447_UNSAFE_ZIP_ENTRY_PATH")


def archive(raw: bytes, kind: str) -> tuple[set[str], set[str], dict[str, zipfile.ZipInfo]]:
    """Central-directory-only inventory: never decompress a ZIP entry."""
    need(kind in ("original", "dependency"), "R447_UNKNOWN_ARCHIVE_KIND")
    need(type(raw) is bytes and raw, "R447_EMPTY_ARCHIVE_BYTES")
    try:
        jar = zipfile.ZipFile(io.BytesIO(raw), "r")
        with jar:
            infos = jar.infolist()
            need(len(infos) <= MAX_ZIP_ENTRIES,
                 "R447_ZIP_ENTRY_BUDGET_EXCEEDED")
            classes: set[str] = set()
            resources: set[str] = set()
            resource_info: dict[str, zipfile.ZipInfo] = {}
            seen: set[str] = set()
            uncompressed = 0
            for info in infos:
                name = info.filename
                zip_path(name, info.is_dir())
                need(name not in seen, "R447_DUPLICATE_ZIP_ENTRY")
                seen.add(name)
                need(not (info.flag_bits & 0x1), "R447_ENCRYPTED_ZIP_ENTRY")
                mode = (info.external_attr >> 16) & 0o170000
                need(mode not in (stat.S_IFLNK, stat.S_IFCHR, stat.S_IFBLK,
                                  stat.S_IFIFO, stat.S_IFSOCK),
                     "R447_ZIP_SPECIAL_ENTRY_REFUSED")
                need(0 <= info.file_size <= MAX_UNCOMPRESSED_ENTRY,
                     "R447_UNCOMPRESSED_ENTRY_TOO_LARGE")
                uncompressed += info.file_size
                need(uncompressed <= MAX_UNCOMPRESSED_TOTAL,
                     "R447_UNCOMPRESSED_TOTAL_BUDGET_EXCEEDED")
                if info.is_dir():
                    continue
                if name.endswith(".class"):
                    classes.add(name)
                else:
                    resources.add(name)
                    resource_info[name] = info
            return classes, resources, resource_info
    except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile):
        raise Refused("R447_INVALID_ZIP_ARCHIVE") from None


def read_pinned_original(path: Path) -> bytes:
    raw = scanner.read_bounded_regular(
        path, MAX_ORIGINAL_JAR_BYTES, "R447_ORIGINAL_JAR_TOO_LARGE")
    need(raw is not None, "R447_ORIGINAL_JAR_MISSING_OR_UNSAFE")
    need(sha256(raw).hexdigest() == ORIGINAL_SHA,
         "R447_ORIGINAL_V309_SHA_MISMATCH")
    return raw


def java_owner_heuristic(classname: str) -> str:
    """Advisory filename heuristic, not a proven source-to-class mapping."""
    return classname.split("$", 1)[0].removesuffix(".class") + ".java"


def resource_companion(root: Path, original_jar: bytes,
                       resources: set[str]) -> tuple[dict[str, int], list[str], list[str]]:
    """Read-only compare actual bytes, never follow companion symlinks."""
    need(scanner.directory(root), "R447_COMPANION_ROOT_MISSING_OR_ALIAS")
    # Guard every existing parent of a user-supplied original companion root.
    for parent in (root.absolute(), *root.absolute().parents):
        need(scanner.directory(parent) and not r440.path_is_link(parent),
             "R447_COMPANION_PARENT_LINK_OR_NONDIR")
    found: set[str] = set()
    seen = 0
    stack = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        need(depth <= MAX_COMPANION_DEPTH and scanner.directory(directory),
             "R447_COMPANION_DEPTH_OR_LINK")
        for path in scanner.bounded_children(
                directory, MAX_COMPANION_ENTRIES, "R447_COMPANION_DIR_TOO_LARGE"):
            seen += 1
            need(seen <= MAX_COMPANION_ENTRIES,
                 "R447_COMPANION_ENTRY_BUDGET_EXCEEDED")
            if scanner.directory(path):
                stack.append((path, depth + 1))
                continue
            need(scanner.regular(path), "R447_COMPANION_LINK_OR_SPECIAL")
            name = path.relative_to(root).as_posix()
            zip_path(name)
            found.add(name)
    matching = 0
    mismatching: list[str] = []
    missing: list[str] = []
    with zipfile.ZipFile(io.BytesIO(original_jar)) as z:
        for name in sorted(resources):
            if name not in found:
                missing.append(name)
                continue
            expected_size = z.getinfo(name).file_size
            need(expected_size <= MAX_UNCOMPRESSED_ENTRY,
                 "R447_RESOURCE_UNCOMPRESSED_BUDGET")
            actual = scanner.read_bounded_regular(
                root.joinpath(*name.split("/")), MAX_UNCOMPRESSED_ENTRY,
                "R447_COMPANION_RESOURCE_TOO_LARGE")
            need(actual is not None,
                 "R447_COMPANION_RESOURCE_CHANGED_DURING_READ")
            # Bounded decompression, one entry at a time.
            with z.open(name, "r") as stream:
                digest = sha256()
                count = 0
                while True:
                    chunk = stream.read(65536)
                    if not chunk:
                        break
                    count += len(chunk)
                    need(count <= MAX_UNCOMPRESSED_ENTRY,
                         "R447_ORIGINAL_RESOURCE_TOO_LARGE")
                    digest.update(chunk)
            if count == len(actual) and digest.digest() == sha256(actual).digest():
                matching += 1
            else:
                mismatching.append(name)
    extras = sorted(found - resources)
    return {
        "companion_resource_byte_matches": matching,
        "companion_resource_mismatches": len(mismatching),
        "companion_resource_missing": len(missing),
        "companion_unreferenced_files": len(extras),
    }, missing + mismatching, extras


def examine(original_jar: Path, companion: Path | None = None) -> tuple[dict, dict]:
    current, _receipt = r446.observe()
    raw = read_pinned_original(original_jar)
    source = set(current["source_inventory"])
    rebuilt = set(current["class_inventory"])
    classes, resources, _ = archive(raw, "original")
    need(len(classes) == ORIGINAL_CLASSES and len(resources) == ORIGINAL_RESOURCES,
         "R447_PINNED_ORIGINAL_ARCHIVE_INVENTORY_DRIFT")
    _, _, _, dep_a, dep_b = r446.roots()
    dep_a_bytes = scanner.read_bounded_regular(
        dep_a, MAX_DEPENDENCY_BYTES, "R447_DEPENDENCY_A_TOO_LARGE")
    dep_b_bytes = scanner.read_bounded_regular(
        dep_b, MAX_DEPENDENCY_BYTES, "R447_DEPENDENCY_B_TOO_LARGE")
    need(dep_a_bytes is not None and dep_b_bytes is not None,
         "R447_DEPENDENCY_MISSING_OR_UNSAFE")
    need(sha256(dep_a_bytes).hexdigest() ==
         current["dependency_sha256"]["R239_filtered.jar"] and
         sha256(dep_b_bytes).hexdigest() ==
         current["dependency_sha256"]["R218.jar"],
         "R447_DEPENDENCY_CHANGED_DURING_AUDIT")
    primary, primary_res, _ = archive(dep_a_bytes, "dependency")
    alternate, alternate_res, _ = archive(dep_b_bytes, "dependency")
    runtime = rebuilt | primary
    original_not_on_runtime = sorted(classes - runtime)
    reconstructed_not_original = sorted(rebuilt - classes)
    unexpected_runtime = sorted(runtime - classes)
    orphan_compiled = sorted(x for x in rebuilt
                             if java_owner_heuristic(x) not in source)
    no_matching_top_class = sorted(x for x in source
                                   if x.removesuffix(".java")+".class" not in rebuilt)
    summary = {
        "status": "R447_ORIGINAL_CLASS_ASSET_COVERAGE_UNAPPROVED",
        "original_v309_exact_SHA_matched": True,
        "original_class_count": len(classes),
        "original_nonclass_resource_count": len(resources),
        "r421_observed_java_sources": len(source),
        "r421_observed_compiled_classes": len(rebuilt),
        "preferred_dependency_classes": len(primary),
        "alternate_dependency_classes": len(alternate),
        "preferred_dependency_resources": len(primary_res),
        "alternate_dependency_resources": len(alternate_res),
        "rebuilt_classes_also_named_in_original": len(rebuilt & classes),
        "rebuilt_classes_not_named_in_original": len(reconstructed_not_original),
        "rebuilt_class_source_filename_unmatched_heuristic": len(orphan_compiled),
        "java_sources_without_matching_top_level_class_heuristic": len(no_matching_top_class),
        "rebuilt_preferred_dependency_overlap": len(rebuilt & primary),
        "rebuilt_alternate_dependency_overlap": len(rebuilt & alternate),
        "preferred_alternate_dependency_overlap": len(primary & alternate),
        "combined_preferred_classpath_unique_paths": len(runtime),
        "original_class_names_on_combined_classpath": len(classes & runtime),
        "original_class_names_absent_from_combined_classpath": len(original_not_on_runtime),
        "combined_classpaths_not_named_in_original": len(unexpected_runtime),
        "resource_companion_examined": companion is not None,
        "assets_packaged_in_rebuilt_client_verified": False,
        "compiled_class_behavioural_equivalence_proven": False,
        "complete_readable_client_source_proven": False,
        "v312_compatibility_proven": False,
        "original_jar_modified": False,
        "client_started": False,
        "history_accessed": False,
        "candidate_compiled": False,
        "independent_R421_custody_approved": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    unverified_resources = sorted(resources)
    extra_companion: list[str] = []
    if companion is not None:
        extra, unverified_resources, extra_companion = resource_companion(
            companion, raw, resources)
        summary.update(extra)
    detail = {
        "schema": PRIVATE_SCHEMA,
        "status": "UNAPPROVED_OFFLINE_NAME_COVERAGE_ONLY",
        "original_class_names_not_on_reconstructed_classpath": original_not_on_runtime,
        "rebuilt_class_names_not_in_original": reconstructed_not_original,
        "original_class_names_covered_by_rebuilt_or_preferred_dep": sorted(classes & runtime),
        "classes_without_matching_source_filename_heuristic": orphan_compiled,
        "sources_without_matching_top_class_filename_heuristic": no_matching_top_class,
        "original_resource_names_needing_byte_verification": unverified_resources,
        "companion_extra_resource_paths": extra_companion,
        "compilation_authorized": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return summary, detail


def write_private_report(detail: dict) -> str:
    temp, *_ = r446.roots()
    need(scanner.directory(temp), "R447_PRIVATE_TEMP_UNAVAILABLE")
    raw = (json.dumps(detail, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)+"\n").encode("ascii")
    need(0 < len(raw) <= MAX_REPORT_BYTES,
         "R447_PRIVATE_NAME_MAP_TOO_LARGE")
    directory = Path(tempfile.mkdtemp(prefix=PRIVATE_PREFIX, dir=str(temp)))
    need(scanner.directory(directory) and directory.parent == temp,
         "R447_PRIVATE_OUTPUT_DIRECTORY_UNSAFE")
    name = directory / PRIVATE_NAME
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(name, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return directory.name


def run(original: Path, companion: Path | None = None,
        save_private_map: bool = False) -> dict:
    summary, detail = examine(original, companion)
    if save_private_map:
        # Recheck observed source/class/dependencies, exact original JAR and
        # optional companion before leaving any new private file on disk.
        after, detail_after = examine(original, companion)
        need(after == summary and detail_after == detail,
             "R447_INPUT_CHANGED_BEFORE_PRIVATE_REPORT")
        summary["private_quarantine_directory_name"] = write_private_report(detail)
        summary["private_name_map_created"] = True
    else:
        summary["private_name_map_created"] = False
    return summary


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-v309-jar", type=Path, required=True)
    p.add_argument("--resource-companion-root", type=Path)
    p.add_argument("--save-private-unapproved-name-map", action="store_true")
    a = p.parse_args(argv)
    try:
        result = run(a.original_v309_jar, a.resource_companion_root,
                     a.save_private_unapproved_name_map)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, r446.Refused, scanner.Refused, r440.Refused,
            OSError, ValueError, TypeError, UnicodeError, zipfile.BadZipFile) as e:
        reason = str(e) if isinstance(
            e, (Refused, r446.Refused, scanner.Refused, r440.Refused)) else (
                "R447_UNREADABLE_OR_CHANGED_OWNER_INPUT")
        print(json.dumps({
            "status": "R447_ORIGINAL_CLASS_ASSET_COVERAGE_REFUSED",
            "reason": reason[:120],
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
