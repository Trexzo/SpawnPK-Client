from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .source_rewrite_acceptance import (
    SourceRewriteAcceptanceError,
    accept_rewritten_source,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-rewrite-accept")
    p.add_argument("recovered_manifest", type=Path)
    p.add_argument("rewrite_manifest", type=Path)
    p.add_argument("rewritten_source_root", type=Path)
    p.add_argument("source_authority_jar", type=Path)
    p.add_argument("source_authority_index", type=Path)
    p.add_argument("readable_manifest", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("--class-prefix", default="rs/")
    p.add_argument(
        "--source-prefix",
        action="append",
        dest="source_prefixes",
    )
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = accept_rewritten_source(
            _load(args.recovered_manifest),
            _load(args.rewrite_manifest),
            args.rewritten_source_root,
            args.source_authority_jar,
            _load(args.source_authority_index),
            _load(args.readable_manifest),
            args.readable_jar,
            out_dir=args.out_dir,
            class_prefix=args.class_prefix,
            source_prefixes=args.source_prefixes,
        )
    except (
        SourceRewriteAcceptanceError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RECOVERY_SOURCE_REWRITE_ACCEPTANCE_COMPLETE")
    print(f"acceptance_id={report['acceptance_id']}")
    print(f"accepted={str(report['accepted']).lower()}")
    print(
        "clean_project_build="
        + str(report["clean_rebuild"]["clean_project_build"]).lower()
    )
    print(
        "project_binary_fallback_count="
        + str(
            report["clean_rebuild"][
                "project_binary_fallback_count"
            ]
        )
    )
    if report["roundtrip"] is not None:
        print(
            "roundtrip_ready="
            + str(report["roundtrip"]["ready"]).lower()
        )
        print(
            "semantic_surface_blockers="
            + str(
                report["roundtrip"][
                    "semantic_surface_blockers"
                ]
            )
        )
    print(f"out_dir={args.out_dir}")
    return 0 if report["accepted"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
