from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .source_name_acceptance import (
    SourceNameAcceptanceError,
    build_source_rename_plan,
    write_source_rename_plan,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-name-plan")
    p.add_argument("inventory", type=Path)
    p.add_argument("review", type=Path)
    p.add_argument("acceptance", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        plan = build_source_rename_plan(
            _load(args.inventory),
            _load(args.review),
            _load(args.acceptance),
        )
        write_source_rename_plan(plan, args.out)
    except (
        SourceNameAcceptanceError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RECOVERY_SOURCE_NAME_PLAN_PASS")
    print(f"plan_id={plan['plan_id']}")
    print(f"accepted_proposals={plan['accepted_proposal_count']}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
