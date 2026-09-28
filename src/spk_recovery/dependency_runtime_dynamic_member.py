from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from .dependency_artifact_proof import (
    DependencyArtifactProofError,
    _artifact_index,
)
from .dependency_remap_proof import (
    DependencyRemapProofError,
    _bundled_index,
    _field_sequence,
    _ordinary_method_sequence,
    _translate_descriptor,
)
from .dependency_runtime_frontier import (
    DependencyRuntimeFrontierError,
    _artifact_rows_key,
    _load_private_plan,
    _normalize_prefixes,
)
from .decompiler import sha256_file


class DependencyRuntimeDynamicMemberError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _load_private_dynamic_mapping(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRuntimeDynamicMemberError(
            "invalid dynamic mapping authority"
        ) from exc
    if value.get("kind") != "dependency_runtime_dynamic_mapping_proof":
        raise DependencyRuntimeDynamicMemberError(
            "unexpected dynamic mapping authority kind"
        )
    if value.get("identifiers_included") is not True:
        raise DependencyRuntimeDynamicMemberError(
            "dynamic member proof requires private dynamic mapping authority"
        )
    return value


def _class_mapping_index(
    plan: dict[str, Any],
    dynamic: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    mappings: dict[str, dict[str, Any]] = {}

    for row in plan.get("owners", []):
        if (
            isinstance(row, dict)
            and row.get("classification") == "official_replaceable"
            and isinstance(row.get("old_owner"), str)
            and isinstance(row.get("new_owner"), str)
            and isinstance(row.get("artifact"), str)
        ):
            mappings[str(row["old_owner"])] = {
                "new_name": str(row["new_owner"]),
                "artifact": str(row["artifact"]),
                "source": "depreplace",
            }

    for row in dynamic.get("rows", []):
        if (
            isinstance(row, dict)
            and row.get("status") == "accepted_class_mapping"
            and isinstance(row.get("old_owner"), str)
            and isinstance(row.get("new_owner"), str)
            and isinstance(row.get("artifact"), str)
        ):
            owner = str(row["old_owner"])
            candidate = {
                "new_name": str(row["new_owner"]),
                "artifact": str(row["artifact"]),
                "source": "dynamic_mapping",
            }
            prior = mappings.get(owner)
            if prior is not None and (
                prior["new_name"] != candidate["new_name"]
                or prior["artifact"] != candidate["artifact"]
            ):
                raise DependencyRuntimeDynamicMemberError(
                    "dynamic class mapping conflicts with DEPREPLACE"
                )
            mappings[owner] = candidate

    return mappings


def _member_public_id(
    owner: str,
    kind: str,
    ordinal: int,
) -> str:
    raw = f"{owner}\0{kind}\0{ordinal}".encode("utf-8")
    return "DEPDYNMEMBER_" + hashlib.sha256(raw).hexdigest()[:18].upper()


def build_dependency_runtime_dynamic_member_proof(
    private_dynamic_mapping_path: Path,
    private_replacement_plan_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    dynamic = _load_private_dynamic_mapping(
        private_dynamic_mapping_path.resolve()
    )
    try:
        plan = _load_private_plan(
            private_replacement_plan_path.resolve()
        )
    except DependencyRuntimeFrontierError as exc:
        raise DependencyRuntimeDynamicMemberError(str(exc)) from exc

    bundled_jar = bundled_jar.resolve()
    prefixes = _normalize_prefixes(plan.get("project_prefixes"))
    bundled_sha = sha256_file(bundled_jar)
    if plan.get("bundled_jar_sha256") != bundled_sha:
        raise DependencyRuntimeDynamicMemberError(
            "bundled/readable JAR SHA differs from DEPREPLACE"
        )
    if dynamic.get("bundled_jar_sha256") != bundled_sha:
        raise DependencyRuntimeDynamicMemberError(
            "dynamic mapping authority is bound to a different bundled JAR"
        )
    if dynamic.get("replacement_plan_id") != plan.get(
        "replacement_plan_id"
    ):
        raise DependencyRuntimeDynamicMemberError(
            "dynamic mapping authority is bound to a different DEPREPLACE"
        )

    release = plan.get("java_release")
    if (
        not isinstance(release, int)
        or isinstance(release, bool)
        or release < 1
    ):
        raise DependencyRuntimeDynamicMemberError(
            "private DEPREPLACE has invalid java_release"
        )

    try:
        bundled = _bundled_index(
            bundled_jar,
            project_prefixes=prefixes,
        )
        official, artifact_by_class, artifact_rows = _artifact_index(
            [path.resolve() for path in official_artifacts],
            java_release=release,
        )
    except (
        DependencyRemapProofError,
        DependencyArtifactProofError,
    ) as exc:
        raise DependencyRuntimeDynamicMemberError(str(exc)) from exc

    expected_rows = plan.get("official_artifacts")
    if (
        not isinstance(expected_rows, list)
        or _artifact_rows_key(expected_rows)
        != _artifact_rows_key(artifact_rows)
    ):
        raise DependencyRuntimeDynamicMemberError(
            "official artifact authority differs from DEPREPLACE"
        )

    artifact_sha = sorted(
        str(row["sha256"]).lower()
        for row in artifact_rows
    )
    if sorted(
        str(value).lower()
        for value in dynamic.get("official_artifact_sha256", [])
    ) != artifact_sha:
        raise DependencyRuntimeDynamicMemberError(
            "dynamic mapping official artifact authority drifted"
        )

    mappings = _class_mapping_index(plan, dynamic)
    dynamic_rows = [
        row
        for row in dynamic.get("rows", [])
        if isinstance(row, dict)
        and row.get("status") == "accepted_class_mapping"
    ]

    class_rows_public: list[dict[str, Any]] = []
    class_rows_private: list[dict[str, Any]] = []
    member_rows_public: list[dict[str, Any]] = []
    member_rows_private: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    constructor_counts: Counter[str] = Counter()
    hierarchy_counts: Counter[str] = Counter()

    for class_index, mapping_row in enumerate(
        sorted(
            dynamic_rows,
            key=lambda row: str(row.get("old_owner", "")),
        ),
        start=1,
    ):
        old_owner = mapping_row.get("old_owner")
        new_owner = mapping_row.get("new_owner")
        artifact = mapping_row.get("artifact")
        if (
            not isinstance(old_owner, str)
            or not isinstance(new_owner, str)
            or not isinstance(artifact, str)
        ):
            raise DependencyRuntimeDynamicMemberError(
                "accepted dynamic class mapping lacks private identifiers"
            )
        if any(old_owner.startswith(prefix) for prefix in prefixes):
            raise DependencyRuntimeDynamicMemberError(
                "dynamic member target overlaps project prefix"
            )

        old_class = bundled.get(old_owner)
        new_class = official.get(new_owner)
        if (
            old_class is None
            or new_class is None
            or artifact_by_class.get(new_owner) != artifact
        ):
            raise DependencyRuntimeDynamicMemberError(
                "accepted dynamic class mapping no longer matches exact artifacts"
            )
        if old_class.structural_sha256() != str(
            mapping_row.get("structural_sha256")
        ):
            raise DependencyRuntimeDynamicMemberError(
                "dynamic class structural authority drifted"
            )
        if (
            _field_sequence(old_class) != _field_sequence(new_class)
            or _ordinary_method_sequence(old_class)
            != _ordinary_method_sequence(new_class)
        ):
            raise DependencyRuntimeDynamicMemberError(
                "dynamic class ordered member structure drifted"
            )

        class_complete = True
        class_member_count = 0
        class_accepted_count = 0
        class_unresolved_count = 0

        for ordinal, (old_member, new_member) in enumerate(
            zip(old_class.fields, new_class.fields),
            start=1,
        ):
            class_member_count += 1
            old_desc = str(old_member["descriptor"])
            translated = _translate_descriptor(
                old_desc,
                class_mappings=mappings,
                bundled_classes=bundled,
            )
            expected_desc = str(new_member["descriptor"])
            if translated is None:
                status = "descriptor_mapping_unresolved"
                class_complete = False
                class_unresolved_count += 1
                new_name = None
                new_desc = None
            elif translated != expected_desc:
                status = "descriptor_transport_mismatch"
                class_complete = False
                class_unresolved_count += 1
                new_name = None
                new_desc = None
            else:
                new_name = str(new_member["name"])
                new_desc = expected_desc
                status = (
                    "accepted_identity"
                    if (
                        str(old_member["name"]) == new_name
                        and old_desc == new_desc
                    )
                    else "accepted_remap"
                )
                class_accepted_count += 1
            status_counts[status] += 1
            public = {
                "member_id": _member_public_id(
                    old_owner,
                    "field",
                    ordinal,
                ),
                "class_id": f"DEPDYNCLASS_{class_index:05d}",
                "kind": "field",
                "status": status,
                "ordinal": ordinal,
            }
            member_rows_public.append(public)
            if include_identifiers:
                member_rows_private.append(
                    {
                        **public,
                        "old_owner": old_owner,
                        "old_name": str(old_member["name"]),
                        "old_descriptor": old_desc,
                        "new_owner": new_owner,
                        "new_name": new_name,
                        "new_descriptor": new_desc,
                    }
                )

        old_methods = [
            row
            for row in old_class.methods
            if row["name"] not in {"<init>", "<clinit>"}
        ]
        new_methods = [
            row
            for row in new_class.methods
            if row["name"] not in {"<init>", "<clinit>"}
        ]
        for ordinal, (old_member, new_member) in enumerate(
            zip(old_methods, new_methods),
            start=1,
        ):
            class_member_count += 1
            old_desc = str(old_member["descriptor"])
            translated = _translate_descriptor(
                old_desc,
                class_mappings=mappings,
                bundled_classes=bundled,
            )
            expected_desc = str(new_member["descriptor"])
            if translated is None:
                status = "descriptor_mapping_unresolved"
                class_complete = False
                class_unresolved_count += 1
                new_name = None
                new_desc = None
            elif translated != expected_desc:
                status = "descriptor_transport_mismatch"
                class_complete = False
                class_unresolved_count += 1
                new_name = None
                new_desc = None
            else:
                new_name = str(new_member["name"])
                new_desc = expected_desc
                status = (
                    "accepted_identity"
                    if (
                        str(old_member["name"]) == new_name
                        and old_desc == new_desc
                    )
                    else "accepted_remap"
                )
                class_accepted_count += 1
            status_counts[status] += 1
            public = {
                "member_id": _member_public_id(
                    old_owner,
                    "method",
                    ordinal,
                ),
                "class_id": f"DEPDYNCLASS_{class_index:05d}",
                "kind": "method",
                "status": status,
                "ordinal": ordinal,
            }
            member_rows_public.append(public)
            if include_identifiers:
                member_rows_private.append(
                    {
                        **public,
                        "old_owner": old_owner,
                        "old_name": str(old_member["name"]),
                        "old_descriptor": old_desc,
                        "new_owner": new_owner,
                        "new_name": new_name,
                        "new_descriptor": new_desc,
                    }
                )

        new_constructors = [
            row
            for row in new_class.methods
            if row["name"] == "<init>"
        ]
        for ordinal, old_ctor in enumerate(
            (
                row
                for row in old_class.methods
                if row["name"] == "<init>"
            ),
            start=1,
        ):
            class_member_count += 1
            old_desc = str(old_ctor["descriptor"])
            translated = _translate_descriptor(
                old_desc,
                class_mappings=mappings,
                bundled_classes=bundled,
            )
            candidates = (
                [
                    row
                    for row in new_constructors
                    if str(row["descriptor"]) == translated
                ]
                if translated is not None
                else []
            )
            if len(candidates) == 1:
                status = "accepted_constructor"
                class_accepted_count += 1
                new_desc = str(candidates[0]["descriptor"])
            else:
                status = "constructor_unresolved"
                class_complete = False
                class_unresolved_count += 1
                new_desc = None
            constructor_counts[status] += 1
            status_counts[status] += 1
            public = {
                "member_id": _member_public_id(
                    old_owner,
                    "constructor",
                    ordinal,
                ),
                "class_id": f"DEPDYNCLASS_{class_index:05d}",
                "kind": "constructor",
                "status": status,
                "ordinal": ordinal,
            }
            member_rows_public.append(public)
            if include_identifiers:
                member_rows_private.append(
                    {
                        **public,
                        "old_owner": old_owner,
                        "old_name": "<init>",
                        "old_descriptor": old_desc,
                        "new_owner": new_owner,
                        "new_name": (
                            "<init>"
                            if new_desc is not None
                            else None
                        ),
                        "new_descriptor": new_desc,
                    }
                )

        hierarchy_pairs: list[tuple[str, str | None, str]] = []
        if old_class.super_name is not None:
            hierarchy_pairs.append(
                ("super", old_class.super_name, str(new_class.super_name))
            )
        if len(old_class.interfaces) != len(new_class.interfaces):
            class_complete = False
            hierarchy_counts["hierarchy_arity_mismatch"] += 1
        else:
            for old_interface, new_interface in zip(
                old_class.interfaces,
                new_class.interfaces,
            ):
                hierarchy_pairs.append(
                    ("interface", old_interface, new_interface)
                )

        hierarchy_public: list[dict[str, Any]] = []
        hierarchy_private: list[dict[str, Any]] = []
        for edge_index, (kind, old_parent, new_parent) in enumerate(
            hierarchy_pairs,
            start=1,
        ):
            if old_parent is None:
                continue
            mapped = mappings.get(old_parent)
            if mapped is not None:
                expected_parent = str(mapped["new_name"])
            elif old_parent not in bundled:
                expected_parent = old_parent
            else:
                expected_parent = None

            if expected_parent is None:
                edge_status = "external_hierarchy_mapping_unresolved"
                class_complete = False
            elif expected_parent == new_parent:
                edge_status = "hierarchy_convergent"
            else:
                edge_status = "hierarchy_target_mismatch"
                class_complete = False
            hierarchy_counts[edge_status] += 1

            public_edge = {
                "hierarchy_edge_id": (
                    f"DEPDYNHIER_{class_index:05d}_{edge_index:04d}"
                ),
                "kind": kind,
                "status": edge_status,
            }
            hierarchy_public.append(public_edge)
            if include_identifiers:
                hierarchy_private.append(
                    {
                        **public_edge,
                        "old_parent": old_parent,
                        "expected_new_parent": expected_parent,
                        "actual_new_parent": new_parent,
                    }
                )

        public_class = {
            "class_id": f"DEPDYNCLASS_{class_index:05d}",
            "source_dynamic_mapping_id": mapping_row.get(
                "dynamic_mapping_id"
            ),
            "declared_member_count": class_member_count,
            "accepted_member_count": class_accepted_count,
            "unresolved_member_count": class_unresolved_count,
            "member_transport_complete": class_complete,
            "hierarchy": (
                hierarchy_private
                if include_identifiers
                else hierarchy_public
            ),
        }
        class_rows_public.append(
            {
                **public_class,
                "hierarchy": hierarchy_public,
            }
        )
        if include_identifiers:
            class_rows_private.append(
                {
                    **public_class,
                    "old_owner": old_owner,
                    "new_owner": new_owner,
                    "artifact": artifact,
                }
            )

    ready = bool(dynamic_rows) and all(
        row["member_transport_complete"]
        for row in class_rows_public
    )

    material = {
        "runtime_dynamic_mapping_id": dynamic.get(
            "runtime_dynamic_mapping_id"
        ),
        "replacement_plan_id": plan.get("replacement_plan_id"),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": artifact_sha,
        "classes": class_rows_public,
        "members": member_rows_public,
        "ready_for_dynamic_root_promotion": ready,
    }
    proof_id = (
        "DEPRUNTIMEDYNMEMBER_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "dependency_runtime_dynamic_member_proof",
        "runtime_dynamic_member_id": proof_id,
        "runtime_dynamic_mapping_id": dynamic.get(
            "runtime_dynamic_mapping_id"
        ),
        "replacement_plan_id": plan.get("replacement_plan_id"),
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": artifact_sha,
        "summary": {
            "accepted_dynamic_class_mapping_count": len(dynamic_rows),
            "declared_member_count": len(member_rows_public),
            "accepted_identity_member_count": status_counts.get(
                "accepted_identity",
                0,
            ),
            "accepted_remap_member_count": status_counts.get(
                "accepted_remap",
                0,
            ),
            "accepted_constructor_count": constructor_counts.get(
                "accepted_constructor",
                0,
            ),
            "constructor_unresolved_count": constructor_counts.get(
                "constructor_unresolved",
                0,
            ),
            "hierarchy_convergent_count": hierarchy_counts.get(
                "hierarchy_convergent",
                0,
            ),
            "hierarchy_unresolved_or_mismatch_count": sum(
                count
                for status, count in hierarchy_counts.items()
                if status != "hierarchy_convergent"
            ),
            "ambiguous_member_count": status_counts.get(
                "member_ambiguous",
                0,
            ),
            "unresolved_member_count": sum(
                count
                for status, count in status_counts.items()
                if status in {
                    "descriptor_mapping_unresolved",
                    "descriptor_transport_mismatch",
                    "constructor_unresolved",
                    "member_ambiguous",
                    "external_hierarchy_member",
                }
            ),
            "ready_for_dynamic_root_promotion": ready,
        },
        "classes": (
            class_rows_private
            if include_identifiers
            else class_rows_public
        ),
        "members": (
            member_rows_private
            if include_identifiers
            else member_rows_public
        ),
        "identifiers_included": include_identifiers,
        "note": (
            "Dynamic-only class replacement authority is promotable only "
            "when every declared member descriptor/position transfer, "
            "constructor mapping, and hierarchy edge is exact and complete."
        ),
    }


def write_dependency_runtime_dynamic_member_proof(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
