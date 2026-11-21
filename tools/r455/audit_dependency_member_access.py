#!/usr/bin/env python3
"""R455 owner-local, SHA-pinned R421 dependency member access worklist.

Builds on the full R454 audit; selectively decompresses *only referenced*
Java 1.1..11 class metadata from the existing SHA-verified preferred JAR.
No code executes. No original source, game history, installed client, assets
or R415/R417 journal evidence is modified. Details are private opt-in only.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r440 import read_only_private_acceptance_preflight as r440
from tools.r444 import scan_owner_r421_artifacts as scanner
from tools.r446 import observe_owner_private_inventory as r446
from tools.r447 import audit_original_class_asset_coverage as r447
from tools.r448 import audit_rebuilt_class_linkage as r448
from tools.r449 import audit_descriptor_resource_gaps as r449
from tools.r450 import audit_generic_resource_proximity as r450
from tools.r451 import audit_resource_operand_arguments as r451
from tools.r452 import audit_forward_branch_resource as r452
from tools.r453 import audit_member_reference_coverage as r453
from tools.r454 import audit_inherited_member_ancestry as r454
from tools.r455 import dependency_member_access as dep

SCHEMA = "SpawnPK-R455-preferred-dependency-access-UNAPPROVED-v1"
PREFIX = "SpawnPK-R455-Private-DependencyAccess-"
NAME = "R455-UNAPPROVED-DEPENDENCY-ACCESS.json"
MAX_PRIVATE_BYTES = 5 * 1024 * 1024


class Refused(RuntimeError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    prior, _ = r454.inspect(original, companion)
    observation, _ = r446.observe()
    records = r453.observed_members(observation)
    original_bytes = r447.read_pinned_original(original)
    original_names, _resources, _ = r447.archive(original_bytes, "original")
    _, _, _, preferred_path, alternate_path = r446.roots()
    preferred_bytes = scanner.read_bounded_regular(
        preferred_path, r447.MAX_DEPENDENCY_BYTES,
        "R455_PREFERRED_JAR_UNSAFE_OR_TOO_LARGE")
    alternate_bytes = scanner.read_bounded_regular(
        alternate_path, r447.MAX_DEPENDENCY_BYTES,
        "R455_ALTERNATE_JAR_UNSAFE_OR_TOO_LARGE")
    need(preferred_bytes is not None and alternate_bytes is not None,
         "R455_DEPENDENCY_BYTES_UNAVAILABLE")
    preferred_sha = observation["dependency_sha256"]["R239_filtered.jar"]
    alternate_sha = observation["dependency_sha256"]["R218.jar"]
    need(sha256(preferred_bytes).hexdigest() == preferred_sha
         and sha256(alternate_bytes).hexdigest() == alternate_sha,
         "R455_DEPENDENCY_SHA_CHANGED")
    preferred_names, _, _ = r447.archive(preferred_bytes, "dependency")
    alternate_names, _, _ = r447.archive(alternate_bytes, "dependency")

    selected = dep.selected_dependencies(
        preferred_bytes, preferred_sha, preferred_names, records)
    result_counts, private = dep.analyze(
        records, selected, original_names, alternate_names)
    need(result_counts["rebuilt_classfiles_examined"] ==
         prior["isolated_r421_compiled_classes"],
         "R455_R421_CLASS_COUNT_DISAGREEMENT")
    need(result_counts["unique_member_references_in_rebuilt_classfiles"] ==
         prior["unique_rebuilt_constant_pool_member_references"],
         "R455_R454_MEMBER_COUNT_DISAGREEMENT")
    need(r446.observe()[0] == observation,
         "R455_R421_INPUT_CHANGED_DURING_ANALYSIS")
    need(sha256(r447.read_pinned_original(original)).hexdigest() ==
         r447.ORIGINAL_SHA, "R455_ORIGINAL_V309_CHANGED_DURING_ANALYSIS")
    summary = {
        "status": "R455_SELECTED_DEPENDENCY_MEMBER_ACCESS_UNAPPROVED",
        "original_v309_sha_verified": prior["original_v309_exact_sha_verified"],
        "original_v309_classes": prior["original_v309_class_count"],
        "original_v309_resources": prior["original_v309_resource_count"],
        "isolated_r421_sources": prior["isolated_r421_source_count"],
        "isolated_r421_classes": prior["isolated_r421_compiled_classes"],
        "original_resource_companion_checked": companion is not None,
        "owner_client_started": False,
        "private_game_history_accessed": False,
        "original_bytecode_behavioral_parity_proven": False,
        "full_runnable_deobfuscated_source_proven": False,
        "historical_R421_full_inventory_independently_approved": False,
        "write_fences_or_deletion_intent_changed": False,
        "client_build_authorized": False,
        "merge_authorized": False,
        "release_authorized": False,
        **result_counts,
    }
    if companion is not None:
        for key in ("companion_resource_byte_matches",
                    "companion_resource_missing",
                    "companion_resource_mismatches"):
            summary[key] = prior[key]
    detail = {
        "schema": SCHEMA,
        "status": "UNAPPROVED_PREFERRED_DEPENDENCY_MEMBER_ACCESS_SIGNALS",
        "private_only_dependency_member_access": private,
        "historical_R421_manifest_approved": False,
        "runtime_binary_linkage_proven": False,
        "merge_authorized": False,
        "release_authorized": False,
    }
    return summary, detail


def save_private(detail: dict) -> str:
    temp, *_ = r446.roots()
    need(scanner.directory(temp), "R455_OWNER_OS_TEMP_UNAVAILABLE")
    raw = (json.dumps(detail, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True) + "\n").encode("ascii")
    need(0 < len(raw) <= MAX_PRIVATE_BYTES,
         "R455_PRIVATE_WORKLIST_SIZE_EXCEEDED")
    folder = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(temp)))
    need(folder.parent == temp and scanner.directory(folder),
         "R455_PRIVATE_DIRECTORY_INVALID")
    target = folder / NAME
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    fd = os.open(target, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return folder.name


def run(original: Path, companion: Path | None = None,
        save: bool = False) -> dict:
    before = r446.observe()[0] if save else None
    report, detail = inspect(original, companion)
    if save:
        after, rechecked = inspect(original, companion)
        need(report == after and detail == rechecked
             and before == r446.observe()[0],
             "R455_INPUTS_CHANGED_BEFORE_PRIVATE_OUTPUT")
        report["private_quarantine_directory"] = save_private(detail)
        report["private_worklist_saved"] = True
    else:
        report["private_worklist_saved"] = False
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-v309-jar", required=True, type=Path)
    p.add_argument("--resource-companion-root", type=Path)
    p.add_argument("--save-private-unapproved-worklist", action="store_true")
    a = p.parse_args(argv)
    try:
        print(json.dumps(run(
            a.original_v309_jar, a.resource_companion_root,
            a.save_private_unapproved_worklist), sort_keys=True))
        return 0
    except (Refused, dep.Refused, r454.Refused, r453.Refused, r452.Refused,
            r451.Refused, r450.Refused, r449.Refused, r448.Refused,
            r447.Refused, r446.Refused, r440.Refused, scanner.Refused,
            ValueError, TypeError, UnicodeError, OSError) as error:
        if isinstance(error, (
            Refused, dep.Refused, r454.Refused, r453.Refused, r452.Refused,
            r451.Refused, r450.Refused, r449.Refused, r448.Refused,
            r447.Refused, r446.Refused, r440.Refused, scanner.Refused)):
            reason = str(error)[:120]
        else:
            reason = "R455_PRIVATE_DEPENDENCY_INPUT_REFUSED"
        print(json.dumps({
            "status": "R455_DEPENDENCY_MEMBER_ACCESS_AUDIT_REFUSED",
            "reason": reason,
            "merge_authorized": False,
            "release_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
