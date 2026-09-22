from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lineage import load_lineage
from .member_lineage import load_member_lineage
from .source_symbols import (
    SourceSymbolInventoryError,
    build_source_symbol_inventory,
    write_source_symbol_inventory,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-symbols")
    p.add_argument("recovered_manifest", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("class_lineage", type=Path)
    p.add_argument("member_lineage", type=Path)
    p.add_argument("--build-id", required=True)
    p.add_argument(
        "--target-package",
        default="recovered/spawnpk/client",
    )
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        inventory = build_source_symbol_inventory(
            _load(args.recovered_manifest),
            args.source_root,
            load_lineage(args.class_lineage),
            load_member_lineage(args.member_lineage),
            build_id=args.build_id,
            target_package=args.target_package,
        )
        write_source_symbol_inventory(inventory, args.out)
    except (
        SourceSymbolInventoryError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RECOVERY_SOURCE_SYMBOLS_PASS")
    print(f"inventory_id={inventory['inventory_id']}")
    for key, value in inventory["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
