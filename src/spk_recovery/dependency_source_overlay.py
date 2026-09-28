from __future__ import annotations

import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .decompiler import sha256_file
from .dependency_artifact_proof import (
    DependencyArtifactProofError,
    _artifact_index,
)
from .dependency_source_binding import _artifact_key
from .source_digest import source_tree_digest


class DependencySourceOverlayError(ValueError):
    pass


_DIRECT_EDIT_ACTIONS = {
    "class_type_rename_required",
    "member_name_rename_required",
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
        raise DependencySourceOverlayError(
            f"invalid JSON authority: {path}"
        ) from exc
    if data.get("kind") != kind:
        raise DependencySourceOverlayError(
            f"{path}: expected kind {kind!r}, "
            f"got {data.get('kind')!r}"
        )
    return data


def _helper_source() -> Path:
    path = (
        Path(__file__).resolve().parent
        / "java"
        / "DependencySourceOverlay.java"
    )
    if not path.is_file():
        raise DependencySourceOverlayError(
            f"missing packaged dependency overlay helper: {path}"
        )
    return path


def _require(command: str) -> str:
    candidate = Path(command)
    if candidate.is_absolute():
        if not candidate.is_file():
            raise DependencySourceOverlayError(
                f"required executable missing: {candidate}"
            )
        return str(candidate)
    found = shutil.which(command)
    if found is None:
        raise DependencySourceOverlayError(
            f"required executable not found on PATH: {command}"
        )
    return found


def _b64(value: str | None) -> str:
    text = value or ""
    return base64.urlsafe_b64encode(
        text.encode("utf-8")
    ).decode("ascii").rstrip("=")


def _official_source_name(
    internal_name: str,
    official: dict[str, Any],
    *,
    seen: set[str] | None = None,
) -> str:
    parsed = official.get(internal_name)
    if parsed is None:
        raise DependencySourceOverlayError(
            f"official target class missing: {internal_name}"
        )

    active = set(seen or set())
    if internal_name in active:
        raise DependencySourceOverlayError(
            "official InnerClasses metadata cycle"
        )
    active.add(internal_name)

    outer = parsed.inner_outer_name
    simple = parsed.inner_simple_name
    if outer is not None:
        if not simple:
            raise DependencySourceOverlayError(
                f"anonymous/local official class is not source-nameable: "
                f"{internal_name}"
            )
        return (
            _official_source_name(
                outer,
                official,
                seen=active,
            )
            + "."
            + simple
        )

    return internal_name.replace("/", ".")


def _compile_helper(
    classes: Path,
    *,
    javac: str,
) -> None:
    classes.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            javac,
            "--add-modules",
            "jdk.compiler",
            "-d",
            str(classes),
            str(_helper_source()),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise DependencySourceOverlayError(
            "dependency source overlay helper compilation failed:\n"
            + proc.stdout
            + proc.stderr
        )


def _write_targets(
    obligations: list[dict[str, Any]],
    official: dict[str, Any],
    out: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for obligation in obligations:
        action = str(obligation.get("action"))
        if action not in _DIRECT_EDIT_ACTIONS:
            continue

        required_strings = (
            "edit_binding_id",
            "source_file",
            "element_kind",
            "old_owner",
            "old_name",
            "old_descriptor",
        )
        for key in required_strings:
            if not isinstance(obligation.get(key), str):
                raise DependencySourceOverlayError(
                    f"direct edit obligation lacks {key}"
                )

        start = obligation.get("start")
        end = obligation.get("end")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or end < start
        ):
            raise DependencySourceOverlayError(
                "direct edit obligation has invalid source span"
            )

        if action == "class_type_rename_required":
            new_owner = obligation.get("new_owner")
            if not isinstance(new_owner, str) or not new_owner:
                raise DependencySourceOverlayError(
                    "class edit lacks new_owner"
                )
            new_text = _official_source_name(
                new_owner,
                official,
            )
        else:
            new_name = obligation.get("new_name")
            if not isinstance(new_name, str) or not new_name:
                raise DependencySourceOverlayError(
                    "member edit lacks new_name"
                )
            if new_name.startswith("<"):
                raise DependencySourceOverlayError(
                    "special JVM method cannot be source-name edited"
                )
            new_text = new_name

        row = {
            "binding_id": obligation["edit_binding_id"],
            "source_file": obligation["source_file"],
            "start": start,
            "end": end,
            "action": action,
            "element_kind": obligation["element_kind"],
            "old_owner": obligation["old_owner"],
            "old_name": obligation["old_name"],
            "old_descriptor": obligation["old_descriptor"],
            "new_text": new_text,
        }
        rows.append(row)

    rows.sort(
        key=lambda row: (
            row["source_file"],
            row["start"],
            row["end"],
            row["binding_id"],
        )
    )

    lines = [
        "\t".join(
            [
                "E",
                _b64(str(row["binding_id"])),
                _b64(str(row["source_file"])),
                str(row["start"]),
                str(row["end"]),
                _b64(str(row["action"])),
                _b64(str(row["element_kind"])),
                _b64(str(row["old_owner"])),
                _b64(str(row["old_name"])),
                _b64(str(row["old_descriptor"])),
                _b64(str(row["new_text"])),
            ]
        )
        for row in rows
    ]
    out.write_text(
        ("\n".join(lines) + "\n") if lines else "",
        encoding="utf-8",
    )
    return rows


def _parse_helper_output(stdout: str) -> dict[str, int]:
    expected = {
        "planned_edits",
        "applied_edits",
        "files_changed",
        "pre_diagnostic_errors",
        "post_diagnostic_errors",
    }
    values: dict[str, int] = {}
    passed = False
    for line in stdout.splitlines():
        if line.strip() == "SPK_DEPENDENCY_SOURCE_OVERLAY_PASS":
            passed = True
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key not in expected:
            continue
        try:
            values[key] = int(value)
        except ValueError as exc:
            raise DependencySourceOverlayError(
                f"invalid overlay helper counter: {line!r}"
            ) from exc

    if not passed:
        raise DependencySourceOverlayError(
            "overlay helper exited without PASS marker"
        )
    missing = expected - set(values)
    if missing:
        raise DependencySourceOverlayError(
            f"overlay helper omitted counters: {sorted(missing)!r}"
        )
    return values


def apply_dependency_source_overlay(
    source_root: Path,
    private_edit_plan_path: Path,
    private_replacement_plan_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    out_dir: Path,
    java_command: str = "java",
    javac_command: str = "javac",
) -> dict[str, Any]:
    source_root = source_root.resolve()
    private_edit_plan_path = private_edit_plan_path.resolve()
    private_replacement_plan_path = (
        private_replacement_plan_path.resolve()
    )
    bundled_jar = bundled_jar.resolve()
    out_dir = out_dir.resolve()

    if not source_root.is_dir():
        raise DependencySourceOverlayError(
            "source root does not exist"
        )
    if not bundled_jar.is_file():
        raise DependencySourceOverlayError(
            "bundled JAR does not exist"
        )

    plan = _load_json(
        private_edit_plan_path,
        kind="dependency_source_edit_obligation_plan",
    )
    replacement = _load_json(
        private_replacement_plan_path,
        kind="dependency_replacement_boundary_plan",
    )

    if plan.get("identifiers_included") is not True:
        raise DependencySourceOverlayError(
            "requires private identifier-bearing DEPSRCEDIT plan"
        )
    if replacement.get("identifiers_included") is not True:
        raise DependencySourceOverlayError(
            "requires private identifier-bearing DEPREPLACE plan"
        )
    if plan.get("replacement_plan_id") != replacement.get(
        "replacement_plan_id"
    ):
        raise DependencySourceOverlayError(
            "DEPSRCEDIT is bound to a different DEPREPLACE"
        )
    if plan.get("dependency_remap_proof_id") != replacement.get(
        "dependency_remap_proof_id"
    ):
        raise DependencySourceOverlayError(
            "DEPSRCEDIT/DEPREPLACE remap authority differs"
        )
    bundled_sha = sha256_file(bundled_jar)
    if plan.get("bundled_jar_sha256") != bundled_sha:
        raise DependencySourceOverlayError(
            "DEPSRCEDIT bundled JAR authority drifted"
        )
    if replacement.get("bundled_jar_sha256") != bundled_sha:
        raise DependencySourceOverlayError(
            "DEPREPLACE bundled JAR authority drifted"
        )
    if plan.get("summary", {}).get(
        "ready_for_source_overlay"
    ) is not True:
        raise DependencySourceOverlayError(
            "DEPSRCEDIT is not ready for source overlay"
        )

    input_sha, input_files, input_bytes = source_tree_digest(
        source_root
    )
    if plan.get("source_tree_sha256") != input_sha:
        raise DependencySourceOverlayError(
            "source tree SHA does not match DEPSRCEDIT"
        )

    release = replacement.get("java_release")
    if (
        not isinstance(release, int)
        or isinstance(release, bool)
        or release < 1
    ):
        raise DependencySourceOverlayError(
            "DEPREPLACE has invalid java_release"
        )

    try:
        official, _artifact_owners, artifact_rows = _artifact_index(
            official_artifacts,
            java_release=release,
        )
    except DependencyArtifactProofError as exc:
        raise DependencySourceOverlayError(str(exc)) from exc

    if replacement.get("official_artifacts") is None:
        raise DependencySourceOverlayError(
            "private DEPREPLACE lacks official artifact rows"
        )
    if _artifact_key(
        list(replacement.get("official_artifacts", []))
    ) != _artifact_key(artifact_rows):
        raise DependencySourceOverlayError(
            "official artifact set disagrees with DEPREPLACE"
        )

    resolved_artifacts = [
        path.resolve()
        for path in official_artifacts
    ]
    for path in resolved_artifacts:
        if not path.is_file():
            raise DependencySourceOverlayError(
                f"official artifact missing: {path}"
            )

    if out_dir.exists() and any(out_dir.iterdir()):
        raise DependencySourceOverlayError(
            "overlay output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    overlay_root = out_dir / "src"
    shutil.copytree(source_root, overlay_root)

    java = _require(java_command)
    javac = _require(javac_command)

    obligations = list(plan.get("obligations", []))

    try:
        with tempfile.TemporaryDirectory(
            prefix="spk-dependency-source-overlay-"
        ) as td:
            temp = Path(td)
            helper_classes = temp / "helper-classes"
            targets_path = temp / "targets.tsv"
            direct_rows = _write_targets(
                obligations,
                official,
                targets_path,
            )
            _compile_helper(
                helper_classes,
                javac=javac,
            )

            pre_classpath = [
                bundled_jar,
                *resolved_artifacts,
            ]
            post_classpath = [
                *resolved_artifacts,
                bundled_jar,
            ]

            proc = subprocess.run(
                [
                    java,
                    "--add-modules",
                    "jdk.compiler",
                    "-cp",
                    str(helper_classes),
                    "DependencySourceOverlay",
                    str(overlay_root),
                    str(targets_path),
                    os.pathsep.join(
                        str(path)
                        for path in pre_classpath
                    ),
                    os.pathsep.join(
                        str(path)
                        for path in post_classpath
                    ),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if proc.returncode != 0:
                raise DependencySourceOverlayError(
                    "dependency source overlay failed:\n"
                    + proc.stdout
                    + proc.stderr
                )
            counters = _parse_helper_output(proc.stdout)
    except Exception:
        shutil.rmtree(overlay_root, ignore_errors=True)
        raise

    if counters["planned_edits"] != len(direct_rows):
        shutil.rmtree(overlay_root, ignore_errors=True)
        raise DependencySourceOverlayError(
            "helper planned-edit count differs from DEPSRCEDIT"
        )
    if counters["applied_edits"] != len(direct_rows):
        shutil.rmtree(overlay_root, ignore_errors=True)
        raise DependencySourceOverlayError(
            "helper applied-edit count differs from DEPSRCEDIT"
        )

    output_sha, output_files, output_bytes = source_tree_digest(
        overlay_root
    )
    if len(output_files) != len(input_files):
        shutil.rmtree(overlay_root, ignore_errors=True)
        raise DependencySourceOverlayError(
            "Java source file count changed during overlay"
        )
    if direct_rows and output_sha == input_sha:
        shutil.rmtree(overlay_root, ignore_errors=True)
        raise DependencySourceOverlayError(
            "direct dependency edits produced no source-tree change"
        )
    if not direct_rows and output_sha != input_sha:
        shutil.rmtree(overlay_root, ignore_errors=True)
        raise DependencySourceOverlayError(
            "no-edit overlay changed source tree"
        )

    original_sha_after, _, _ = source_tree_digest(source_root)
    if original_sha_after != input_sha:
        shutil.rmtree(overlay_root, ignore_errors=True)
        raise DependencySourceOverlayError(
            "canonical input source tree was modified"
        )

    action_counts = Counter(
        str(row.get("action"))
        for row in obligations
    )
    artifact_sha_rows = [
        {
            "sha256": str(row["sha256"]),
            "java_release": row.get("java_release"),
        }
        for row in sorted(
            artifact_rows,
            key=lambda item: (
                str(item["sha256"]),
                str(item["artifact"]),
            ),
        )
    ]
    material = {
        "edit_plan_id": plan["edit_plan_id"],
        "replacement_plan_id": replacement[
            "replacement_plan_id"
        ],
        "input_source_tree_sha256": input_sha,
        "output_source_tree_sha256": output_sha,
        "bundled_jar_sha256": bundled_sha,
        "official_artifacts": artifact_sha_rows,
        "direct_edit_count": len(direct_rows),
        "action_counts": dict(sorted(action_counts.items())),
    }
    manifest = {
        "schema_version": 1,
        "kind": "dependency_source_overlay_manifest",
        "overlay_id": (
            "DEPSRCOVERLAY_"
            + _stable_digest(material)[:20].upper()
        ),
        "edit_plan_id": plan["edit_plan_id"],
        "binding_inventory_id": plan[
            "binding_inventory_id"
        ],
        "replacement_plan_id": replacement[
            "replacement_plan_id"
        ],
        "dependency_remap_proof_id": plan[
            "dependency_remap_proof_id"
        ],
        "input_source_tree_sha256": input_sha,
        "output_source_tree_sha256": output_sha,
        "java_file_count": len(output_files),
        "input_source_bytes": input_bytes,
        "output_source_bytes": output_bytes,
        "bundled_jar_sha256": bundled_sha,
        "java_release": release,
        "official_artifact_sha256": [
            row["sha256"]
            for row in artifact_sha_rows
        ],
        "summary": {
            "direct_edit_count": len(direct_rows),
            "files_changed": counters["files_changed"],
            "action_counts": dict(
                sorted(action_counts.items())
            ),
            "pre_diagnostic_error_count": counters[
                "pre_diagnostic_errors"
            ],
            "post_diagnostic_error_count": counters[
                "post_diagnostic_errors"
            ],
            "canonical_input_unchanged": True,
        },
        "source_directory": "src",
    }

    (out_dir / "dependency-source-overlay-manifest.json").write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest
