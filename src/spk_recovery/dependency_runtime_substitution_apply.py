from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from typing import Any
import zipfile

from .dependency_runtime_substitution_plan import (
    _redacted_id,
    _stable_digest,
)


class DependencyRuntimeSubstitutionApplyError(ValueError):
    pass


_RESIDUAL_NAME = "residual-dependency-capsule.jar"
_MANIFEST_NAME = "DEPENDENCY-RUNTIME-SUBSTITUTION.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_private_plan(path: Path) -> dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRuntimeSubstitutionApplyError(
            "invalid runtime substitution plan"
        ) from exc
    if plan.get("kind") != "dependency_runtime_substitution_plan":
        raise DependencyRuntimeSubstitutionApplyError(
            "unexpected runtime substitution plan kind"
        )
    if plan.get("identifiers_included") is not True:
        raise DependencyRuntimeSubstitutionApplyError(
            "apply requires private identifier-bearing substitution plan"
        )
    if plan.get("schema_version") != 2:
        raise DependencyRuntimeSubstitutionApplyError(
            "apply requires substitution-plan schema version 2"
        )
    return plan


def _require_string(report: dict[str, Any], key: str) -> str:
    value = report.get(key)
    if not isinstance(value, str) or not value:
        raise DependencyRuntimeSubstitutionApplyError(
            f"substitution plan lacks valid {key}"
        )
    return value


def _zip_payloads(path: Path) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(path) as archive:
            out: dict[str, bytes] = {}
            for info in archive.infolist():
                if info.is_dir():
                    continue
                if info.filename in out:
                    raise DependencyRuntimeSubstitutionApplyError(
                        f"duplicate ZIP entry: {path.name}:{info.filename}"
                    )
                out[info.filename] = archive.read(info)
            return out
    except zipfile.BadZipFile as exc:
        raise DependencyRuntimeSubstitutionApplyError(
            f"invalid JAR/ZIP: {path}"
        ) from exc


def _sorted_private_rows(
    rows: Any,
    *,
    label: str,
) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise DependencyRuntimeSubstitutionApplyError(
            f"substitution plan lacks {label}"
        )
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise DependencyRuntimeSubstitutionApplyError(
                f"malformed {label} row"
            )
        out.append(row)
    return out


def _public_class_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out = []
    for row in sorted(rows, key=lambda value: str(value.get("entry", ""))):
        for key in ("old_owner", "new_owner", "artifact", "entry"):
            if not isinstance(row.get(key), str) or not row.get(key):
                raise DependencyRuntimeSubstitutionApplyError(
                    "class removal row lacks exact private authority"
                )
        out.append(
            {
                "class_removal_id": _redacted_id(
                    "DEPSUBCLASS_",
                    str(row["old_owner"]),
                    str(row["new_owner"]),
                    str(row["artifact"]),
                    str(row["entry"]),
                ),
                "owner_remapped": row["old_owner"] != row["new_owner"],
            }
        )
    return out


def _public_resource_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out = []
    for row in sorted(rows, key=lambda value: str(value.get("entry", ""))):
        for key in ("entry", "artifact", "equivalence"):
            if not isinstance(row.get(key), str) or not row.get(key):
                raise DependencyRuntimeSubstitutionApplyError(
                    "resource removal row lacks exact private authority"
                )
        out.append(
            {
                "resource_removal_id": _redacted_id(
                    "DEPSUBRESOURCE_",
                    str(row["entry"]),
                    str(row["artifact"]),
                    str(row["equivalence"]),
                ),
                "equivalence": str(row["equivalence"]),
                "service_entry": bool(row.get("service_entry")),
            }
        )
    return out


