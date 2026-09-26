from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .namespace_collision_proof import (
    NamespaceCollisionProofError,
    prove_namespace_collisions,
    write_namespace_collision_proof,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-namespace-collision-proof"
    )
    parser.add_argument("private_plan", type=Path)
    parser.add_argument("readable_jar", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = parser.parse_args(argv)

    try:
        plan = json.loads(
            args.private_plan.read_text(encoding="utf-8")
        )
        report = prove_namespace_collisions(
            plan,
            args.readable_jar,
            include_identifiers=args.include_identifiers,
        )
        write_namespace_collision_proof(report, args.out)
    except (
        NamespaceCollisionProofError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_NAMESPACE_COLLISION_PROOF_PASS")
    print(f"proof_id={report['proof_id']}")
    print(
        "candidate_count="
        f"{summary['candidate_count']}"
    )
    print(
        "collision_proven_candidate_count="
        f"{summary['collision_proven_candidate_count']}"
    )
    print(
        "collision_unproven_candidate_count="
        f"{summary['collision_unproven_candidate_count']}"
    )
    print(
        "candidate_collision_node_count="
        f"{summary['candidate_collision_node_count']}"
    )
    print(
        "candidate_collision_depths="
        + json.dumps(
            summary["candidate_collision_depths"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        "planned_colliding_class_rename_count="
        f"{summary['planned_colliding_class_rename_count']}"
    )
    print(
        "identifiers_included="
        f"{report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
