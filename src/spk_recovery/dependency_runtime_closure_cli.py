from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .dependency_runtime_closure import (
    DependencyRuntimeClosureError,
    build_dependency_runtime_closure,
    write_dependency_runtime_closure,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-runtime-closure"
    )
    parser.add_argument("private_replacement_plan", type=Path)
    parser.add_argument("runtime_frontier", type=Path)
    parser.add_argument("bundled_jar", type=Path)
    parser.add_argument(
        "--official-artifact",
        action="append",
        type=Path,
        required=True,
        dest="official_artifacts",
    )
    parser.add_argument("--include-identifiers", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        report = build_dependency_runtime_closure(
            args.private_replacement_plan,
            args.runtime_frontier,
            args.bundled_jar,
            list(args.official_artifacts),
            include_identifiers=args.include_identifiers,
        )
        write_dependency_runtime_closure(report, args.out)
    except (
        DependencyRuntimeClosureError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_DEPENDENCY_RUNTIME_CLOSURE_PASS")
    print(f"runtime_closure_id={report['runtime_closure_id']}")
    print(
        "class_closure_blocker_count="
        + str(report["summary"]["class_closure_blocker_count"])
    )
    print(
        "runtime_capsule_mutation_ready="
        + str(
            report["summary"]["runtime_capsule_mutation_ready"]
        ).lower()
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
