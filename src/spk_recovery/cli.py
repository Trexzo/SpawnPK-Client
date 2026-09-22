from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .indexer import index_jar, write_index
from .diffing import diff_indexes
from .lineage import LineageValidationError, load_lineage, seed_lineage, validate_lineage, write_lineage


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

    ps = sub.add_parser("lineage-seed", help="Create deterministic logical class IDs from an exact baseline index")
    ps.add_argument("index", type=Path)
    ps.add_argument("--build-id", required=True)
    ps.add_argument("--build-number", type=int)
    ps.add_argument("--authority", default="EXACT_CURRENT_CLIENT")
    ps.add_argument("--prefix", default="rs/")
    ps.add_argument("--out", type=Path, required=True)

    pv = sub.add_parser("lineage-validate", help="Validate a canonical logical-lineage document")
    pv.add_argument("lineage", type=Path)

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
    if args.cmd == "lineage-seed":
        try:
            doc = seed_lineage(
                _load(args.index),
                build_id=args.build_id,
                build_number=args.build_number,
                authority=args.authority,
                prefix=args.prefix,
            )
            write_lineage(doc, args.out)
        except LineageValidationError as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print("SPK_RECOVERY_LINEAGE_SEED_PASS")
        print(f"build_id={args.build_id}")
        print(f"logical_classes={len(doc['classes'])}")
        print(f"out={args.out}")
        return 0
    if args.cmd == "lineage-validate":
        try:
            summary = validate_lineage(load_lineage(args.lineage))
        except (LineageValidationError, json.JSONDecodeError) as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print("SPK_RECOVERY_LINEAGE_VALIDATE_PASS")
        for k, v in summary.items():
            print(f"{k}={v}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
