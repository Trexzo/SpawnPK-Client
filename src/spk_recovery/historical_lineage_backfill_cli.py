from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .historical_lineage_backfill import (
    HistoricalLineageBackfillError,
    backfill_historical_v307_lineage,
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise HistoricalLineageBackfillError(
            f"expected JSON object: {path}"
        )
    return value


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Derive exact historical v307 canonical class/member lineage "
            "from canonical v308 authority using the existing R3 migration."
        )
    )
    p.add_argument("v308_client_jar", type=Path)
    p.add_argument("v307_client_jar", type=Path)
    p.add_argument("v308_index", type=Path)
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()

    try:
        report = backfill_historical_v307_lineage(
            args.v308_client_jar,
            args.v307_client_jar,
            _load(args.v308_index),
            _load(args.class_lineage),
            _load(args.member_lineage),
            out_dir=args.out_dir,
        )
    except (
        HistoricalLineageBackfillError,
        OSError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print(
        "SPK_HISTORICAL_V307_LINEAGE_BACKFILL_PASS"
        if report["ready_for_authority"]
        else "SPK_HISTORICAL_V307_LINEAGE_BACKFILL_BLOCKED"
    )
    print(f"backfill_id={report['backfill_id']}")
    print(f"workspace_id={report['workspace_id']}")
    print(
        "ready_for_authority="
        + str(report["ready_for_authority"]).lower()
    )
    print(
        f"focused_analysis_items={report['focused_analysis_items']}"
    )
    print(
        "trusted_classes="
        + str(
            report["class_transfer_summary"].get(
                "trusted_applied",
                0,
            )
        )
    )
    print(
        "applied_members="
        + str(
            report["member_transfer_summary"].get(
                "applied_member_relationships",
                0,
            )
        )
    )
    print(
        "field_proof_applied="
        + str(
            report["field_proof_summary"].get(
                "applied_fields",
                0,
            )
        )
    )
    print(f"class_lineage={report['paths']['class_lineage']}")
    print(f"member_lineage={report['paths']['member_lineage']}")
    print(f"report={report['paths']['report']}")

    return 0 if report["ready_for_authority"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
