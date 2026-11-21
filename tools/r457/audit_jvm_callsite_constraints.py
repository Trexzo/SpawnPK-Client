#!/usr/bin/env python3
"""R457 read-only SHA-pinned v309/R421 JVM invocation constraint audit.

Extends R456's exact decoded instruction-site inventory with method
argument slot widths and JVM special-method syntax checks. Does not
interpret/execute Java or modify client runtime, assets, histories or journal
markers. Console emits aggregates only; name-only report is opt-in private.
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
from tools.r455 import audit_dependency_member_access as r455
from tools.r455 import dependency_member_access as selected_jars
from tools.r456 import audit_member_opcode_staticness as r456
from tools.r457 import jvm_callsite_constraints as calls

SCHEMA = "SpawnPK-R457-JVM-callsite-constraints-UNAPPROVED-v1"
PREFIX = "SpawnPK-R457-Private-Callsites-"
NAME = "R457-UNAPPROVED-CALLSITE-CONSTRAINTS.json"
MAX_PRIVATE_BYTES = 5 * 1024 * 1024


class Refused(RuntimeError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    # Inherited complete original v309 SHA and current R421/source/class/
    # Store/dependency custody admission. Never create historical approval.
    previous, _ = r456.inspect(original, companion)
    snapshot, _ = r446.observe()
    rebuilt = r453.observed_members(snapshot)
    site_list, dynamic = r456.code_sites(snapshot)

    original_bytes = r447.read_pinned_original(original)
    _, _, _, preferred_path, alternate_path = r446.roots()
    preferred = scanner.read_bounded_regular(
        preferred_path, r447.MAX_DEPENDENCY_BYTES,
        "R457_PREFERRED_DEPENDENCY_TOO_LARGE")
    alternate = scanner.read_bounded_regular(
        alternate_path, r447.MAX_DEPENDENCY_BYTES,
        "R457_ALTERNATE_DEPENDENCY_TOO_LARGE")
    need(preferred is not None and alternate is not None,
         "R457_DEPENDENCY_FILES_UNAVAILABLE")
    preferred_sha = snapshot["dependency_sha256"]["R239_filtered.jar"]
    alternate_sha = snapshot["dependency_sha256"]["R218.jar"]
    need(sha256(preferred).hexdigest() == preferred_sha and
         sha256(alternate).hexdigest() == alternate_sha,
         "R457_DEPENDENCY_SHA_CHANGED")
    preferred_classes, _, _ = r447.archive(preferred, "dependency")
    r447.archive(alternate, "dependency")
    selected = selected_jars.selected_dependencies(
        preferred, preferred_sha, preferred_classes, rebuilt)
    totals, private = calls.analyze(rebuilt, selected, site_list, dynamic)
    need(totals["rebuilt_classfiles_checked"] ==
         previous["isolated_r421_compiled_classes"],
         "R457_REBUILT_CLASS_COUNT_CHANGED")
    need(totals["decoded_field_and_method_sites"] ==
         previous["field_and_method_bytecode_sites_inspected"] and
         totals["invokedynamic_sites_not_resolved"] ==
         previous["invokedynamic_sites_without_static_owner_resolution"],
         "R457_R456_OPCODE_EVIDENCE_COUNT_CHANGED")
    need(totals["selected_preferred_dependency_classes"] ==
         previous["selected_dependency_classes_available"],
         "R457_SELECTED_DEPENDENCY_COUNT_CHANGED")
    need(r446.observe()[0] == snapshot and
         sha256(r447.read_pinned_original(original)).hexdigest() ==
         r447.ORIGINAL_SHA,
         "R457_OWNER_INPUT_CHANGED_DURING_ANALYSIS")
    summary = {
        "status": "R457_STATIC_JVM_CALLSITE_CONSTRAINTS_UNAPPROVED",
        "original_v309_SHA_verified":
            previous["exact_original_v309_SHA_verified"],
        "original_v309_classes": previous["original_v309_classes"],
        "original_v309_resources": previous["original_v309_resources"],
        "isolated_r421_sources": previous["isolated_r421_java_sources"],
        "isolated_r421_compiled_classes":
            previous["isolated_r421_compiled_classes"],
        "resource_companion_checked": companion is not None,
        "client_executed": False,
        "production_history_or_deletion_journals_accessed": False,
        "historical_R421_full_inventory_independently_approved": False,
        "full_client_source_deobfuscation_proven": False,
        "assets_packaged_or_installed": False,
        "compile_authorized": False,
        "release_authorized": False,
        "merge_authorized": False,
        **totals,
    }
    if companion is not None:
        for key in (
            "companion_resource_byte_matches",
            "companion_resource_missing",
            "companion_resource_mismatches",
        ):
            summary[key] = previous[key]
    detail = {
        "schema": SCHEMA,
        "status": "UNAPPROVED_CURRENT_REBUILT_JVM_CALLSITE_EVIDENCE",
        "owner_private_callsite_worklist": private,
        "historical_R421_baseline_approved": False,
        "client_execution_or_linkage_proven": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return summary, detail


def save_private(details: dict) -> str:
    temporary, *_ = r446.roots()
    need(scanner.directory(temporary), "R457_OWNER_TEMP_ROOT_INVALID")
    data = (json.dumps(details, sort_keys=True, ensure_ascii=True,
                       separators=(",", ":")) + "\n").encode("ascii")
    need(0 < len(data) <= MAX_PRIVATE_BYTES,
         "R457_PRIVATE_WORKLIST_SIZE_EXCEEDED")
    path = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(temporary)))
    need(path.parent == temporary and scanner.directory(path),
         "R457_PRIVATE_WORKLIST_LOCATION_INVALID")
    output = path / NAME
    fd = os.open(
        output,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL |
        getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0),
        0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    return path.name


def run(original: Path, companion: Path | None = None,
        save: bool = False) -> dict:
    baseline = r446.observe()[0] if save else None
    report, detail = inspect(original, companion)
    if save:
        second, second_detail = inspect(original, companion)
        need(second == report and second_detail == detail
             and baseline == r446.observe()[0],
             "R457_CURRENT_INVENTORY_CHANGED_BETWEEN_SCANS")
        report["private_quarantine_directory_name"] = save_private(detail)
        report["private_worklist_created"] = True
    else:
        report["private_worklist_created"] = False
    return report


def main(argv=None) -> int:
    arg = argparse.ArgumentParser(description=__doc__)
    arg.add_argument("--original-v309-jar", type=Path, required=True)
    arg.add_argument("--resource-companion-root", type=Path)
    arg.add_argument("--save-private-unapproved-worklist", action="store_true")
    config = arg.parse_args(argv)
    try:
        print(json.dumps(run(
            config.original_v309_jar, config.resource_companion_root,
            config.save_private_unapproved_worklist), sort_keys=True))
        return 0
    except (Refused, calls.Refused, r456.Refused, r455.Refused, r454.Refused,
            r453.Refused, r452.Refused, r451.Refused, r450.Refused,
            r449.Refused, r448.Refused, r447.Refused, r446.Refused,
            r440.Refused, scanner.Refused, selected_jars.Refused,
            OSError, UnicodeError, TypeError, ValueError) as error:
        if isinstance(error, (
            Refused, calls.Refused, r456.Refused, r455.Refused, r454.Refused,
            r453.Refused, r452.Refused, r451.Refused, r450.Refused,
            r449.Refused, r448.Refused, r447.Refused, r446.Refused,
            r440.Refused, scanner.Refused, selected_jars.Refused
        )):
            reason = str(error)[:120]
        else:
            reason = "R457_OWNER_PRIVATE_STATIC_INPUT_REFUSED"
        print(json.dumps({
            "status": "R457_JVM_CALLSITE_AUDIT_REFUSED",
            "reason": reason,
            "merge_authorized": False,
            "release_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
