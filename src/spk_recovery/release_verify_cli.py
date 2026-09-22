from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lineage import load_lineage
from .member_lineage import load_member_lineage
from .release_verify import (
    RecoveryReleaseVerificationError,
    verify_recovery_release,
    write_recovery_release_verification,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-release-verify")
    p.add_argument("release_manifest", type=Path)
    p.add_argument("authority_index", type=Path)
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("readable_manifest", type=Path)
    p.add_argument("recovered_source_manifest", type=Path)
    p.add_argument("clean_rebuild_report", type=Path)
    p.add_argument("roundtrip_report", type=Path)
    p.add_argument("--source-rewrite-acceptance", type=Path)
    p.add_argument("--authority-jar", type=Path)
    p.add_argument("--readable-jar", type=Path)
    p.add_argument("--decompiler-jar", type=Path)
    p.add_argument("--source-root", type=Path)
    p.add_argument("--javac")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = verify_recovery_release(
            _load(args.release_manifest),
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
            authority_jar=args.authority_jar,
            readable_jar=args.readable_jar,
            decompiler_jar=args.decompiler_jar,
            source_root=args.source_root,
            javac_command=args.javac,
        )
        write_recovery_release_verification(
            report,
            args.out,
        )
    except (
        RecoveryReleaseVerificationError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RECOVERY_RELEASE_VERIFY_COMPLETE")
    print(f"verification_id={report['verification_id']}")
    print(f"release_ready={str(report['release_ready']).lower()}")
    print(f"verified={str(report['verified']).lower()}")
    print(
        "failed_required_checks="
        + str(report["failed_required_check_count"])
    )
    print(f"out={args.out}")
    return 0 if report["verified"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
