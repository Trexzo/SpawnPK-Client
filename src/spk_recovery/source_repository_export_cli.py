from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .source_repository_export import (
    SourceRepositoryExportError,
    export_source_repository,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-export")
    p.add_argument("milestone_manifest", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("out_dir", type=Path)
    args = p.parse_args(argv)

    try:
        milestone = json.loads(
            args.milestone_manifest.read_text(encoding="utf-8")
        )
        report = export_source_repository(
            milestone,
            args.source_root,
            args.out_dir,
        )
    except (
        SourceRepositoryExportError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_SOURCE_EXPORT_COMPLETE")
    print(f"export_id={report['export_id']}")
    print(f"publishable={str(report['publishable']).lower()}")
    print(f"source_tree_sha256={report['source_tree_sha256']}")
    print(f"java_file_count={report['java_file_count']}")
    print(f"authority_commit={report['authority_commit']}")
    print(f"out={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
