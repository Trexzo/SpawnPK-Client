from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .dependency_capsule_audit import (
    DependencyCapsuleAuditError,
    audit_dependency_capsule,
    write_dependency_capsule_audit,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-dependency-capsule-audit"
    )
    p.add_argument("private_plan", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("dependency_capsule", type=Path)
    p.add_argument(
        "--javac-command",
        default="javac",
    )
    p.add_argument("--release", type=int)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = p.parse_args(argv)

    try:
        private_plan = json.loads(
            args.private_plan.read_text(encoding="utf-8")
        )
        report = audit_dependency_capsule(
            private_plan,
            args.readable_jar,
            args.dependency_capsule,
            javac_command=args.javac_command,
            release=args.release,
            include_identifiers=args.include_identifiers,
        )
        write_dependency_capsule_audit(report, args.out)
    except (
        DependencyCapsuleAuditError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_DEPENDENCY_CAPSULE_AUDIT_PASS")
    print(f"audit_id={report['audit_id']}")
    print(f"candidate_count={summary['candidate_count']}")
    print(
        "readable_present_count="
        f"{summary['readable_present_count']}"
    )
    print(
        "capsule_present_count="
        f"{summary['capsule_present_count']}"
    )
    print(
        "byte_identical_count="
        f"{summary['byte_identical_count']}"
    )
    print(
        "class_major_versions="
        + json.dumps(
            summary["class_major_versions"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "source_name_classifications="
        + json.dumps(
            summary["source_name_classifications"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "source_name_failure_shapes="
        + json.dumps(
            summary["source_name_failure_shapes"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "source_name_failure_roles="
        + json.dumps(
            summary["source_name_failure_roles"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "source_spellable_count="
        f"{summary['source_spellable_count']}"
    )
    print(
        "source_unspellable_count="
        f"{summary['source_unspellable_count']}"
    )
    print(
        "package_depths="
        + json.dumps(
            summary["package_depths"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "default_package_count="
        f"{summary['default_package_count']}"
    )
    print(
        "class_signature_attribute_count="
        f"{summary['class_signature_attribute_count']}"
    )
    print(
        "field_signature_attribute_count="
        f"{summary['field_signature_attribute_count']}"
    )
    print(
        "method_signature_attribute_count="
        f"{summary['method_signature_attribute_count']}"
    )
    print(
        "source_form_classifications="
        + json.dumps(
            summary["source_form_classifications"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "source_form_diagnostic_keys="
        + json.dumps(
            summary["source_form_diagnostic_keys"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "capsule_release_classifications="
        + json.dumps(
            summary["capsule_release_classifications"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "capsule_default_classifications="
        + json.dumps(
            summary["capsule_default_classifications"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "readable_release_classifications="
        + json.dumps(
            summary["readable_release_classifications"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "javap_classifications="
        + json.dumps(
            summary["javap_classifications"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "capsule_release_resolved_count="
        f"{summary['capsule_release_resolved_count']}"
    )
    print(
        "capsule_default_resolved_count="
        f"{summary['capsule_default_resolved_count']}"
    )
    print(
        "readable_release_resolved_count="
        f"{summary['readable_release_resolved_count']}"
    )
    print(
        "javap_resolved_count="
        f"{summary['javap_resolved_count']}"
    )
    print(f"identifiers_included={report['identifiers_included']}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
