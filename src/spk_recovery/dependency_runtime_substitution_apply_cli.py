from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .dependency_runtime_substitution_apply import (
    DependencyRuntimeSubstitutionApplyError,
    apply_dependency_runtime_substitution,
    verify_dependency_runtime_substitution_postimage,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-dependency-runtime-substitution-apply"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    apply_parser = sub.add_parser("apply")
    verify_parser = sub.add_parser("verify")
    for command in (apply_parser, verify_parser):
        command.add_argument("private_plan", type=Path)
        command.add_argument("bundled_jar", type=Path)
        command.add_argument(
            "--official-artifact",
            action="append",
            type=Path,
            required=True,
            dest="official_artifacts",
        )
        command.add_argument("--out-dir", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "apply":
            report = apply_dependency_runtime_substitution(
                args.private_plan,
                args.bundled_jar,
                list(args.official_artifacts),
                args.out_dir,
            )
            marker = "SPK_DEPENDENCY_RUNTIME_SUBSTITUTION_APPLY_PASS"
        else:
            report = verify_dependency_runtime_substitution_postimage(
                args.private_plan,
                args.bundled_jar,
                list(args.official_artifacts),
                args.out_dir,
            )
            marker = "SPK_DEPENDENCY_RUNTIME_SUBSTITUTION_VERIFY_PASS"
    except (
        DependencyRuntimeSubstitutionApplyError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print(marker)
    print("runtime_postimage_id=" + str(report["runtime_postimage_id"]))
    print("verified=true")
    print(f"out_dir={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
