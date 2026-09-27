from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .namespace_alias_plan import (
    NamespaceAliasPlanError,
    build_namespace_alias_plan,
    write_namespace_alias_plan,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-namespace-alias-plan"
    )
    p.add_argument("readable_jar", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    args = p.parse_args(argv)

    try:
        report = build_namespace_alias_plan(
            args.readable_jar,
            include_identifiers=args.include_identifiers,
        )
        write_namespace_alias_plan(
            report,
            args.out,
        )
    except (
        NamespaceAliasPlanError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print("SPK_NAMESPACE_ALIAS_PLAN_PASS")
    print(f"plan_id={report['plan_id']}")
    print(
        "collision_node_count="
        f"{summary['collision_node_count']}"
    )
    print(
        "mapped_class_identity_count="
        f"{summary['mapped_class_identity_count']}"
    )
    print(
        "nested_class_count="
        f"{summary['nested_class_count']}"
    )
    print(
        "package_descendant_class_count="
        f"{summary['package_descendant_class_count']}"
    )
    print(
        f"identifiers_included={report['identifiers_included']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
