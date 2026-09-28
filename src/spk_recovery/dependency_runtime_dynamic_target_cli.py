from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .dependency_runtime_dynamic_target import (
    DependencyRuntimeDynamicTargetError,
    build_dependency_runtime_dynamic_target_classification,
    write_dependency_runtime_dynamic_target_classification,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-runtime-dynamic-target"
    )
    parser.add_argument("private_dynamic", type=Path)
    parser.add_argument(
        "private_replacement_plan",
        type=Path,
    )
    parser.add_argument(
        "private_runtime_resource",
        type=Path,
    )
    parser.add_argument("bundled_jar", type=Path)
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        report = (
            build_dependency_runtime_dynamic_target_classification(
                args.private_dynamic,
                args.private_replacement_plan,
                args.private_runtime_resource,
                args.bundled_jar,
                include_identifiers=(
                    args.include_identifiers
                ),
            )
        )
        write_dependency_runtime_dynamic_target_classification(
            report,
            args.out,
        )
    except (
        DependencyRuntimeDynamicTargetError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_DEPENDENCY_RUNTIME_DYNAMIC_TARGET_PASS")
    print(
        "runtime_dynamic_target_id="
        + str(report["runtime_dynamic_target_id"])
    )
    print(
        "unresolved_or_blocked_count="
        + str(
            report["summary"][
                "unresolved_or_blocked_count"
            ]
        )
    )
    print("runtime_capsule_mutation_ready=false")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
