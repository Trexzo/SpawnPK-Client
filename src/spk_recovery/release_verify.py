from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .release_manifest import (
    RecoveryReleaseError,
    build_recovery_release_manifest,
)


class RecoveryReleaseVerificationError(ValueError):
    pass


def _exact_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise RecoveryReleaseVerificationError(
                f"duplicate JSON key: {key!r}"
            )
        out[key] = value
    return out


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_tree_digest(root: Path) -> str:
    if not root.is_dir():
        raise RecoveryReleaseVerificationError(
            f"source root does not exist: {root}"
        )
    files = sorted(root.rglob("*.java"))
    if not files:
        raise RecoveryReleaseVerificationError(
            "source root contains no Java files"
        )
    h = hashlib.sha256()
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def _probe_version(command: str) -> dict[str, Any]:
    resolved = shutil.which(command)
    if resolved is None:
        return {
            "available": False,
            "requested_command": command,
            "resolved_path": None,
            "binary_sha256": None,
            "version_output": None,
        }
    path = Path(resolved).resolve()
    proc = subprocess.run(
        [str(path), "-version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        return {
            "available": False,
            "requested_command": command,
            "resolved_path": str(path),
            "binary_sha256": (
                _sha256_file(path) if path.is_file() else None
            ),
            "version_output": (proc.stdout + proc.stderr).strip(),
        }
    return {
        "available": True,
        "requested_command": command,
        "resolved_path": str(path),
        "binary_sha256": (
            _sha256_file(path) if path.is_file() else None
        ),
        "version_output": (proc.stdout + proc.stderr).strip(),
    }


def _check(
    checks: list[dict[str, Any]],
    *,
    name: str,
    expected: Any,
    actual: Any,
    required: bool = True,
) -> None:
    passed = expected == actual
    checks.append(
        {
            "name": name,
            "required": required,
            "passed": passed,
            "expected": expected,
            "actual": actual,
        }
    )



def _load_json_authority(
    path: Path,
    *,
    label: str,
    kind: str,
) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise RecoveryReleaseVerificationError(
            f"{label} does not exist: {resolved}"
        )
    try:
        data = json.loads(
            resolved.read_text(encoding="utf-8"),
            object_pairs_hook=_exact_object,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryReleaseVerificationError(
            f"{label} is not valid JSON"
        ) from exc
    if data.get("kind") != kind:
        raise RecoveryReleaseVerificationError(
            f"{label} has unexpected kind: {data.get('kind')!r}"
        )
    return data


def _sha_list(value: Any, *, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(
            not isinstance(item, str) or not item
            for item in value
        )
    ):
        raise RecoveryReleaseVerificationError(
            f"{label} must be a non-empty SHA-256 list"
        )
    normalized = [item.lower() for item in value]
    if any(
        len(item) != 64
        or any(ch not in "0123456789abcdef" for ch in item)
        for item in normalized
    ):
        raise RecoveryReleaseVerificationError(
            f"{label} contains an invalid SHA-256"
        )
    if len(set(normalized)) != len(normalized):
        raise RecoveryReleaseVerificationError(
            f"{label} contains duplicate SHA-256 values"
        )
    return sorted(normalized)


def _artifact_row_sha_list(
    rows: Any,
    *,
    label: str,
) -> list[str]:
    if not isinstance(rows, list) or not rows:
        raise RecoveryReleaseVerificationError(
            f"{label} must contain official artifact rows"
        )
    values: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise RecoveryReleaseVerificationError(
                f"{label} contains a malformed artifact row"
            )
        sha = row.get("sha256")
        if not isinstance(sha, str) or not sha:
            raise RecoveryReleaseVerificationError(
                f"{label} artifact row lacks sha256"
            )
        values.append(sha)
    return _sha_list(values, label=label)


def verify_recovery_release(
    release_manifest: dict[str, Any],
    authority_index: dict[str, Any],
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    readable_manifest: dict[str, Any],
    recovered_source_manifest: dict[str, Any],
    clean_rebuild_report: dict[str, Any],
    roundtrip_report: dict[str, Any],
    *,
    source_rewrite_acceptance: dict[str, Any] | None = None,
    authority_jar: Path | None = None,
    readable_jar: Path | None = None,
    decompiler_jar: Path | None = None,
    source_root: Path | None = None,
    javac_command: str | None = None,
    private_collision_plan_path: Path | None = None,
    official_overlay_manifest_path: Path | None = None,
    official_overlay_source_root: Path | None = None,
    private_dependency_replacement_plan_path: Path | None = None,
    private_dependency_reverse_plan_path: Path | None = None,
    official_artifacts: list[Path] | None = None,
) -> dict[str, Any]:
    if (
        release_manifest.get("schema_version") != 1
        or release_manifest.get("kind")
        != "recovery_release_manifest"
    ):
        raise RecoveryReleaseVerificationError(
            "unsupported recovery release manifest"
        )

    try:
        recomputed = build_recovery_release_manifest(
            authority_index,
            class_lineage,
            member_lineage,
            readable_manifest,
            recovered_source_manifest,
            clean_rebuild_report,
            roundtrip_report,
            source_rewrite_acceptance=source_rewrite_acceptance,
        )
    except RecoveryReleaseError as exc:
        raise RecoveryReleaseVerificationError(str(exc)) from exc

    checks: list[dict[str, Any]] = []
    _check(
        checks,
        name="release_manifest_exact_reproduction",
        expected=release_manifest,
        actual=recomputed,
    )

    if authority_jar is not None:
        path = authority_jar.resolve()
        if not path.is_file():
            raise RecoveryReleaseVerificationError(
                f"authority JAR does not exist: {path}"
            )
        _check(
            checks,
            name="authority_jar_sha256",
            expected=str(
                release_manifest.get("authority_sha256", "")
            ).lower(),
            actual=_sha256_file(path),
        )

    if readable_jar is not None:
        path = readable_jar.resolve()
        if not path.is_file():
            raise RecoveryReleaseVerificationError(
                f"readable JAR does not exist: {path}"
            )
        _check(
            checks,
            name="readable_jar_sha256",
            expected=str(
                release_manifest.get(
                    "readable_jar_sha256",
                    "",
                )
            ).lower(),
            actual=_sha256_file(path),
        )

    if decompiler_jar is not None:
        path = decompiler_jar.resolve()
        if not path.is_file():
            raise RecoveryReleaseVerificationError(
                f"decompiler JAR does not exist: {path}"
            )
        _check(
            checks,
            name="decompiler_jar_sha256",
            expected=str(
                recovered_source_manifest.get(
                    "decompiler_sha256",
                    "",
                )
            ).lower(),
            actual=_sha256_file(path),
        )

    if source_root is not None:
        _check(
            checks,
            name="final_source_tree_sha256",
            expected=str(
                release_manifest.get(
                    "final_source_tree_sha256",
                    "",
                )
            ).lower(),
            actual=_source_tree_digest(
                source_root.resolve()
            ),
        )

    toolchain: dict[str, Any] | None = None
    if javac_command is not None:
        expected_javac = (
            clean_rebuild_report.get("compiler", {})
            .get("javac", {})
        )
        if not isinstance(expected_javac, dict):
            raise RecoveryReleaseVerificationError(
                "clean rebuild report lacks compiler.javac metadata"
            )
        toolchain = _probe_version(javac_command)
        _check(
            checks,
            name="javac_available",
            expected=True,
            actual=toolchain["available"],
        )
        if toolchain["available"]:
            _check(
                checks,
                name="javac_version_output",
                expected=expected_javac.get(
                    "version_output"
                ),
                actual=toolchain.get(
                    "version_output"
                ),
            )
            expected_binary_sha = expected_javac.get(
                "binary_sha256"
            )
            if expected_binary_sha:
                _check(
                    checks,
                    name="javac_binary_sha256",
                    expected=expected_binary_sha,
                    actual=toolchain.get(
                        "binary_sha256"
                    ),
                )

    compile_transport = clean_rebuild_report.get(
        "compile_transport"
    )
    collision_mode = (
        isinstance(compile_transport, dict)
        and compile_transport.get("mode")
        == "collision_derived_remap"
    )

    if collision_mode:
        _check(
            checks,
            name="collision_private_plan_supplied",
            expected=True,
            actual=private_collision_plan_path is not None,
        )

        _check(
            checks,
            name="collision_plan_id_authority",
            expected=recovered_source_manifest.get(
                "collision_plan_id"
            ),
            actual=compile_transport.get(
                "collision_plan_id"
            ),
        )
        _check(
            checks,
            name="collision_report_id_authority",
            expected=recovered_source_manifest.get(
                "collision_report_id"
            ),
            actual=compile_transport.get(
                "collision_report_id"
            ),
        )
        _check(
            checks,
            name="collision_transform_id_authority",
            expected=recovered_source_manifest.get(
                "collision_transform_id"
            ),
            actual=compile_transport.get(
                "collision_transform_id"
            ),
        )
        _check(
            checks,
            name="collision_base_readable_authority",
            expected=str(
                recovered_source_manifest.get(
                    "base_readable_jar_sha256",
                    "",
                )
            ).lower(),
            actual=str(
                clean_rebuild_report.get(
                    "readable_jar_sha256",
                    "",
                )
            ).lower(),
        )

        if private_collision_plan_path is not None:
            plan_path = private_collision_plan_path.resolve()
            if not plan_path.is_file():
                raise RecoveryReleaseVerificationError(
                    "private collision plan does not exist: "
                    + str(plan_path)
                )
            try:
                private_plan = json.loads(
                    plan_path.read_text(encoding="utf-8"),
                    object_pairs_hook=_exact_object,
                )
            except (
                OSError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                raise RecoveryReleaseVerificationError(
                    "private collision plan is not valid JSON"
                ) from exc

            _check(
                checks,
                name="collision_private_plan_kind",
                expected=(
                    "class_package_namespace_collision_plan"
                ),
                actual=private_plan.get("kind"),
            )
            _check(
                checks,
                name="collision_private_plan_id",
                expected=compile_transport.get(
                    "collision_plan_id"
                ),
                actual=private_plan.get("plan_id"),
            )
            _check(
                checks,
                name="collision_private_plan_report_id",
                expected=compile_transport.get(
                    "collision_report_id"
                ),
                actual=private_plan.get(
                    "collision_report_id"
                ),
            )
            _check(
                checks,
                name="collision_private_plan_readable_sha256",
                expected=str(
                    recovered_source_manifest.get(
                        "base_readable_jar_sha256",
                        "",
                    )
                ).lower(),
                actual=str(
                    private_plan.get(
                        "readable_jar_sha256",
                        "",
                    )
                ).lower(),
            )
            _check(
                checks,
                name="collision_private_plan_sha256",
                expected=str(
                    compile_transport.get(
                        "collision_plan_sha256",
                        "",
                    )
                ).lower(),
                actual=_sha256_file(plan_path),
            )

    official_first_mode = (
        isinstance(compile_transport, dict)
        and compile_transport.get("mode")
        == "official_first_restored"
    )
    official_inputs_supplied = any(
        value is not None
        for value in (
            official_overlay_manifest_path,
            official_overlay_source_root,
            private_dependency_replacement_plan_path,
            private_dependency_reverse_plan_path,
            official_artifacts,
        )
    )

    if not official_first_mode and official_inputs_supplied:
        raise RecoveryReleaseVerificationError(
            "official-first verification inputs require "
            "official_first_restored compile transport"
        )

    if official_first_mode:
        _check(
            checks,
            name="official_overlay_manifest_supplied",
            expected=True,
            actual=official_overlay_manifest_path is not None,
        )
        _check(
            checks,
            name="official_overlay_source_root_supplied",
            expected=True,
            actual=official_overlay_source_root is not None,
        )
        _check(
            checks,
            name="official_private_replacement_plan_supplied",
            expected=True,
            actual=private_dependency_replacement_plan_path is not None,
        )
        _check(
            checks,
            name="official_private_reverse_plan_supplied",
            expected=True,
            actual=private_dependency_reverse_plan_path is not None,
        )
        _check(
            checks,
            name="official_artifacts_supplied",
            expected=True,
            actual=bool(official_artifacts),
        )

        transport_artifacts = _sha_list(
            compile_transport.get("official_artifact_sha256"),
            label="compile transport official_artifact_sha256",
        )
        bundled_authority = str(
            clean_rebuild_report.get("readable_jar_sha256", "")
        ).lower()
        canonical_source_authority = str(
            clean_rebuild_report.get("source_tree_sha256", "")
        ).lower()

        overlay: dict[str, Any] | None = None
        if official_overlay_manifest_path is not None:
            overlay = _load_json_authority(
                official_overlay_manifest_path,
                label="official overlay manifest",
                kind="dependency_source_overlay_manifest",
            )
            _check(
                checks,
                name="official_overlay_id",
                expected=compile_transport.get("overlay_id"),
                actual=overlay.get("overlay_id"),
            )
            _check(
                checks,
                name="official_overlay_replacement_plan_id",
                expected=compile_transport.get("replacement_plan_id"),
                actual=overlay.get("replacement_plan_id"),
            )
            _check(
                checks,
                name="official_overlay_canonical_source_tree_sha256",
                expected=canonical_source_authority,
                actual=str(
                    overlay.get("input_source_tree_sha256", "")
                ).lower(),
            )
            _check(
                checks,
                name="official_overlay_bundled_readable_sha256",
                expected=bundled_authority,
                actual=str(
                    overlay.get("bundled_jar_sha256", "")
                ).lower(),
            )
            _check(
                checks,
                name="official_overlay_artifact_sha256",
                expected=transport_artifacts,
                actual=_sha_list(
                    overlay.get("official_artifact_sha256"),
                    label="overlay official_artifact_sha256",
                ),
            )

        if official_overlay_source_root is not None:
            overlay_root = official_overlay_source_root.resolve()
            if not overlay_root.is_dir():
                raise RecoveryReleaseVerificationError(
                    "official overlay source root does not exist: "
                    + str(overlay_root)
                )
            actual_overlay_tree = _source_tree_digest(overlay_root)
            expected_overlay_tree = (
                str(
                    overlay.get("output_source_tree_sha256", "")
                ).lower()
                if overlay is not None
                else None
            )
            _check(
                checks,
                name="official_overlay_source_tree_sha256",
                expected=expected_overlay_tree,
                actual=actual_overlay_tree,
            )

        replacement: dict[str, Any] | None = None
        if private_dependency_replacement_plan_path is not None:
            replacement = _load_json_authority(
                private_dependency_replacement_plan_path,
                label="private dependency replacement plan",
                kind="dependency_replacement_boundary_plan",
            )
            _check(
                checks,
                name="official_private_replacement_identifiers",
                expected=True,
                actual=replacement.get("identifiers_included"),
            )
            _check(
                checks,
                name="official_private_replacement_plan_id",
                expected=compile_transport.get("replacement_plan_id"),
                actual=replacement.get("replacement_plan_id"),
            )
            _check(
                checks,
                name="official_private_replacement_bundled_readable_sha256",
                expected=bundled_authority,
                actual=str(
                    replacement.get("bundled_jar_sha256", "")
                ).lower(),
            )
            _check(
                checks,
                name="official_private_replacement_artifact_sha256",
                expected=transport_artifacts,
                actual=_artifact_row_sha_list(
                    replacement.get("official_artifacts"),
                    label="private replacement official_artifacts",
                ),
            )

        if private_dependency_reverse_plan_path is not None:
            reverse = _load_json_authority(
                private_dependency_reverse_plan_path,
                label="private dependency reverse plan",
                kind="dependency_reverse_compile_transport_plan",
            )
            _check(
                checks,
                name="official_private_reverse_identifiers",
                expected=True,
                actual=reverse.get("identifiers_included"),
            )
            _check(
                checks,
                name="official_private_reverse_plan_id",
                expected=compile_transport.get("reverse_plan_id"),
                actual=reverse.get("reverse_plan_id"),
            )
            _check(
                checks,
                name="official_private_reverse_replacement_plan_id",
                expected=compile_transport.get("replacement_plan_id"),
                actual=reverse.get("replacement_plan_id"),
            )
            _check(
                checks,
                name="official_private_reverse_bundled_readable_sha256",
                expected=bundled_authority,
                actual=str(
                    reverse.get("bundled_jar_sha256", "")
                ).lower(),
            )
            _check(
                checks,
                name="official_private_reverse_bytecode_restore_ready",
                expected=True,
                actual=reverse.get("summary", {}).get(
                    "ready_for_bytecode_restore"
                ),
            )

        if official_artifacts:
            actual_artifacts: list[str] = []
            for artifact in official_artifacts:
                resolved = artifact.resolve()
                if not resolved.is_file():
                    raise RecoveryReleaseVerificationError(
                        "official dependency artifact does not exist: "
                        + str(resolved)
                    )
                actual_artifacts.append(_sha256_file(resolved))
            _check(
                checks,
                name="official_artifact_file_sha256",
                expected=transport_artifacts,
                actual=sorted(actual_artifacts),
            )

    required_failures = [
        row
        for row in checks
        if row["required"] and not row["passed"]
    ]
    verified = len(required_failures) == 0

    material = {
        "release_id": release_manifest.get("release_id"),
        "checks": [
            (
                row["name"],
                row["required"],
                row["passed"],
                row["expected"],
                row["actual"],
            )
            for row in checks
        ],
    }
    verification_id = (
        "REPRO_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "recovery_release_verification",
        "verification_id": verification_id,
        "release_id": release_manifest.get("release_id"),
        "release_ready": bool(
            release_manifest.get("ready_for_release")
        ),
        "verified": verified,
        "required_check_count": sum(
            1 for row in checks if row["required"]
        ),
        "failed_required_check_count": len(
            required_failures
        ),
        "checks": checks,
        "toolchain_probe": toolchain,
        "note": (
            (
                "verified means the supplied official-first release manifest "
                "reproduces exactly, its overlay source tree, private replacement "
                "and reverse plans, and exact official artifact bytes match the "
                "clean-build transport authority, and all explicitly supplied "
                "artifact/toolchain checks match their recorded pins."
            )
            if official_first_mode
            else (
                (
                    "verified means the supplied collision-derived release "
                    "manifest reproduces exactly, the private collision plan "
                    "matches its recorded plan/report/readable/SHA authority, "
                    "and all explicitly supplied on-disk artifacts/toolchain "
                    "checks match their recorded pins."
                )
                if collision_mode
                else (
                    "verified means the supplied release manifest reproduces "
                    "exactly from its authority documents and all explicitly "
                    "supplied on-disk artifacts/toolchain checks match their "
                    "recorded pins."
                )
            )
        ),
    }


def write_recovery_release_verification(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
