from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .namespace_remap_boundary import (
    NamespaceRemapBoundaryError,
    build_namespace_remap_boundary,
    write_namespace_remap_boundary,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-namespace-remap-boundary"
    )
    p.add_argument("private_graph", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = p.parse_args(argv)

    try:
        graph = json.loads(
            args.private_graph.read_text(encoding="utf-8")
        )
        report = build_namespace_remap_boundary(
            graph,
            args.readable_jar,
            include_identifiers=args.include_identifiers,
        )
        write_namespace_remap_boundary(
            report,
            args.out,
        )
    except (
        NamespaceRemapBoundaryError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_NAMESPACE_REMAP_BOUNDARY_PASS")
    print(f"boundary_id={report['boundary_id']}")
    print(
        "collision_node_count="
        f"{summary['collision_node_count']}"
    )
    print(
        "affected_candidate_count="
        f"{summary['affected_candidate_count']}"
    )
    print(
        "automatic_strategy_selection_count="
        f"{summary['automatic_strategy_selection_count']}"
    )
    print(
        "all_nodes_review_required="
        f"{summary['all_nodes_review_required']}"
    )
    print(
        f"identifiers_included={report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
