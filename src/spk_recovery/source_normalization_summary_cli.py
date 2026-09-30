from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


class SourceNormalizationSummaryError(ValueError):
    pass


def _exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise SourceNormalizationSummaryError(
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
        raise SourceNormalizationSummaryError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise SourceNormalizationSummaryError(str(exc)) from exc

    if not isinstance(value, dict):
        raise SourceNormalizationSummaryError(
            "source normalization report root must be an object"
        )
    return value


def summarize(
    report: dict[str, Any],
    *,
    top: int,
) -> list[str]:
    if report.get("kind") != "procyon_source_normalization_report":
        raise SourceNormalizationSummaryError(
            "not a Procyon source normalization report"
        )

    normalization_id = report.get("normalization_id")
    if not isinstance(normalization_id, str) or not normalization_id:
        raise SourceNormalizationSummaryError(
            "normalization_id must be a non-empty string"
        )

    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise SourceNormalizationSummaryError(
            "summary must be an object"
        )

    actions = report.get("actions")
    if not isinstance(actions, list):
        raise SourceNormalizationSummaryError(
            "actions must be an array"
        )

    kind = "shadowed_same_package_static_field_owner_type_context"
    methods_by_source: Counter[str] = Counter()
    refs_by_source: Counter[str] = Counter()
    actions_by_source: dict[str, list[dict[str, Any]]] = {}

    for action in actions:
        if not isinstance(action, dict):
            raise SourceNormalizationSummaryError(
                "normalization action must be an object"
            )
        if action.get("kind") != kind:
            continue

        source_path = action.get("source_path")
        if not isinstance(source_path, str) or not source_path:
            raise SourceNormalizationSummaryError(
                "same-package action source_path must be non-empty"
            )
        source_path = source_path.replace("\\", "/")

        method_name = action.get("method_name")
        descriptor = action.get("method_descriptor")
        if not isinstance(method_name, str) or not method_name:
            raise SourceNormalizationSummaryError(
                f"{source_path}: method_name must be non-empty"
            )
        if not isinstance(descriptor, str) or not descriptor:
            raise SourceNormalizationSummaryError(
                f"{source_path}: method_descriptor must be non-empty"
            )

        replacement_count = action.get("replacement_count")
        if (
            isinstance(replacement_count, bool)
            or not isinstance(replacement_count, int)
            or replacement_count < 1
        ):
            raise SourceNormalizationSummaryError(
                f"{source_path}: replacement_count must be a positive integer"
            )

        owners = action.get("same_package_owners")
        if (
            not isinstance(owners, list)
            or not owners
            or not all(
                isinstance(owner, str) and owner
                for owner in owners
            )
        ):
            raise SourceNormalizationSummaryError(
                f"{source_path}: same_package_owners must be non-empty strings"
            )

        methods_by_source[source_path] += 1
        refs_by_source[source_path] += replacement_count
        actions_by_source.setdefault(source_path, []).append(action)

    computed_methods = sum(methods_by_source.values())
    computed_refs = sum(refs_by_source.values())

    expected_methods = summary.get(
        "shadowed_same_package_static_field_method_count"
    )
    expected_refs = summary.get(
        "shadowed_same_package_static_field_reference_count"
    )
    if expected_methods != computed_methods:
        raise SourceNormalizationSummaryError(
            "same-package method count mismatch: "
            f"summary={expected_methods!r} computed={computed_methods}"
        )
    if expected_refs != computed_refs:
        raise SourceNormalizationSummaryError(
            "same-package reference count mismatch: "
            f"summary={expected_refs!r} computed={computed_refs}"
        )

    ranked_sources = sorted(
        methods_by_source,
        key=lambda path: (
            -refs_by_source[path],
            -methods_by_source[path],
            path,
        ),
    )[:top]

    out = [
        "============================================================",
        " SOURCE NORMALIZATION SAME-PACKAGE EVIDENCE",
        "============================================================",
        f"SOURCE_NORMALIZATION_ID={normalization_id}",
        f"SAME_PACKAGE_SHADOW_METHODS={computed_methods}",
        f"SAME_PACKAGE_SHADOW_REFERENCES={computed_refs}",
        "",
        f"=== TOP {top} SAME-PACKAGE SHADOW SOURCES ===",
    ]

    if not ranked_sources:
        out.append("<none>")
        return out

    for source_path in ranked_sources:
        out.append(
            f"SOURCE {source_path} | "
            f"methods={methods_by_source[source_path]} | "
            f"references={refs_by_source[source_path]}"
        )
        rows = sorted(
            actions_by_source[source_path],
            key=lambda action: (
                str(action["method_name"]),
                str(action["method_descriptor"]),
                tuple(str(v) for v in action["same_package_owners"]),
            ),
        )
        for action in rows:
            owners = ",".join(
                str(owner)
                for owner in action["same_package_owners"]
            )
            out.append(
                "  "
                + str(action["method_name"])
                + str(action["method_descriptor"])
                + " | references="
                + str(action["replacement_count"])
                + " | owners="
                + owners
            )

    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-source-normalization-summary"
    )
    parser.add_argument("normalization_report", type=Path)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args(argv)

    if args.top < 1 or args.top > 100:
        print(
            "REFUSED: --top must be between 1 and 100",
            file=sys.stderr,
        )
        return 2

    try:
        report = _load(args.normalization_report)
        lines = summarize(report, top=args.top)
    except SourceNormalizationSummaryError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
