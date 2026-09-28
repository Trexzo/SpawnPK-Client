from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .dependency_runtime_readiness import (
    DependencyRuntimeReadinessError,
    build_dependency_runtime_readiness,
    write_dependency_runtime_readiness,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-runtime-readiness"
    )
    parser.add_argument("extended_closure", type=Path)
    parser.add_argument("extended_resource", type=Path)
    parser.add_argument("dynamic_target", type=Path)
    parser.add_argument("bundled_jar", type=Path)
    parser.add_argument(
        "--official-artifact",
        action="append",
        type=Path,
        required=True,
        dest="official_artifacts",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        report = build_dependency_runtime_readiness(
            args.extended_closure,
            args.extended_resource,
            args.dynamic_target,
            args.bundled_jar,
            list(args.official_artifacts),
        )
        write_dependency_runtime_readiness(
            report,
            args.out,
        )
    except (
        DependencyRuntimeReadinessError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_DEPENDENCY_RUNTIME_READINESS_PASS")
    print(f"runtime_readiness_id={report['runtime_readiness_id']}")
    print(
        "runtime_dependency_substitution_ready="
        + str(
            report["summary"][
                "runtime_dependency_substitution_ready"
            ]
        ).lower()
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
