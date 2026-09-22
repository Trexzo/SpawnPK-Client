from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lineage import load_lineage
from .member_lineage import load_member_lineage
from .semantic_carryforward import (
    SemanticCarryForwardError,
    build_semantic_carryforward,
    write_json,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-semantic-carry-forward")
    p.add_argument("previous_authority", type=Path)
    p.add_argument("new_authority", type=Path)
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("new_index", type=Path)
    p.add_argument("--target-package", default="recovered/spawnpk/client")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report, namespace, class_plan, member_plan = build_semantic_carryforward(
            _load(args.previous_authority),
            _load(args.new_authority),
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            _load(args.new_index),
            target_package=args.target_package,
        )
        out = args.out_dir.resolve()
        write_json(report, out / "semantic-carryforward.json")
        write_json(namespace, out / "semantic-namespace.json")
        write_json(class_plan, out / "class-remap-plan.json")
        write_json(member_plan, out / "member-remap-plan.json")
    except (
        SemanticCarryForwardError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_SEMANTIC_CARRY_FORWARD_PASS")
    print(f"report_id={report['report_id']}")
    print(f"namespace_id={report['namespace_id']}")
    print(f"ready_for_readable_build={str(report['ready_for_readable_build']).lower()}")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"out_dir={out}")
    return 0 if report["ready_for_readable_build"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
