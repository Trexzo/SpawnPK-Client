from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .dependency_runtime_dynamic import (
    DependencyRuntimeDynamicError,
    build_dependency_runtime_dynamic_inventory,
    write_dependency_runtime_dynamic_inventory,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-runtime-dynamic"
    )
    parser.add_argument(
        "runtime_resource_authority",
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
        report = build_dependency_runtime_dynamic_inventory(
            args.runtime_resource_authority,
            args.bundled_jar,
            include_identifiers=args.include_identifiers,
        )
        write_dependency_runtime_dynamic_inventory(
            report,
            args.out,
        )
    except (
        DependencyRuntimeDynamicError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_DEPENDENCY_RUNTIME_DYNAMIC_PASS")
    print(
        f"runtime_dynamic_id={report['runtime_dynamic_id']}"
    )
    print(
        "dynamic_callsite_count="
        + str(report["summary"]["dynamic_callsite_count"])
    )
    print(
        "dynamic_target_unresolved_count="
        + str(
            report["summary"][
                "dynamic_target_unresolved_count"
            ]
        )
    )
    print("runtime_capsule_mutation_ready=false")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
