from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile


class MemberSafetyError(ValueError):
    pass


ACC_PUBLIC = 0x0001
ACC_PRIVATE = 0x0002
ACC_PROTECTED = 0x0004
ACC_STATIC = 0x0008
ACC_FINAL = 0x0010
ACC_BRIDGE = 0x0040
ACC_SYNTHETIC = 0x1000
ACC_NATIVE = 0x0100
ACC_ABSTRACT = 0x0400

_SEVERITY_ORDER = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

_REFLECTION_MARKERS: tuple[tuple[str, tuple[bytes, ...]], ...] = (
    (
        "class_method_lookup",
        (
            b"java/lang/Class",
            b"getMethod",
        ),
    ),
    (
        "class_declared_method_lookup",
        (
            b"java/lang/Class",
            b"getDeclaredMethod",
        ),
    ),
    (
        "class_field_lookup",
        (
            b"java/lang/Class",
            b"getField",
        ),
    ),
    (
        "class_declared_field_lookup",
        (
            b"java/lang/Class",
            b"getDeclaredField",
        ),
    ),
    (
        "method_name_observation",
        (
            b"java/lang/reflect/Method",
            b"getName",
        ),
    ),
    (
        "field_name_observation",
        (
            b"java/lang/reflect/Field",
            b"getName",
        ),
    ),
    (
        "methodhandle_named_lookup",
        (
            b"java/lang/invoke/MethodHandles$Lookup",
            b"findVirtual",
        ),
    ),
    (
        "methodhandle_static_lookup",
        (
            b"java/lang/invoke/MethodHandles$Lookup",
            b"findStatic",
        ),
    ),
    (
        "methodhandle_getter_lookup",
        (
            b"java/lang/invoke/MethodHandles$Lookup",
            b"findGetter",
        ),
    ),
    (
        "methodhandle_setter_lookup",
        (
            b"java/lang/invoke/MethodHandles$Lookup",
            b"findSetter",
        ),
    ),
)

_EVENTBUS_SUBSCRIBE_MARKERS = (
    b"Lrs/eventbus/Subscribe;",
    b"rs/eventbus/Subscribe",
)


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def member_plan_digest(plan: dict[str, Any]) -> str:
    if (
        plan.get("schema_version") != 1
        or plan.get("kind") != "member_remap_plan"
    ):
        raise MemberSafetyError("unsupported member remap plan")
    payload = {
        "source_sha256": str(plan.get("source_sha256", "")).lower(),
        "members": sorted(
            [
                {
                    "member_id": row.get("member_id"),
                    "owner_internal_name": row.get("owner_internal_name"),
                    "kind": row.get("kind"),
                    "source_name": row.get("source_name"),
                    "descriptor": row.get("descriptor"),
                    "target_name": row.get("target_name"),
                }
                for row in plan.get("members", [])
            ],
            key=lambda row: (
                str(row["member_id"]),
                str(row["owner_internal_name"]),
                str(row["kind"]),
                str(row["source_name"]),
                str(row["descriptor"]),
                str(row["target_name"]),
            ),
        ),
    }
    return hashlib.sha256(_stable_json(payload)).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _declaration(
    index: dict[str, Any],
    row: dict[str, Any],
) -> dict[str, Any]:
    owner = row["owner_internal_name"]
    cls = index.get("classes", {}).get(owner + ".class")
    if not isinstance(cls, dict):
        raise MemberSafetyError(
            f"member owner missing from exact index: {owner}"
        )
    collection = "fields" if row["kind"] == "field" else "methods"
    hits = [
        member
        for member in cls.get(collection, [])
        if member.get("name") == row["source_name"]
        and member.get("descriptor") == row["descriptor"]
    ]
    if len(hits) != 1:
        raise MemberSafetyError(
            f"expected one exact declaration for {row['member_id']}, "
            f"found {len(hits)}"
        )
    return hits[0]


def _reflection_surface(
    source_jar: Path,
) -> tuple[dict[str, list[str]], set[str]]:
    reflection: dict[str, list[str]] = {}
    subscribe_owners: set[str] = set()

    with zipfile.ZipFile(source_jar) as z:
        for path in z.namelist():
            if not path.endswith(".class"):
                continue
            data = z.read(path)
            markers = [
                name
                for name, required in _REFLECTION_MARKERS
                if all(token in data for token in required)
            ]
            if markers:
                reflection[path] = markers
            if any(marker in data for marker in _EVENTBUS_SUBSCRIBE_MARKERS):
                subscribe_owners.add(path[:-6])

    return reflection, subscribe_owners


def _literal_locations(
    index: dict[str, Any],
    value: str,
) -> list[str]:
    out = []
    for path, cls in index.get("classes", {}).items():
        strings = cls.get("literal_strings", [])
        if isinstance(strings, list) and value in strings:
            out.append(path)
    return sorted(out)


def _hazard(
    code: str,
    severity: str,
    detail: str,
    **extra: Any,
) -> dict[str, Any]:
    row = {
        "code": code,
        "severity": severity,
        "detail": detail,
    }
    row.update(extra)
    return row


