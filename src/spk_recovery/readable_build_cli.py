from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lineage import load_lineage
from .member_lineage import load_member_lineage
from .readable_build import ReadableBuildError, build_readable_client


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-readable-build")
    p.add_argument("source_jar", type=Path)
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("index", type=Path)
    p.add_argument("--build-id", required=True)
    p.add_argument("--target-package", default="recovered/spawnpk/client")
    p.add_argument(
        "--source-safe-fallback",
        action="store_true",
        help="rename residual Java class/package collision roots without changing their packages",
    )
    p.add_argument(
        "--fallback-name-prefix",
        default="Recovered_",
    )
    p.add_argument("--member-safety-acceptance", type=Path)
    p.add_argument("--allow-package-resource-risk", action="store_true")
    p.add_argument("--rewrite-class-name-strings", action="store_true")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        manifest = build_readable_client(
            args.source_jar,
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.index),
            build_id=args.build_id,
            target_package=args.target_package,
            source_safe_fallback=args.source_safe_fallback,
            fallback_name_prefix=args.fallback_name_prefix,
            member_safety_acceptance=(
                _load(args.member_safety_acceptance)
                if args.member_safety_acceptance
                else None
            ),
            allow_package_resource_risk=args.allow_package_resource_risk,
            rewrite_class_name_strings=args.rewrite_class_name_strings,
            out_dir=args.out_dir,
        )
    except (
        ReadableBuildError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_READABLE_BUILD_" + manifest["status"].upper())
    print(f"manifest_id={manifest['manifest_id']}")
    print(f"namespace_id={manifest['namespace_id']}")
    print(f"status={manifest['status']}")
    print(f"source_sha256={manifest['source_sha256']}")
    if manifest.get("output_sha256"):
        print(f"output_sha256={manifest['output_sha256']}")
    if manifest.get("blocker"):
        print(f"blocker={manifest['blocker']['code']}")
    print(f"out_dir={args.out_dir.resolve()}")
    return 0 if manifest["status"] == "complete" else 3


if __name__ == "__main__":
    raise SystemExit(main())
