#!/usr/bin/env python3
"""R454 owner-private JVM inherited member *signature* audit.

Read-only SHA-guarded R421 compiled metadata, pinned original v309 Java ZIP
and filtered dependencies; no class execution, client installation, history
access or R415/R417 deletion-journal changes. Inheritance matches are
structural candidates, not JVM accessibility/linkage proof.
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
from tools.r453 import classfile_member_reference as members
from tools.r454 import member_ancestry_evidence as ancestry

SCHEMA = "SpawnPK-R454-inherited-member-ancestry-UNAPPROVED-v1"
PREFIX = "SpawnPK-R454-Private-Ancestry-"
NAME = "R454-UNAPPROVED-MEMBER-ANCESTRY.json"
MAX_PRIVATE_BYTES = 5 * 1024 * 1024


class Refused(RuntimeError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise Refused(code)


def inspect(original: Path, companion: Path | None = None) -> tuple[dict, dict]:
    """Inherits all historical provenance denials and current SHA gates."""
    previous, _ = r453.inspect(original, companion)
    observed, _ = r446.observe()
    records = r453.observed_members(observed)
    original_bytes = r447.read_pinned_original(original)
    original_names, _resources, _ = r447.archive(original_bytes, "original")
    _, _, _, preferred_path, alternate_path = r446.roots()
    preferred_bytes = scanner.read_bounded_regular(
        preferred_path, r447.MAX_DEPENDENCY_BYTES,
        "R454_PREFERRED_DEPENDENCY_OVERSIZE")
    alternate_bytes = scanner.read_bounded_regular(
        alternate_path, r447.MAX_DEPENDENCY_BYTES,
        "R454_ALTERNATE_DEPENDENCY_OVERSIZE")
    need(preferred_bytes is not None and alternate_bytes is not None,
         "R454_DEPENDENCY_UNAVAILABLE_OR_UNSAFE")
    need(sha256(preferred_bytes).hexdigest() ==
         observed["dependency_sha256"]["R239_filtered.jar"]
         and sha256(alternate_bytes).hexdigest() ==
         observed["dependency_sha256"]["R218.jar"],
         "R454_DEPENDENCY_CHANGED")
    preferred_names, _, _ = r447.archive(preferred_bytes, "dependency")
    alternate_names, _, _ = r447.archive(alternate_bytes, "dependency")
    summary, private = ancestry.analyze(
        records, preferred_names, alternate_names, original_names)
    need(summary["parsed_rebuilt_classfiles"] ==
         previous["isolated_r421_compiled_classfiles"],
         "R454_R421_CLASS_COUNT_CHANGED")
    need(summary["unique_rebuilt_constant_pool_member_references"] ==
         previous["unique_constant_pool_member_references"],
         "R454_R453_MEMBER_COUNT_DISAGREEMENT")
    freshly_observed, _ = r446.observe()
    need(freshly_observed == observed,
         "R454_CURRENT_R421_INPUT_CHANGED_DURING_SCAN")
    need(sha256(r447.read_pinned_original(original)).hexdigest() ==
         r447.ORIGINAL_SHA, "R454_ORIGINAL_V309_CHANGED_DURING_SCAN")

    aggregate = {
        "status": "R454_REBUILT_ANCESTRY_MEMBER_EVIDENCE_UNAPPROVED",
        "original_v309_exact_sha_verified":
            previous["original_v309_exact_sha_matched"],
        "original_v309_class_count": previous["original_v309_class_count"],
        "original_v309_resource_count":
            previous["original_v309_resource_count"],
        "isolated_r421_source_count": previous["isolated_r421_java_sources"],
        "isolated_r421_compiled_classes":
            previous["isolated_r421_compiled_classfiles"],
        "resource_companion_checked": companion is not None,
        "owner_client_executed": False,
        "jvm_member_resolution_proven": False,
        "jvm_access_control_checked": False,
        "full_source_deobfuscation_proven": False,
        "original_functionality_mapped_completely": False,
        "original_resource_packaging_proven": False,
        "historical_R421_full_inventory_independently_approved": False,
        "build_authorized": False,
        "release_authorized": False,
        "merge_authorized": False,
        **summary,
    }
    if companion is not None:
        for key in ("companion_resource_byte_matches",
                    "companion_resource_missing",
                    "companion_resource_mismatches"):
            aggregate[key] = previous[key]
    detail = {
        "schema": SCHEMA,
        "status": "UNAPPROVED_CURRENT_STATIC_ANCESTRY_SIGNALS",
        "owner_private_worklist": private,
        "historical_R421_full_inventory_approved": False,
        "client_runtime_verified": False,
        "release_authorized": False,
        "merge_authorized": False,
    }
    return aggregate, detail


def save_private(detail: dict) -> str:
    temp, *_ = r446.roots()
    need(scanner.directory(temp), "R454_OWNER_TEMP_UNAVAILABLE")
    content = (json.dumps(detail, sort_keys=True, ensure_ascii=True,
                          separators=(",", ":")) + "\n").encode("ascii")
    need(0 < len(content) <= MAX_PRIVATE_BYTES,
         "R454_PRIVATE_EVIDENCE_BUDGET_EXCEEDED")
    folder = Path(tempfile.mkdtemp(prefix=PREFIX, dir=str(temp)))
    need(folder.parent == temp and scanner.directory(folder),
         "R454_PRIVATE_REPORT_LOCATION_UNSAFE")
    target = folder / NAME
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL |
             getattr(os, "O_NOFOLLOW", 0) |
             getattr(os, "O_BINARY", 0))
    fd = os.open(target, flags, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    return folder.name


def run(original: Path, companion: Path | None = None,
        save: bool = False) -> dict:
    baseline, _ = r446.observe() if save else (None, None)
    report, detail = inspect(original, companion)
    if save:
        again, again_detail = inspect(original, companion)
        need(again == report and again_detail == detail
             and r446.observe()[0] == baseline,
             "R454_INPUTS_CHANGED_BETWEEN_PRIVATE_SCANS")
        report["owner_private_directory"] = save_private(detail)
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
        print(json.dumps(run(
            args.original_v309_jar, args.resource_companion_root,
            args.save_private_unapproved_worklist), sort_keys=True))
        return 0
    except (Refused, ancestry.Refused, members.Refused, r453.Refused,
            r452.Refused, r451.Refused, r450.Refused, r449.Refused,
            r448.Refused, r447.Refused, r446.Refused, r440.Refused,
            scanner.Refused, ValueError, TypeError, UnicodeError,
            OSError) as error:
        reason = str(error) if isinstance(error, (
            Refused, ancestry.Refused, members.Refused, r453.Refused,
            r452.Refused, r451.Refused, r450.Refused, r449.Refused,
            r448.Refused, r447.Refused, r446.Refused, r440.Refused,
            scanner.Refused)) else "R454_OWNER_PRIVATE_INPUT_REFUSED"
        print(json.dumps({
            "status": "R454_MEMBER_ANCESTRY_AUDIT_REFUSED",
            "reason": reason[:120],
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
