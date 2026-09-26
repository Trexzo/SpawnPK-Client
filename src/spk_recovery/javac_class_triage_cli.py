from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .javac_class_triage import (
    JavacClassTriageError,
    analyze_unresolved_classes,
    write_unresolved_class_triage,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-javac-class-triage")
    p.add_argument("diagnostic_report", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--include-identifiers",
        action="store_true",
        help="include exact private class identities in output",
    )
    args = p.parse_args(argv)

    try:
        diagnostic = json.loads(
            args.diagnostic_report.read_text(encoding="utf-8")
        )
        report = analyze_unresolved_classes(
            diagnostic,
            args.readable_jar,
            args.source_root,
            include_identifiers=args.include_identifiers,
        )
        write_unresolved_class_triage(report, args.out)
    except (
        JavacClassTriageError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_JAVAC_CLASS_TRIAGE_PASS")
    print(f"report_id={report['report_id']}")
    print(
        "frontier_id="
        f"{report['diagnostic_frontier_id']}"
    )
    print(
        "class_diagnostic_count="
        f"{summary['class_diagnostic_count']}"
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
        "source_materialization="
        + json.dumps(
            summary["source_materialization"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "source_declared_type_count="
        f"{summary['source_declared_type_count']}"
    )
    print(
        "visible_exact_source_declared_count="
        f"{summary['visible_exact_source_declared_count']}"
    )
    print(
        "visible_exact_source_missing_count="
        f"{summary['visible_exact_source_missing_count']}"
    )
    print(
        "repair_candidate_diagnostic_count="
        f"{summary['repair_candidate_diagnostic_count']}"
    )
    print(
        "visible_exact_diagnostic_count="
        f"{summary['visible_exact_diagnostic_count']}"
    )
    print(
        "ambiguous_diagnostic_count="
        f"{summary['ambiguous_diagnostic_count']}"
    )
    print(
        "absent_diagnostic_count="
        f"{summary['absent_diagnostic_count']}"
    )
    print(f"identifiers_included={report['identifiers_included']}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