def _public_path_rows(
    rows: list[dict[str, Any]],
    *,
    prefix: str,
    id_key: str,
) -> list[dict[str, Any]]:
    out = []
    for row in sorted(
        rows,
        key=lambda value: (
            str(value.get("entry", "")),
            str(value.get("kind", "")),
            str(value.get("left", "")),
            str(value.get("right", "")),
        ),
    ):
        for key in ("entry", "kind", "left", "right"):
            if not isinstance(row.get(key), str) or not row.get(key):
                raise DependencyRuntimeSubstitutionApplyError(
                    f"{id_key} row lacks exact private authority"
                )
        out.append(
            {
                id_key: _redacted_id(
                    prefix,
                    str(row["entry"]),
                    str(row["kind"]),
                    str(row["left"]),
                    str(row["right"]),
                ),
                "kind": str(row["kind"]),
            }
        )
    return out


def verify_private_substitution_plan(
    plan: dict[str, Any],
) -> None:
    summary = plan.get("summary")
    if not isinstance(summary, dict):
        raise DependencyRuntimeSubstitutionApplyError(
            "substitution plan lacks summary"
        )
    for key in (
        "preimage_verified",
        "official_artifacts_verified",
        "collision_free",
    ):
        if summary.get(key) is not True:
            raise DependencyRuntimeSubstitutionApplyError(
                f"substitution plan is not apply-safe: {key}"
            )
    if summary.get("apply_authorized") is not False:
        raise DependencyRuntimeSubstitutionApplyError(
            "R8DEP37 plan apply_authorized boundary drifted"
        )
    if plan.get("apply_authorized") is not False:
        raise DependencyRuntimeSubstitutionApplyError(
            "R8DEP37 top-level apply_authorized boundary drifted"
        )

    readiness_id = _require_string(plan, "runtime_readiness_id")
    replacement_id = _require_string(plan, "replacement_plan_id")
    extension_id = _require_string(plan, "replacement_extension_id")
    closure_id = _require_string(plan, "runtime_extended_closure_id")
    resource_id = _require_string(plan, "runtime_extended_resource_id")
    bundled_sha = _require_string(plan, "bundled_jar_sha256").lower()

    official_sha = plan.get("official_artifact_sha256")
    if (
        not isinstance(official_sha, list)
        or any(not isinstance(value, str) for value in official_sha)
    ):
        raise DependencyRuntimeSubstitutionApplyError(
            "substitution plan lacks official artifact SHA authority"
        )
    official_sha = sorted(str(value).lower() for value in official_sha)

    artifact_rows = _sorted_private_rows(
        plan.get("required_artifacts"),
        label="required_artifacts",
    )
    artifact_ids: list[str] = []
    seen_artifact_names: set[str] = set()
    for row in sorted(
        artifact_rows,
        key=lambda value: str(value.get("artifact", "")),
    ):
        artifact = row.get("artifact")
        sha = row.get("sha256")
        artifact_id = row.get("artifact_id")
        if (
            not isinstance(artifact, str)
            or not artifact
            or not isinstance(sha, str)
            or not sha
            or not isinstance(artifact_id, str)
            or not artifact_id
        ):
            raise DependencyRuntimeSubstitutionApplyError(
                "required artifact row lacks exact private authority"
            )
        if artifact in seen_artifact_names:
            raise DependencyRuntimeSubstitutionApplyError(
                "substitution plan repeats required artifact"
            )
        seen_artifact_names.add(artifact)
        expected_id = _redacted_id(
            "DEPSUBARTIFACT_",
            artifact,
            sha.lower(),
        )
        if artifact_id != expected_id:
            raise DependencyRuntimeSubstitutionApplyError(
                "required artifact redacted ID drifted"
            )
        artifact_ids.append(expected_id)

    class_rows = _sorted_private_rows(
        plan.get("class_removals"),
        label="class_removals",
    )
    resource_rows = _sorted_private_rows(
        plan.get("resource_removals"),
        label="resource_removals",
    )
    collision_rows = _sorted_private_rows(
        plan.get("collisions"),
        label="collisions",
    )
    resource_overlap_rows = _sorted_private_rows(
        plan.get("resource_overlaps"),
        label="resource_overlaps",
    )
    if collision_rows:
        raise DependencyRuntimeSubstitutionApplyError(
            "substitution plan contains blocking class collisions"
        )

    public_classes = _public_class_rows(class_rows)
    public_resources = _public_resource_rows(resource_rows)
    public_collisions = _public_path_rows(
        collision_rows,
        prefix="DEPSUBCOLLISION_",
        id_key="collision_id",
    )
    public_overlaps = _public_path_rows(
        resource_overlap_rows,
        prefix="DEPSUBRESOURCEOVERLAP_",
        id_key="resource_overlap_id",
    )

    material = {
        "runtime_readiness_id": readiness_id,
        "replacement_plan_id": replacement_id,
        "replacement_extension_id": extension_id,
        "runtime_extended_closure_id": closure_id,
        "runtime_extended_resource_id": resource_id,
        "bundled_jar_sha256": bundled_sha,
        "official_artifact_sha256": official_sha,
        "required_artifact_ids": artifact_ids,
        "class_removals": public_classes,
        "resource_removals": public_resources,
        "collisions": public_collisions,
        "resource_overlaps": public_overlaps,
        "summary": summary,
    }
    expected_id = (
        "DEPRUNTIMESUBPLAN_"
        + _stable_digest(material)[:20].upper()
    )
    if plan.get("runtime_substitution_plan_id") != expected_id:
        raise DependencyRuntimeSubstitutionApplyError(
            "runtime substitution plan ID does not verify"
        )


