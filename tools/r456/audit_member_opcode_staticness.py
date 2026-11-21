#!/usr/bin/env python3
"""R456 original-v309/R421 SHA-gated JVM opcode vs member-flag census.

Owner-only static metadata; inherited full R455→R446 admission, bounded
classfile reads, safe selected dependency parsing. Stdout is aggregate-only.
No original client launch, source modification or production history access.
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
from tools.r450 import classfile_signature_resource as classfile
from tools.r451 import audit_resource_operand_arguments as r451
from tools.r452 import audit_forward_branch_resource as r452
from tools.r453 import audit_member_reference_coverage as r453
from tools.r454 import audit_inherited_member_ancestry as r454
from tools.r455 import audit_dependency_member_access as r455
from tools.r455 import dependency_member_access as selected_jars
from tools.r456 import member_opcode_evidence as opcodes

SCHEMA = "SpawnPK-R456-opcode-member-staticness-UNAPPROVED-v1"
PREFIX = "SpawnPK-R456-Private-OpcodeMembers-"
NAME = "R456-UNAPPROVED-OPCODE-MEMBER-CANDIDATES.json"
MAX_TOTAL_CLASS_BYTES = 700 * 1024 * 1024
MAX_TOTAL_MEMBER_SITES = 250000
MAX_PRIVATE_BYTES = 5 * 1024 * 1024


class Refused(RuntimeError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def code_sites(observation: dict):
    """Reopen each compiled class from exact owner inventory, validate SHA."""
    _, _, class_root, _, _ = r446.roots()
    need(scanner.directory(class_root), "R456_COMPILED_CLASS_ROOT_UNSAFE")
    sites: list[opcodes.Site] = []
    dynamic = 0
    bytes_seen = 0
    classes = observation["class_inventory"]
    for path, fingerprint in sorted(classes.items()):
        r447.zip_path(path)
        need(path.endswith(".class"), "R456_NON_CLASS_MEMBER_IN_INVENTORY")
        data = scanner.read_bounded_regular(
            class_root.joinpath(*path.split("/")), r448.MAX_CLASS_BYTES,
            "R456_CLASS_INPUT_TOO_LARGE")
        need(data is not None and sha256(data).hexdigest() == fingerprint,
             "R456_COMPILED_INPUT_CHANGED_DURING_SCAN")
        bytes_seen += len(data)
        need(bytes_seen <= MAX_TOTAL_CLASS_BYTES,
             "R456_TOTAL_CLASS_BYTES_EXCEEDED")
        observer = opcodes.Collector(path)
        # The original Code scanner validates Java 11 CP, attributes and
        # decoded instruction boundaries; only typed references are emitted.
        classfile.classfile_evidence(
            data, r449.resource_literal, member_observer=observer)
        sites.extend(observer.sites)
        dynamic += observer.dynamic_sites
        need(len(sites) + dynamic <= MAX_TOTAL_MEMBER_SITES,
             "R456_TOTAL_OPCODE_SITE_BUDGET")
    return sites, dynamic


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    prior, _ = r455.inspect(original, companion)
    observed, _ = r446.observe()
    rebuilt = r453.observed_members(observed)
    sites, dynamic = code_sites(observed)

    original_bytes = r447.read_pinned_original(original)
    _, _, _, preferred_path, alternate_path = r446.roots()
    preferred_raw = scanner.read_bounded_regular(
        preferred_path, r447.MAX_DEPENDENCY_BYTES,
        "R456_PREFERRED_DEPENDENCY_TOO_LARGE")
    alternate_raw = scanner.read_bounded_regular(
        alternate_path, r447.MAX_DEPENDENCY_BYTES,
        "R456_ALTERNATE_DEPENDENCY_TOO_LARGE")
    need(preferred_raw is not None and alternate_raw is not None,
         "R456_DEPENDENCY_UNAVAILABLE")
    preferred_sha = observed["dependency_sha256"]["R239_filtered.jar"]
    alternate_sha = observed["dependency_sha256"]["R218.jar"]
    need(sha256(preferred_raw).hexdigest() == preferred_sha and
         sha256(alternate_raw).hexdigest() == alternate_sha,
         "R456_DEPENDENCY_CHANGED_DURING_SCAN")
    preferred_names, _, _ = r447.archive(preferred_raw, "dependency")
    # Exact class path inventory admission applies to alternate too.
    r447.archive(alternate_raw, "dependency")
    selected = selected_jars.selected_dependencies(
        preferred_raw, preferred_sha, preferred_names, rebuilt)
    stats, detail = opcodes.analyze(rebuilt, selected, sites, dynamic)
    need(stats["rebuilt_classes_inspected"] ==
         prior["isolated_r421_classes"],
         "R456_R421_CLASS_COUNT_DRIFT")
    need(stats["selected_dependency_classes_available"] ==
         prior["preferred_dependency_classfiles_selected_and_parsed"],
         "R456_SELECTED_DEPENDENCY_COUNT_DRIFT")
    need(sha256(r447.read_pinned_original(original)).hexdigest() ==
         r447.ORIGINAL_SHA and
         r446.observe()[0] == observed,
         "R456_INPUT_CHANGED_DURING_ANALYSIS")
    aggregate = {
        "status": "R456_JAVA11_OPCODE_MEMBER_STATICNESS_UNAPPROVED",
        "exact_original_v309_SHA_verified":
            prior["original_v309_sha_verified"],
        "original_v309_classes": prior["original_v309_classes"],
        "original_v309_resources": prior["original_v309_resources"],
        "isolated_r421_java_sources": prior["isolated_r421_sources"],
        "isolated_r421_compiled_classes": prior["isolated_r421_classes"],
        "original_resource_companion_checked": companion is not None,
        "historical_R421_full_inventory_independently_approved": False,
        "client_started": False,
        "client_bytecode_executed": False,
        "real_static_linkage_proven": False,
        "original_functionality_recovered": False,
        "assets_packaged_in_runnable_client": False,
        "persistent_history_or_deletion_journals_accessed": False,
        "build_authorized": False,
        "merge_authorized": False,
        "release_authorized": False,
        **stats,
    }
    if companion is not None:
        for key in ("companion_resource_byte_matches",
                    "companion_resource_missing",
                    "companion_resource_mismatches"):
            aggregate[key] = prior[key]
    private = {
        "schema": SCHEMA,
        "status": "UNAPPROVED_STATIC_JVM_OPCODE_AND_MEMBER_FLAG_LEADS",
        "private_only": detail,
        "exact_original_provenance_authorized": False,
        "runtime_jvm_linkage_verified": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return aggregate, private


def save_private(detail: dict) -> str:
    temp, *_ = r446.roots()
    need(scanner.directory(temp), "R456_OWNER_TEMP_UNAVAILABLE")
    raw = (json.dumps(detail, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")) + "\n").encode("ascii")
    need(0 < len(raw) <= MAX_PRIVATE_BYTES,
         "R456_PRIVATE_WORKLIST_BYTE_BUDGET")
    path = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(temp)))
    need(path.parent == temp and scanner.directory(path),
         "R456_PRIVATE_FOLDER_UNSAFE")
    dest = path / NAME
    fd = os.open(
        dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
        getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0),
        0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return path.name


def run(original: Path, companion: Path | None = None,
        save: bool = False) -> dict:
    baseline = r446.observe()[0] if save else None
    report, worklist = inspect(original, companion)
    if save:
        repeated, repeated_worklist = inspect(original, companion)
        need(repeated == report and repeated_worklist == worklist
             and r446.observe()[0] == baseline,
             "R456_FULL_INVENTORY_CHANGED_BETWEEN_PRIVATE_SCANS")
        report["owner_private_quarantine_folder"] = save_private(worklist)
        report["private_worklist_created"] = True
    else:
        report["private_worklist_created"] = False
    return report


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--original-v309-jar", required=True, type=Path)
    cli.add_argument("--resource-companion-root", type=Path)
    cli.add_argument("--save-private-unapproved-worklist", action="store_true")
    args = cli.parse_args(argv)
    try:
        print(json.dumps(
            run(args.original_v309_jar, args.resource_companion_root,
                args.save_private_unapproved_worklist), sort_keys=True))
        return 0
    except (Refused, opcodes.Refused, selected_jars.Refused, r455.Refused,
            r454.Refused, r453.Refused, r452.Refused, r451.Refused,
            r450.Refused, classfile.Refused, r449.Refused, r448.Refused,
            r447.Refused, r446.Refused, r440.Refused, scanner.Refused,
            OSError, ValueError, TypeError, UnicodeError) as e:
        reason = str(e) if isinstance(e, (
            Refused, opcodes.Refused, selected_jars.Refused, r455.Refused,
            r454.Refused, r453.Refused, r452.Refused, r451.Refused,
            r450.Refused, classfile.Refused, r449.Refused, r448.Refused,
            r447.Refused, r446.Refused, r440.Refused, scanner.Refused)
        ) else "R456_OWNER_PRIVATE_STATIC_INPUT_REFUSED"
        print(json.dumps({
            "status": "R456_MEMBER_OPCODE_AUDIT_REFUSED",
            "reason": reason[:120],
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
