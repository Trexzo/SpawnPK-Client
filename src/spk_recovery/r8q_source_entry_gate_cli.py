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


def _sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-r8q-source-entry-gate"
    )
    p.add_argument("private_plan", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("dependency_capsule", type=Path)
    p.add_argument("--javac-command", required=True)
    p.add_argument("--release", type=int, default=9)
    p.add_argument("--expected-plan-id", required=True)
    p.add_argument("--expected-readable-sha256", required=True)
    p.add_argument("--expected-capsule-sha256", required=True)
    p.add_argument("--expected-candidates", type=int, default=8)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        plan = json.loads(
            args.private_plan.read_text(encoding="utf-8")
        )
        if plan.get("plan_id") != args.expected_plan_id:
            raise DependencyCapsuleAuditError(
                "private plan id mismatch"
            )

        readable_sha = _sha256_file(args.readable_jar)
        capsule_sha = _sha256_file(args.dependency_capsule)

        if readable_sha != args.expected_readable_sha256:
            raise DependencyCapsuleAuditError(
                "readable JAR SHA-256 mismatch"
            )
        if capsule_sha != args.expected_capsule_sha256:
            raise DependencyCapsuleAuditError(
                "dependency capsule SHA-256 mismatch"
            )

        report = audit_dependency_capsule(
            plan,
            args.readable_jar,
            args.dependency_capsule,
            javac_command=args.javac_command,
            release=args.release,
            include_identifiers=False,
        )

        summary = report["summary"]
        if summary["candidate_count"] != args.expected_candidates:
            raise DependencyCapsuleAuditError(
                "candidate count mismatch"
            )
        if summary["readable_present_count"] != args.expected_candidates:
            raise DependencyCapsuleAuditError(
                "not all candidates are present in readable JAR"
            )
        if summary["capsule_present_count"] != args.expected_candidates:
            raise DependencyCapsuleAuditError(
                "not all candidates are present in dependency capsule"
            )
        if summary["byte_identical_count"] != args.expected_candidates:
            raise DependencyCapsuleAuditError(
                "candidate bytes are not exact between authorities"
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

    print("R8Q_EXACT_SOURCE_ENTRY_GATE_PASS")
    print(f"audit_id={report['audit_id']}")
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
        "readable_package_class_collision_count="
        f"{summary['readable_package_class_collision_count']}"
    )
    print(
        "capsule_package_class_collision_count="
        f"{summary['capsule_package_class_collision_count']}"
    )
    print(
        "readable_collision_depths="
        + json.dumps(
            summary["readable_collision_depths"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "capsule_collision_depths="
        + json.dumps(
            summary["capsule_collision_depths"],
            sort_keys=True,
            separators=(",", ":"),
        )
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
        "source_form_target_loaded_counts="
        + json.dumps(
            summary["source_form_target_loaded_counts"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "javap_resolved_count="
        f"{summary['javap_resolved_count']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
