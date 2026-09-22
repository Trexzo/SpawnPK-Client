from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .source_rewrite import (
    SourceRewriteError,
    rewrite_source_workspace,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-rewrite")
    p.add_argument("plan", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument(
        "--classpath",
        action="append",
        type=Path,
        default=[],
        help="Repeat for dependency JAR/directories required by javac semantic analysis.",
    )
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        manifest = rewrite_source_workspace(
            _load(args.plan),
            args.source_root,
            out_dir=args.out_dir,
            classpath=args.classpath,
        )
    except (
        SourceRewriteError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RECOVERY_SOURCE_REWRITE_PASS")
    print(f"rewrite_id={manifest['rewrite_id']}")
    print(f"accepted_renames={manifest['accepted_rename_count']}")
    print(f"files_changed={manifest['files_changed']}")
    print(f"identifier_replacements={manifest['identifier_replacements']}")
    print(f"input_sha256={manifest['input_source_tree_sha256']}")
    print(f"output_sha256={manifest['output_source_tree_sha256']}")
    print(f"out_dir={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
