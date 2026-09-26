from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from .javac_class_triage import (
    JavacClassTriageError,
    _source_declared_types,
    analyze_unresolved_classes,
)
from .javac_variable_triage import _load_classes
from .source_digest import source_tree_digest


class ClassRecoveryPlanError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _normalize_prefixes(
    recovered_manifest: dict[str, Any],
) -> list[str]:
    values = recovered_manifest.get("project_source_prefixes")
    if not isinstance(values, list) or not values:
        raise ClassRecoveryPlanError(
            "recovered manifest lacks project source prefixes"
        )
    out: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise ClassRecoveryPlanError(
                "invalid project source prefix"
            )
        normalized = value.replace("\\", "/").lstrip("/")
        parts = [
            part
            for part in normalized.rstrip("/").split("/")
            if part
        ]
        if (
            not parts
            or any(part in {".", ".."} for part in parts)
            or normalized.startswith("META-INF/")
        ):
            raise ClassRecoveryPlanError(
                "unsafe project source prefix"
            )
        out.append("/".join(parts) + "/")
    return sorted(set(out))


def _package_of_internal(name: str) -> str:
    return name.rsplit("/", 1)[0] if "/" in name else ""


def _source_package_from_rel(rel: str) -> str:
    return rel.rsplit("/", 1)[0] if "/" in rel else ""


