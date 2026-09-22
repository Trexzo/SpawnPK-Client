from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lineage import load_lineage
from .member_lineage import load_member_lineage
from .semantic_namespace import (
    SemanticNamespaceError,
    build_semantic_namespace,
    write_json,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-semantic-namespace")
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("index", type=Path)
    p.add_argument("--build-id", required=True)
    p.add_argument(
        "--target-package",
        default="recovered/spawnpk/client",
    )
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        manifest, class_plan, member_plan = build_semantic_namespace(
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.index),
            build_id=args.build_id,
            target_package=args.target_package,
        )
        out = args.out_dir.resolve()
        write_json(manifest, out / "semantic-namespace.json")
        write_json(class_plan, out / "class-remap-plan.json")
        write_json(member_plan, out / "member-remap-plan.json")
    except (
        SemanticNamespaceError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_SEMANTIC_NAMESPACE_PASS")
    print(f"namespace_id={manifest['namespace_id']}")
    for key, value in manifest["summary"].items():
        print(f"{key}={value}")
    print(f"out_dir={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
