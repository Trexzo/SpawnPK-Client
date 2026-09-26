from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .javac_diagnostics import (
    JavacDiagnosticError,
    classify_javac_diagnostics,
    write_javac_diagnostic_report,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-javac-diagnostics")
    p.add_argument("diagnostics", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--include-identifiers",
        action="store_true",
        help="include raw paths/symbols for private local analysis",
    )
    args = p.parse_args(argv)

    try:
        raw = args.diagnostics.read_text(encoding="utf-8", errors="replace")
        report = classify_javac_diagnostics(
            raw,
            include_identifiers=args.include_identifiers,
        )
        write_javac_diagnostic_report(report, args.out)
    except (JavacDiagnosticError, OSError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_JAVAC_DIAGNOSTICS_PASS")
    print(f"report_id={report['report_id']}")
    print(f"input_sha256={report['input_sha256']}")
    print(f"total_errors={summary['total_errors']}")
    print(f"affected_files={summary['affected_files']}")
    print(
        "cannot_find_symbol="
        f"{summary['cannot_find_symbol']['count']}"
    )
    print(f"identifiers_included={report['identifiers_included']}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