def _write_deterministic_jar(
    payloads: dict[str, bytes],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        out,
        "w",
        compression=zipfile.ZIP_STORED,
    ) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(
                filename=name,
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payloads[name])


def _required_artifact_map(
    plan: dict[str, Any],
    official_artifacts: list[Path],
) -> tuple[dict[str, Path], dict[str, str]]:
    supplied: dict[str, Path] = {}
    supplied_sha: dict[str, str] = {}
    for raw in official_artifacts:
        path = raw.resolve()
        if not path.is_file():
            raise DependencyRuntimeSubstitutionApplyError(
                f"official artifact missing: {path}"
            )
        if path.name in supplied:
            raise DependencyRuntimeSubstitutionApplyError(
                f"duplicate official artifact basename: {path.name}"
            )
        supplied[path.name] = path
        supplied_sha[path.name] = _sha256_file(path)

    expected_all = sorted(
        str(value).lower()
        for value in plan.get("official_artifact_sha256", [])
    )
    if sorted(supplied_sha.values()) != expected_all:
        raise DependencyRuntimeSubstitutionApplyError(
            "official artifact SHA set differs from substitution plan"
        )

    required: dict[str, str] = {}
    for row in plan["required_artifacts"]:
        artifact = str(row["artifact"])
        sha = str(row["sha256"]).lower()
        if artifact not in supplied or supplied_sha[artifact] != sha:
            raise DependencyRuntimeSubstitutionApplyError(
                f"required official artifact authority drifted: {artifact}"
            )
        required[artifact] = sha
    return supplied, required


def _expected_residual_payloads(
    plan: dict[str, Any],
    bundled_jar: Path,
) -> dict[str, bytes]:
    bundled = _zip_payloads(bundled_jar)
    removal_entries: set[str] = set()
    for collection in ("class_removals", "resource_removals"):
        for row in plan[collection]:
            entry = str(row["entry"])
            if entry in removal_entries:
                raise DependencyRuntimeSubstitutionApplyError(
                    f"substitution plan removes entry twice: {entry}"
                )
            if entry not in bundled:
                raise DependencyRuntimeSubstitutionApplyError(
                    f"planned removal is absent from bundled preimage: {entry}"
                )
            removal_entries.add(entry)
    return {
        name: payload
        for name, payload in bundled.items()
        if name not in removal_entries
    }


