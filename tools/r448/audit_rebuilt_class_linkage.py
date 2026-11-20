#!/usr/bin/env python3
"""R448 offline bytecode-reference worklist for reconstructed v309/R421 client.

Inspects the constant-pool Class entries of the *isolated R421 compiled*
classfiles, intersects their references with the known original v309 JAR
and preferred/alternate dependencies, and ranks absent names as a private
reconstruction worklist. Exact original-v309 SHA and R446 R421 Store pins
are mandatory. Never executes classes, launches client, decompiles, writes
source, reads player histories, or approves a release.

Constant-pool refs are incomplete (reflection, descriptors, JNI, resource
lookups and dynamic loading). A missing class name is not necessarily a
missing feature; an observed class name is not proof of behavioral parity.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from hashlib import sha256
import json
import os
from pathlib import Path
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

SCHEMA = "SpawnPK-R448-rebuilt-bytecode-linkage-UNAPPROVED-v1"
PREFIX = "SpawnPK-R448-Private-Linkage-"
NAME = "R448-UNAPPROVED-LINKAGE-WORKLIST.json"
MAX_CLASS_BYTES = 32 * 1024 * 1024
MAX_CLASS_TOTAL_BYTES = 700 * 1024 * 1024
MAX_CLASS_REFS = 200000
MAX_WORKLIST_BYTES = 5 * 1024 * 1024
MAX_ORIGINAL_SIZE = 256 * 1024 * 1024


class Refused(RuntimeError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def source_class_refs(observed: dict) -> dict[str, set[str]]:
    """Hash-check class bytes again and parse only their constant pools."""
    _, _, classes_dir, _, _ = r446.roots()
    need(scanner.directory(classes_dir),
         "R448_ISOLATED_R421_COMPILED_ROOT_MISSING")
    expected = observed["class_inventory"]
    need(type(expected) is dict and len(expected) > 0,
         "R448_EMPTY_R421_CLASS_INVENTORY")
    graph: dict[str, set[str]] = {}
    bytes_total = 0
    references_total = 0
    for class_name, approved_current_sha in sorted(expected.items()):
        r447.zip_path(class_name)
        need(class_name.endswith(".class"), "R448_NON_CLASS_IN_R421_SNAPSHOT")
        target = classes_dir.joinpath(*class_name.split("/"))
        raw = scanner.read_bounded_regular(
            target, MAX_CLASS_BYTES, "R448_COMPILED_CLASS_FILE_TOO_LARGE")
        need(raw is not None, "R448_R421_COMPILED_FILE_MISSING_OR_UNSAFE")
        bytes_total += len(raw)
        need(bytes_total <= MAX_CLASS_TOTAL_BYTES,
             "R448_R421_COMPILED_TOTAL_BYTES_LIMIT")
        need(sha256(raw).hexdigest() == approved_current_sha,
             "R448_R421_COMPILED_MEMBER_CHANGED_SINCE_OBSERVATION")
        try:
            need(len(raw) >= 10 and raw[:4] == b"\xca\xfe\xba\xbe"
                 and int.from_bytes(raw[6:8], "big") == 55,
                 "R448_JAVA11_R421_CLASSFILE_REQUIRED")
            refs = r388.constant_class_refs(raw)
        except ValueError:
            raise Refused("R448_BAD_OR_TRUNCATED_CLASS_CONSTANT_POOL") from None
        references_total += len(refs)
        need(references_total <= MAX_CLASS_REFS,
             "R448_CLASS_REFERENCE_BUDGET_EXCEEDED")
        graph[class_name] = refs
    return graph


def direct_graph_worklist(
    graph: dict[str, set[str]],
    original: set[str],
    preferred: set[str],
    alternate: set[str],
    owner_source_paths: set[str],
    entrypoint: str | None = None,
) -> tuple[dict, dict]:
    """Pure graph analysis; no class/JAR bytecode, no I/O or source content."""
    rebuilt = set(graph)
    preferred_runtime = rebuilt | preferred
    all_references = set().union(*graph.values()) if graph else set()
    nonplatform = {x for x in all_references
                   if not x.startswith(r388.PLATFORM_ROOTS)}
    absent = nonplatform - preferred_runtime
    missing_original = absent & original
    missing_not_original = absent - original
    preferred_unique = preferred - rebuilt
    alternate_rescues = absent & alternate
    owners_without_source = {
        class_name for class_name in rebuilt
        if r447.java_owner_heuristic(class_name) not in owner_source_paths
    }

    reference_users: dict[str, set[str]] = defaultdict(set)
    for user, refs in graph.items():
        for ref in refs & absent:
            reference_users[ref].add(user)

    def priority(ref: str) -> tuple:
        users = reference_users.get(ref, set())
        # More affected compiled files rank first, followed by names with
        # a classfile in the SHA-pinned original JAR, then lexical name.
        return (-len(users), 0 if ref in original else 1, ref)

    ordered = sorted(absent, key=priority)
    worklist = [{
        "class_name": name,
        "referencing_rebuilt_class_names": sorted(reference_users[name]),
        "direct_rebuilt_referencer_count": len(reference_users[name]),
        "original_v309_class_name_present": name in original,
        "available_only_in_alternate_dependency": name in alternate_rescues,
        "source_filename_heuristic_present":
            r447.java_owner_heuristic(name) in owner_source_paths,
        "behavioral_parity_verified": False,
    } for name in ordered]

    reachable = None
    reach_class_count = None
    reach_missing_original = None
    reach_missing_unknown = None
    if entrypoint is not None:
        need(entrypoint in graph, "R448_ENTRYPOINT_NOT_IN_REBUILT_TREE")
        reached: set[str] = set()
        pending = deque([entrypoint])
        reachable = set()
        while pending:
            current = pending.popleft()
            if current in reached:
                continue
            reached.add(current)
            refs = graph[current]
            reachable.update(refs & absent)
            pending.extend(sorted((refs & rebuilt) - reached))
        reach_class_count = len(reached)
        reach_missing_original = len(reachable & original)
        reach_missing_unknown = len(reachable - original)

    class_report = {
        "rebuilt_compiled_classfiles_parsed": len(graph),
        "rebuilt_compiled_classfiles_without_same_named_source_heuristic":
            len(owners_without_source),
        "unique_rebuilt_constant_pool_class_targets": len(all_references),
        "unique_rebuilt_nonplatform_class_targets": len(nonplatform),
        "class_targets_resolved_by_rebuilt_or_preferred_dependency":
            len(nonplatform & preferred_runtime),
        "class_targets_unresolved_in_preferred_runtime": len(absent),
        "unresolved_class_targets_present_in_original_v309": len(missing_original),
        "unresolved_class_targets_absent_from_original_v309":
            len(missing_not_original),
        "unresolved_class_targets_available_in_alternate_dependency":
            len(alternate_rescues),
        "preferred_dependency_class_paths_not_in_rebuilt": len(preferred_unique),
        "selected_rebuilt_entrypoint_requested": entrypoint is not None,
        "selected_entrypoint_rebuilt_reachable_classes": reach_class_count,
        "selected_entrypoint_reachable_unresolved_present_in_original":
            reach_missing_original,
        "selected_entrypoint_reachable_unresolved_absent_from_original":
            reach_missing_unknown,
        "constant_pool_only_advisory": True,
        "runtime_linkage_proven": False,
        "client_runnable_proven": False,
        "complete_deobfuscation_proven": False,
    }
    private = {
        "unresolved_reconstruction_worklist": worklist,
        "rebuilt_class_names_without_matching_source_filename_heuristic":
            sorted(owners_without_source),
        "selected_entrypoint_reachable_missing_class_names":
            sorted(reachable) if reachable is not None else None,
        "source_mapping_is_heuristic_only": True,
        "release_authorized": False,
    }
    return class_report, private


def resource_extension_counts(names: set[str]) -> dict[str, int]:
    """Aggregate resource extension labels; no resource paths in stdout."""
    counts = Counter()
    for name in names:
        # Name is a ZIP entry from R447's already path-checked original jar.
        file = name.rsplit("/", 1)[-1]
        ext = file.rsplit(".", 1)[-1].lower() if "." in file else "<no extension>"
        if ext != "<no extension>" and (not ext or len(ext) > 12 or
                                        not ext.isascii() or not ext.isalnum()):
            ext = "<other>"
        counts[ext] += 1
    return dict(sorted(counts.items()))


def inspect(original_jar: Path, companion: Path | None = None,
            entrypoint: str | None = None) -> tuple[dict, dict]:
    # The R447 gate verifies original JAR exact hash and fixed original 10,502
    # class/419 resource census, and calls R446 strict owner-isolated file gates.
    coverage, _original_detail = r447.examine(original_jar, companion)
    observation, _receipt = r446.observe()
    graph = source_class_refs(observation)
    original_bytes = r447.read_pinned_original(original_jar)
    original_classes, original_resources, _ = r447.archive(
        original_bytes, "original")
    _, _, _, preferred_jar, alternate_jar = r446.roots()
    preferred_raw = scanner.read_bounded_regular(
        preferred_jar, r447.MAX_DEPENDENCY_BYTES,
        "R448_PREFERRED_DEPENDENCY_TOO_LARGE")
    alternate_raw = scanner.read_bounded_regular(
        alternate_jar, r447.MAX_DEPENDENCY_BYTES,
        "R448_ALTERNATE_DEPENDENCY_TOO_LARGE")
    need(preferred_raw is not None and alternate_raw is not None,
         "R448_DEPENDENCY_MISSING_OR_UNSAFE")
    need(sha256(preferred_raw).hexdigest() ==
         observation["dependency_sha256"]["R239_filtered.jar"]
         and sha256(alternate_raw).hexdigest() ==
         observation["dependency_sha256"]["R218.jar"],
         "R448_DEPENDENCY_CHANGED_DURING_AUDIT")
    preferred_classes, _, _ = r447.archive(preferred_raw, "dependency")
    alternate_classes, _, _ = r447.archive(alternate_raw, "dependency")
    classes, private = direct_graph_worklist(
        graph, original_classes, preferred_classes, alternate_classes,
        set(observation["source_inventory"]), entrypoint)

    # Reject even an identical-count substitution between graph, JAR reads,
    # and optional source/asset comparison. Full per-file inventory equality
    # is a current-observation stability check, NOT historical approval.
    again, _ = r446.observe()
    need(again == observation, "R448_R421_INPUT_CHANGED_DURING_ANALYSIS")
    need(sha256(r447.read_pinned_original(original_jar)).hexdigest()
         == r447.ORIGINAL_SHA, "R448_ORIGINAL_CHANGED_DURING_ANALYSIS")
    summary = {
        "status": "R448_REBUILT_CONSTANT_POOL_GAP_ANALYSIS_UNAPPROVED",
        "original_exact_sha_matched": coverage["original_v309_exact_SHA_matched"],
        "original_class_count": coverage["original_class_count"],
        "original_resource_count": coverage["original_nonclass_resource_count"],
        "reconstructed_java_sources": coverage["r421_observed_java_sources"],
        "reconstructed_classfiles": coverage["r421_observed_compiled_classes"],
        "original_class_names_not_on_combined_classpath":
            coverage["original_class_names_absent_from_combined_classpath"],
        "original_resource_file_extension_counts":
            resource_extension_counts(original_resources),
        "resource_companion_examined": companion is not None,
        "independent_prior_R421_custody_proven": False,
        "bytecode_instruction_parity_proven": False,
        "runtime_tested": False,
        "assets_packaged_into_rebuilt_JAR_proven": False,
        "client_started": False,
        "player_history_accessed": False,
        "build_authorized": False,
        "release_authorized": False,
        "merge_authorized": False,
        **classes,
    }
    if companion is not None:
        for key in ("companion_resource_byte_matches",
                    "companion_resource_mismatches",
                    "companion_resource_missing",
                    "companion_unreferenced_files"):
            summary[key] = coverage[key]
    worklist = {
        "schema": SCHEMA,
        "status": "UNAPPROVED_CURRENT_REBUILT_CLASS_REFERENCE_WORKLIST",
        "original_v309_class_count": coverage["original_class_count"],
        "reconstructed_class_count": coverage["r421_observed_compiled_classes"],
        "missing_class_details": private["unresolved_reconstruction_worklist"],
        "rebuilt_unmatched_source_heuristic":
            private["rebuilt_class_names_without_matching_source_filename_heuristic"],
        "selected_entrypoint_reachable_missing_class_names":
            private["selected_entrypoint_reachable_missing_class_names"],
        "original_resource_extension_counts":
            resource_extension_counts(original_resources),
        "resource_companion_examined": companion is not None,
        "complete_client_source_proven": False,
        "original_jvm_instruction_parity_proven": False,
        "historical_R421_reference_approved": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return summary, worklist


def write_private_worklist(payload: dict) -> str:
    """Only opt-in NEW owner-TEMP quarantine; no existing file overwritten."""
    temporary, *_ = r446.roots()
    need(scanner.directory(temporary), "R448_OWNER_TEMP_MISSING")
    blob = (json.dumps(payload, sort_keys=True, ensure_ascii=True,
                       separators=(",", ":")) + "\n").encode("ascii")
    need(0 < len(blob) <= MAX_WORKLIST_BYTES,
         "R448_PRIVATE_WORKLIST_TOO_LARGE")
    folder = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(temporary)))
    need(folder.parent == temporary and scanner.directory(folder),
         "R448_PRIVATE_REPORT_DIR_INVALID")
    output = folder / NAME
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_BINARY", 0) |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(blob)
        handle.flush()
        os.fsync(handle.fileno())
    return folder.name


def run(original_jar: Path, companion: Path | None = None,
        entrypoint: str | None = None, save_private: bool = False) -> dict:
    report, private = inspect(original_jar, companion, entrypoint)
    if save_private:
        # Require the entire public/private result to remain identical under
        # a fresh read-only scan before creating a new private report.
        reread_report, reread_private = inspect(original_jar, companion, entrypoint)
        need(reread_report == report and reread_private == private,
             "R448_INPUT_CHANGED_BEFORE_PRIVATE_REPORT")
        report["private_quarantine_directory_name"] = (
            write_private_worklist(private))
        report["private_worklist_saved"] = True
    else:
        report["private_worklist_saved"] = False
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-v309-jar", type=Path, required=True)
    parser.add_argument("--resource-companion-root", type=Path)
    parser.add_argument("--entrypoint-class")
    parser.add_argument("--save-private-unapproved-worklist", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run(
            args.original_v309_jar, args.resource_companion_root,
            args.entrypoint_class, args.save_private_unapproved_worklist),
            sort_keys=True))
        return 0
    except (Refused, scanner.Refused, r440.Refused, r446.Refused,
            r447.Refused, ValueError, TypeError, OSError, UnicodeError) as error:
        reason = str(error) if isinstance(
            error, (Refused, scanner.Refused, r440.Refused,
                    r446.Refused, r447.Refused)) else (
            "R448_OWNER_PRIVATE_INPUT_OR_BYTECODE_REFUSED")
        print(json.dumps({
            "status": "R448_REBUILT_REFERENCE_ANALYSIS_REFUSED",
            "reason": reason[:130],
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
