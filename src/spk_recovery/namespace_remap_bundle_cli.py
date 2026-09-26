from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .namespace_remap_bundle import (
    NamespaceRemapBundleError,
    build_namespace_remap_bundle_plan,
    mapping_tsv,
    write_bundle_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-namespace-remap-bundle"
    )
    parser.add_argument("private_collision_proof", type=Path)
    parser.add_argument("impact_plan", type=Path)
    parser.add_argument("readable_jar", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
    )
    parser.add_argument("--mapping-out", type=Path)
    args = parser.parse_args(argv)

    try:
        proof = json.loads(
            args.private_collision_proof.read_text(
                encoding="utf-8"
            )
        )
        impact = json.loads(
            args.impact_plan.read_text(encoding="utf-8")
        )
        plan = build_namespace_remap_bundle_plan(
            proof,
            impact,
            args.readable_jar,
            include_identifiers=args.include_identifiers,
        )
        write_bundle_plan(plan, args.out)

        if args.mapping_out is not None:
            if not args.include_identifiers:
                raise NamespaceRemapBundleError(
                    "--mapping-out requires --include-identifiers"
                )
            args.mapping_out.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            args.mapping_out.write_text(
                mapping_tsv(plan),
                encoding="utf-8",
            )
    except (
        NamespaceRemapBundleError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_NAMESPACE_REMAP_BUNDLE_PASS")
    print(f"bundle_plan_id={plan['bundle_plan_id']}")
    print(f"class_mapping_count={plan['class_mapping_count']}")
    print(
        "rewrite_class_name_strings="
        f"{plan['rewrite_class_name_strings']}"
    )
    print(
        "identifiers_included="
        f"{plan['identifiers_included']}"
    )
    print(f"out={args.out}")
    if args.mapping_out is not None:
        print(f"mapping_out={args.mapping_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
