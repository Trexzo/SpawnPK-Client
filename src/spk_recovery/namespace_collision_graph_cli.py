from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .namespace_collision_graph import (
    NamespaceCollisionError,
    build_namespace_collision_graph,
    write_namespace_collision_graph,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-namespace-collision-graph"
    )
    p.add_argument("private_plan", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = p.parse_args(argv)

    try:
        plan = json.loads(
            args.private_plan.read_text(encoding="utf-8")
        )
        report = build_namespace_collision_graph(
            plan,
            args.readable_jar,
            include_identifiers=args.include_identifiers,
        )
        write_namespace_collision_graph(
            report,
            args.out,
        )
    except (
        NamespaceCollisionError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_NAMESPACE_COLLISION_GRAPH_PASS")
    print(f"graph_id={report['graph_id']}")
    print(
        "readable_class_count="
        f"{summary['readable_class_count']}"
    )
    print(
        "global_collision_node_count="
        f"{summary['global_collision_node_count']}"
    )
    print(
        "candidate_count="
        f"{summary['candidate_count']}"
    )
    print(
        "candidate_collision_count="
        f"{summary['candidate_collision_count']}"
    )
    print(
        "candidate_ancestor_collision_count="
        f"{summary['candidate_ancestor_collision_count']}"
    )
    print(
        "candidate_descendant_collision_count="
        f"{summary['candidate_descendant_collision_count']}"
    )
    print(
        "relation_counts="
        + json.dumps(
            summary["relation_counts"],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print(
        f"identifiers_included={report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
