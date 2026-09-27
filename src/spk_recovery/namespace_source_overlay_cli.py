from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .namespace_source_overlay import (
    NamespaceSourceOverlayError,
    build_namespace_source_overlay,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-namespace-source-overlay"
    )
    p.add_argument("private_alias_plan", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        plan = json.loads(
            args.private_alias_plan.read_text(encoding="utf-8")
        )
        report = build_namespace_source_overlay(
            plan,
            args.source_root,
            args.out_dir,
        )
        args.manifest.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.manifest.write_text(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except (
        NamespaceSourceOverlayError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_NAMESPACE_SOURCE_OVERLAY_PASS")
    print(f"overlay_id={report['overlay_id']}")
    print(
        "changed_file_count="
        f"{report['changed_file_count']}"
    )
    print(
        "replacement_count="
        f"{report['replacement_count']}"
    )
    print(
        "rewritten_import_count="
        f"{report['rewritten_import_count']}"
    )
    print(
        "rewritten_qualified_count="
        f"{report['rewritten_qualified_count']}"
    )
    print(
        "canonical_source_modified="
        f"{report['canonical_source_modified']}"
    )
    print(f"manifest={args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
