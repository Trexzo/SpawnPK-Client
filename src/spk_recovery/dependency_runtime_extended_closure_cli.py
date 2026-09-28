from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .dependency_runtime_extended_closure import (
    DependencyRuntimeExtendedClosureError,
    build_dependency_runtime_extended_closure,
    write_dependency_runtime_extended_closure,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-runtime-extended-closure"
    )
    parser.add_argument("private_replacement_plan", type=Path)
    parser.add_argument("private_replacement_extension", type=Path)
    parser.add_argument("private_runtime_closure", type=Path)
    parser.add_argument("private_dynamic_target", type=Path)
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
        report = build_dependency_runtime_extended_closure(
            args.private_replacement_plan,
            args.private_replacement_extension,
            args.private_runtime_closure,
            args.private_dynamic_target,
            args.bundled_jar,
            list(args.official_artifacts),
            include_identifiers=args.include_identifiers,
        )
        write_dependency_runtime_extended_closure(
            report,
            args.out,
        )
    except (
        DependencyRuntimeExtendedClosureError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_DEPENDENCY_RUNTIME_EXTENDED_CLOSURE_PASS")
    print(
        "runtime_extended_closure_id="
        + str(report["runtime_extended_closure_id"])
    )
    print(
        "remaining_mapping_gap_count="
        + str(report["summary"]["remaining_mapping_gap_count"])
    )
    print("runtime_capsule_mutation_ready=false")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
