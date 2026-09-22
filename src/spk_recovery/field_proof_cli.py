from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .field_proof import (
    FieldProofError,
    prove_and_apply_fields,
    write_json,
)
from .lineage import load_lineage, LineageValidationError
from .member_lineage import (
    load_member_lineage,
    write_member_lineage,
    MemberLineageError,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-field-proof-transfer")
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("old_index", type=Path)
    p.add_argument("new_index", type=Path)
    p.add_argument("old_jar", type=Path)
    p.add_argument("new_jar", type=Path)
    p.add_argument("--old-build-id", required=True)
    p.add_argument("--new-build-id", required=True)
    p.add_argument("--min-observations", type=int, default=2)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--proof-out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        member_out, proof, summary = prove_and_apply_fields(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.old_index),
            _load(args.new_index),
            args.old_jar,
            args.new_jar,
            old_build_id=args.old_build_id,
            new_build_id=args.new_build_id,
            min_observations=args.min_observations,
        )
        write_member_lineage(member_out, args.out)
        write_json(proof, args.proof_out)
    except (
        FieldProofError,
        MemberLineageError,
        LineageValidationError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_FIELD_PROOF_TRANSFER_PASS")
    print(f"report_id={proof['report_id']}")
    print(f"proofs={summary['proofs']}")
    print(f"applied_fields={summary['applied_fields']}")
    print(f"already_present={summary['already_present']}")
    print(f"unresolved_removed={summary['unresolved_removed']}")
    print(f"remaining_unresolved={summary['remaining_unresolved']}")
    print(f"out={args.out}")
    print(f"proof_out={args.proof_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
