from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .clean_rebuild import (
    CleanRebuildError,
    clean_project_rebuild,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-clean-rebuild")
    p.add_argument("recovered_manifest", type=Path)
    p.add_argument("source_readiness", type=Path)
    p.add_argument("readable_manifest", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("build_authority", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("--javac-command", default="javac")
    p.add_argument(
        "--source-prefix",
        action="append",
        dest="source_prefixes",
    )
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = clean_project_rebuild(
            _load(args.recovered_manifest),
            _load(args.source_readiness),
            _load(args.readable_manifest),
            args.readable_jar,
            _load(args.build_authority),
            args.source_root,
            out_dir=args.out_dir,
            javac_command=args.javac_command,
            source_prefixes=args.source_prefixes,
        )
    except (
        CleanRebuildError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_CLEAN_REBUILD_" + report["status"].upper())
    print(f"rebuild_id={report['rebuild_id']}")
    print(f"status={report['status']}")
    print(
        "project_source_files="
        f"{report['source_scope']['project_source_files']}"
    )
    print(
        "expected_project_classes="
        f"{report['project_classes']['expected_count']}"
    )
    print(
        "generated_project_classes="
        f"{report['project_classes']['generated_count']}"
    )
    print(
        "project_binary_fallback_count="
        f"{report['project_classes']['binary_fallback_count']}"
    )
    if report["rebuilt_client"]["sha256"]:
        print(
            "rebuilt_jar_sha256="
            f"{report['rebuilt_client']['sha256']}"
        )
    diagnostic = report["compiler"].get(
        "diagnostic_classification"
    )
    if diagnostic is not None:
        summary = diagnostic["summary"]
        cannot = summary["cannot_find_symbol"]
        print(f"javac_diagnostic_report_id={diagnostic['report_id']}")
        print(f"javac_total_errors={summary['total_errors']}")
        print(f"javac_affected_files={summary['affected_files']}")
        print(
            "javac_categories_json="
            + json.dumps(
                summary["categories"],
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        print(f"javac_cannot_find_symbol={cannot['count']}")
        print(
            "javac_cannot_find_symbol_kinds_json="
            + json.dumps(
                cannot["symbol_kinds"],
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        print(
            "javac_cannot_find_symbol_shapes_json="
            + json.dumps(
                cannot["symbol_shapes"],
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    print(f"out_dir={args.out_dir.resolve()}")
    return 0 if report["status"] == "complete" else 3


if __name__ == "__main__":
    raise SystemExit(main())
