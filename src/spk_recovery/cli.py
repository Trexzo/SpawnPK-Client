from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .indexer import index_jar, write_index
from .diffing import diff_indexes


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-recovery")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("index", help="Index and fingerprint a client JAR")
    pi.add_argument("jar", type=Path)
    pi.add_argument("--out", type=Path, required=True)
    pi.add_argument("--expect-sha256")

    pd = sub.add_parser("diff", help="Compare two previously generated indexes")
    pd.add_argument("old", type=Path)
    pd.add_argument("new", type=Path)
    pd.add_argument("--out", type=Path, required=True)

    args = p.parse_args(argv)
    if args.cmd == "index":
        idx = index_jar(args.jar)
        if args.expect_sha256 and idx["sha256"].lower() != args.expect_sha256.lower():
            print(f"REFUSED: SHA-256 {idx['sha256']} != expected {args.expect_sha256}", file=sys.stderr)
            return 2
        write_index(idx, args.out)
        print("SPK_RECOVERY_INDEX_PASS")
        print(f"sha256={idx['sha256']}")
        print(f"entries={idx['summary']['entry_count']}")
        print(f"classes={idx['summary']['class_count']}")
        print(f"rs_classes={idx['summary']['rs_class_count']}")
        print(f"parse_errors={idx['summary']['class_parse_error_count']}")
        print(f"out={args.out}")
        return 0
    if args.cmd == "diff":
        report = diff_indexes(_load(args.old), _load(args.new))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print("SPK_RECOVERY_DIFF_PASS")
        for k, v in report["summary"].items():
            print(f"{k}={v}")
        print(f"out={args.out}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
