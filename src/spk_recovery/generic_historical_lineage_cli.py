from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .generic_historical_lineage import (
    GenericHistoricalLineageBackfillError,
    backfill_historical_lineage,
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GenericHistoricalLineageBackfillError(
            f"expected JSON object: {path}"
        )
    return value


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Derive a historical build through the ordinary R3 migration "
            "thresholds and emit PASS or deterministic BLOCKED authority."
        )
    )
    p.add_argument("current_client_jar", type=Path)
    p.add_argument("historical_client_jar", type=Path)
    p.add_argument("current_index", type=Path)
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("--current-build-id", required=True)
    p.add_argument("--historical-build-id", required=True)
    p.add_argument("--historical-build-number", type=int)
    p.add_argument("--expected-current-sha256", required=True)
    p.add_argument("--expected-historical-sha256", required=True)
    p.add_argument("--scope-prefix", default="rs/")
    p.add_argument(
        "--expected-match-summary",
        type=Path,
        help=(
            "Optional JSON object containing exact matcher summary fields "
            "that must reproduce before migration."
        ),
    )
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()

    try:
        expected = (
            _load(args.expected_match_summary)
            if args.expected_match_summary
            else None
        )
        report = backfill_historical_lineage(
            args.current_client_jar,
            args.historical_client_jar,
            _load(args.current_index),
            _load(args.class_lineage),
            _load(args.member_lineage),
            current_build_id=args.current_build_id,
            historical_build_id=args.historical_build_id,
            historical_build_number=args.historical_build_number,
            expected_current_sha256=args.expected_current_sha256,
            expected_historical_sha256=args.expected_historical_sha256,
            out_dir=args.out_dir,
            scope_prefix=args.scope_prefix,
            expected_match_summary=expected,
        )
    except (
        GenericHistoricalLineageBackfillError,
        OSError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print(
        "SPK_GENERIC_HISTORICAL_LINEAGE_BACKFILL_PASS"
        if report["ready_for_authority"]
        else "SPK_GENERIC_HISTORICAL_LINEAGE_BACKFILL_BLOCKED"
    )
    print(f"backfill_id={report['backfill_id']}")
    print(f"current_build_id={report['current_build_id']}")
    print(f"historical_build_id={report['historical_build_id']}")
    print(
        "ready_for_authority="
        + str(report["ready_for_authority"]).lower()
    )
    print(
        f"matched_classes={report['class_match_summary']['matched']}"
    )
    print(
        f"ambiguous_classes={report['class_match_summary']['ambiguous']}"
    )
    print(
        "current_unmatched_classes="
        + str(report["class_match_summary"]["unmatched_old"])
    )
    print(
        "historical_unmatched_classes="
        + str(report["class_match_summary"]["unmatched_new"])
    )
    print(
        f"focused_analysis_items={report['focused_analysis_items']}"
    )
    print(f"report={report['paths']['report']}")

    return 0 if report["ready_for_authority"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
