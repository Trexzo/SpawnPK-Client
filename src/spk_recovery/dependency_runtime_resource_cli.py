from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .dependency_runtime_resource import (
    DependencyRuntimeResourceError,
    build_dependency_runtime_resource_equivalence,
    write_dependency_runtime_resource_equivalence,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-runtime-resource"
    )
    parser.add_argument(
        "private_runtime_closure",
        type=Path,
    )
    parser.add_argument("bundled_jar", type=Path)
    parser.add_argument(
        "--official-artifact",
        action="append",
        type=Path,
        required=True,
        dest="official_artifacts",
    )
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        report = (
            build_dependency_runtime_resource_equivalence(
                args.private_runtime_closure,
                args.bundled_jar,
                list(args.official_artifacts),
                include_identifiers=(
                    args.include_identifiers
                ),
            )
        )
        write_dependency_runtime_resource_equivalence(
            report,
            args.out,
        )
    except (
        DependencyRuntimeResourceError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_DEPENDENCY_RUNTIME_RESOURCE_PASS")
    print(
        f"runtime_resource_id={report['runtime_resource_id']}"
    )
    print(
        "resource_blocker_count="
        + str(report["summary"]["resource_blocker_count"])
    )
    print("runtime_capsule_mutation_ready=false")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
