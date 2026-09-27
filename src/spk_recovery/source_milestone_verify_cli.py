from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .source_milestone_verify import (
    SourceMilestoneVerificationError,
    verify_source_milestone,
    write_source_milestone_verification,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-milestone-verify")
    p.add_argument("milestone_manifest", type=Path)
    p.add_argument("authority_index", type=Path)
    p.add_argument("readable_manifest", type=Path)
    p.add_argument("recovered_manifest", type=Path)
    p.add_argument("clean_rebuild_report", type=Path)
    p.add_argument("--authority-commit", required=True)
    p.add_argument("--source-root", type=Path)
    p.add_argument("--export-root", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = verify_source_milestone(
            _load(args.milestone_manifest),
            _load(args.authority_index),
            _load(args.readable_manifest),
            _load(args.recovered_manifest),
            _load(args.clean_rebuild_report),
            authority_commit=args.authority_commit,
            source_root=args.source_root,
            exported_repository_root=args.export_root,
        )
        write_source_milestone_verification(report, args.out)
    except (
        SourceMilestoneVerificationError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_SOURCE_MILESTONE_VERIFY_COMPLETE")
    print(f"verification_id={report['verification_id']}")
    print(f"verified={str(report['verified']).lower()}")
    print(f"publishable={str(report['publishable']).lower()}")
    print(f"failed_checks={report['failed_check_count']}")
    print(f"out={args.out}")
    return 0 if report["publishable"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
