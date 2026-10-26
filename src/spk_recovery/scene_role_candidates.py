"""Read-only structural candidates for the original client's scene graph.

This is a *role probe*, NOT cross-build identity acceptance. It consumes the
existing full-JAR index; no proprietary JAR or decompiled source is published.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .indexer import project_class_surface


class SceneRoleProbeError(ValueError):
    pass


def discover_scene_role(index: dict[str, Any], authority: dict[str, Any]) -> dict[str, Any]:
    """Detect 4-plane scene and tile roles after exact original-authority checks."""
    if index.get("sha256") != authority.get("sha256"):
        raise SceneRoleProbeError("SCENE_ROLE_ORIGINAL_JAR_SHA_MISMATCH")
    if authority.get("build") != 311:
        raise SceneRoleProbeError("SCENE_ROLE_EXPECTED_V311_AUTHORITY")
    pinned = authority.get("project_class_surface")
    if not isinstance(pinned, dict):
        raise SceneRoleProbeError("SCENE_ROLE_PROJECT_SURFACE_MISSING")
    try:
        surface = project_class_surface(index, "rs/")
    except ValueError as exc:
        raise SceneRoleProbeError("SCENE_ROLE_CLASS_SURFACE_INVALID") from exc
    if any(surface.get(k) != pinned.get(k) for k in (
        "scope", "class_count", "class_major_versions",
        "path_sha256_manifest_digest",
    )):
        raise SceneRoleProbeError("SCENE_ROLE_ORIGINAL_PROJECT_SURFACE_MISMATCH")
    classes = index["classes"]
    client = classes.get("rs/Client.class")
    if not isinstance(client, dict):
        raise SceneRoleProbeError("SCENE_ROLE_CLIENT_CLASS_MISSING")

    def fields_of(item: dict) -> list[dict]:
        return item.get("fields", [])

    candidates: list[dict] = []
    for path, klass in sorted(classes.items()):
        if not path.startswith("rs/") or not path.endswith(".class"):
            continue
        fields = fields_of(klass)
        if not any(f.get("descriptor") == "[[[[Z" for f in fields):
            continue
        if not any(m.get("name") == "<init>" and m.get("descriptor") == "([[[I)V"
                   for m in klass.get("methods", [])):
            continue
        if len(klass.get("methods", [])) < 40:
            continue
        grids = [
            f["descriptor"][4:-1]
            for f in fields
            if isinstance(f.get("descriptor"), str)
            and f["descriptor"].startswith("[[[L")
            and f["descriptor"].endswith(";")
        ]
        for tile_name in sorted(set(grids)):
            tile_path = tile_name + ".class"
            tile = classes.get(tile_path)
            if not isinstance(tile, dict) or not tile_path.startswith("rs/"):
                continue
            tile_fields = fields_of(tile)
            if not any(f.get("descriptor") == "L" + tile_name + ";" for f in tile_fields):
                continue
            if not any(m.get("name") == "<init>" and m.get("descriptor") == "(III)V"
                       for m in tile.get("methods", [])):
                continue
            if not any(f.get("descriptor", "").startswith("[Lrs/") for f in tile_fields):
                continue
            if not any(f.get("descriptor") == "L" + klass["internal_name"] + ";"
                       for f in fields_of(client)):
                continue
            candidates.append({
                "scene_class_path": path,
                "tile_class_path": tile_path,
                "client_class_path": "rs/Client.class",
                "scene_methods": len(klass["methods"]),
                "scene_fields": len(fields),
                "tile_methods": len(tile["methods"]),
                "tile_fields": len(tile_fields),
                "witnesses": [
                    "scene_instantiated_from_3d_int_height_array",
                    "scene_owns_3d_tile_object_grid",
                    "scene_owns_4d_boolean_visibility_grid",
                    "tile_constructor_accepts_three_ints",
                    "tile_has_self_reference_and_scene_entities",
                    "original_client_holds_scene_reference",
                ],
                "historical_v308_class_identity": "NOT_ESTABLISHED",
                "semantic_name_promotion": "NOT_AUTHORIZED",
            })
    if len(candidates) != 1:
        raise SceneRoleProbeError(
            "SCENE_ROLE_NOT_UNIQUE candidate_count=" + str(len(candidates))
        )
    report = {
        "schema_version": 1,
        "kind": "v311_original_scene_role_candidate",
        "original_jar_sha256": index["sha256"],
        "original_project_class_surface_digest": surface[
            "path_sha256_manifest_digest"
        ],
        "candidates": candidates,
        "gameplay_executed": False,
        "source_compiled": False,
        "cross_build_identity_proven": False,
    }
    return report
