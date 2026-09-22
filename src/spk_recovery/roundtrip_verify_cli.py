from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .roundtrip_verify import (
    RoundTripVerificationError,
    verify_clean_round_trip,
    write_roundtrip_report,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-roundtrip-verify")
    p.add_argument("clean_rebuild_report", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("rebuilt_jar", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = verify_clean_round_trip(
            _load(args.clean_rebuild_report),
            args.readable_jar,
            args.rebuilt_jar,
        )
        write_roundtrip_report(report, args.out)
    except (
        RoundTripVerificationError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RECOVERY_ROUNDTRIP_VERIFY_PASS")
    print(f"verification_id={report['verification_id']}")
    print(
        "candidate_ready="
        + str(report["rebuild_authority_candidate"]["ready"]).lower()
    )
    for key, value in report["comparison"]["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
