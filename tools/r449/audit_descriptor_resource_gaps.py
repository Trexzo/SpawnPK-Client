#!/usr/bin/env python3
"""R449 read-only owner-private descriptor and resource-literal gap audit.

R448 scans CONSTANT_Class references. R449 additionally parses references
embedded in declared field/method descriptors, CONSTANT_NameAndType and
CONSTANT_MethodType descriptors, plus *candidate* resource paths from
CONSTANT_String entries. None proves dynamic linkage or resource loading.

Only the exact SHA-pinned v309 original and R446 pinned isolated R421 tree
are admissible. No Java is run, no original source is published, no installed
client/history/journal is touched. Private names only with opt-in TEMP output.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r388 import audit_offline_classpath as r388
from tools.r440 import read_only_private_acceptance_preflight as r440
from tools.r444 import scan_owner_r421_artifacts as scanner
from tools.r446 import observe_owner_private_inventory as r446
from tools.r447 import audit_original_class_asset_coverage as r447
from tools.r448 import audit_rebuilt_class_linkage as r448

SCHEMA = "SpawnPK-R449-descriptor-resource-candidates-UNAPPROVED-v1"
PREFIX = "SpawnPK-R449-Private-Descriptors-"
REPORT_NAME = "R449-UNAPPROVED-DESCRIPTORS-AND-RESOURCES.json"
MAX_ENTRIES = 65535
MAX_CLASS_TOTAL_BYTES = r448.MAX_CLASS_TOTAL_BYTES
MAX_REFS = 200000
MAX_STRING_CANDIDATES = 30000
MAX_OUTPUT_BYTES = 5 * 1024 * 1024
RESOURCE_SUFFIXES = frozenset({
    "png", "jpg", "jpeg", "gif", "webp", "bmp", "json", "xml", "txt",
    "dat", "bin", "properties", "csv", "idx", "ogg", "wav", "ttf",
    "otf", "fnt", "atlas", "vert", "frag", "glsl", "shader", "mf",
    "zip", "pack", "ini", "cfg", "yaml", "yml",
})


class Refused(RuntimeError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def descriptor_classes(descriptor: str) -> set[str]:
    """Parse JVMS field/method descriptor grammar, not arbitrary UTF8 blobs."""
    need(type(descriptor) is str and 0 < len(descriptor) <= 65535
         and descriptor.isascii(), "R449_INVALID_DESCRIPTOR_TEXT")
    result: set[str] = set()
    pos = 0

    def field_type(allow_void: bool = False) -> None:
        nonlocal pos
        arrays = 0
        while pos < len(descriptor) and descriptor[pos] == "[":
            pos += 1
            arrays += 1
            need(arrays <= 255, "R449_INVALID_ARRAY_DIMENSIONS")
        need(pos < len(descriptor), "R449_TRUNCATED_DESCRIPTOR")
        token = descriptor[pos]
        pos += 1
        if token in "BCDFIJSZ":
            return
        if token == "V" and allow_void and arrays == 0:
            return
        if token != "L":
            raise Refused("R449_INVALID_DESCRIPTOR_TYPE")
        terminal = descriptor.find(";", pos)
        need(terminal > pos, "R449_OBJECT_TYPE_TERMINATOR_MISSING")
        name = descriptor[pos:terminal]
        need(len(name) <= 4096 and "\\" not in name
             and all(part and part not in (".", "..")
                     and re.fullmatch(r"[A-Za-z0-9_$]+", part)
                     for part in name.split("/")),
             "R449_UNSAFE_DESCRIPTOR_OBJECT_PATH")
        result.add(name + ".class")
        pos = terminal + 1

    if descriptor[0] == "(":
        pos = 1
        argument_count = 0
        while pos < len(descriptor) and descriptor[pos] != ")":
            field_type()
            argument_count += 1
            need(argument_count <= 255, "R449_METHOD_ARGUMENT_LIMIT")
        need(pos < len(descriptor) and descriptor[pos] == ")",
             "R449_METHOD_CLOSING_PAREN_MISSING")
        pos += 1
        field_type(allow_void=True)
    else:
        field_type()
    need(pos == len(descriptor), "R449_TRAILING_DESCRIPTOR_BYTES")
    return result


def resource_literal(value: str) -> str | None:
    """Possible resource filename only; does not prove a resource API call."""
    if type(value) is not str or not (3 <= len(value) <= 512):
        return None
    normalized = value[1:] if value.startswith("/") else value
    if not normalized or any(ord(c) < 33 or ord(c) > 126 for c in normalized):
        return None
    try:
        r447.zip_path(normalized)
    except r447.Refused:
        return None
    basename = normalized.rsplit("/", 1)[-1]
    if "." not in basename:
        return None
    extension = basename.rsplit(".", 1)[-1].lower()
    return normalized if extension in RESOURCE_SUFFIXES else None


def class_metadata(raw: bytes) -> tuple[set[str], set[str], set[str]]:
    """Strictly bounded Java 11 CP/member parser, no Java class execution.

    Returns (CONSTANT_Class refs, descriptor-only refs, resource candidates).
    No arbitrary CONSTANT_Utf8 string is a presumed resource: only explicit
    CONSTANT_String items are considered, and only as weak candidates.
    """
    need(type(raw) is bytes and len(raw) >= 10
         and raw[:4] == b"\xca\xfe\xba\xbe"
         and int.from_bytes(raw[6:8], "big") == 55,
         "R449_JAVA11_CLASSFILE_REQUIRED")
    pos = 8

    def take(size: int) -> bytes:
        nonlocal pos
        need(0 <= size <= len(raw) - pos, "R449_TRUNCATED_CLASSFILE")
        result = raw[pos:pos+size]
        pos += size
        return result

    def u1() -> int:
        return take(1)[0]

    def u2() -> int:
        return int.from_bytes(take(2), "big")

    def u4() -> int:
        return int.from_bytes(take(4), "big")

    count = u2()
    need(1 <= count <= MAX_ENTRIES, "R449_INVALID_CONSTANT_POOL_COUNT")
    tags = [0] * count
    pool: list[object | None] = [None] * count
    descriptor_indexes: set[int] = set()
    resource_indexes: set[int] = set()
    i = 1
    while i < count:
        tag = u1()
        tags[i] = tag
        if tag == 1:
            size = u2()
            # Modified UTF-8 Java sequences are not always valid Python UTF8.
            # Decode with replacement: non-ASCII descriptor text is refused.
            pool[i] = take(size).decode("utf-8", "replace")
        elif tag in (3, 4):
            take(4)
        elif tag in (5, 6):
            take(8)
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            index = u2()
            pool[i] = index
            if tag == 8:
                resource_indexes.add(index)
            elif tag == 16:
                descriptor_indexes.add(index)
        elif tag in (9, 10, 11, 12, 17, 18):
            left, right = u2(), u2()
            pool[i] = (left, right)
            if tag == 12:
                descriptor_indexes.add(right)
        elif tag == 15:
            take(3)
        else:
            raise Refused("R449_UNKNOWN_CONSTANT_POOL_TAG")
        i += 1

    def utf(index: int) -> str:
        need(1 <= index < count and tags[index] == 1
             and type(pool[index]) is str, "R449_INVALID_UTF8_CONSTANT_INDEX")
        return pool[index]

    # Constant-pool index references must resolve to the right entry type.
    for i in range(1, count):
        if tags[i] in (7, 8, 16, 19, 20):
            utf(pool[i])
        if tags[i] == 12:
            name_idx, desc_idx = pool[i]
            utf(name_idx)
            utf(desc_idx)

    found_desc: set[str] = set()
    for index in descriptor_indexes:
        found_desc.update(descriptor_classes(utf(index)))

    # Field/method declaration descriptors may have no NameAndType entries.
    u2()  # access_flags
    u2()  # this_class
    u2()  # super_class
    interfaces = u2()
    need(interfaces <= MAX_ENTRIES, "R449_INTERFACES_LIMIT")
    take(interfaces * 2)

    def attributes() -> None:
        number = u2()
        need(number <= MAX_ENTRIES, "R449_ATTRIBUTE_COUNT_LIMIT")
        for _ in range(number):
            name_index = u2()
            length = u4()
            name = utf(name_index)
            need(length <= len(raw) - pos, "R449_INVALID_ATTRIBUTE_LENGTH")
            # Generic Signature attributes can encode additional type refs;
            # unsupported signatures are explicitly not claimed as covered.
            take(length)

    for _kind in ("fields", "methods"):
        members = u2()
        need(members <= MAX_ENTRIES, "R449_MEMBER_COUNT_LIMIT")
        for _ in range(members):
            u2()  # access_flags
            utf(u2())  # name_index
            descriptor_index = u2()
            found_desc.update(descriptor_classes(utf(descriptor_index)))
            attributes()

    attributes()  # class-level attributes
    need(pos == len(raw), "R449_CLASSFILE_TRAILING_DATA")

    try:
        class_refs = r388.constant_class_refs(raw)
    except ValueError:
        raise Refused("R449_INVALID_CLASS_REFERENCE_POOL") from None
    resource_candidates: set[str] = set()
    for index in resource_indexes:
        candidate = resource_literal(utf(index))
        if candidate is not None:
            resource_candidates.add(candidate)
    return class_refs, found_desc - class_refs, resource_candidates


def combined_graph(observation: dict) -> tuple[
        dict[str, set[str]], dict[str, set[str]], dict[str, set[str]]]:
    """Second independent bounded read of every SHA-verified R421 class."""
    _, _, class_root, _, _ = r446.roots()
    old: dict[str, set[str]] = {}
    descriptor_only: dict[str, set[str]] = {}
    resources: dict[str, set[str]] = {}
    bytes_total = 0
    ref_total = 0
    candidates_total = 0
    for name, fingerprint in sorted(observation["class_inventory"].items()):
        r447.zip_path(name)
        need(name.endswith(".class"), "R449_NON_CLASS_IN_COMPILED_MAP")
        raw = scanner.read_bounded_regular(
            class_root.joinpath(*name.split("/")), r448.MAX_CLASS_BYTES,
            "R449_CODE_FILE_TOO_LARGE")
        need(raw is not None and sha256(raw).hexdigest() == fingerprint,
             "R449_COMPILED_CLASS_CHANGED_DURING_AUDIT")
        bytes_total += len(raw)
        need(bytes_total <= MAX_CLASS_TOTAL_BYTES,
             "R449_CLASS_TOTAL_BYTE_BUDGET_EXCEEDED")
        before, added, asset_candidates = class_metadata(raw)
        old[name] = before
        descriptor_only[name] = added
        resources[name] = asset_candidates
        ref_total += len(before) + len(added)
        candidates_total += len(asset_candidates)
        need(ref_total <= MAX_REFS, "R449_REFERENCE_BUDGET_EXCEEDED")
        need(candidates_total <= MAX_STRING_CANDIDATES,
             "R449_RESOURCE_CANDIDATE_BUDGET_EXCEEDED")
    return old, descriptor_only, resources


def analyze_graphs(
    class_ref_graph: dict[str, set[str]],
    descriptor_graph: dict[str, set[str]],
    asset_graph: dict[str, set[str]],
    original_classes: set[str],
    preferred_classes: set[str],
    alternate_classes: set[str],
    original_resources: set[str],
) -> tuple[dict, dict]:
    """Pure aggregation; detailed referencers remain private."""
    need(class_ref_graph.keys() == descriptor_graph.keys()
         == asset_graph.keys(), "R449_GRAPH_KEYS_MISMATCH")
    rebuilt = set(class_ref_graph)
    runtime = rebuilt | preferred_classes
    prior = set().union(*class_ref_graph.values()) if rebuilt else set()
    descriptor_only = set().union(*descriptor_graph.values()) if rebuilt else set()
    # Count only newly uncovered descriptor targets, not fields already
    # represented as CONSTANT_Class in a different rebuilt class.
    incremental = descriptor_only - prior
    nonplatform = {c for c in incremental
                   if not c.startswith(r388.PLATFORM_ROOTS)}
    unresolved = nonplatform - runtime
    old_unresolved = {
        c for c in prior if not c.startswith(r388.PLATFORM_ROOTS)
        and c not in runtime
    }
    all_unresolved = old_unresolved | unresolved
    candidate_paths = set().union(*asset_graph.values()) if rebuilt else set()
    potential_existing = candidate_paths & original_resources
    potential_missing = candidate_paths - original_resources

    affected: dict[str, set[str]] = defaultdict(set)
    for source, refs in descriptor_graph.items():
        for name in refs & unresolved:
            affected[name].add(source)
    impacted_resources: dict[str, set[str]] = defaultdict(set)
    for source, refs in asset_graph.items():
        for name in refs:
            impacted_resources[name].add(source)

    summary = {
        "parsed_rebuilt_class_count": len(rebuilt),
        "unique_class_constant_pool_targets": len(prior),
        "unique_descriptor_only_targets": len(descriptor_only),
        "newly_discovered_descriptor_targets_not_in_any_class_index":
            len(incremental),
        "new_nonplatform_descriptor_targets": len(nonplatform),
        "newly_unresolved_descriptor_class_targets": len(unresolved),
        "new_unresolved_descriptor_targets_present_in_original_v309":
            len(unresolved & original_classes),
        "new_unresolved_descriptor_targets_absent_from_original_v309":
            len(unresolved - original_classes),
        "new_unresolved_descriptor_targets_present_in_alternate_dependency":
            len(unresolved & alternate_classes),
        "previous_unresolved_class_index_targets": len(old_unresolved),
        "combined_unresolved_static_class_targets": len(all_unresolved),
        "possible_literal_resource_paths": len(candidate_paths),
        "possible_literal_resource_paths_present_in_original":
            len(potential_existing),
        "possible_literal_resource_paths_absent_from_original":
            len(potential_missing),
        "resource_literal_usage_proven": False,
        "descriptor_reference_behavioral_linkage_proven": False,
        "dynamic_reflection_or_JNI_covered": False,
        "generic_signature_type_references_complete": False,
    }
    private = {
        "new_descriptor_only_unresolved_references": [
            {"class_name": name,
             "referencing_rebuilt_classes": sorted(affected[name]),
             "referencer_count": len(affected[name]),
             "present_in_original_v309": name in original_classes,
             "available_in_alternate_dependency": name in alternate_classes,
             "runtime_reachable_proven": False}
            for name in sorted(unresolved,
                               key=lambda x: (-len(affected[x]), x))],
        "possible_resource_literals": [
            {"resource_path": name,
             "referencing_rebuilt_classes": sorted(impacted_resources[name]),
             "present_in_original_v309": name in original_resources,
             "resource_load_proven": False}
            for name in sorted(candidate_paths)],
        "new_descriptor_refs_are_incremental_over_R448": True,
        "independently_approved_R421_reference": False,
        "runtime_tested": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return summary, private


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    # R448 enforces exact v309 original SHA, source/class pins, dependencies,
    # and already checked 1,277/1,394 inventories. Nothing is executed.
    prior, _ = r448.inspect(original, companion)
    observed, _ = r446.observe()
    class_refs, desc_refs, asset_strings = combined_graph(observed)
    raw = r447.read_pinned_original(original)
    original_classes, original_resources, _ = r447.archive(raw, "original")
    _, _, _, preferred_path, alternate_path = r446.roots()
    preferred = scanner.read_bounded_regular(
        preferred_path, r447.MAX_DEPENDENCY_BYTES,
        "R449_PREFERRED_JAR_TOO_LARGE")
    alternate = scanner.read_bounded_regular(
        alternate_path, r447.MAX_DEPENDENCY_BYTES,
        "R449_ALTERNATE_JAR_TOO_LARGE")
    need(preferred is not None and alternate is not None,
         "R449_DEPENDENCY_MISSING")
    need(sha256(preferred).hexdigest() ==
         observed["dependency_sha256"]["R239_filtered.jar"]
         and sha256(alternate).hexdigest() ==
         observed["dependency_sha256"]["R218.jar"],
         "R449_DEPENDENCIES_CHANGED")
    preferred_names, _, _ = r447.archive(preferred, "dependency")
    alternate_names, _, _ = r447.archive(alternate, "dependency")
    summary, private = analyze_graphs(
        class_refs, desc_refs, asset_strings, original_classes,
        preferred_names, alternate_names, original_resources)
    # A matching *current* double-check is NOT an approved historical digest.
    after, _ = r446.observe()
    need(after == observed, "R449_R421_INPUT_CHANGED_DURING_AUDIT")
    need(sha256(r447.read_pinned_original(original)).hexdigest()
         == r447.ORIGINAL_SHA, "R449_ORIGINAL_CHANGED_DURING_AUDIT")
    result = {
        "status": "R449_DESCRIPTOR_AND_RESOURCE_LITERAL_GAPS_UNAPPROVED",
        "exact_original_v309_sha_matched": prior["original_exact_sha_matched"],
        "original_class_files": prior["original_class_count"],
        "original_resource_files": prior["original_resource_count"],
        "rebuilt_java_sources": prior["reconstructed_java_sources"],
        "rebuilt_compiled_class_files": prior["reconstructed_classfiles"],
        "original_resource_companion_checked": companion is not None,
        "owner_private_classes_executed": False,
        "complete_client_source_proven": False,
        "assets_packaged_proven": False,
        "prior_R421_custody_approved": False,
        "build_authorized": False,
        "release_authorized": False,
        "merge_authorized": False,
        **summary,
    }
    if companion is not None:
        for name in ("companion_resource_byte_matches",
                     "companion_resource_missing",
                     "companion_resource_mismatches"):
            result[name] = prior[name]
    worklist = {
        "schema": SCHEMA,
        "status": "CURRENT_STATIC_OBSERVATIONS_NOT_AUTHENTICATED_HISTORICAL_BASELINE",
        "descriptor_and_resource_details": private,
        "historical_R421_reference_approved": False,
        "complete_client_parity_proven": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return result, worklist


def save_private_worklist(details: dict) -> str:
    temp, *_ = r446.roots()
    need(scanner.directory(temp), "R449_OWNER_TEMP_MISSING")
    blob = (json.dumps(details, sort_keys=True, ensure_ascii=True,
                       separators=(",", ":")) + "\n").encode("ascii")
    need(0 < len(blob) <= MAX_OUTPUT_BYTES, "R449_PRIVATE_WORKLIST_TOO_LARGE")
    folder = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(temp)))
    need(folder.parent == temp and scanner.directory(folder),
         "R449_PRIVATE_OUTPUT_NOT_ISOLATED")
    target = folder / REPORT_NAME
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_BINARY", 0) |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as file:
        file.write(blob)
        file.flush()
        os.fsync(file.fileno())
    return folder.name


def run(original: Path, companion: Path | None = None,
        save_private: bool = False) -> dict:
    report, worklist = inspect(original, companion)
    if save_private:
        new_report, new_details = inspect(original, companion)
        need(new_report == report and new_details == worklist,
             "R449_INPUT_CHANGED_BEFORE_SAVING_PRIVATE_WORKLIST")
        report["private_quarantine_directory_name"] = (
            save_private_worklist(worklist))
        report["private_worklist_saved"] = True
    else:
        report["private_worklist_saved"] = False
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-v309-jar", required=True, type=Path)
    p.add_argument("--resource-companion-root", type=Path)
    p.add_argument("--save-private-unapproved-worklist", action="store_true")
    args = p.parse_args(argv)
    try:
        print(json.dumps(run(args.original_v309_jar, args.resource_companion_root,
                             args.save_private_unapproved_worklist),
                         sort_keys=True))
        return 0
    except (Refused, r448.Refused, r447.Refused, r446.Refused,
            scanner.Refused, r440.Refused,
            OSError, ValueError, UnicodeError, TypeError) as error:
        reason = str(error) if isinstance(error, (
            Refused, r448.Refused, r447.Refused, r446.Refused,
            scanner.Refused, r440.Refused)) else (
                "R449_PRIVATE_REFERENCE_INPUT_REFUSED")
        print(json.dumps({
            "status": "R449_DESCRIPTOR_RESOURCE_AUDIT_REFUSED",
            "reason": reason[:120],
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
