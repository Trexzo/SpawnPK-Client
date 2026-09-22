from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lineage import load_lineage
from .member_lineage import load_member_lineage
from .update_release import (
    UpdateReleaseError,
    migrate_update_to_release,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-update-release")
    p.add_argument("old_index", type=Path)
    p.add_argument("old_authority", type=Path)
    p.add_argument("new_jar", type=Path)
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("decompiler_jar", type=Path)
    p.add_argument("--decompiler-sha256", required=True)
    p.add_argument("--engine", choices=["cfr", "vineflower", "procyon"], required=True)
    p.add_argument("--old-build-id", required=True)
    p.add_argument("--new-build-id", required=True)
    p.add_argument("--new-build-number", type=int)
    p.add_argument("--member-candidates", type=Path)
    p.add_argument("--old-jar", type=Path)
    p.add_argument("--scope-prefix", default="rs/")
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
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = migrate_update_to_release(
            _load(args.old_index),
            _load(args.old_authority),
            args.new_jar,
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            args.decompiler_jar,
            expected_decompiler_sha256=args.decompiler_sha256,
            engine=args.engine,
            old_build_id=args.old_build_id,
            new_build_id=args.new_build_id,
            new_build_number=args.new_build_number,
            out_dir=args.out_dir,
            member_candidates=(
                _load(args.member_candidates)
                if args.member_candidates
                else None
            ),
            old_jar=args.old_jar,
            scope_prefix=args.scope_prefix,
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
        )
    except (
        UpdateReleaseError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RECOVERY_UPDATE_RELEASE_COMPLETE")
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
