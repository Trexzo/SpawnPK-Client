from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .progressive_compile import (
    ProgressiveCompileError,
    progressive_compile,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-progressive-compile")
    p.add_argument("recovered_manifest", type=Path)
    p.add_argument("source_readiness", type=Path)
    p.add_argument("readable_manifest", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("build_authority", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("--javac-command", default="javac")
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = progressive_compile(
            _load(args.recovered_manifest),
            _load(args.source_readiness),
            _load(args.readable_manifest),
            args.readable_jar,
            _load(args.build_authority),
            args.source_root,
            out_dir=args.out_dir,
            javac_command=args.javac_command,
            batch_size=args.batch_size,
        )
    except (
        ProgressiveCompileError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_PROGRESSIVE_COMPILE_PASS")
    print(f"run_id={report['run_id']}")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"out_dir={args.out_dir.resolve()}")
    return 0 if report["summary"]["full_source_compile_ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
