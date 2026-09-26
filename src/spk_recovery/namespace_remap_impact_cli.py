from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .namespace_remap_impact import (
    NamespaceRemapImpactError,
    plan_namespace_remap_impact,
    write_namespace_remap_impact,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-namespace-remap-impact"
    )
    parser.add_argument("private_collision_proof", type=Path)
    parser.add_argument("readable_jar", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = parser.parse_args(argv)

    try:
        proof = json.loads(
            args.private_collision_proof.read_text(
                encoding="utf-8"
            )
        )
        report = plan_namespace_remap_impact(
            proof,
            args.readable_jar,
            include_identifiers=args.include_identifiers,
        )
        write_namespace_remap_impact(report, args.out)
    except (
        NamespaceRemapImpactError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_NAMESPACE_REMAP_IMPACT_PASS")
    print(f"impact_plan_id={report['impact_plan_id']}")
    for key in (
        "planned_binary_class_rename_count",
        "planned_nested_binary_class_rename_count",
        "impacted_classfile_count",
        "hard_class_reference_count",
        "descriptor_signature_reference_count",
        "unclassified_utf8_risk_count",
        "reflective_literal_risk_count",
        "automatic_bytecode_rewrite_safe",
        "source_reference_rewrite_required",
    ):
        print(f"{key}={summary[key]}")
    print(
        "identifiers_included="
        f"{report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
