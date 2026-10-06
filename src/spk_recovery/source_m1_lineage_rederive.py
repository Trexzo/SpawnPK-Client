from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .lineage import seed_lineage, validate_lineage, write_lineage
from .member_lineage import (
    seed_member_lineage,
    validate_member_lineage,
    write_member_lineage,
)
from .semantic_review import accept_semantic_proposals


EXPECTED_V308_SHA256 = (
    "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
)
EXPECTED_REVIEW_ID = "SEMREVIEW_DD69CD752A6E46181BAC"
EXPECTED_ACCEPTED_CLASSES = 32
EXPECTED_ACCEPTED_MEMBERS = 7
EXPECTED_ACCEPTED_TOTAL = 39
EXPECTED_CLASS_COUNT = 1129
EXPECTED_MEMBER_COUNT = 13811

HISTORICAL_MEMBER_ANCHORS = {
    ("rs/Client", "do", "[Lrs/a/k;"): "CLIENT_FIELD_000367",
    ("rs/Client", "if", "Ljava/util/Map;"): "CLIENT_FIELD_000552",
    ("rs/n/c/d/a", "do", "Lrs/n/d/c;"): "CLIENT_FIELD_005256",
}


class SourceM1LineageRederiveError(ValueError):
    pass


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceM1LineageRederiveError(
            f"could not read JSON {path}: {exc}"
        ) from exc
    if not isinstance(doc, dict):
        raise SourceM1LineageRederiveError(
            f"JSON root must be an object: {path}"
        )
    return doc


def _proposal_projection(
    review: dict[str, Any],
    acceptance: dict[str, Any],
) -> list[dict[str, Any]]:
    if review.get("review_id") != EXPECTED_REVIEW_ID:
        raise SourceM1LineageRederiveError(
            "review is not the canonical v308 R2 review"
        )
    if acceptance.get("review_id") != EXPECTED_REVIEW_ID:
        raise SourceM1LineageRederiveError(
            "acceptance is not bound to the canonical v308 R2 review"
        )

    proposals = review.get("proposals")
    accepted_ids = acceptance.get("accept")
    if not isinstance(proposals, list) or not isinstance(accepted_ids, list):
        raise SourceM1LineageRederiveError(
            "review proposals and acceptance list must be arrays"
        )
    if len(accepted_ids) != EXPECTED_ACCEPTED_TOTAL:
        raise SourceM1LineageRederiveError(
            f"canonical acceptance must contain {EXPECTED_ACCEPTED_TOTAL} proposals"
        )

    by_id = {
        row.get("proposal_id"): row
        for row in proposals
        if isinstance(row, dict)
    }
    if set(accepted_ids) != set(by_id):
        raise SourceM1LineageRederiveError(
            "canonical acceptance must equal the complete R2 proposal set"
        )

    rows: list[dict[str, Any]] = []
    for proposal_id in sorted(accepted_ids):
        proposal = by_id[proposal_id]
        rows.append(
            {
                "proposal_id": proposal_id,
                "target_kind": proposal.get("target_kind"),
                "stable_id": proposal.get("stable_id"),
                "owner_logical_id": proposal.get("owner_logical_id"),
                "source_build": proposal.get("source_build"),
                "source_sha256": proposal.get("source_sha256"),
                "source_coordinate": copy.deepcopy(
                    proposal.get("source_coordinate")
                ),
                "semantic_name": proposal.get("proposed_name"),
                "semantic_confidence": float(proposal.get("confidence")),
                "evidence": copy.deepcopy(proposal.get("evidence")),
                "note": proposal.get("note"),
            }
        )
    return rows


