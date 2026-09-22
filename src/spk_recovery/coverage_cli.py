from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .coverage import CoverageError, build_coverage_report, write_coverage_report
from .lineage import load_lineage
from .member_lineage import load_member_lineage


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-coverage")
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("--build-id", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = build_coverage_report(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            build_id=args.build_id,
        )
        write_coverage_report(report, args.out)
    except (CoverageError, OSError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_COVERAGE_PASS")
    print(f"coverage_id={report['coverage_id']}")
    for kind in ("classes", "fields", "methods"):
        row = report["summary"][kind]
        print(
            f"{kind}=accepted:{row['accepted']} "
            f"candidate:{row['candidate']} unknown:{row['unknown']} "
            f"total:{row['total']} accepted_percent:{row['accepted_percent']}"
        )
    print(f"overall_accepted_percent={report['overall']['accepted_percent']}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