def _risk_level(hazards: list[dict[str, Any]]) -> str:
    if not hazards:
        return "low"
    return max(
        (str(row["severity"]) for row in hazards),
        key=lambda severity: _SEVERITY_ORDER[severity],
    )


def build_member_safety_report(
    source_jar: Path,
    index: dict[str, Any],
    member_plan: dict[str, Any],
) -> dict[str, Any]:
    """Build deterministic risk evidence for every planned member rename.

    This report deliberately does not claim that any rename is proven safe.
    It creates a precise review surface bound to one source JAR + member plan.
    """
    source_jar = source_jar.resolve()
    if not source_jar.is_file():
        raise MemberSafetyError(
            f"source JAR does not exist: {source_jar}"
        )
    if (
        member_plan.get("schema_version") != 1
        or member_plan.get("kind") != "member_remap_plan"
    ):
        raise MemberSafetyError("unsupported member remap plan")

    source_sha = str(member_plan.get("source_sha256", "")).lower()
    actual_sha = _sha256_file(source_jar)
    if actual_sha.lower() != source_sha:
        raise MemberSafetyError(
            f"source JAR SHA {actual_sha} does not match member plan {source_sha}"
        )
    if str(index.get("sha256", "")).lower() != source_sha:
        raise MemberSafetyError(
            "source index SHA does not match member plan"
        )

    reflection_classes, subscribe_owners = _reflection_surface(source_jar)
    reflection_paths = set(reflection_classes)

    rows: list[dict[str, Any]] = []
    for plan_row in sorted(
        member_plan.get("members", []),
        key=lambda row: str(row.get("member_id")),
    ):
        declaration = _declaration(index, plan_row)
        access = int(declaration.get("access", 0))
        kind = plan_row["kind"]
        owner = plan_row["owner_internal_name"]
        source_name = plan_row["source_name"]

        hazards: list[dict[str, Any]] = []

        if access & ACC_NATIVE:
            hazards.append(
                _hazard(
                    "native_method",
                    "critical",
                    "Native method names may participate in native symbol/linkage contracts.",
                )
            )
        if access & ACC_ABSTRACT:
            hazards.append(
                _hazard(
                    "abstract_contract",
                    "high",
                    "Abstract method name may participate in an interface/supertype contract.",
                )
            )
        if access & ACC_BRIDGE:
            hazards.append(
                _hazard(
                    "bridge_method",
                    "high",
                    "Bridge method participates in compiler-generated override dispatch.",
                )
            )
        if access & ACC_PUBLIC:
            hazards.append(
                _hazard(
                    "public_api",
                    "high",
                    "Public member may be referenced by code outside the transformed archive.",
                )
            )
        elif access & ACC_PROTECTED:
            hazards.append(
                _hazard(
                    "protected_api",
                    "high",
                    "Protected member may be referenced by external subclasses.",
                )
            )
        elif not (access & ACC_PRIVATE):
            hazards.append(
                _hazard(
                    "package_visible",
                    "medium",
                    "Package-visible member may have package-local name contracts.",
                )
            )

        if access & ACC_SYNTHETIC:
            hazards.append(
                _hazard(
                    "synthetic_member",
                    "medium",
                    "Synthetic member may participate in compiler/framework-generated linkage.",
                )
            )

        literal_paths = _literal_locations(index, source_name)
        if literal_paths:
            hazards.append(
                _hazard(
                    "source_name_literal",
                    "medium",
                    "The old member name survives as an exact string literal in the archive.",
                    count=len(literal_paths),
                    sample_paths=literal_paths[:20],
                )
            )
            reflective_literal_paths = sorted(
                set(literal_paths) & reflection_paths
            )
            if reflective_literal_paths:
                hazards.append(
                    _hazard(
                        "source_name_literal_in_reflection_surface",
                        "high",
                        "The old member name appears inside a class with direct reflection/name lookup APIs.",
                        count=len(reflective_literal_paths),
                        sample_paths=reflective_literal_paths[:20],
                    )
                )

        owner_literal_paths = sorted(
            set(_literal_locations(index, owner))
            | set(_literal_locations(index, owner.replace("/", ".")))
        )
        owner_reflective = sorted(
            set(owner_literal_paths) & reflection_paths
        )
        if owner_reflective:
            hazards.append(
                _hazard(
                    "owner_name_literal_in_reflection_surface",
                    "high",
                    "The owner class name appears as a literal inside reflection-heavy code.",
                    count=len(owner_reflective),
                    sample_paths=owner_reflective[:20],
                )
            )

        if kind == "method" and owner in subscribe_owners:
            hazards.append(
                _hazard(
                    "eventbus_subscribe_owner",
                    "high",
                    "Owner class contains EventBus Subscribe annotations; method names may be framework-observed.",
                )
            )

        risk_material = {
            "source_sha256": source_sha,
            "plan_digest": member_plan_digest(member_plan),
            "member_id": plan_row["member_id"],
            "kind": kind,
            "owner_internal_name": owner,
            "source_name": source_name,
            "descriptor": plan_row["descriptor"],
            "target_name": plan_row["target_name"],
            "access": access,
            "hazards": hazards,
        }
        risk_id = (
            "MEMRISK_"
            + hashlib.sha256(_stable_json(risk_material))
            .hexdigest()[:20]
            .upper()
        )
        rows.append(
            {
                **risk_material,
                "risk_id": risk_id,
                "risk_level": _risk_level(hazards),
            }
        )

    digest = member_plan_digest(member_plan)
    report_material = {
        "source_sha256": source_sha,
        "member_plan_digest": digest,
        "members": [
            {
                "risk_id": row["risk_id"],
                "member_id": row["member_id"],
                "risk_level": row["risk_level"],
            }
            for row in rows
        ],
    }
    report_id = (
        "MEMRISKREVIEW_"
        + hashlib.sha256(_stable_json(report_material))
        .hexdigest()[:20]
        .upper()
    )

    level_counts = {
        level: sum(
            1 for row in rows if row["risk_level"] == level
        )
        for level in ("low", "medium", "high", "critical")
    }

    return {
        "schema_version": 1,
        "kind": "member_safety_report",
        "source_sha256": source_sha,
        "member_plan_digest": digest,
        "report_id": report_id,
        "member_count": len(rows),
        "risk_level_counts": level_counts,
        "reflection_surface": {
            "class_count": len(reflection_classes),
            "classes": [
                {
                    "class_path": path,
                    "markers": reflection_classes[path],
                }
                for path in sorted(reflection_classes)
            ],
            "subscribe_owner_count": len(subscribe_owners),
            "subscribe_owners": sorted(subscribe_owners),
        },
        "members": rows,
    }


