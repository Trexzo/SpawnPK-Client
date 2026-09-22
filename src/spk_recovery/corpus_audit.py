from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .diffing import diff_indexes
from .indexer import index_jar
from .matcher import match_classes


class CorpusAuditError(ValueError):
    pass


def _check(
    checks: list[dict[str, Any]],
    name: str,
    actual: Any,
    expected: Any,
    *,
    comparator: str = "eq",
) -> None:
    if expected is None:
        return
    if comparator == "eq":
        passed = actual == expected
    elif comparator == "gte":
        passed = actual >= expected
    elif comparator == "lte":
        passed = actual <= expected
    else:
        raise CorpusAuditError(f"unsupported comparator {comparator!r}")
    checks.append(
        {
            "name": name,
            "actual": actual,
            "expected": expected,
            "comparator": comparator,
            "passed": passed,
        }
    )


def build_corpus_report(
    previous: dict[str, Any],
    current: dict[str, Any],
    alternate: dict[str, Any],
    *,
    scope_prefix: str = "rs/",
    expect_previous_sha256: str | None = None,
    expect_current_sha256: str | None = None,
    expect_alternate_sha256: str | None = None,
    expect_changed_same_path: int | None = None,
    expect_added_entries: int | None = None,
    expect_removed_entries: int | None = None,
    min_alternate_matches: int | None = None,
    min_structural_or_better_matches: int | None = None,
    max_alternate_unmatched_old: int | None = None,
) -> dict[str, Any]:
    previous_to_current = diff_indexes(previous, current)
    alternate_to_current = match_classes(
        alternate,
        current,
        prefix=scope_prefix,
    )

    checks: list[dict[str, Any]] = []
    _check(
        checks,
        "previous_sha256",
        str(previous.get("sha256", "")).lower(),
        expect_previous_sha256.lower() if expect_previous_sha256 else None,
    )
    _check(
        checks,
        "current_sha256",
        str(current.get("sha256", "")).lower(),
        expect_current_sha256.lower() if expect_current_sha256 else None,
    )
    _check(
        checks,
        "alternate_sha256",
        str(alternate.get("sha256", "")).lower(),
        expect_alternate_sha256.lower() if expect_alternate_sha256 else None,
    )

    delta = previous_to_current["summary"]
    _check(
        checks,
        "changed_same_path_entries",
        delta["changed_same_path_entries"],
        expect_changed_same_path,
    )
    _check(
        checks,
        "added_entries",
        delta["added_entries"],
        expect_added_entries,
    )
    _check(
        checks,
        "removed_entries",
        delta["removed_entries"],
        expect_removed_entries,
    )

    match_summary = alternate_to_current["summary"]
    _check(
        checks,
        "alternate_matched",
        match_summary["matched"],
        min_alternate_matches,
        comparator="gte",
    )

    strong = (
        match_summary.get("exact_sha256", 0)
        + match_summary.get("structural_unique", 0)
        + match_summary.get("package_anchor", 0)
    )
    _check(
        checks,
        "alternate_strong_matches",
        strong,
        min_structural_or_better_matches,
        comparator="gte",
    )
    _check(
        checks,
        "alternate_unmatched_old",
        match_summary["unmatched_old"],
        max_alternate_unmatched_old,
        comparator="lte",
    )

    for label, index in [
        ("previous", previous),
        ("current", current),
        ("alternate", alternate),
    ]:
        _check(
            checks,
            f"{label}_parse_errors",
            index.get("summary", {}).get("class_parse_error_count"),
            0,
        )

    passed = all(check["passed"] for check in checks)

    return {
        "schema_version": 1,
        "kind": "corpus_audit_report",
        "scope_prefix": scope_prefix,
        "passed": passed,
        "inputs": {
            "previous": {
                "source_name": previous.get("source_name"),
                "sha256": previous.get("sha256"),
                "summary": previous.get("summary"),
            },
            "current": {
                "source_name": current.get("source_name"),
                "sha256": current.get("sha256"),
                "summary": current.get("summary"),
            },
            "alternate": {
                "source_name": alternate.get("source_name"),
                "sha256": alternate.get("sha256"),
                "summary": alternate.get("summary"),
            },
        },
        "previous_to_current": previous_to_current,
        "alternate_to_current": alternate_to_current,
        "checks": checks,
        "summary": {
            "check_count": len(checks),
            "failed_checks": sum(1 for check in checks if not check["passed"]),
            "changed_same_path_entries": delta["changed_same_path_entries"],
            "added_entries": delta["added_entries"],
            "removed_entries": delta["removed_entries"],
            "alternate_matched": match_summary["matched"],
            "alternate_exact_sha256": match_summary.get("exact_sha256", 0),
            "alternate_structural_unique": match_summary.get("structural_unique", 0),
            "alternate_package_anchor": match_summary.get("package_anchor", 0),
            "alternate_weighted_mutual_best": match_summary.get(
                "weighted_mutual_best",
                0,
            ),
            "alternate_ambiguous": match_summary["ambiguous"],
            "alternate_unmatched_old": match_summary["unmatched_old"],
            "alternate_unmatched_new": match_summary["unmatched_new"],
        },
    }


def audit_corpus(
    previous_jar: Path,
    current_jar: Path,
    alternate_jar: Path,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_corpus_report(
        index_jar(previous_jar),
        index_jar(current_jar),
        index_jar(alternate_jar),
        **kwargs,
    )


def write_report(report: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-corpus-audit")
    p.add_argument("previous_jar", type=Path)
    p.add_argument("current_jar", type=Path)
    p.add_argument("alternate_jar", type=Path)
    p.add_argument("--scope-prefix", default="rs/")
    p.add_argument("--expect-previous-sha256")
    p.add_argument("--expect-current-sha256")
    p.add_argument("--expect-alternate-sha256")
    p.add_argument("--expect-changed-same-path", type=int)
    p.add_argument("--expect-added-entries", type=int)
    p.add_argument("--expect-removed-entries", type=int)
    p.add_argument("--min-alternate-matches", type=int)
    p.add_argument("--min-structural-or-better-matches", type=int)
    p.add_argument("--max-alternate-unmatched-old", type=int)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = audit_corpus(
            args.previous_jar,
            args.current_jar,
            args.alternate_jar,
            scope_prefix=args.scope_prefix,
            expect_previous_sha256=args.expect_previous_sha256,
            expect_current_sha256=args.expect_current_sha256,
            expect_alternate_sha256=args.expect_alternate_sha256,
            expect_changed_same_path=args.expect_changed_same_path,
            expect_added_entries=args.expect_added_entries,
            expect_removed_entries=args.expect_removed_entries,
            min_alternate_matches=args.min_alternate_matches,
            min_structural_or_better_matches=(
                args.min_structural_or_better_matches
            ),
            max_alternate_unmatched_old=args.max_alternate_unmatched_old,
        )
        write_report(report, args.out)
    except Exception as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2

    print(
        "SPK_CORPUS_AUDIT_PASS"
        if report["passed"]
        else "SPK_CORPUS_AUDIT_FAIL"
    )
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
