from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from .dependency_source_binding import _mapping_rows


class DependencySourceEditPlanError(ValueError):
    pass


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
        raise DependencySourceEditPlanError(
            f"invalid JSON authority: {path}"
        ) from exc
    if data.get("kind") != kind:
        raise DependencySourceEditPlanError(
            f"{path}: expected kind {kind!r}, "
            f"got {data.get('kind')!r}"
        )
    return data


def build_dependency_source_edit_plan(
    private_binding_inventory_path: Path,
    dependency_remap_report_path: Path,
    private_replacement_plan_path: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    binding = _load_json(
        private_binding_inventory_path.resolve(),
        kind="dependency_source_binding_inventory",
    )
    remap = _load_json(
        dependency_remap_report_path.resolve(),
        kind="dependency_structural_remap_proof",
    )
    replacement = _load_json(
        private_replacement_plan_path.resolve(),
        kind="dependency_replacement_boundary_plan",
    )

    if binding.get("identifiers_included") is not True:
        raise DependencySourceEditPlanError(
            "requires private identifier-bearing DEPSRCBIND inventory"
        )
    if replacement.get("identifiers_included") is not True:
        raise DependencySourceEditPlanError(
            "requires private identifier-bearing DEPREPLACE plan"
        )

    remap_id = remap.get("dependency_remap_proof_id")
    if binding.get("dependency_remap_proof_id") != remap_id:
        raise DependencySourceEditPlanError(
            "DEPSRCBIND is bound to a different DEPREMAP"
        )
    if replacement.get("dependency_remap_proof_id") != remap_id:
        raise DependencySourceEditPlanError(
            "DEPREPLACE is bound to a different DEPREMAP"
        )
    if binding.get("replacement_plan_id") != replacement.get(
        "replacement_plan_id"
    ):
        raise DependencySourceEditPlanError(
            "DEPSRCBIND is bound to a different DEPREPLACE"
        )

    bundled_sha = remap.get("bundled_jar_sha256")
    if binding.get("bundled_jar_sha256") != bundled_sha:
        raise DependencySourceEditPlanError(
            "DEPSRCBIND bundled JAR authority drifted"
        )
    if replacement.get("bundled_jar_sha256") != bundled_sha:
        raise DependencySourceEditPlanError(
            "DEPREPLACE bundled JAR authority drifted"
        )

    owners, members = _mapping_rows(remap, replacement)
    owner_by_id = {
        str(row["owner_id"]): row
        for row in owners
    }
    member_by_id = {
        str(row["member_id"]): row
        for row in members
    }
    if len(owner_by_id) != len(owners):
        raise DependencySourceEditPlanError(
            "duplicate DEPREPLACE owner IDs"
        )
    if len(member_by_id) != len(members):
        raise DependencySourceEditPlanError(
            "duplicate DEPREMAP member IDs"
        )

    bindings = list(binding.get("bindings", []))
    class_bindings_by_file_owner: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ] = {}
    for row in bindings:
        if row.get("match_status") != "exact_approved_class":
            continue
        source_file = row.get("source_file")
        old_owner = row.get("old_owner")
        if (
            not isinstance(source_file, str)
            or not source_file
            or not isinstance(old_owner, str)
            or not old_owner
        ):
            raise DependencySourceEditPlanError(
                "private class binding lacks exact source/owner identity"
            )
        class_bindings_by_file_owner.setdefault(
            (source_file, old_owner),
            [],
        ).append(row)

    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    blocker_rows: list[dict[str, Any]] = []

    for binding_row in bindings:
        binding_id = str(binding_row.get("binding_id"))
        file_id = str(binding_row.get("source_file_id"))
        match_status = str(binding_row.get("match_status"))
        element_kind = str(binding_row.get("element_kind"))
        mapping_id = str(binding_row.get("mapping_id"))
        start = binding_row.get("start")
        end = binding_row.get("end")

        if (
            not binding_id
            or not file_id
            or not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or end < start
        ):
            raise DependencySourceEditPlanError(
                "binding row lacks stable source position"
            )

        old_owner = binding_row.get("old_owner")
        old_name = binding_row.get("old_name")
        old_descriptor = binding_row.get("old_descriptor")
        if not all(
            isinstance(value, str)
            for value in (
                old_owner,
                old_name,
                old_descriptor,
            )
        ):
            raise DependencySourceEditPlanError(
                "private binding row lacks exact old identity"
            )

        new_owner: str | None = None
        new_name: str | None = None
        new_descriptor: str | None = None
        action: str
        blocker_code: str | None = None

        if match_status == "exact_approved_class":
            owner = owner_by_id.get(mapping_id)
            if owner is None:
                raise DependencySourceEditPlanError(
                    f"{binding_id}: unknown owner mapping ID"
                )
            if owner.get("old_owner") != old_owner:
                raise DependencySourceEditPlanError(
                    f"{binding_id}: owner mapping identity mismatch"
                )
            if owner.get("classification") != "official_replaceable":
                raise DependencySourceEditPlanError(
                    f"{binding_id}: exact approved class is not replaceable"
                )
            new_owner = str(owner.get("new_owner"))
            if not new_owner or new_owner == "None":
                raise DependencySourceEditPlanError(
                    f"{binding_id}: replaceable owner lacks new_owner"
                )
            action = (
                "class_type_rename_required"
                if old_owner != new_owner
                else "identity_no_edit"
            )

        elif match_status == "exact_approved_member":
            member = member_by_id.get(mapping_id)
            if member is None:
                raise DependencySourceEditPlanError(
                    f"{binding_id}: unknown member mapping ID"
                )
            expected = (
                member["old_owner"],
                member["old_name"],
                member["old_descriptor"],
            )
            actual = (
                old_owner,
                old_name,
                old_descriptor,
            )
            if actual != expected:
                raise DependencySourceEditPlanError(
                    f"{binding_id}: member mapping identity mismatch"
                )

            new_owner = str(member["new_owner"])
            new_name = str(member["new_name"])
            new_descriptor = str(member["new_descriptor"])

            if element_kind == "constructor":
                if old_name != "<init>" or new_name != "<init>":
                    raise DependencySourceEditPlanError(
                        f"{binding_id}: constructor mapping is not <init>"
                    )
                if old_owner != new_owner:
                    source_file = str(binding_row["source_file"])
                    candidates = class_bindings_by_file_owner.get(
                        (source_file, old_owner),
                        [],
                    )
                    covered = any(
                        int(candidate["start"]) >= start
                        and int(candidate["end"]) <= end
                        for candidate in candidates
                    )
                    if covered:
                        action = "constructor_covered_by_type_edit"
                    else:
                        action = "blocked_constructor_missing_type_binding"
                        blocker_code = (
                            "constructor_owner_change_without_type_binding"
                        )
                else:
                    action = "identity_no_edit"
            elif old_name != new_name:
                action = "member_name_rename_required"
            elif (
                old_owner != new_owner
                or old_descriptor != new_descriptor
            ):
                action = "mapped_signature_no_direct_edit"
            else:
                action = "identity_no_edit"

        elif match_status == "approved_owner_unmatched_member":
            action = "blocked_unmatched_member"
            blocker_code = "approved_owner_unmatched_member"

        elif match_status == "non_replaceable_owner":
            action = "non_replaceable_no_edit"

        else:
            raise DependencySourceEditPlanError(
                f"{binding_id}: unsupported match status {match_status!r}"
            )

        public = {
            "edit_binding_id": binding_id,
            "source_file_id": file_id,
            "start": start,
            "end": end,
            "element_kind": element_kind,
            "match_status": match_status,
            "mapping_id": mapping_id,
            "action": action,
            "blocker_code": blocker_code,
        }
        public_rows.append(public)

        if blocker_code is not None:
            blocker_rows.append(public)

        if include_identifiers:
            private_rows.append(
                {
                    **public,
                    "source_file": binding_row["source_file"],
                    "old_owner": old_owner,
                    "old_name": old_name,
                    "old_descriptor": old_descriptor,
                    "new_owner": new_owner,
                    "new_name": new_name,
                    "new_descriptor": new_descriptor,
                }
            )

    public_rows.sort(
        key=lambda row: (
            row["source_file_id"],
            row["start"],
            row["end"],
            row["edit_binding_id"],
        )
    )
    if include_identifiers:
        private_rows.sort(
            key=lambda row: (
                row["source_file_id"],
                row["start"],
                row["end"],
                row["edit_binding_id"],
            )
        )

    action_counts = Counter(
        row["action"] for row in public_rows
    )
    blocker_counts = Counter(
        row["blocker_code"]
        for row in blocker_rows
        if row["blocker_code"] is not None
    )

    material = {
        "binding_inventory_id": binding[
            "binding_inventory_id"
        ],
        "source_tree_sha256": binding["source_tree_sha256"],
        "dependency_remap_proof_id": remap_id,
        "replacement_plan_id": replacement[
            "replacement_plan_id"
        ],
        "bundled_jar_sha256": bundled_sha,
        "rows": public_rows,
    }

    return {
        "schema_version": 1,
        "kind": "dependency_source_edit_obligation_plan",
        "edit_plan_id": (
            "DEPSRCEDIT_"
            + _stable_digest(material)[:20].upper()
        ),
        "binding_inventory_id": binding[
            "binding_inventory_id"
        ],
        "source_tree_sha256": binding["source_tree_sha256"],
        "dependency_remap_proof_id": remap_id,
        "replacement_plan_id": replacement[
            "replacement_plan_id"
        ],
        "bundled_jar_sha256": bundled_sha,
        "summary": {
            "binding_count": len(public_rows),
            "action_counts": dict(
                sorted(action_counts.items())
            ),
            "blocker_count": len(blocker_rows),
            "blocker_counts": dict(
                sorted(blocker_counts.items())
            ),
            "class_type_rename_required_count": action_counts.get(
                "class_type_rename_required",
                0,
            ),
            "member_name_rename_required_count": action_counts.get(
                "member_name_rename_required",
                0,
            ),
            "identity_no_edit_count": action_counts.get(
                "identity_no_edit",
                0,
            ),
            "non_replaceable_no_edit_count": action_counts.get(
                "non_replaceable_no_edit",
                0,
            ),
            "ready_for_source_overlay": len(blocker_rows) == 0,
        },
        "obligations": (
            private_rows
            if include_identifiers
            else public_rows
        ),
        "identifiers_included": include_identifiers,
    }


def write_dependency_source_edit_plan(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
