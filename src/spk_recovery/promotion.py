from __future__ import annotations

import copy
import re
from typing import Any

from .lineage import ALLOWED_AUTHORITIES, LineageValidationError, validate_lineage


class NewClassPromotionError(LineageValidationError):
    pass


_ID_RE = re.compile(r"^CLIENT_CLASS_(\d{6})$")


def _build(doc: dict[str, Any], build_id: str) -> dict[str, Any]:
    hits = [b for b in doc.get("builds", []) if b.get("build_id") == build_id]
    if len(hits) != 1:
        raise NewClassPromotionError(
            f"expected exactly one canonical build {build_id!r}, found {len(hits)}"
        )
    return hits[0]


def _unresolved_new_path(
    item: dict[str, Any],
    build_id: str,
) -> str | None:
    if (
        item.get("kind") != "unmatched_new"
        or item.get("new_build_id") != build_id
    ):
        return None
    candidate = item.get("candidate")
    if isinstance(candidate, str):
        return candidate
    if isinstance(candidate, dict):
        for key in ("path", "new", "entry_path"):
            value = candidate.get(key)
            if isinstance(value, str):
                return value
    return None


def _next_ordinal(doc: dict[str, Any]) -> int:
    highest = 0
    for record in doc.get("classes", []):
        logical_id = record.get("logical_id")
        if not isinstance(logical_id, str):
            continue
        match = _ID_RE.fullmatch(logical_id)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def promote_new_classes(
    lineage: dict[str, Any],
    new_index: dict[str, Any],
    *,
    build_id: str,
    paths: list[str],
    authority: str = "RESEARCH",
    note: str = "Explicitly reviewed and promoted from unmatched_new.",
) -> tuple[dict[str, Any], dict[str, int]]:
    """Promote reviewed unmatched target-build classes into new logical IDs."""
    validate_lineage(lineage)
    if authority not in ALLOWED_AUTHORITIES:
        raise NewClassPromotionError(
            f"unsupported promotion authority {authority!r}"
        )
    if not paths:
        raise NewClassPromotionError("at least one path must be supplied")
    if len(set(paths)) != len(paths):
        raise NewClassPromotionError("duplicate promotion path supplied")

    build = _build(lineage, build_id)
    index_sha = str(new_index.get("sha256", "")).lower()
    build_sha = str(build.get("sha256", "")).lower()
    if index_sha != build_sha:
        raise NewClassPromotionError(
            f"target index SHA-256 {index_sha} != canonical build SHA-256 "
            f"{build_sha}"
        )

    owned_paths = {
        entry.get("entry_path")
        for record in lineage.get("classes", [])
        for entry in record.get("lineage", [])
        if entry.get("build_id") == build_id
    }
    unresolved_paths = {
        path
        for item in lineage.get("unresolved", [])
        if isinstance(item, dict)
        for path in [_unresolved_new_path(item, build_id)]
        if path is not None
    }

    requested = sorted(paths)
    for path in requested:
        if path in owned_paths:
            raise NewClassPromotionError(
                f"path {path!r} is already owned by a canonical logical class "
                f"in {build_id}"
            )
        if path not in unresolved_paths:
            raise NewClassPromotionError(
                f"path {path!r} is not recorded as unmatched_new for build "
                f"{build_id!r}"
            )
        cls = new_index.get("classes", {}).get(path)
        entry = new_index.get("entries", {}).get(path)
        if not isinstance(cls, dict):
            raise NewClassPromotionError(
                f"target index has no class record for {path!r}"
            )
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("sha256"), str)
        ):
            raise NewClassPromotionError(
                f"target index has no entry SHA-256 for {path!r}"
            )
        internal_name = cls.get("internal_name")
        structural = cls.get("structural_sha256")
        if (
            not isinstance(internal_name, str)
            or path != internal_name + ".class"
        ):
            raise NewClassPromotionError(
                f"target internal-name/path mismatch for {path!r}"
            )
        if not isinstance(structural, str):
            raise NewClassPromotionError(
                f"target structural SHA missing for {path!r}"
            )

    out = copy.deepcopy(lineage)
    ordinal = _next_ordinal(out)
    for path in requested:
        cls = new_index["classes"][path]
        entry = new_index["entries"][path]
        logical_id = f"CLIENT_CLASS_{ordinal:06d}"
        ordinal += 1
        out["classes"].append(
            {
                "logical_id": logical_id,
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": build_id,
                        "internal_name": cls["internal_name"],
                        "entry_path": path,
                        "entry_sha256": entry["sha256"].lower(),
                        "structural_sha256": (
                            cls["structural_sha256"].lower()
                        ),
                        "relation": "MANUAL",
                        "confidence": 1.0,
                        "provenance": [
                            {
                                "authority": authority,
                                "source": "new-class-promotion",
                                "note": note,
                            }
                        ],
                    }
                ],
                "semantic_provenance": [],
            }
        )

    requested_set = set(requested)
    retained = []
    removed = 0
    for item in out.get("unresolved", []):
        if (
            isinstance(item, dict)
            and _unresolved_new_path(item, build_id) in requested_set
        ):
            removed += 1
            continue
        retained.append(item)
    out["unresolved"] = retained

    summary = dict(validate_lineage(out))
    summary.update(
        {
            "promoted_new_classes": len(requested),
            "unresolved_removed": removed,
        }
    )
    return out, summary
