from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .dependency_source_overlay import (
    DependencySourceOverlayError,
    apply_dependency_source_overlay,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-source-overlay"
    )
    parser.add_argument("source_root", type=Path)
    parser.add_argument("private_edit_plan", type=Path)
    parser.add_argument(
        "private_replacement_plan",
        type=Path,
    )
    parser.add_argument("bundled_jar", type=Path)
    parser.add_argument("artifact", type=Path, nargs="+")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--java-command", default="java")
    parser.add_argument("--javac-command", default="javac")
    args = parser.parse_args(argv)

    try:
        report = apply_dependency_source_overlay(
            args.source_root,
            args.private_edit_plan,
            args.private_replacement_plan,
            args.bundled_jar,
            args.artifact,
            out_dir=args.out_dir,
            java_command=args.java_command,
            javac_command=args.javac_command,
        )
    except (
        DependencySourceOverlayError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_DEPENDENCY_SOURCE_OVERLAY_PASS")
    print(f"overlay_id={report['overlay_id']}")
    print(
        "direct_edit_count="
        f"{summary['direct_edit_count']}"
    )
    print(
        "files_changed="
        f"{summary['files_changed']}"
    )
    print(
        "pre_diagnostic_error_count="
        f"{summary['pre_diagnostic_error_count']}"
    )
    print(
        "post_diagnostic_error_count="
        f"{summary['post_diagnostic_error_count']}"
    )
    print(
        "canonical_input_unchanged="
        f"{summary['canonical_input_unchanged']}"
    )
    print(f"out_dir={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
