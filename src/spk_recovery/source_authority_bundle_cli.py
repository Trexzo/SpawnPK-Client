from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .source_authority_bundle import (
    SourceAuthorityBundleError,
    build_source_authority_bundle,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-authority-bundle")
    p.add_argument("authority_index", type=Path)
    p.add_argument("readable_manifest", type=Path)
    p.add_argument("recovered_manifest", type=Path)
    p.add_argument("clean_rebuild_report", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("out_dir", type=Path)
    args = p.parse_args(argv)

    try:
        report = build_source_authority_bundle(
            _load(args.authority_index),
            _load(args.readable_manifest),
            _load(args.recovered_manifest),
            _load(args.clean_rebuild_report),
            args.source_root,
            args.out_dir,
        )
    except (
        SourceAuthorityBundleError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_SOURCE_AUTHORITY_BUNDLE_COMPLETE")
    print(f"bundle_id={report['bundle_id']}")
    print(f"source_tree_sha256={report['source_tree_sha256']}")
    print(f"java_file_count={report['java_file_count']}")
    print(f"out={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