def build_class_recovery_plan(
    diagnostic_report: dict[str, Any],
    readable_jar: Path,
    source_root: Path,
    recovered_manifest: dict[str, Any],
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    readable_jar = readable_jar.resolve()

    tree_sha, _files, _bytes = source_tree_digest(source_root)
    if recovered_manifest.get("source_tree_sha256") != tree_sha:
        raise ClassRecoveryPlanError(
            "recovered manifest source tree authority mismatch"
        )

    prefixes = _normalize_prefixes(recovered_manifest)

    try:
        private_triage = analyze_unresolved_classes(
            diagnostic_report,
            readable_jar,
            source_root,
            include_identifiers=True,
        )
    except JavacClassTriageError as exc:
        raise ClassRecoveryPlanError(str(exc)) from exc

    classes = _load_classes(readable_jar)
    declared, declared_files = _source_declared_types(source_root)

    unique: dict[str, dict[str, Any]] = {}
    for row in private_triage["diagnostics"]:
        if (
            row.get("proof_class") != "java_visible_exact_class"
            or row.get("source_materialization")
            != "missing_exact_declaration"
        ):
            continue

        candidates = row.get("visible_candidates") or []
        if len(candidates) != 1:
            raise ClassRecoveryPlanError(
                "exact-visible missing declaration lacks one candidate"
            )

        candidate = str(candidates[0])
        class_row = classes.get(candidate)
        if class_row is None:
            raise ClassRecoveryPlanError(
                "triage candidate missing from readable class map"
            )

        rel = row.get("relative_source_path")
        if not isinstance(rel, str):
            raise ClassRecoveryPlanError(
                "triage candidate lacks relative source path"
            )

        package = _package_of_internal(candidate)
        source_package = _source_package_from_rel(rel)
        is_public = bool(int(class_row.get("access", 0)) & 0x0001)
        access_class = (
            "public"
            if is_public
            else (
                "package_accessible"
                if package == source_package
                else "package_inaccessible"
            )
        )

        entry = candidate + ".class"
        project_scoped = any(
            entry.startswith(prefix)
            for prefix in prefixes
        )

        structure = str(row.get("candidate_structure"))
        if structure != "top_level":
            responsibility = "structurally_unsafe_for_top_level_plan"
            expected_source_rel = None
            expected_source_exists = False
            expected_source_declares_candidate = False
            expected_source_declared_type_count = 0
        elif project_scoped:
            expected_source_rel = candidate + ".java"
            expected_source = source_root / Path(expected_source_rel)
            expected_source_exists = expected_source.is_file()
            expected_source_declares_candidate = (
                declared_files.get(candidate) == expected_source_rel
            )
            if expected_source_exists:
                expected_source_declared_type_count = sum(
                    1
                    for owner_rel in declared_files.values()
                    if owner_rel == expected_source_rel
                )
            else:
                expected_source_declared_type_count = 0

            if expected_source_declares_candidate:
                responsibility = "project_declared_in_expected_unit"
            elif expected_source_exists:
                responsibility = (
                    "project_expected_source_identity_mismatch"
                )
            else:
                responsibility = "project_source_unit_missing"
        else:
            expected_source_rel = None
            expected_source_exists = False
            expected_source_declares_candidate = False
            expected_source_declared_type_count = 0
            responsibility = "dependency_binary_responsibility"

        evidence = {
            "candidate_structure": structure,
            "candidate_kind": str(row.get("candidate_kind")),
            "candidate_synthetic": bool(
                row.get("candidate_synthetic")
            ),
            "project_scoped": project_scoped,
            "access_class": access_class,
            "responsibility": responsibility,
            "expected_source_exists": expected_source_exists,
            "expected_source_declares_candidate": (
                expected_source_declares_candidate
            ),
            "expected_source_declared_type_count": (
                expected_source_declared_type_count
            ),
        }

        existing = unique.get(candidate)
        if existing is None:
            unique[candidate] = {
                **evidence,
                "diagnostic_count": 1,
                "symbol_ids": {str(row.get("symbol_id"))},
                "file_ids": {str(row.get("file_id"))},
                "expected_source_rel": expected_source_rel,
            }
        else:
            comparable = {
                key: existing[key]
                for key in evidence
            }
            if comparable != evidence:
                raise ClassRecoveryPlanError(
                    "candidate evidence drifted across diagnostics"
                )
            existing["diagnostic_count"] += 1
            existing["symbol_ids"].add(str(row.get("symbol_id")))
            existing["file_ids"].add(str(row.get("file_id")))

    responsibility_counts = Counter(
        row["responsibility"]
        for row in unique.values()
    )
    access_counts = Counter(
        row["access_class"]
        for row in unique.values()
    )
    structure_counts = Counter(
        row["candidate_structure"]
        for row in unique.values()
    )
    kind_counts = Counter(
        row["candidate_kind"]
        for row in unique.values()
    )

    safe_source_candidates = [
        (candidate, row)
        for candidate, row in unique.items()
        if (
            row["responsibility"]
            in {
                "project_expected_source_identity_mismatch",
                "project_source_unit_missing",
            }
            and row["candidate_structure"] == "top_level"
            and not row["candidate_synthetic"]
            and row["access_class"]
            != "package_inaccessible"
        )
    ]

    public_candidates = []
    for index, (_candidate, row) in enumerate(
        sorted(
            unique.items(),
            key=lambda item: (
                -int(item[1]["diagnostic_count"]),
                item[0],
            ),
        ),
        start=1,
    ):
        public_candidates.append(
            {
                "candidate_id": f"JCLASSMISS_{index:03d}",
                "diagnostic_count": row["diagnostic_count"],
                "affected_file_count": len(row["file_ids"]),
                "symbol_cluster_count": len(row["symbol_ids"]),
                "candidate_structure": row["candidate_structure"],
                "candidate_kind": row["candidate_kind"],
                "candidate_synthetic": row["candidate_synthetic"],
                "project_scoped": row["project_scoped"],
                "access_class": row["access_class"],
                "responsibility": row["responsibility"],
                "expected_source_exists": row[
                    "expected_source_exists"
                ],
                "expected_source_declares_candidate": row[
                    "expected_source_declares_candidate"
                ],
                "expected_source_declared_type_count": row[
                    "expected_source_declared_type_count"
                ],
            }
        )

    material = {
        "diagnostic_frontier_id": private_triage[
            "diagnostic_frontier_id"
        ],
        "class_triage_report_id": private_triage["report_id"],
        "readable_jar_sha256": private_triage[
            "readable_jar_sha256"
        ],
        "source_tree_sha256": tree_sha,
        "project_source_prefixes": prefixes,
        "candidates": public_candidates,
    }
    report: dict[str, Any] = {
        "schema_version": 1,
        "kind": "javac_missing_class_recovery_plan",
        "plan_id": (
            "JCLASSPLAN_"
            + _stable_digest(material)[:20].upper()
        ),
        "diagnostic_frontier_id": private_triage[
            "diagnostic_frontier_id"
        ],
        "class_triage_report_id": private_triage["report_id"],
        "readable_jar_sha256": private_triage[
            "readable_jar_sha256"
        ],
        "source_tree_sha256": tree_sha,
        "project_source_prefixes": prefixes,
        "summary": {
            "missing_unique_class_count": len(unique),
            "responsibility_counts": dict(
                sorted(responsibility_counts.items())
            ),
            "access_counts": dict(sorted(access_counts.items())),
            "structure_counts": dict(
                sorted(structure_counts.items())
            ),
            "kind_counts": dict(sorted(kind_counts.items())),
            "safe_source_recovery_candidate_count": len(
                safe_source_candidates
            ),
            "dependency_responsibility_count": (
                responsibility_counts.get(
                    "dependency_binary_responsibility",
                    0,
                )
            ),
            "project_identity_mismatch_count": (
                responsibility_counts.get(
                    "project_expected_source_identity_mismatch",
                    0,
                )
            ),
            "project_source_unit_missing_count": (
                responsibility_counts.get(
                    "project_source_unit_missing",
                    0,
                )
            ),
        },
        "candidates": public_candidates,
        "identifiers_included": include_identifiers,
    }

    if include_identifiers:
        private_rows = []
        public_by_index = {
            row["candidate_id"]: row
            for row in public_candidates
        }
        ordered = sorted(
            unique.items(),
            key=lambda item: (
                -int(item[1]["diagnostic_count"]),
                item[0],
            ),
        )
        for index, (candidate, row) in enumerate(
            ordered,
            start=1,
        ):
            candidate_id = f"JCLASSMISS_{index:03d}"
            private_rows.append(
                {
                    **public_by_index[candidate_id],
                    "candidate_internal_name": candidate,
                    "class_entry": candidate + ".class",
                    "expected_source_rel": row[
                        "expected_source_rel"
                    ],
                    "symbol_ids": sorted(row["symbol_ids"]),
                    "file_ids": sorted(row["file_ids"]),
                }
            )
        report["candidates"] = private_rows

    return report


def write_class_recovery_plan(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