def validate_member_safety_acceptance(
    member_plan: dict[str, Any],
    report: dict[str, Any],
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    """Verify explicit per-member review covers the exact member plan."""
    digest = member_plan_digest(member_plan)
    if report.get("schema_version") != 1:
        raise MemberSafetyError("safety report schema_version must be 1")
    if report.get("kind") != "member_safety_report":
        raise MemberSafetyError("safety report kind mismatch")
    if report.get("member_plan_digest") != digest:
        raise MemberSafetyError(
            "safety report is stale for this member plan"
        )

    expected_report_material = {
        "source_sha256": report.get("source_sha256"),
        "member_plan_digest": report.get("member_plan_digest"),
        "members": [
            {
                "risk_id": row.get("risk_id"),
                "member_id": row.get("member_id"),
                "risk_level": row.get("risk_level"),
            }
            for row in report.get("members", [])
        ],
    }
    expected_report_id = (
        "MEMRISKREVIEW_"
        + hashlib.sha256(_stable_json(expected_report_material))
        .hexdigest()[:20]
        .upper()
    )
    if report.get("report_id") != expected_report_id:
        raise MemberSafetyError(
            "safety report_id does not match report contents"
        )

    if acceptance.get("schema_version") != 1:
        raise MemberSafetyError(
            "safety acceptance schema_version must be 1"
        )
    if acceptance.get("kind") != "member_safety_acceptance":
        raise MemberSafetyError("safety acceptance kind mismatch")
    if acceptance.get("report_id") != report.get("report_id"):
        raise MemberSafetyError(
            "safety acceptance report_id does not match report"
        )

    decisions = acceptance.get("allow")
    if not isinstance(decisions, list) or not decisions:
        raise MemberSafetyError(
            "safety acceptance allow must be a non-empty array"
        )

    by_risk = {
        row["risk_id"]: row
        for row in report.get("members", [])
    }
    accepted: dict[str, dict[str, Any]] = {}
    for decision in decisions:
        if not isinstance(decision, dict):
            raise MemberSafetyError(
                "each safety decision must be an object"
            )
        risk_id = decision.get("risk_id")
        reason = decision.get("reason")
        if risk_id not in by_risk:
            raise MemberSafetyError(
                f"unknown safety risk_id {risk_id!r}"
            )
        if risk_id in accepted:
            raise MemberSafetyError(
                f"duplicate safety decision for {risk_id}"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise MemberSafetyError(
                f"{risk_id}: explicit non-empty review reason required"
            )
        accepted[risk_id] = decision

    required = {
        row["risk_id"] for row in report.get("members", [])
    }
    missing = sorted(required - set(accepted))
    if missing:
        raise MemberSafetyError(
            f"safety acceptance does not cover all planned members: {missing}"
        )

    plan_ids = {
        str(row.get("member_id"))
        for row in member_plan.get("members", [])
    }
    report_ids = {
        str(row.get("member_id"))
        for row in report.get("members", [])
    }
    if plan_ids != report_ids:
        raise MemberSafetyError(
            "safety report member set does not equal member plan"
        )

    return {
        "report_id": report["report_id"],
        "member_plan_digest": digest,
        "approved_members": len(required),
        "critical_approved": sum(
            1
            for row in report.get("members", [])
            if row.get("risk_level") == "critical"
        ),
        "high_approved": sum(
            1
            for row in report.get("members", [])
            if row.get("risk_level") == "high"
        ),
    }


def write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
