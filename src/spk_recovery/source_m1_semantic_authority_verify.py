from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from .semantic_review_authority import (
    SemanticReviewAuthorityError,
    build_semantic_review_authority_registry,
    verify_accepted_semantic_lineage,
)


EXPECTED_V308_SHA256 = (
    "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
)
EXPECTED_REVIEW_ID = "SEMREVIEW_DD69CD752A6E46181BAC"
EXPECTED_ACCEPTED_CLASSES = 32
EXPECTED_ACCEPTED_MEMBERS = 7
EXPECTED_ACCEPTED_TOTAL = 39


class SourceM1SemanticAuthorityError(ValueError):
    pass


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise SourceM1SemanticAuthorityError(
                f"duplicate JSON key: {key!r}"
            )
        out[key] = value
    return out


def _load(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_exact_object,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceM1SemanticAuthorityError(
            f"could not read JSON {path}: {exc}"
        ) from exc
    if not isinstance(doc, dict):
        raise SourceM1SemanticAuthorityError(
            f"JSON root must be an object: {path}"
        )
    return doc


def _require_exact_v308_lineage_authority(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
) -> None:
    if class_lineage.get("baseline_build_id") != "v308":
        raise SourceM1SemanticAuthorityError(
            "class lineage baseline is not v308"
        )
    builds = [
        row
        for row in class_lineage.get("builds", [])
        if isinstance(row, dict) and row.get("build_id") == "v308"
    ]
    if len(builds) != 1:
        raise SourceM1SemanticAuthorityError(
            "class lineage must contain exactly one v308 build"
        )
    if str(builds[0].get("sha256", "")).lower() != EXPECTED_V308_SHA256:
        raise SourceM1SemanticAuthorityError(
            "class lineage is not bound to exact v308"
        )
    if member_lineage.get("baseline_build_id") != "v308":
        raise SourceM1SemanticAuthorityError(
            "member lineage baseline is not v308"
        )
    if (
        str(member_lineage.get("source_sha256", "")).lower()
        != EXPECTED_V308_SHA256
    ):
        raise SourceM1SemanticAuthorityError(
            "member lineage is not bound to exact v308"
        )


def verify_v308_semantic_review_authority(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    review: dict[str, Any],
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    _require_exact_v308_lineage_authority(
        class_lineage,
        member_lineage,
    )

    if review.get("review_id") != EXPECTED_REVIEW_ID:
        raise SourceM1SemanticAuthorityError(
            "semantic review is not the canonical v308 R2 authority"
        )
    if review.get("source_build") != "v308":
        raise SourceM1SemanticAuthorityError(
            "semantic review source build is not v308"
        )
    if (
        str(review.get("source_sha256", "")).lower()
        != EXPECTED_V308_SHA256
    ):
        raise SourceM1SemanticAuthorityError(
            "semantic review is not bound to exact v308"
        )
    if review.get("proposal_count") != EXPECTED_ACCEPTED_TOTAL:
        raise SourceM1SemanticAuthorityError(
            "canonical v308 R2 review must contain exactly 39 proposals"
        )
    if acceptance.get("review_id") != EXPECTED_REVIEW_ID:
        raise SourceM1SemanticAuthorityError(
            "semantic acceptance is not bound to canonical v308 R2 review"
        )

    try:
        registry = build_semantic_review_authority_registry(
            [
                {
                    "review_set": review,
                    "acceptance_spec": acceptance,
                }
            ]
        )
        summary = verify_accepted_semantic_lineage(
            class_lineage,
            member_lineage,
            registry,
        )
    except SemanticReviewAuthorityError as exc:
        raise SourceM1SemanticAuthorityError(str(exc)) from exc

    expected = {
        "trusted_review_count": 1,
        "trusted_accepted_proposal_count": EXPECTED_ACCEPTED_TOTAL,
        "accepted_class_records": EXPECTED_ACCEPTED_CLASSES,
        "accepted_member_records": EXPECTED_ACCEPTED_MEMBERS,
        "accepted_records": EXPECTED_ACCEPTED_TOTAL,
        "verified_provenance_rows": EXPECTED_ACCEPTED_TOTAL,
        "used_review_ids": [EXPECTED_REVIEW_ID],
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise SourceM1SemanticAuthorityError(
                f"trusted semantic authority summary drifted at {key}: "
                f"{summary.get(key)!r} != {value!r}"
            )

    material = {
        "source_sha256": EXPECTED_V308_SHA256,
        "review_id": EXPECTED_REVIEW_ID,
        "registry_id": summary["registry_id"],
        **expected,
    }
    return {
        "schema_version": 1,
        "kind": "source_m1_semantic_review_authority_verification",
        **material,
        "verification_id": (
            "SOURCESEMAUTH_"
            + hashlib.sha256(_stable_json(material))
            .hexdigest()[:20]
            .upper()
        ),
        "verified": True,
    }


def _write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            doc,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-source-m1-semantic-authority-verify",
        description=(
            "Authenticate canonical exact-v308 accepted semantic lineage "
            "against the complete trusted R2 review + acceptance authority."
        ),
    )
    parser.add_argument("class_lineage", type=Path)
    parser.add_argument("member_lineage", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("acceptance", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        proof = verify_v308_semantic_review_authority(
            _load(args.class_lineage),
            _load(args.member_lineage),
            _load(args.review),
            _load(args.acceptance),
        )
    except SourceM1SemanticAuthorityError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    _write_json(proof, args.out)
    print("SPK_SOURCE_M1_SEMANTIC_AUTHORITY_PASS")
    print(f"verification_id={proof['verification_id']}")
    print(f"registry_id={proof['registry_id']}")
    print(f"review_id={proof['review_id']}")
    print(f"accepted_records={proof['accepted_records']}")
    print(
        "accepted_class_records="
        f"{proof['accepted_class_records']}"
    )
    print(
        "accepted_member_records="
        f"{proof['accepted_member_records']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
