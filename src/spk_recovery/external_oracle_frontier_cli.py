from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .external_oracle_frontier import (
    ExternalOracleFrontierError,
    build_external_oracle_frontier,
)


def _exact_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ExternalOracleFrontierError(
                f"duplicate JSON key: {key!r}"
            )
        out[key] = value
    return out


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_exact_object,
        )
    except OSError as exc:
        raise ExternalOracleFrontierError(
            str(exc)
        ) from exc
    except json.JSONDecodeError as exc:
        raise ExternalOracleFrontierError(
            str(exc)
        ) from exc
    if not isinstance(value, dict):
        raise ExternalOracleFrontierError(
            f"expected JSON object: {path}"
        )
    return value


def _print_human(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print("SPK_EXTERNAL_ORACLE_FRONTIER_PASS")
    print(f"report_id={report['report_id']}")
    print(
        f"javac_frontier_id={report['javac_frontier_id']}"
    )
    print(f"oracle_id={report['oracle_id']}")
    print(
        "failing_source_units="
        f"{summary['failing_source_units']}"
    )
    print(
        "matched_source_units="
        f"{summary['matched_source_units']}"
    )
    print(
        "strong_source_units="
        f"{summary['strong_source_units']}"
    )
    print(
        "inferred_source_units="
        f"{summary['inferred_source_units']}"
    )
    print(
        "unmatched_source_units="
        f"{summary['unmatched_source_units']}"
    )
    print(f"strong_errors={summary['strong_errors']}")
    print(
        f"inferred_errors={summary['inferred_errors']}"
    )
    print(
        f"unmatched_errors={summary['unmatched_errors']}"
    )
    for row in report["matches"][:20]:
        print(
            "MATCH "
            f"tier={row['evidence_tier']} "
            f"errors={row['error_count']} "
            f"source={row['source_unit']} "
            f"external={row['external_internal_name']} "
            f"exact={row['exact_v308_entry']}"
        )
    print("research_only=true")
    print("semantic_name_accepted=false")
    print("source_mutation_allowed=false")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Intersect a private Source-M1 javac frontier with "
            "the research-only external readable-v308 oracle."
        )
    )
    parser.add_argument(
        "private_diagnostic",
        type=Path,
    )
    parser.add_argument(
        "external_oracle",
        type=Path,
    )
    parser.add_argument(
        "class_remap_plan",
        type=Path,
    )
    parser.add_argument(
        "--collision-plan",
        type=Path,
    )
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
    )
    args = parser.parse_args(argv)

    try:
        report = build_external_oracle_frontier(
            private_diagnostic=_load(
                args.private_diagnostic
            ),
            external_oracle=_load(
                args.external_oracle
            ),
            class_remap_plan=_load(
                args.class_remap_plan
            ),
            collision_plan=(
                _load(args.collision_plan)
                if args.collision_plan is not None
                else None
            ),
        )
    except ExternalOracleFrontierError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    args.out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    args.out.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    _print_human(report)
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
