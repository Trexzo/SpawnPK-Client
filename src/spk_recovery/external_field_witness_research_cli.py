"""Private, no-overwrite runner for external canonical field-witness research."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from .external_field_witness_research import (
    ExternalWitnessError, build_external_field_witness_research,
)


def _read_pinned_json(path: Path, expected_sha256: str) -> dict:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest().lower() != expected_sha256.lower():
        raise ExternalWitnessError("AUTHORITY_JSON_SHA256_MISMATCH")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ExternalWitnessError("AUTHORITY_JSON_MUST_BE_OBJECT")
    return obj


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--class-lineage", required=True, type=Path)
    p.add_argument("--class-lineage-sha256", required=True)
    p.add_argument("--member-lineage", required=True, type=Path)
    p.add_argument("--member-lineage-sha256", required=True)
    p.add_argument("--old-index", required=True, type=Path)
    p.add_argument("--new-index", required=True, type=Path)
    p.add_argument("--old-jar", required=True, type=Path)
    p.add_argument("--new-jar", required=True, type=Path)
    p.add_argument("--old-build-id", required=True)
    p.add_argument("--new-build-id", required=True)
    p.add_argument("--class-id", required=True)
    p.add_argument("--min-independent-methods", type=int, default=2)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        if args.out.exists():
            raise ExternalWitnessError("OUTPUT_EXISTS_NO_OVERWRITE")
        class_lineage = _read_pinned_json(args.class_lineage, args.class_lineage_sha256)
        member_lineage = _read_pinned_json(args.member_lineage, args.member_lineage_sha256)
        old_index = json.loads(args.old_index.read_text(encoding="utf-8"))
        new_index = json.loads(args.new_index.read_text(encoding="utf-8"))
        report = build_external_field_witness_research(
            class_lineage, member_lineage, old_index, new_index,
            args.old_jar, args.new_jar,
            old_build_id=args.old_build_id, new_build_id=args.new_build_id,
            logical_class_id=args.class_id,
            min_independent_methods=args.min_independent_methods,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
            f.write("\n")
    except (ExternalWitnessError, ValueError, KeyError, OSError, json.JSONDecodeError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    print("EXTERNAL_FIELD_WITNESS_RESEARCH_PASS")
    print(f"report_id={report['report_id']}")
    print(f"reviewable={sum(c['status'] == 'REVIEWABLE_EXTERNAL_ANCHORS' for c in report['candidates'])}")
    print(f"accepted_identities={report['accepted_identities']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
