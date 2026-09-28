from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .dependency_runtime_substitution_plan import (
    DependencyRuntimeSubstitutionPlanError,
    build_dependency_runtime_substitution_plan,
    write_dependency_runtime_substitution_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-runtime-substitution-plan"
    )
    parser.add_argument("runtime_readiness", type=Path)
    parser.add_argument("private_replacement_plan", type=Path)
    parser.add_argument("private_replacement_extension", type=Path)
    parser.add_argument("private_extended_closure", type=Path)
    parser.add_argument("private_extended_resource", type=Path)
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
        report = build_dependency_runtime_substitution_plan(
            args.runtime_readiness,
            args.private_replacement_plan,
            args.private_replacement_extension,
            args.private_extended_closure,
            args.private_extended_resource,
            args.bundled_jar,
            list(args.official_artifacts),
            include_identifiers=args.include_identifiers,
        )
        write_dependency_runtime_substitution_plan(
            report,
            args.out,
        )
    except (
        DependencyRuntimeSubstitutionPlanError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_DEPENDENCY_RUNTIME_SUBSTITUTION_PLAN_PASS")
    print(
        "runtime_substitution_plan_id="
        + str(report["runtime_substitution_plan_id"])
    )
    print(
        "collision_free="
        + str(report["summary"]["collision_free"]).lower()
    )
    print("apply_authorized=false")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
