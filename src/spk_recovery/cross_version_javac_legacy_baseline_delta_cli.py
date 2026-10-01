from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .cross_version_javac_legacy_baseline_delta import (
    CrossVersionJavacLegacyBaselineDeltaError,
    build_cross_version_javac_legacy_baseline_delta,
    write_cross_version_javac_legacy_baseline_delta,
)


def _exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise CrossVersionJavacLegacyBaselineDeltaError(
                f"duplicate JSON key: {key!r}"
            )
        out[key] = value
    return out


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_exact_object,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise CrossVersionJavacLegacyBaselineDeltaError(
            f"failed to read JSON {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise CrossVersionJavacLegacyBaselineDeltaError(
            f"expected JSON object: {path}"
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare the canonical pre-checkpoint v307/v308 350-error "
            "baseline fixture with one verified modern javac checkpoint."
        )
    )
    parser.add_argument("legacy_baseline", type=Path)
    parser.add_argument("current_checkpoint", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        report = build_cross_version_javac_legacy_baseline_delta(
            _load(args.legacy_baseline),
            _load(args.current_checkpoint),
        )
        write_cross_version_javac_legacy_baseline_delta(report, args.out)
    except CrossVersionJavacLegacyBaselineDeltaError as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "delta_id": report["delta_id"],
                "baseline_fixture_id": report["baseline_fixture_id"],
                "current_checkpoint_id": report["current_checkpoint_id"],
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
