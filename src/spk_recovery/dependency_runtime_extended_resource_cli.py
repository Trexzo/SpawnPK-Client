from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .dependency_runtime_extended_resource import (
    DependencyRuntimeExtendedResourceError,
    build_dependency_runtime_extended_resource,
    write_dependency_runtime_extended_resource,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-runtime-extended-resource"
    )
    parser.add_argument("private_extended_closure", type=Path)
    parser.add_argument("private_original_resource", type=Path)
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
        report = build_dependency_runtime_extended_resource(
            args.private_extended_closure,
            args.private_original_resource,
            args.bundled_jar,
            list(args.official_artifacts),
            include_identifiers=args.include_identifiers,
        )
        write_dependency_runtime_extended_resource(
            report,
            args.out,
        )
    except (
        DependencyRuntimeExtendedResourceError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_DEPENDENCY_RUNTIME_EXTENDED_RESOURCE_PASS")
    print(
        "runtime_extended_resource_id="
        + str(report["runtime_extended_resource_id"])
    )
    print(
        "resource_equivalence_complete="
        + str(
            report["summary"]["resource_equivalence_complete"]
        ).lower()
    )
    print(
        "native_runtime_safety_unproven="
        + str(
            report["summary"][
                "native_runtime_safety_unproven"
            ]
        ).lower()
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
