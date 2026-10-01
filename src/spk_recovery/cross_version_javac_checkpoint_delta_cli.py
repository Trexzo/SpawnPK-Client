from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .cross_version_javac_checkpoint_delta import (
    CrossVersionJavacCheckpointDeltaError,
    build_cross_version_javac_checkpoint_delta,
    write_cross_version_javac_checkpoint_delta,
)


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CrossVersionJavacCheckpointDeltaError(
            f"failed to read JSON {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise CrossVersionJavacCheckpointDeltaError(
            f"expected JSON object: {path}"
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two verified public-safe cross-version javac checkpoints "
            "and emit one deterministic aggregate progress delta."
        )
    )
    parser.add_argument("baseline_checkpoint", type=Path)
    parser.add_argument("current_checkpoint", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        report = build_cross_version_javac_checkpoint_delta(
            _load(args.baseline_checkpoint),
            _load(args.current_checkpoint),
        )
        write_cross_version_javac_checkpoint_delta(report, args.out)
    except CrossVersionJavacCheckpointDeltaError as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "delta_id": report["delta_id"],
                "baseline_checkpoint_id": report[
                    "baseline_checkpoint_id"
                ],
                "current_checkpoint_id": report[
                    "current_checkpoint_id"
                ],
                "baseline_tooling_commit": report[
                    "baseline_tooling_commit"
                ],
                "current_tooling_commit": report[
                    "current_tooling_commit"
                ],
                "old_total_errors_delta": report["scalar_delta"][
                    "old_total_errors"
                ],
                "new_total_errors_delta": report["scalar_delta"][
                    "new_total_errors"
                ],
                "exact_frontier_equality_transition": report[
                    "exact_frontier_equality_transition"
                ],
                "identifiers_included": report["identifiers_included"],
                "out": str(args.out),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
