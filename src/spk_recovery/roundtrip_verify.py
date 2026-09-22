from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .indexer import index_jar


class RoundTripVerificationError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _normalize_prefixes(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise RoundTripVerificationError("project prefixes must be non-empty strings")
        normalized = value.replace("\\", "/").lstrip("/")
        if normalized and not normalized.endswith("/"):
            normalized += "/"
        out.append(normalized)
    if not out:
        raise RoundTripVerificationError("at least one project prefix is required")
    return sorted(set(out))


def _project_classes(index: dict[str, Any], prefixes: list[str]) -> dict[str, dict[str, Any]]:
    return {
        path: cls
        for path, cls in index.get("classes", {}).items()
        if any(path.startswith(prefix) for prefix in prefixes)
    }


def _field_surface(cls: dict[str, Any]) -> list[tuple[Any, ...]]:
    return sorted(
        (
            int(field.get("access", 0)),
            str(field.get("name", "")),
            str(field.get("descriptor", "")),
        )
        for field in cls.get("fields", [])
    )


def _method_surface(cls: dict[str, Any]) -> list[tuple[Any, ...]]:
    return sorted(
        (
            int(method.get("access", 0)),
            str(method.get("name", "")),
            str(method.get("descriptor", "")),
        )
        for method in cls.get("methods", [])
    )


def _method_codegen(cls: dict[str, Any]) -> list[tuple[Any, ...]]:
    return sorted(
        (
            int(method.get("access", 0)),
            str(method.get("name", "")),
            str(method.get("descriptor", "")),
            method.get("code_length"),
        )
        for method in cls.get("methods", [])
    )


def _semantic_surface(cls: dict[str, Any]) -> dict[str, Any]:
    return {
        "internal_name": cls.get("internal_name"),
        "major": cls.get("major"),
        "minor": cls.get("minor"),
        "access": cls.get("access"),
        "super_name": cls.get("super_name"),
        "interfaces": sorted(cls.get("interfaces", [])),
        "fields": _field_surface(cls),
        "methods": _method_surface(cls),
        "literal_strings": sorted(set(cls.get("literal_strings", []))),
        "numeric_constants": sorted(
            cls.get("numeric_constants", []),
            key=lambda value: (type(value).__name__, repr(value)),
        ),
    }


def _surface_differences(
    authority: dict[str, Any],
    rebuilt: dict[str, Any],
) -> list[str]:
    differences: list[str] = []
    for key in (
        "internal_name",
        "major",
        "minor",
        "access",
        "super_name",
        "interfaces",
        "fields",
        "methods",
        "literal_strings",
        "numeric_constants",
    ):
        if authority.get(key) != rebuilt.get(key):
            differences.append(key)
    return differences


def compare_project_classes(
    readable_index: dict[str, Any],
    rebuilt_index: dict[str, Any],
    *,
    prefixes: list[str],
) -> dict[str, Any]:
    prefixes = _normalize_prefixes(prefixes)
    authority = _project_classes(readable_index, prefixes)
    rebuilt = _project_classes(rebuilt_index, prefixes)

    authority_paths = set(authority)
    rebuilt_paths = set(rebuilt)
    missing = sorted(authority_paths - rebuilt_paths)
    unexpected = sorted(rebuilt_paths - authority_paths)

    rows: list[dict[str, Any]] = []
    counts = {
        "byte_identical": 0,
        "structural_equivalent": 0,
        "codegen_variance_only": 0,
        "semantic_surface_drift": 0,
    }

    for path in sorted(authority_paths & rebuilt_paths):
        a = authority[path]
        b = rebuilt[path]
        a_entry = readable_index["entries"][path]
        b_entry = rebuilt_index["entries"][path]

        if a_entry.get("sha256") == b_entry.get("sha256"):
            classification = "byte_identical"
            differences: list[str] = []
        else:
            a_surface = _semantic_surface(a)
            b_surface = _semantic_surface(b)
            differences = _surface_differences(a_surface, b_surface)

            if differences:
                classification = "semantic_surface_drift"
            elif a.get("structural_sha256") == b.get("structural_sha256"):
                classification = "structural_equivalent"
            elif _method_codegen(a) != _method_codegen(b):
                classification = "codegen_variance_only"
                differences = ["method_code_length"]
            else:
                # Same public/member/constant surface but a structural hash still
                # changed for parser-level reasons we do not understand.
                classification = "semantic_surface_drift"
                differences = ["unexplained_structural_hash_drift"]

        counts[classification] += 1
        rows.append(
            {
                "class_path": path,
                "classification": classification,
                "authority_entry_sha256": a_entry.get("sha256"),
                "rebuilt_entry_sha256": b_entry.get("sha256"),
                "authority_structural_sha256": a.get("structural_sha256"),
                "rebuilt_structural_sha256": b.get("structural_sha256"),
                "differences": differences,
            }
        )

    blockers = (
        len(missing)
        + len(unexpected)
        + counts["semantic_surface_drift"]
    )
    return {
        "prefixes": prefixes,
        "authority_project_classes": len(authority),
        "rebuilt_project_classes": len(rebuilt),
        "missing_classes": missing,
        "unexpected_classes": unexpected,
        "summary": {
            **counts,
            "missing": len(missing),
            "unexpected": len(unexpected),
            "blockers": blockers,
        },
        "classes": rows,
    }


def verify_clean_round_trip(
    clean_rebuild_report: dict[str, Any],
    readable_jar: Path,
    rebuilt_jar: Path,
) -> dict[str, Any]:
    if clean_rebuild_report.get("schema_version") != 1:
        raise RoundTripVerificationError("unsupported clean rebuild report schema")
    if clean_rebuild_report.get("kind") != "clean_project_rebuild_report":
        raise RoundTripVerificationError("wrong clean rebuild report kind")
    if clean_rebuild_report.get("status") != "complete":
        raise RoundTripVerificationError("clean rebuild report is not complete")
    if clean_rebuild_report.get("clean_project_build") is not True:
        raise RoundTripVerificationError("clean rebuild is not marked clean_project_build")

    readable_jar = readable_jar.resolve()
    rebuilt_jar = rebuilt_jar.resolve()
    if not readable_jar.is_file() or not rebuilt_jar.is_file():
        raise RoundTripVerificationError("readable/rebuilt JAR path does not exist")

    readable_sha = _sha256_file(readable_jar)
    expected_readable = str(clean_rebuild_report.get("readable_jar_sha256", "")).lower()
    if readable_sha.lower() != expected_readable:
        raise RoundTripVerificationError(
            f"readable JAR SHA-256 {readable_sha} does not match clean rebuild authority {expected_readable}"
        )

    rebuilt_sha = _sha256_file(rebuilt_jar)
    expected_rebuilt = str(
        clean_rebuild_report.get("rebuilt_client", {}).get("sha256", "")
    ).lower()
    if rebuilt_sha.lower() != expected_rebuilt:
        raise RoundTripVerificationError(
            f"rebuilt JAR SHA-256 {rebuilt_sha} does not match clean rebuild report {expected_rebuilt}"
        )

    prefixes = clean_rebuild_report.get("source_scope", {}).get("prefixes")
    if not isinstance(prefixes, list):
        raise RoundTripVerificationError("clean rebuild report has no project prefixes")

    readable_index = index_jar(readable_jar)
    rebuilt_index = index_jar(rebuilt_jar)

    if readable_index["summary"]["class_parse_error_count"] != 0:
        raise RoundTripVerificationError("readable authority contains class parse errors")
    if rebuilt_index["summary"]["class_parse_error_count"] != 0:
        raise RoundTripVerificationError("rebuilt client contains class parse errors")

    comparison = compare_project_classes(
        readable_index,
        rebuilt_index,
        prefixes=prefixes,
    )

    material = {
        "rebuild_id": clean_rebuild_report.get("rebuild_id"),
        "readable_sha256": readable_sha,
        "rebuilt_sha256": rebuilt_sha,
        "comparison_summary": comparison["summary"],
    }
    verification_id = (
        "ROUNDTRIP_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    blockers = comparison["summary"]["blockers"]
    candidate_ready = blockers == 0

    return {
        "schema_version": 1,
        "kind": "round_trip_verification_report",
        "verification_id": verification_id,
        "rebuild_id": clean_rebuild_report.get("rebuild_id"),
        "build_id": clean_rebuild_report.get("build_id"),
        "workspace_id": clean_rebuild_report.get("workspace_id"),
        "namespace_id": clean_rebuild_report.get("namespace_id"),
        "source_authority_sha256": clean_rebuild_report.get(
            "source_authority_sha256"
        ),
        "readable_jar_sha256": readable_sha,
        "rebuilt_jar_sha256": rebuilt_sha,
        "comparison": comparison,
        "rebuild_authority_candidate": {
            "ready": candidate_ready,
            "project_binary_fallback_count": clean_rebuild_report.get(
                "project_classes", {}
            ).get("binary_fallback_count"),
            "semantic_surface_blockers": blockers,
            "byte_identical_class_count": comparison["summary"]["byte_identical"],
            "structural_equivalent_class_count": comparison["summary"][
                "structural_equivalent"
            ],
            "codegen_variance_only_class_count": comparison["summary"][
                "codegen_variance_only"
            ],
            "note": (
                "ready means no class-set/API/hierarchy/constant drift was detected "
                "by the current static verifier. It does not claim byte-identical "
                "or runtime-behavior equivalence for codegen-variance classes."
            ),
        },
    }


def write_roundtrip_report(report: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
