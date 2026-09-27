from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .source_milestone import (
    SourceMilestoneError,
    build_source_milestone_manifest,
    write_source_milestone_manifest,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-milestone")
    p.add_argument("authority_index", type=Path)
    p.add_argument("readable_manifest", type=Path)
    p.add_argument("recovered_manifest", type=Path)
    p.add_argument("clean_rebuild_report", type=Path)
    p.add_argument("--authority-commit", required=True)
    p.add_argument("--expected-build-id", default="v308")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        manifest = build_source_milestone_manifest(
            _load(args.authority_index),
            _load(args.readable_manifest),
            _load(args.recovered_manifest),
            _load(args.clean_rebuild_report),
            authority_commit=args.authority_commit,
            expected_build_id=args.expected_build_id,
        )
        write_source_milestone_manifest(manifest, args.out)
    except (
        SourceMilestoneError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_SOURCE_MILESTONE_COMPLETE")
    print(f"milestone_id={manifest['milestone_id']}")
    print(f"publishable={str(manifest['publishable']).lower()}")
    print(
        "source_tree_sha256="
        + manifest["source"]["source_tree_sha256"]
    )
    print(
        "expected_project_classes="
        + str(manifest["project_class_set"]["expected_count"])
    )
    print(
        "generated_project_classes="
        + str(manifest["project_class_set"]["generated_count"])
    )
    print(
        "project_binary_fallback="
        + str(manifest["project_class_set"]["binary_fallback_count"])
    )
    print(
        "authority_commit="
        + manifest["provenance"][
            "spawnpk_client_authority_commit"
        ]
    )
    print(f"out={args.out}")
    return 0 if manifest["publishable"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
