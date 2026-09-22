from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .source_name_review import (
    SourceNameCandidateError,
    resolve_source_name_candidates,
    write_source_name_review,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-name-review")
    p.add_argument("inventory", type=Path)
    p.add_argument("candidates", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        review = resolve_source_name_candidates(
            _load(args.inventory),
            _load(args.candidates),
        )
        write_source_name_review(review, args.out)
    except (
        SourceNameCandidateError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_RECOVERY_SOURCE_NAME_REVIEW_PASS")
    print(f"review_id={review['review_id']}")
    for key, value in review["summary"].items():
        print(f"{key}={value}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
