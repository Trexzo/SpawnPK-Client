from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .build_authority import (
    BuildAuthorityError,
    build_build_authority,
    write_build_authority,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-build-authority")
    p.add_argument("source_jar", type=Path)
    p.add_argument("source_index", type=Path)
    p.add_argument("--source-readiness", type=Path)
    p.add_argument("--class-prefix", default="rs/")
    p.add_argument("--java-command", default="java")
    p.add_argument("--javac-command", default="javac")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        manifest = build_build_authority(
            args.source_jar,
            _load(args.source_index),
            source_readiness=(
                _load(args.source_readiness)
                if args.source_readiness
                else None
            ),
            class_prefix=args.class_prefix,
            java_command=args.java_command,
            javac_command=args.javac_command,
        )
        write_build_authority(manifest, args.out)
    except (
        BuildAuthorityError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_BUILD_AUTHORITY_PASS")
    print(f"authority_id={manifest['authority_id']}")
    print(f"source_sha256={manifest['source_sha256']}")
    print(
        "dominant_java_release="
        f"{manifest['bytecode']['dominant_java_release']}"
    )
    print(
        "embedded_maven_metadata="
        f"{len(manifest['embedded_maven_metadata'])}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
