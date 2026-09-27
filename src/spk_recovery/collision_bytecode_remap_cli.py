from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .collision_bytecode_remap import (
    CollisionBytecodeRemapError,
    transform_collision_jar,
    write_transform_report,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-collision-bytecode-remap"
    )
    p.add_argument("input_jar", type=Path)
    p.add_argument("private_plan", type=Path)
    p.add_argument("output_jar", type=Path)
    p.add_argument("--report-out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = transform_collision_jar(
            args.input_jar,
            args.private_plan,
            args.output_jar,
        )
        write_transform_report(
            report,
            args.report_out,
        )
    except (
        CollisionBytecodeRemapError,
        OSError,
        ValueError,
        zipfile.BadZipFile,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_COLLISION_BYTECODE_REMAP_PASS")
    print(f"transform_id={report['transform_id']}")
    print(f"plan_id={report['plan_id']}")
    print(
        "explicit_remap_count="
        f"{summary['explicit_remap_count']}"
    )
    print(
        "expanded_remap_count="
        f"{summary['expanded_remap_count']}"
    )
    print(
        "nested_family_added_count="
        f"{summary['nested_family_added_count']}"
    )
    print(
        "rewritten_class_count="
        f"{summary['rewritten_class_count']}"
    )
    print(
        "changed_utf8_count="
        f"{summary['changed_utf8_count']}"
    )
    print(
        "pre_collision_edge_count="
        f"{summary['pre_collision_edge_count']}"
    )
    print(
        "post_collision_edge_count="
        f"{summary['post_collision_edge_count']}"
    )
    print(f"output_jar_sha256={report['output_jar_sha256']}")
    print(f"output_jar={args.output_jar}")
    print(f"report={args.report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
