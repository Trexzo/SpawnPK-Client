from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .source_readiness import (
    SourceReadinessError,
    audit_source_workspace,
    write_source_readiness_report,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-readiness")
    p.add_argument("recovered_manifest", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = audit_source_workspace(
            _load(args.recovered_manifest),
            args.source_root,
        )
        write_source_readiness_report(report, args.out)
    except (
        SourceReadinessError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_SOURCE_READINESS_PASS")
    print(f"audit_id={report['audit_id']}")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0 if report["summary"]["static_readiness_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
