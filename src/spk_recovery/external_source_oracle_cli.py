from __future__ import annotations

import argparse
import json
from pathlib import Path

from .external_source_oracle import (
    EXACT_V308_SHA256,
    build_external_source_oracle,
)


def _print_human(report: dict) -> None:
    summary = report["summary"]
    print("SPK_EXTERNAL_SOURCE_ORACLE_PASS")
    print(f"oracle_id={report['oracle_id']}")
    print(f"corpus_id={report['corpus_id']}")
    print(f"external_revision={report['external']['revision']}")
    print(
        "external_rs_classes="
        f"{report['external']['rs_class_count']}"
    )
    print(
        "exact_v308_rs_classes="
        f"{report['exact_v308']['rs_class_count']}"
    )
    print(f"matched={summary.get('matched', 0)}")
    print(
        "strong_candidates="
        f"{summary.get('strong_candidates', 0)}"
    )
    print(
        "inferred_candidates="
        f"{summary.get('inferred_candidates', 0)}"
    )
    print(f"ambiguous={summary.get('ambiguous', 0)}")
    print(
        "unmatched_external="
        f"{summary.get('unmatched_old', 0)}"
    )
    print(
        "unmatched_exact_v308="
        f"{summary.get('unmatched_new', 0)}"
    )
    print("research_only=true")
    print("semantic_name_accepted=false")
    print("source_mutation_allowed=false")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Correlate a compiled external readable SpawnPK corpus "
            "against exact-v308 as research-only evidence."
        )
    )
    parser.add_argument(
        "--external-repo",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--external-classes",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--external-revision",
        required=True,
    )
    parser.add_argument(
        "--exact-v308-jar",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--expected-v308-sha256",
        default=EXACT_V308_SHA256,
    )
    parser.add_argument(
        "--json-out",
        required=True,
        type=Path,
    )
    args = parser.parse_args(argv)

    report = build_external_source_oracle(
        external_repo=args.external_repo,
        external_classes=args.external_classes,
        external_revision=args.external_revision,
        exact_v308_jar=args.exact_v308_jar,
        expected_v308_sha256=args.expected_v308_sha256,
    )
    args.json_out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    args.json_out.write_text(
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
    print(f"json_out={args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
