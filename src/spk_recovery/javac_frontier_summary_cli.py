from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


class JavacFrontierSummaryError(ValueError):
    pass


def _exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise JavacFrontierSummaryError(
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
        raise JavacFrontierSummaryError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise JavacFrontierSummaryError(str(exc)) from exc

    if not isinstance(value, dict):
        raise JavacFrontierSummaryError(
            "private javac diagnostic root must be an object"
        )
    return value


def _rank(counter: Counter[Any], limit: int) -> list[tuple[Any, int]]:
    return sorted(
        counter.items(),
        key=lambda item: (-int(item[1]), str(item[0])),
    )[:limit]


def summarize(
    report: dict[str, Any],
    *,
    top: int,
) -> list[str]:
    if report.get("kind") != "javac_diagnostic_classification_report":
        raise JavacFrontierSummaryError(
            "not a javac diagnostic classification report"
        )
    if report.get("identifiers_included") is not True:
        raise JavacFrontierSummaryError(
            "private diagnostic must include identifiers"
        )

    rows = report.get("diagnostics")
    if not isinstance(rows, list):
        raise JavacFrontierSummaryError(
            "diagnostics must be an array"
        )

    categories: Counter[str] = Counter()
    files: Counter[str] = Counter()
    symbols: Counter[tuple[str, str]] = Counter()

    for row in rows:
        if not isinstance(row, dict):
            raise JavacFrontierSummaryError(
                "diagnostic row must be an object"
            )

        category = str(row.get("category") or "unknown")
        categories[category] += 1

        source_path = row.get("source_path")
        if source_path:
            files[str(source_path).replace("\\", "/")] += 1

        if category == "cannot_find_symbol":
            symbol = row.get("symbol")
            if symbol:
                kind = str(row.get("symbol_kind") or "none")
                symbols[(kind, str(symbol))] += 1

    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise JavacFrontierSummaryError(
            "summary must be an object"
        )

    cannot = summary.get("cannot_find_symbol")
    cannot_count = (
        cannot.get("count")
        if isinstance(cannot, dict)
        else None
    )

    out = [
        "============================================================",
        " PRIVATE JAVAC FRONTIER SUMMARY",
        "============================================================",
        f"JAVAC_FRONTIER_ID={report.get('frontier_id')}",
        f"JAVAC_TOTAL_ERRORS={summary.get('total_errors')}",
        f"JAVAC_AFFECTED_FILES={summary.get('affected_files')}",
        f"JAVAC_CANNOT_FIND_SYMBOL={cannot_count}",
        "",
        "=== ERROR CATEGORIES ===",
    ]

    for category, count in _rank(categories, top):
        out.append(f"{count:5d}  {category}")

    out.extend(
        [
            "",
            f"=== TOP {top} ERROR FILES ===",
        ]
    )
    for path, count in _rank(files, top):
        out.append(f"{count:5d}  {path}")

    out.extend(
        [
            "",
            f"=== TOP {top} CANNOT-FIND SYMBOLS ===",
        ]
    )
    for (kind, symbol), count in sorted(
        symbols.items(),
        key=lambda item: (
            -int(item[1]),
            item[0][0],
            item[0][1],
        ),
    )[:top]:
        out.append(f"{count:5d}  {kind:10s}  {symbol}")

    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-javac-frontier-summary"
    )
    parser.add_argument("private_diagnostic", type=Path)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args(argv)

    if args.top < 1 or args.top > 100:
        print(
            "REFUSED: --top must be between 1 and 100",
            file=sys.stderr,
        )
        return 2

    try:
        report = _load(args.private_diagnostic)
        lines = summarize(report, top=args.top)
    except JavacFrontierSummaryError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
