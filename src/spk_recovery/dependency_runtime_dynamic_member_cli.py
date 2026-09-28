from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .dependency_runtime_dynamic_member import (
    DependencyRuntimeDynamicMemberError,
    build_dependency_runtime_dynamic_member_proof,
    write_dependency_runtime_dynamic_member_proof,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-runtime-dynamic-member"
    )
    parser.add_argument("private_dynamic_mapping", type=Path)
    parser.add_argument("private_replacement_plan", type=Path)
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
        report = build_dependency_runtime_dynamic_member_proof(
            args.private_dynamic_mapping,
            args.private_replacement_plan,
            args.bundled_jar,
            list(args.official_artifacts),
            include_identifiers=args.include_identifiers,
        )
        write_dependency_runtime_dynamic_member_proof(
            report,
            args.out,
        )
    except (
        DependencyRuntimeDynamicMemberError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_DEPENDENCY_RUNTIME_DYNAMIC_MEMBER_PASS")
    print(
        "runtime_dynamic_member_id="
        + str(report["runtime_dynamic_member_id"])
    )
    print(
        "ready_for_dynamic_root_promotion="
        + str(
            report["summary"]["ready_for_dynamic_root_promotion"]
        ).lower()
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
