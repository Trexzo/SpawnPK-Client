from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


class DependencyReverseTransportPlanError(ValueError):
    pass


_ACCEPTED_MEMBER_STATUSES = {
    "accepted_identity",
    "accepted_remap",
    "official_unbundled_direct",
}


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_json(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyReverseTransportPlanError(
            f"invalid JSON authority: {path}"
        ) from exc
    if data.get("kind") != kind:
        raise DependencyReverseTransportPlanError(
            f"{path}: expected kind {kind!r}, "
            f"got {data.get('kind')!r}"
        )
    return data


def build_dependency_reverse_transport_plan(
    dependency_remap_report_path: Path,
    private_replacement_plan_path: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    remap = _load_json(
        dependency_remap_report_path.resolve(),
        kind="dependency_structural_remap_proof",
    )
    replacement = _load_json(
        private_replacement_plan_path.resolve(),
        kind="dependency_replacement_boundary_plan",
    )

    if replacement.get("identifiers_included") is not True:
        raise DependencyReverseTransportPlanError(
            "requires private identifier-bearing DEPREPLACE plan"
        )
    remap_id = remap.get("dependency_remap_proof_id")
    if replacement.get("dependency_remap_proof_id") != remap_id:
        raise DependencyReverseTransportPlanError(
            "DEPREPLACE is bound to a different DEPREMAP"
        )
    if replacement.get("bundled_jar_sha256") != remap.get(
        "bundled_jar_sha256"
    ):
        raise DependencyReverseTransportPlanError(
            "bundled JAR authority differs"
        )

    owner_rows = list(replacement.get("owners", []))
    by_owner: dict[str, dict[str, Any]] = {}
    for row in owner_rows:
        old_owner = row.get("old_owner")
        if not isinstance(old_owner, str) or not old_owner:
            raise DependencyReverseTransportPlanError(
                "private DEPREPLACE owner row lacks old_owner"
            )
        if old_owner in by_owner:
            raise DependencyReverseTransportPlanError(
                f"duplicate DEPREPLACE owner: {old_owner}"
            )
        by_owner[old_owner] = row

    all_source_owners = set(by_owner)
    class_candidates: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    class_identity_count = 0

    for old_owner, row in sorted(by_owner.items()):
        if row.get("classification") != "official_replaceable":
            continue
        new_owner = row.get("new_owner")
        if not isinstance(new_owner, str) or not new_owner:
            raise DependencyReverseTransportPlanError(
                f"replaceable owner lacks new_owner: {old_owner}"
            )
        if old_owner == new_owner:
            class_identity_count += 1
            continue

        class_candidates.append(
            {
                "old_owner": old_owner,
                "new_owner": new_owner,
                "owner_id": str(row.get("owner_id")),
            }
        )
        if new_owner in all_source_owners:
            blockers.append(
                {
                    "code": "class_target_also_source_owner",
                    "new_owner": new_owner,
                    "old_owner": old_owner,
                }
            )

    class_by_target: dict[str, list[dict[str, Any]]] = {}
    for row in class_candidates:
        class_by_target.setdefault(
            row["new_owner"],
            [],
        ).append(row)
    for target, rows in sorted(class_by_target.items()):
        old_values = {
            str(row["old_owner"])
            for row in rows
        }
        if len(old_values) > 1:
            blockers.append(
                {
                    "code": "class_reverse_many_to_one",
                    "new_owner": target,
                    "old_owner_count": len(old_values),
                }
            )

    all_old_member_identities: set[
        tuple[str, str, str]
    ] = set()
    for row in remap.get("member_results", []):
        old_owner = row.get("old_owner")
        old_name = row.get("old_name")
        old_descriptor = row.get("old_descriptor")
        if all(
            isinstance(value, str) and value
            for value in (
                old_owner,
                old_name,
                old_descriptor,
            )
        ):
            all_old_member_identities.add(
                (
                    old_owner,
                    old_name,
                    old_descriptor,
                )
            )

    member_candidates: list[dict[str, Any]] = []
    member_identity_count = 0
    owner_only_member_transport_count = 0
    ignored_nonreplaceable_accepted_count = 0

    for row in remap.get("member_results", []):
        status = str(row.get("status"))
        if status not in _ACCEPTED_MEMBER_STATUSES:
            continue

        reference_kind = str(row.get("kind"))
        if reference_kind not in {
            "field",
            "method",
            "interface_method",
        }:
            raise DependencyReverseTransportPlanError(
                "accepted member row has unsupported reference kind"
            )

        old_owner = row.get("old_owner")
        owner_plan = by_owner.get(str(old_owner))
        if (
            owner_plan is None
            or owner_plan.get("classification")
            != "official_replaceable"
        ):
            ignored_nonreplaceable_accepted_count += 1
            continue

        values = (
            row.get("old_owner"),
            row.get("old_name"),
            row.get("old_descriptor"),
            row.get("new_owner"),
            row.get("new_name"),
            row.get("new_descriptor"),
        )
        if not all(
            isinstance(value, str) and value
            for value in values
        ):
            raise DependencyReverseTransportPlanError(
                "accepted official-replaceable member row "
                "lacks exact old/new identity"
            )

        (
            old_owner,
            old_name,
            old_descriptor,
            new_owner,
            new_name,
            new_descriptor,
        ) = values

        if (
            old_name == new_name
            and old_descriptor == new_descriptor
        ):
            if old_owner == new_owner:
                member_identity_count += 1
            else:
                owner_only_member_transport_count += 1
            continue

        old_identity = (
            old_owner,
            old_name,
            old_descriptor,
        )
        new_identity = (
            new_owner,
            new_name,
            new_descriptor,
        )
        member_id = (
            "DEPREVERSEMEMBER_"
            + _stable_digest(
                {
                    "reference_kind": reference_kind,
                    "old": old_identity,
                    "new": new_identity,
                }
            )[:20].upper()
        )
        member_candidates.append(
            {
                "member_id": member_id,
                "reference_kind": reference_kind,
                "old_owner": old_owner,
                "old_name": old_name,
                "old_descriptor": old_descriptor,
                "new_owner": new_owner,
                "new_name": new_name,
                "new_descriptor": new_descriptor,
            }
        )

        if (
            new_identity in all_old_member_identities
            and new_identity != old_identity
        ):
            blockers.append(
                {
                    "code": "member_target_also_source_identity",
                    "member_id": member_id,
                }
            )

    member_by_target: dict[
        tuple[str, str, str],
        list[dict[str, Any]],
    ] = {}
    for row in member_candidates:
        key = (
            row["new_owner"],
            row["new_name"],
            row["new_descriptor"],
        )
        member_by_target.setdefault(key, []).append(row)

    for target, rows in sorted(member_by_target.items()):
        old_values = {
            (
                row["old_owner"],
                row["old_name"],
                row["old_descriptor"],
            )
            for row in rows
        }
        if len(old_values) > 1:
            blockers.append(
                {
                    "code": "member_reverse_many_to_one",
                    "target_id": (
                        "DEPREVERSETARGET_"
                        + _stable_digest(target)[:16].upper()
                    ),
                    "old_identity_count": len(old_values),
                }
            )

    class_candidates.sort(
        key=lambda row: (
            row["new_owner"],
            row["old_owner"],
        )
    )
    member_candidates.sort(
        key=lambda row: (
            row["reference_kind"],
            row["new_owner"],
            row["new_name"],
            row["new_descriptor"],
            row["old_owner"],
            row["old_name"],
            row["old_descriptor"],
        )
    )

    public_class_rows = [
        {
            "class_reverse_id": (
                "DEPREVERSECLASS_"
                + _stable_digest(
                    {
                        "old_owner": row["old_owner"],
                        "new_owner": row["new_owner"],
                    }
                )[:20].upper()
            ),
            "owner_id": row["owner_id"],
        }
        for row in class_candidates
    ]
    public_member_rows = [
        {
            "member_reverse_id": row["member_id"],
            "reference_kind": row["reference_kind"],
            "transport_kind": (
                "field"
                if row["reference_kind"] == "field"
                else "method"
            ),
        }
        for row in member_candidates
    ]

    blocker_counts = Counter(
        str(row["code"])
        for row in blockers
    )
    public_blockers = [
        {
            "blocker_id": (
                "DEPREVERSEBLOCK_"
                + _stable_digest(row)[:16].upper()
            ),
            "code": row["code"],
        }
        for row in blockers
    ]
    public_blockers.sort(
        key=lambda row: (
            row["code"],
            row["blocker_id"],
        )
    )

    completeness = {
        "class_identity_no_transport_count": (
            class_identity_count
        ),
        "member_identity_no_transport_count": (
            member_identity_count
        ),
        "owner_only_member_transport_count": (
            owner_only_member_transport_count
        ),
        "ignored_nonreplaceable_accepted_member_count": (
            ignored_nonreplaceable_accepted_count
        ),
    }

    public_material = {
        "dependency_remap_proof_id": remap_id,
        "replacement_plan_id": replacement[
            "replacement_plan_id"
        ],
        "bundled_jar_sha256": remap[
            "bundled_jar_sha256"
        ],
        "class_reverse": public_class_rows,
        "member_reverse": public_member_rows,
        "completeness": completeness,
        "blockers": public_blockers,
    }
    reverse_plan_id = (
        "DEPREVERSE_"
        + _stable_digest(public_material)[:20].upper()
    )

    report: dict[str, Any] = {
        "schema_version": 1,
        "kind": "dependency_reverse_compile_transport_plan",
        "reverse_plan_id": reverse_plan_id,
        "dependency_remap_proof_id": remap_id,
        "replacement_plan_id": replacement[
            "replacement_plan_id"
        ],
        "bundled_jar_sha256": remap[
            "bundled_jar_sha256"
        ],
        "summary": {
            "class_reverse_count": len(class_candidates),
            "member_reverse_count": len(member_candidates),
            **completeness,
            "blocker_count": len(blockers),
            "blocker_counts": dict(
                sorted(blocker_counts.items())
            ),
            "ready_for_bytecode_restore": len(blockers) == 0,
        },
        "class_reverse": (
            [
                {
                    **public,
                    "official_owner": private["new_owner"],
                    "bundled_owner": private["old_owner"],
                }
                for public, private in zip(
                    public_class_rows,
                    class_candidates,
                )
            ]
            if include_identifiers
            else public_class_rows
        ),
        "member_reverse": (
            [
                {
                    **public,
                    "official_owner": private["new_owner"],
                    "official_name": private["new_name"],
                    "official_descriptor": private[
                        "new_descriptor"
                    ],
                    "bundled_owner": private["old_owner"],
                    "bundled_name": private["old_name"],
                    "bundled_descriptor": private[
                        "old_descriptor"
                    ],
                }
                for public, private in zip(
                    public_member_rows,
                    member_candidates,
                )
            ]
            if include_identifiers
            else public_member_rows
        ),
        "blockers": (
            [
                {
                    **public,
                    **private,
                }
                for public, private in zip(
                    public_blockers,
                    sorted(
                        blockers,
                        key=lambda row: (
                            row["code"],
                            (
                                "DEPREVERSEBLOCK_"
                                + _stable_digest(row)[:16].upper()
                            ),
                        ),
                    ),
                )
            ]
            if include_identifiers
            else public_blockers
        ),
        "identifiers_included": include_identifiers,
    }
    return report


def write_dependency_reverse_transport_plan(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