def _accepted_lineage_projection(
    classes: dict[str, Any],
    members: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for record in classes.get("classes", []):
        if record.get("semantic_status") != "ACCEPTED":
            continue
        provenance = record.get("semantic_provenance")
        if not isinstance(provenance, list) or len(provenance) != 1:
            raise SourceM1LineageRederiveError(
                f"{record.get('logical_id')}: expected one semantic provenance row"
            )
        p = provenance[0]
        rows.append(
            {
                "proposal_id": p.get("proposal_id"),
                "target_kind": "class",
                "stable_id": record.get("logical_id"),
                "owner_logical_id": record.get("logical_id"),
                "source_build": p.get("source_build"),
                "source_sha256": p.get("source_sha256"),
                "source_coordinate": copy.deepcopy(p.get("source_coordinate")),
                "semantic_name": record.get("semantic_name"),
                "semantic_confidence": float(
                    record.get("semantic_confidence")
                ),
                "evidence": copy.deepcopy(p.get("evidence")),
                "note": p.get("note"),
            }
        )

    for record in members.get("members", []):
        if record.get("semantic_status") != "ACCEPTED":
            continue
        provenance = record.get("semantic_provenance")
        if not isinstance(provenance, list) or len(provenance) != 1:
            raise SourceM1LineageRederiveError(
                f"{record.get('member_id')}: expected one semantic provenance row"
            )
        p = provenance[0]
        rows.append(
            {
                "proposal_id": p.get("proposal_id"),
                "target_kind": record.get("kind"),
                "stable_id": record.get("member_id"),
                "owner_logical_id": record.get("owner_logical_id"),
                "source_build": p.get("source_build"),
                "source_sha256": p.get("source_sha256"),
                "source_coordinate": copy.deepcopy(p.get("source_coordinate")),
                "semantic_name": record.get("semantic_name"),
                "semantic_confidence": float(
                    record.get("semantic_confidence")
                ),
                "evidence": copy.deepcopy(p.get("evidence")),
                "note": p.get("note"),
            }
        )

    return sorted(rows, key=lambda row: str(row["proposal_id"]))


def _assert_historical_member_anchors(
    members: dict[str, Any],
) -> None:
    by_coordinate: dict[tuple[str, str, str], str] = {}
    for row in members.get("members", []):
        lineage = row.get("lineage")
        if not isinstance(lineage, list) or len(lineage) != 1:
            continue
        point = lineage[0]
        if point.get("build_id") != "v308":
            continue
        key = (
            str(point.get("owner_internal_name")),
            str(point.get("name")),
            str(point.get("descriptor")),
        )
        by_coordinate[key] = str(row.get("member_id"))

    for coordinate, expected_id in HISTORICAL_MEMBER_ANCHORS.items():
        actual = by_coordinate.get(coordinate)
        if actual != expected_id:
            raise SourceM1LineageRederiveError(
                "historical member stable-ID anchor mismatch: "
                f"{coordinate!r} expected={expected_id} actual={actual}"
            )


def rederive_v308_lineage(
    index: dict[str, Any],
    review: dict[str, Any],
    acceptance: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if str(index.get("sha256", "")).lower() != EXPECTED_V308_SHA256:
        raise SourceM1LineageRederiveError(
            "source index is not bound to exact v308"
        )

    expected_projection = _proposal_projection(review, acceptance)

    classes = seed_lineage(
        index,
        build_id="v308",
        build_number=308,
        authority="EXACT_CURRENT_CLIENT",
        prefix="rs/",
    )
    members = seed_member_lineage(
        classes,
        index,
        build_id="v308",
    )
    classes, members, summary = accept_semantic_proposals(
        classes,
        members,
        review,
        acceptance,
    )

    validate_lineage(classes)
    validate_member_lineage(members, class_lineage=classes)

    if len(classes.get("classes", [])) != EXPECTED_CLASS_COUNT:
        raise SourceM1LineageRederiveError(
            f"expected {EXPECTED_CLASS_COUNT} class rows"
        )
    if len(members.get("members", [])) != EXPECTED_MEMBER_COUNT:
        raise SourceM1LineageRederiveError(
            f"expected {EXPECTED_MEMBER_COUNT} member rows"
        )
    if classes.get("unresolved") != [] or members.get("unresolved") != []:
        raise SourceM1LineageRederiveError(
            "canonical v308 rederivation must have zero unresolved rows"
        )

    expected_summary = {
        "accepted": EXPECTED_ACCEPTED_TOTAL,
        "accepted_classes": EXPECTED_ACCEPTED_CLASSES,
        "accepted_members": EXPECTED_ACCEPTED_MEMBERS,
        "already_accepted": 0,
    }
    if summary != expected_summary:
        raise SourceM1LineageRederiveError(
            f"semantic acceptance summary mismatch: {summary!r}"
        )

    actual_projection = _accepted_lineage_projection(classes, members)
    if actual_projection != expected_projection:
        raise SourceM1LineageRederiveError(
            "rederived ACCEPTED semantic projection does not equal "
            "the complete committed R2 review/acceptance projection"
        )

    _assert_historical_member_anchors(members)

    material = {
        "source_sha256": EXPECTED_V308_SHA256,
        "review_id": EXPECTED_REVIEW_ID,
        "class_count": EXPECTED_CLASS_COUNT,
        "member_count": EXPECTED_MEMBER_COUNT,
        "accepted_projection": actual_projection,
        "historical_member_anchors": [
            {
                "owner": owner,
                "name": name,
                "descriptor": descriptor,
                "member_id": member_id,
            }
            for (owner, name, descriptor), member_id
            in sorted(HISTORICAL_MEMBER_ANCHORS.items())
        ],
    }
    proof_id = (
        "V308LINEAGEREBUILD_"
        + hashlib.sha256(_stable_json(material)).hexdigest()[:20].upper()
    )
    report = {
        "schema_version": 1,
        "kind": "v308_lineage_rederivation_proof",
        "proof_id": proof_id,
        **material,
        "accepted_classes": EXPECTED_ACCEPTED_CLASSES,
        "accepted_members": EXPECTED_ACCEPTED_MEMBERS,
        "unresolved_classes": 0,
        "unresolved_members": 0,
    }
    return classes, members, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rederive canonical v308 class/member lineage from one exact "
            "index and the committed reviewed semantic authority."
        )
    )
    parser.add_argument("index", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("acceptance", type=Path)
    parser.add_argument("--class-out", type=Path, required=True)
    parser.add_argument("--member-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        classes, members, report = rederive_v308_lineage(
            _load_json(args.index),
            _load_json(args.review),
            _load_json(args.acceptance),
        )
    except (
        SourceM1LineageRederiveError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        print(f"REFUSED: {exc}")
        return 2

    write_lineage(classes, args.class_out)
    write_member_lineage(members, args.member_out)
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("SPK_SOURCE_M1_V308_LINEAGE_REDERIVATION_PASS")
    print(f"proof_id={report['proof_id']}")
    print(f"class_count={report['class_count']}")
    print(f"member_count={report['member_count']}")
    print(f"accepted_classes={report['accepted_classes']}")
    print(f"accepted_members={report['accepted_members']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
