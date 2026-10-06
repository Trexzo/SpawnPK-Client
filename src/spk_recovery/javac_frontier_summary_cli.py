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



def focus_diagnostics(
    report: dict[str, Any],
    *,
    focus_files: int,
    include_source_lines: bool = False,
    source_context_lines: int = 0,
) -> list[str]:
    if focus_files <= 0:
        return []

    rows = report.get("diagnostics")
    if not isinstance(rows, list):
        raise JavacFrontierSummaryError(
            "diagnostics must be an array"
        )

    files: Counter[str] = Counter()
    by_file: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise JavacFrontierSummaryError(
                "diagnostic row must be an object"
            )
        source_path = row.get("source_path")
        if not source_path:
            continue
        path = str(source_path).replace("\\", "/")
        files[path] += 1
        by_file.setdefault(path, []).append(row)

    out: list[str] = []
    for path, total in _rank(files, focus_files):
        file_rows = by_file[path]
        categories = Counter(
            str(row.get("category") or "unknown")
            for row in file_rows
        )
        out.extend(
            [
                "",
                "============================================================",
                f" FOCUSED JAVAC DIAGNOSTICS: {path}",
                "============================================================",
                f"FOCUSED_TOTAL_ERRORS={total}",
                "FOCUSED_CATEGORIES="
                + json.dumps(
                    dict(sorted(categories.items())),
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            ]
        )
        if include_source_lines:
            line_numbers = sorted(
                {
                    int(row.get("line"))
                    for row in file_rows
                    if isinstance(row.get("line"), int)
                    and int(row.get("line")) > 0
                }
            )
            try:
                source_text = Path(path).read_text(encoding="utf-8")
                source_lines = source_text.splitlines()
            except OSError as exc:
                out.append(
                    "SOURCE_LINES_UNAVAILABLE="
                    + type(exc).__name__
                )
            else:
                out.append("=== FOCUSED SOURCE LINES ===")
                for line_number in line_numbers:
                    if line_number > len(source_lines):
                        out.append(
                            f"SRC: line={line_number} | <out-of-range>"
                        )
                        continue
                    rendered = source_lines[line_number - 1].replace(
                        "\t", "    "
                    )
                    out.append(
                        f"SRC: line={line_number} | text={rendered}"
                    )

                if source_context_lines > 0 and line_numbers:
                    context_numbers: set[int] = set()
                    for line_number in line_numbers:
                        if line_number > len(source_lines):
                            continue
                        start = max(1, line_number - source_context_lines)
                        end = min(
                            len(source_lines),
                            line_number + source_context_lines,
                        )
                        context_numbers.update(range(start, end + 1))
                    out.append(
                        "=== FOCUSED SOURCE CONTEXT "
                        f"(+/-{source_context_lines}) ==="
                    )
                    for line_number in sorted(context_numbers):
                        rendered = source_lines[line_number - 1].replace(
                            "\t", "    "
                        )
                        out.append(
                            f"SRCCTX: line={line_number} | text={rendered}"
                        )

        for row in sorted(
            file_rows,
            key=lambda item: (
                int(item.get("line") or 0),
                str(item.get("category") or ""),
                str(item.get("message") or ""),
                str(item.get("symbol_kind") or ""),
                str(item.get("symbol") or ""),
                str(item.get("location_kind") or ""),
                str(item.get("location") or ""),
            ),
        ):
            out.append(
                "DIAG: "
                f"line={row.get('line')} | "
                f"category={row.get('category')} | "
                f"message={row.get('message')} | "
                f"symbol_kind={row.get('symbol_kind')} | "
                f"symbol={row.get('symbol')} | "
                f"location_kind={row.get('location_kind')} | "
                f"location={row.get('location')}"
            )
    return out

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-javac-frontier-summary"
    )
    parser.add_argument("private_diagnostic", type=Path)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--focus-files", type=int, default=0)
    parser.add_argument(
        "--source-lines",
        action="store_true",
        help=(
            "print exact local source lines for focused diagnostics; "
            "intended only for private exact-local runs"
        ),
    )
    parser.add_argument(
        "--source-context-lines",
        type=int,
        default=0,
        help=(
            "also print this many local source lines before/after focused "
            "diagnostics; requires --source-lines"
        ),
    )
    args = parser.parse_args(argv)

    if args.top < 1 or args.top > 100:
        print(
            "REFUSED: --top must be between 1 and 100",
            file=sys.stderr,
        )
        return 2
    if args.focus_files < 0 or args.focus_files > 20:
        print(
            "REFUSED: --focus-files must be between 0 and 20",
            file=sys.stderr,
        )
        return 2
    if args.source_context_lines < 0 or args.source_context_lines > 50:
        print(
            "REFUSED: --source-context-lines must be between 0 and 50",
            file=sys.stderr,
        )
        return 2
    if args.source_context_lines and not args.source_lines:
        print(
            "REFUSED: --source-context-lines requires --source-lines",
            file=sys.stderr,
        )
        return 2

    try:
        report = _load(args.private_diagnostic)
        lines = summarize(report, top=args.top)
        lines.extend(
            focus_diagnostics(
                report,
                focus_files=args.focus_files,
                include_source_lines=args.source_lines,
                source_context_lines=args.source_context_lines,
            )
        )
    except JavacFrontierSummaryError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
