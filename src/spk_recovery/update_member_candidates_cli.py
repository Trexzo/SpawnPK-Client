from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from .matcher import match_classes
from .member_identity import build_member_identity_candidates


class UpdateMemberCandidatesError(ValueError):
    pass


_TRUSTED_AUTO_CLASS_STRATEGIES = {
    "exact_sha256",
    "structural_unique",
}


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateMemberCandidatesError(str(exc)) from exc
    if not isinstance(value, dict):
        raise UpdateMemberCandidatesError(
            f"expected JSON object: {path}"
        )
    return value


def _sha(value: Any, *, label: str) -> str:
    text = str(value or "").lower()
    if (
        len(text) != 64
        or any(ch not in "0123456789abcdef" for ch in text)
    ):
        raise UpdateMemberCandidatesError(
            f"{label} must be SHA-256 hex"
        )
    return text


def build_update_member_candidates(
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    intake_report: dict[str, Any],
    *,
    old_build_id: str,
    new_build_id: str,
    expected_migration_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        intake_report.get("schema_version") != 1
        or intake_report.get("kind") != "update_intake_report"
    ):
        raise UpdateMemberCandidatesError(
            "unsupported intake report schema/kind"
        )
    if intake_report.get("old_build_id") != old_build_id:
        raise UpdateMemberCandidatesError("intake old_build_id mismatch")
    if intake_report.get("new_build_id") != new_build_id:
        raise UpdateMemberCandidatesError("intake new_build_id mismatch")

    old_sha = _sha(old_index.get("sha256"), label="old index sha256")
    new_sha = _sha(new_index.get("sha256"), label="new index sha256")
    if _sha(
        intake_report.get("old_sha256"),
        label="intake old_sha256",
    ) != old_sha:
        raise UpdateMemberCandidatesError(
            "intake old SHA does not match old index"
        )
    if _sha(
        intake_report.get("new_sha256"),
        label="intake new_sha256",
    ) != new_sha:
        raise UpdateMemberCandidatesError(
            "intake new SHA does not match new index"
        )

    migration_id = intake_report.get("migration_id")
    if not isinstance(migration_id, str) or not migration_id:
        raise UpdateMemberCandidatesError(
            "intake migration_id must be non-empty"
        )
    if (
        expected_migration_id is not None
        and migration_id != expected_migration_id
    ):
        raise UpdateMemberCandidatesError("intake migration_id mismatch")

    scope_prefix = intake_report.get("scope_prefix", "rs/")
    if not isinstance(scope_prefix, str):
        raise UpdateMemberCandidatesError(
            "intake scope_prefix must be a string"
        )

    matcher = match_classes(
        old_index,
        new_index,
        prefix=scope_prefix,
    )
    trusted_matches: list[dict[str, Any]] = []
    review_only_matches: list[dict[str, Any]] = []
    for row in matcher.get("matches", []):
        if row.get("strategy") in _TRUSTED_AUTO_CLASS_STRATEGIES:
            trusted_matches.append(copy.deepcopy(row))
        else:
            review_only_matches.append(copy.deepcopy(row))

    candidates = build_member_identity_candidates(
        old_index,
        new_index,
        {"matches": trusted_matches},
    )
    candidates["migration_id"] = migration_id
    candidates["old_build_id"] = old_build_id
    candidates["new_build_id"] = new_build_id
    candidates["scope_prefix"] = scope_prefix
    candidates["class_match_authority"] = {
        "trusted_exact": sum(
            1
            for row in trusted_matches
            if row.get("strategy") == "exact_sha256"
        ),
        "trusted_structural": sum(
            1
            for row in trusted_matches
            if row.get("strategy") == "structural_unique"
        ),
        "review_only_matches": len(review_only_matches),
        "ambiguous_classes": len(matcher.get("ambiguous", [])),
        "unmatched_old_classes": len(matcher.get("unmatched_old", [])),
        "unmatched_new_classes": len(matcher.get("unmatched_new", [])),
    }

    return candidates, candidates["class_match_authority"]


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build fail-closed research member-identity candidates "
            "for one exact update intake."
        )
    )
    parser.add_argument("old_index", type=Path)
    parser.add_argument("new_index", type=Path)
    parser.add_argument("intake_report", type=Path)
    parser.add_argument("--old-build-id", required=True)
    parser.add_argument("--new-build-id", required=True)
    parser.add_argument("--expect-migration-id")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        candidates, class_summary = build_update_member_candidates(
            _load(args.old_index),
            _load(args.new_index),
            _load(args.intake_report),
            old_build_id=args.old_build_id,
            new_build_id=args.new_build_id,
            expected_migration_id=args.expect_migration_id,
        )
        _write(args.out, candidates)
    except UpdateMemberCandidatesError as exc:
        parser.error(str(exc))

    summary = candidates.get("summary", {})
    print("SPK_RECOVERY_UPDATE_MEMBER_CANDIDATES_PASS")
    print(f"migration_id={candidates['migration_id']}")
    print(f"old_sha256={candidates['old_sha256']}")
    print(f"new_sha256={candidates['new_sha256']}")
    for key in (
        "trusted_exact",
        "trusted_structural",
        "review_only_matches",
        "ambiguous_classes",
        "unmatched_old_classes",
        "unmatched_new_classes",
    ):
        print(f"{key}={class_summary.get(key, 0)}")
    for key in (
        "class_pairs",
        "method_old",
        "method_new",
        "method_matched",
        "method_renamed",
        "method_coverage",
        "field_old",
        "field_new",
        "field_matched",
        "field_renamed",
        "field_coverage",
    ):
        print(f"{key}={summary.get(key, 0)}")
    print(f"skipped_classes={len(candidates.get('skipped_classes', []))}")
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
