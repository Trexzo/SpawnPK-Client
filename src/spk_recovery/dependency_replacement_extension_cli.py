from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .dependency_replacement_extension import (
    DependencyReplacementExtensionError,
    build_dependency_replacement_extension,
    write_dependency_replacement_extension,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-replacement-extension"
    )
    parser.add_argument("private_replacement_plan", type=Path)
    parser.add_argument("private_dynamic_mapping", type=Path)
    parser.add_argument("private_dynamic_member", type=Path)
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
        report = build_dependency_replacement_extension(
            args.private_replacement_plan,
            args.private_dynamic_mapping,
            args.private_dynamic_member,
            args.bundled_jar,
            list(args.official_artifacts),
            include_identifiers=args.include_identifiers,
        )
        write_dependency_replacement_extension(
            report,
            args.out,
        )
    except (
        DependencyReplacementExtensionError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_DEPENDENCY_REPLACEMENT_EXTENSION_PASS")
    print(
        "replacement_extension_id="
        + str(report["replacement_extension_id"])
    )
    print(
        "ready_for_augmented_closure_reaudit="
        + str(
            report["summary"][
                "ready_for_augmented_closure_reaudit"
            ]
        ).lower()
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
