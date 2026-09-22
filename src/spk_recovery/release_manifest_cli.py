from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lineage import load_lineage
from .member_lineage import load_member_lineage
from .release_manifest import (
    RecoveryReleaseError,
    build_recovery_release_manifest,
    write_recovery_release_manifest,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-release-manifest")
    p.add_argument("authority_index", type=Path)
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("readable_manifest", type=Path)
    p.add_argument("recovered_source_manifest", type=Path)
    p.add_argument("clean_rebuild_report", type=Path)
    p.add_argument("roundtrip_report", type=Path)
    p.add_argument("--source-rewrite-acceptance", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        manifest = build_recovery_release_manifest(
            _load(args.authority_index),
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.readable_manifest),
            _load(args.recovered_source_manifest),
            _load(args.clean_rebuild_report),
            _load(args.roundtrip_report),
            source_rewrite_acceptance=(
                _load(args.source_rewrite_acceptance)
                if args.source_rewrite_acceptance
                else None
            ),
        )
        write_recovery_release_manifest(manifest, args.out)
    except (
        RecoveryReleaseError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RECOVERY_RELEASE_MANIFEST_COMPLETE")
    print(f"release_id={manifest['release_id']}")
    print(
        "ready_for_release="
        + str(manifest["ready_for_release"]).lower()
    )
    print(f"blockers={len(manifest['blockers'])}")
    print(f"out={args.out}")
    return 0 if manifest["ready_for_release"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
