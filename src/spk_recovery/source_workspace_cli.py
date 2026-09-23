from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .source_workspace import SourceWorkspaceError, build_source_workspace


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-workspace")
    p.add_argument("readable_manifest", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("decompiler_jar", type=Path)
    p.add_argument("--decompiler-sha256", required=True)
    p.add_argument("--engine", choices=["cfr", "vineflower", "procyon"], required=True)
    p.add_argument("--project-only", action="store_true")
    p.add_argument("--resume-project-only", action="store_true")
    p.add_argument("--project-batch-size", type=int, default=5)
    p.add_argument("--max-batches-per-run", type=int)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        manifest = build_source_workspace(
            _load(args.readable_manifest),
            args.readable_jar,
            args.decompiler_jar,
            expected_decompiler_sha256=args.decompiler_sha256,
            engine=args.engine,
            out_dir=args.out_dir,
            project_only=args.project_only,
            resume_project_only=args.resume_project_only,
            project_batch_size=args.project_batch_size,
            max_batches_per_run=args.max_batches_per_run,
        )
    except (
        SourceWorkspaceError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    if manifest.get("kind") == "project_source_resume_checkpoint":
        print("SPK_SOURCE_WORKSPACE_INCOMPLETE")
        print(f"checkpoint_id={manifest['checkpoint_id']}")
        print(f"completed_batches={len(manifest['completed_batches'])}")
        print(f"batch_count={manifest['material']['batch_count']}")
        print(f"out_dir={args.out_dir.resolve()}")
        return 3

    print("SPK_SOURCE_WORKSPACE_PASS")
    print(f"workspace_id={manifest['workspace_id']}")
    print(f"namespace_id={manifest['namespace_id']}")
    print(f"engine={manifest['engine']}")
    print(f"java_file_count={manifest['java_file_count']}")
    print(f"source_tree_sha256={manifest['source_tree_sha256']}")
    print(f"out_dir={args.out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
