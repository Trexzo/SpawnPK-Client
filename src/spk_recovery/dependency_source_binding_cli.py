from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .dependency_source_binding import (
    DependencySourceBindingError,
    bind_dependency_source_references,
    write_dependency_source_binding_inventory,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-source-binding"
    )
    parser.add_argument("source_root", type=Path)
    parser.add_argument("dependency_remap_report", type=Path)
    parser.add_argument("private_replacement_plan", type=Path)
    parser.add_argument("bundled_jar", type=Path)
    parser.add_argument("artifact", type=Path, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--java-command", default="java")
    parser.add_argument("--javac-command", default="javac")
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = parser.parse_args(argv)

    try:
        report = bind_dependency_source_references(
            args.source_root,
            args.dependency_remap_report,
            args.private_replacement_plan,
            args.bundled_jar,
            args.artifact,
            java_command=args.java_command,
            javac_command=args.javac_command,
            include_identifiers=args.include_identifiers,
        )
        write_dependency_source_binding_inventory(
            report,
            args.out,
        )
    except (
        DependencySourceBindingError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_DEPENDENCY_SOURCE_BINDING_PASS")
    print(
        "binding_inventory_id="
        f"{report['binding_inventory_id']}"
    )
    print(
        "binding_count="
        f"{summary['binding_count']}"
    )
    print(
        "match_status_counts="
        + json.dumps(
            summary["match_status_counts"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "element_kind_counts="
        + json.dumps(
            summary["element_kind_counts"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "exact_approved_binding_count="
        f"{summary['exact_approved_binding_count']}"
    )
    print(
        "approved_owner_unmatched_member_count="
        f"{summary['approved_owner_unmatched_member_count']}"
    )
    print(
        "javac_diagnostic_error_count="
        f"{summary['javac_diagnostic_error_count']}"
    )
    print(
        "identifiers_included="
        f"{report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
