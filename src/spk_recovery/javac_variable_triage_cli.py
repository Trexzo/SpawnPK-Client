from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .javac_variable_triage import (
    JavacVariableTriageError,
    analyze_unresolved_variables,
    write_unresolved_variable_triage,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-javac-variable-triage")
    p.add_argument("diagnostic_report", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--include-identifiers",
        action="store_true",
        help="include exact private owners/fields/descriptors in output",
    )
    args = p.parse_args(argv)

    try:
        diagnostic = json.loads(
            args.diagnostic_report.read_text(encoding="utf-8")
        )
        report = analyze_unresolved_variables(
            diagnostic,
            args.readable_jar,
            args.source_root,
            include_identifiers=args.include_identifiers,
        )
        write_unresolved_variable_triage(report, args.out)
    except (
        JavacVariableTriageError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_JAVAC_VARIABLE_TRIAGE_PASS")
    print(f"report_id={report['report_id']}")
    print(
        "variable_diagnostic_count="
        f"{summary['variable_diagnostic_count']}"
    )
    print(
        "proof_classes="
        + json.dumps(
            summary["proof_classes"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "owner_resolutions="
        + json.dumps(
            summary["owner_resolutions"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "bytecode_proven_field_diagnostic_count="
        f"{summary['bytecode_proven_field_diagnostic_count']}"
    )
    print(
        "ambiguous_field_diagnostic_count="
        f"{summary['ambiguous_field_diagnostic_count']}"
    )
    print(f"identifiers_included={report['identifiers_included']}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