def _postimage_material(
    plan: dict[str, Any],
    *,
    residual_sha256: str,
    residual_entry_count: int,
    official_rows: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "runtime_substitution_plan_id": plan[
            "runtime_substitution_plan_id"
        ],
        "bundled_jar_sha256": plan["bundled_jar_sha256"],
        "residual_capsule_sha256": residual_sha256,
        "residual_entry_count": residual_entry_count,
        "official_artifacts": official_rows,
        "class_removal_count": plan["summary"][
            "class_removal_count"
        ],
        "resource_removal_count": plan["summary"][
            "resource_removal_count"
        ],
    }


def _verify_dependency_runtime_substitution_postimage(
    private_plan_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    out_dir: Path,
    *,
    require_verified_marker: bool,
) -> dict[str, Any]:
    plan = _load_private_plan(private_plan_path.resolve())
    verify_private_substitution_plan(plan)

    bundled_jar = bundled_jar.resolve()
    if _sha256_file(bundled_jar) != str(
        plan["bundled_jar_sha256"]
    ).lower():
        raise DependencyRuntimeSubstitutionApplyError(
            "bundled/readable JAR SHA differs from substitution plan"
        )
    supplied, required = _required_artifact_map(
        plan,
        official_artifacts,
    )
    expected_residual = _expected_residual_payloads(
        plan,
        bundled_jar,
    )

    out_dir = out_dir.resolve()
    residual_path = out_dir / _RESIDUAL_NAME
    manifest_path = out_dir / _MANIFEST_NAME
    if not residual_path.is_file() or not manifest_path.is_file():
        raise DependencyRuntimeSubstitutionApplyError(
            "substitution postimage is incomplete"
        )

    actual_residual = _zip_payloads(residual_path)
    if actual_residual != expected_residual:
        raise DependencyRuntimeSubstitutionApplyError(
            "residual capsule bytes differ from exact expected retained entries"
        )

    official_rows: list[dict[str, str]] = []
    for artifact in sorted(required):
        copied = out_dir / "official" / artifact
        if not copied.is_file():
            raise DependencyRuntimeSubstitutionApplyError(
                f"postimage missing official artifact: {artifact}"
            )
        copied_sha = _sha256_file(copied)
        if copied_sha != required[artifact]:
            raise DependencyRuntimeSubstitutionApplyError(
                f"postimage official artifact SHA drifted: {artifact}"
            )
        if copied.read_bytes() != supplied[artifact].read_bytes():
            raise DependencyRuntimeSubstitutionApplyError(
                f"postimage official artifact bytes drifted: {artifact}"
            )
        official_rows.append(
            {
                "artifact": artifact,
                "sha256": copied_sha,
            }
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyRuntimeSubstitutionApplyError(
            "invalid substitution postimage manifest"
        ) from exc
    if manifest.get("kind") != "dependency_runtime_substitution_postimage":
        raise DependencyRuntimeSubstitutionApplyError(
            "unexpected substitution postimage manifest kind"
        )

    residual_sha = _sha256_file(residual_path)
    material = _postimage_material(
        plan,
        residual_sha256=residual_sha,
        residual_entry_count=len(actual_residual),
        official_rows=official_rows,
    )
    postimage_id = (
        "DEPRUNTIMEPOSTIMAGE_"
        + _stable_digest(material)[:20].upper()
    )
    if manifest.get("runtime_postimage_id") != postimage_id:
        raise DependencyRuntimeSubstitutionApplyError(
            "substitution postimage ID does not verify"
        )
    if manifest.get("runtime_substitution_plan_id") != plan.get(
        "runtime_substitution_plan_id"
    ):
        raise DependencyRuntimeSubstitutionApplyError(
            "postimage is bound to a different substitution plan"
        )
    if manifest.get("residual_capsule_sha256") != residual_sha:
        raise DependencyRuntimeSubstitutionApplyError(
            "postimage residual capsule SHA does not verify"
        )
    if manifest.get("official_artifacts") != official_rows:
        raise DependencyRuntimeSubstitutionApplyError(
            "postimage official artifact manifest does not verify"
        )
    if require_verified_marker and manifest.get("verified") is not True:
        raise DependencyRuntimeSubstitutionApplyError(
            "postimage manifest is not marked verified"
        )
    return manifest


def verify_dependency_runtime_substitution_postimage(
    private_plan_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    out_dir: Path,
) -> dict[str, Any]:
    return _verify_dependency_runtime_substitution_postimage(
        private_plan_path,
        bundled_jar,
        official_artifacts,
        out_dir,
        require_verified_marker=True,
    )


def apply_dependency_runtime_substitution(
    private_plan_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    out_dir: Path,
) -> dict[str, Any]:
    plan = _load_private_plan(private_plan_path.resolve())
    verify_private_substitution_plan(plan)

    bundled_jar = bundled_jar.resolve()
    if not bundled_jar.is_file():
        raise DependencyRuntimeSubstitutionApplyError(
            "bundled/readable JAR does not exist"
        )
    if _sha256_file(bundled_jar) != str(
        plan["bundled_jar_sha256"]
    ).lower():
        raise DependencyRuntimeSubstitutionApplyError(
            "bundled/readable JAR SHA differs from substitution plan"
        )
    supplied, required = _required_artifact_map(
        plan,
        official_artifacts,
    )
    residual_payloads = _expected_residual_payloads(
        plan,
        bundled_jar,
    )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise DependencyRuntimeSubstitutionApplyError(
            "output directory must be absent or empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    residual_path = out_dir / _RESIDUAL_NAME
    _write_deterministic_jar(residual_payloads, residual_path)

    official_dir = out_dir / "official"
    official_dir.mkdir(parents=True, exist_ok=True)
    official_rows: list[dict[str, str]] = []
    for artifact in sorted(required):
        destination = official_dir / artifact
        shutil.copyfile(supplied[artifact], destination)
        copied_sha = _sha256_file(destination)
        if copied_sha != required[artifact]:
            raise DependencyRuntimeSubstitutionApplyError(
                f"copied official artifact SHA drifted: {artifact}"
            )
        official_rows.append(
            {
                "artifact": artifact,
                "sha256": copied_sha,
            }
        )

    residual_sha = _sha256_file(residual_path)
    material = _postimage_material(
        plan,
        residual_sha256=residual_sha,
        residual_entry_count=len(residual_payloads),
        official_rows=official_rows,
    )
    postimage_id = (
        "DEPRUNTIMEPOSTIMAGE_"
        + _stable_digest(material)[:20].upper()
    )
    manifest = {
        "schema_version": 1,
        "kind": "dependency_runtime_substitution_postimage",
        "runtime_postimage_id": postimage_id,
        "runtime_substitution_plan_id": plan[
            "runtime_substitution_plan_id"
        ],
        "bundled_jar_sha256": plan["bundled_jar_sha256"],
        "residual_capsule": _RESIDUAL_NAME,
        "residual_capsule_sha256": residual_sha,
        "residual_entry_count": len(residual_payloads),
        "class_removal_count": plan["summary"][
            "class_removal_count"
        ],
        "resource_removal_count": plan["summary"][
            "resource_removal_count"
        ],
        "official_artifacts": official_rows,
        "runtime_classpath": [
            _RESIDUAL_NAME,
            *[
                f"official/{row['artifact']}"
                for row in official_rows
            ],
        ],
        "verified": False,
        "note": (
            "Official artifacts remain separate classpath JARs. "
            "The residual capsule contains only exact retained bundled entries."
        ),
    }
    manifest_path = out_dir / _MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    _verify_dependency_runtime_substitution_postimage(
        private_plan_path,
        bundled_jar,
        official_artifacts,
        out_dir,
        require_verified_marker=False,
    )
    manifest["verified"] = True
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return verify_dependency_runtime_substitution_postimage(
        private_plan_path,
        bundled_jar,
        official_artifacts,
        out_dir,
    )
