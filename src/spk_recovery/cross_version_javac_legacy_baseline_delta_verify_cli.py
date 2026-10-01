from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .cross_version_javac_legacy_baseline_delta import (
    CrossVersionJavacLegacyBaselineDeltaError,
    verify_cross_version_javac_legacy_baseline_delta,
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
            "Independently verify one emitted legacy javac baseline delta "
            "against its canonical baseline and current checkpoint inputs."
        )
    )
    parser.add_argument("legacy_baseline", type=Path)
    parser.add_argument("current_checkpoint", type=Path)
    parser.add_argument("delta_report", type=Path)
    args = parser.parse_args()

    try:
        report = verify_cross_version_javac_legacy_baseline_delta(
            _load(args.legacy_baseline),
            _load(args.current_checkpoint),
            _load(args.delta_report),
        )
    except CrossVersionJavacLegacyBaselineDeltaError as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "delta_id": report["delta_id"],
                "baseline_fixture_id": report["baseline_fixture_id"],
                "current_checkpoint_id": report["current_checkpoint_id"],
                "identifiers_included": report["identifiers_included"],
                "verified": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
