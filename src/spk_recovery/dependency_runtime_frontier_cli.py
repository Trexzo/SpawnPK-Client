from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .dependency_runtime_frontier import (
    DependencyRuntimeFrontierError,
    build_dependency_runtime_frontier,
    write_dependency_runtime_frontier,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-dependency-runtime-frontier"
    )
    p.add_argument("private_replacement_plan", type=Path)
    p.add_argument("bundled_jar", type=Path)
    p.add_argument(
        "--official-artifact",
        action="append",
        type=Path,
        required=True,
        dest="official_artifacts",
    )
    p.add_argument("--include-identifiers", action="store_true")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = build_dependency_runtime_frontier(
            args.private_replacement_plan,
            args.bundled_jar,
            list(args.official_artifacts),
            include_identifiers=args.include_identifiers,
        )
        write_dependency_runtime_frontier(report, args.out)
    except (
        DependencyRuntimeFrontierError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_DEPENDENCY_RUNTIME_FRONTIER_PASS")
    print(f"runtime_frontier_id={report['runtime_frontier_id']}")
    print(
        "runtime_capsule_mutation_ready="
        + str(
            report["summary"]["runtime_capsule_mutation_ready"]
        ).lower()
    )
    print(
        "requires_dependency_closure_proof="
        + str(
            report["summary"]["requires_dependency_closure_proof"]
        ).lower()
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
