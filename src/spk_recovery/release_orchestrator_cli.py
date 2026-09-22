from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lineage import load_lineage
from .member_lineage import load_member_lineage
from .release_orchestrator import (
    ExistingAuthorityReleaseError,
    build_existing_authority_release,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-release-build")
    p.add_argument("source_jar", type=Path)
    p.add_argument("source_index", type=Path)
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("decompiler_jar", type=Path)
    p.add_argument("--decompiler-sha256", required=True)
    p.add_argument("--engine", choices=["cfr", "vineflower", "procyon"], required=True)
    p.add_argument("--build-id", required=True)
    p.add_argument("--target-package", default="recovered/spawnpk/client")
    p.add_argument("--source-safe-fallback", action="store_true")
    p.add_argument(
        "--fallback-name-prefix",
        default="Recovered_",
    )
    p.add_argument("--member-safety-acceptance", type=Path)
    p.add_argument("--allow-package-resource-risk", action="store_true")
    p.add_argument("--rewrite-class-name-strings", action="store_true")
    p.add_argument(
        "--source-prefix",
        action="append",
        dest="source_prefixes",
    )
    p.add_argument("--project-source-only", action="store_true")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = build_existing_authority_release(
            args.source_jar,
            _load(args.source_index),
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            args.decompiler_jar,
            expected_decompiler_sha256=args.decompiler_sha256,
            engine=args.engine,
            build_id=args.build_id,
            out_dir=args.out_dir,
            target_package=args.target_package,
            source_safe_fallback=args.source_safe_fallback,
            fallback_name_prefix=args.fallback_name_prefix,
            member_safety_acceptance=(
                _load(args.member_safety_acceptance)
                if args.member_safety_acceptance
                else None
            ),
            allow_package_resource_risk=(
                args.allow_package_resource_risk
            ),
            rewrite_class_name_strings=(
                args.rewrite_class_name_strings
            ),
            source_prefixes=args.source_prefixes,
            project_source_only=args.project_source_only,
        )
    except (
        ExistingAuthorityReleaseError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RECOVERY_RELEASE_BUILD_COMPLETE")
    print(f"run_id={report['run_id']}")
    print(f"status={report['status']}")
    print(
        "ready_for_release="
        + str(report["ready_for_release"]).lower()
    )
    print(f"terminal_stage={report['terminal_stage']}")
    print(f"out_dir={args.out_dir}")
    return 0 if report["ready_for_release"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
