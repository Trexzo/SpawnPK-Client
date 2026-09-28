from __future__ import annotations

from collections import Counter
import base64
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
from .source_digest import source_tree_digest


class DependencySourceBindingError(ValueError):
    pass


_ACCEPTED_MEMBER_STATUSES = {
    "accepted_identity",
    "accepted_remap",
    "official_unbundled_direct",
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
        raise DependencySourceBindingError(
            f"invalid JSON authority: {path}"
        ) from exc
    if data.get("kind") != kind:
        raise DependencySourceBindingError(
            f"{path}: expected kind {kind!r}, "
            f"got {data.get('kind')!r}"
        )
    return data


def _helper_source() -> Path:
    path = (
        Path(__file__).resolve().parent
        / "java"
        / "DependencySourceBindingScanner.java"
    )
    if not path.is_file():
        raise DependencySourceBindingError(
            f"missing packaged source binding helper: {path}"
        )
    return path


def _require(command: str) -> str:
    candidate = Path(command)
    if candidate.is_absolute():
        if not candidate.is_file():
            raise DependencySourceBindingError(
                f"required executable missing: {candidate}"
            )
        return str(candidate)
    found = shutil.which(command)
    if found is None:
        raise DependencySourceBindingError(
            f"required executable not found on PATH: {command}"
        )
    return found


def _b64(value: str | None) -> str:
    text = value or ""
    return base64.urlsafe_b64encode(
        text.encode("utf-8")
    ).decode("ascii").rstrip("=")


def _decode(value: str) -> str:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(
        (value + padding).encode("ascii")
    ).decode("utf-8")


def _artifact_key(
    rows: list[dict[str, Any]],
) -> list[tuple[str, str, int, int | None]]:
    return sorted(
        (
            str(row.get("artifact")),
            str(row.get("sha256")),
            int(row.get("multi_release_class_count", 0)),
            (
                int(row["java_release"])
                if row.get("java_release") is not None
                else None
            ),
        )
        for row in rows
    )


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
        raise DependencySourceBindingError(
            "dependency source binding helper compilation failed:\n"
            + proc.stdout
            + proc.stderr
        )


def _mapping_rows(
    remap: dict[str, Any],
    replacement: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    if replacement.get("identifiers_included") is not True:
        raise DependencySourceBindingError(
            "requires private identifier-bearing DEPREPLACE plan"
        )

    owner_rows = list(replacement.get("owners", []))
    by_owner: dict[str, dict[str, Any]] = {}
    for row in owner_rows:
        owner = row.get("old_owner")
        if not isinstance(owner, str) or not owner:
            raise DependencySourceBindingError(
                "private DEPREPLACE owner row lacks old_owner"
            )
        if owner in by_owner:
            raise DependencySourceBindingError(
                f"duplicate DEPREPLACE owner: {owner}"
            )
        classification = str(row.get("classification"))
        if classification not in {
            "official_replaceable",
            "residual_bundled",
            "project_retained",
            "platform_runtime",
        }:
            raise DependencySourceBindingError(
                "unsupported DEPREPLACE classification"
            )
        by_owner[owner] = row

    member_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in remap.get("member_results", []):
        status = str(row.get("status"))
        if status not in _ACCEPTED_MEMBER_STATUSES:
            continue
        old_owner = str(row.get("old_owner"))
        owner_plan = by_owner.get(old_owner)
        if (
            owner_plan is None
            or owner_plan.get("classification")
            != "official_replaceable"
        ):
            continue

        old_name = str(row.get("old_name"))
        old_descriptor = str(row.get("old_descriptor"))
        new_owner = row.get("new_owner")
        new_name = row.get("new_name")
        new_descriptor = row.get("new_descriptor")
        if not all(
            isinstance(value, str) and value
            for value in (
                old_owner,
                old_name,
                old_descriptor,
                new_owner,
                new_name,
                new_descriptor,
            )
        ):
            raise DependencySourceBindingError(
                "accepted DEPREMAP row lacks exact old/new member identity"
            )

        key = (old_owner, old_name, old_descriptor)
        if key in seen:
            raise DependencySourceBindingError(
                f"duplicate accepted DEPREMAP member key: {key!r}"
            )
        seen.add(key)
        material = {
            "old_owner": old_owner,
            "old_name": old_name,
            "old_descriptor": old_descriptor,
            "new_owner": new_owner,
            "new_name": new_name,
            "new_descriptor": new_descriptor,
        }
        member_rows.append(
            {
                "member_id": (
                    "DEPMEMBER_"
                    + _stable_digest(material)[:20].upper()
                ),
                **material,
            }
        )

    owner_rows.sort(key=lambda row: str(row["old_owner"]))
    member_rows.sort(
        key=lambda row: (
            row["old_owner"],
            row["old_name"],
            row["old_descriptor"],
        )
    )
    return owner_rows, member_rows


def _write_mapping(
    owners: list[dict[str, Any]],
    members: list[dict[str, Any]],
    out: Path,
) -> None:
    lines: list[str] = []
    for row in owners:
        lines.append(
            "\t".join(
                [
                    "O",
                    _b64(str(row["owner_id"])),
                    _b64(str(row["classification"])),
                    _b64(str(row["old_owner"])),
                    _b64(
                        (
                            str(row["new_owner"])
                            if row.get("new_owner") is not None
                            else ""
                        )
                    ),
                ]
            )
        )
    for row in members:
        lines.append(
            "\t".join(
                [
                    "M",
                    _b64(str(row["member_id"])),
                    _b64(str(row["old_owner"])),
                    _b64(str(row["old_name"])),
                    _b64(str(row["old_descriptor"])),
                    _b64(str(row["new_owner"])),
                    _b64(str(row["new_name"])),
                    _b64(str(row["new_descriptor"])),
                ]
            )
        )
    out.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _parse_scanner_output(
    stdout: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in stdout.splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) != 12 or parts[0] != "R":
            raise DependencySourceBindingError(
                f"unexpected source binding scanner row: {raw!r}"
            )
        rows.append(
            {
                "source_file": _decode(parts[1]),
                "start": int(parts[2]),
                "end": int(parts[3]),
                "syntax_kind": _decode(parts[4]),
                "element_kind": _decode(parts[5]),
                "old_owner": _decode(parts[6]),
                "old_name": _decode(parts[7]),
                "old_descriptor": _decode(parts[8]),
                "match_status": _decode(parts[9]),
                "mapping_id": _decode(parts[10]),
                "owner_classification": _decode(parts[11]),
            }
        )
    rows.sort(
        key=lambda row: (
            row["source_file"],
            row["start"],
            row["end"],
            row["element_kind"],
            row["old_owner"],
            row["old_name"],
            row["old_descriptor"],
        )
    )
    return rows


def _diagnostic_error_count(stderr: str) -> int:
    prefix = "SPK_BINDING_DIAGNOSTIC_ERRORS="
    values = [
        line[len(prefix):]
        for line in stderr.splitlines()
        if line.startswith(prefix)
    ]
    if len(values) != 1:
        raise DependencySourceBindingError(
            "source binding scanner did not emit one diagnostic error count"
        )
    try:
        value = int(values[0])
    except ValueError as exc:
        raise DependencySourceBindingError(
            "invalid source binding diagnostic error count"
        ) from exc
    if value < 0:
        raise DependencySourceBindingError(
            "negative source binding diagnostic error count"
        )
    return value


def bind_dependency_source_references(
    source_root: Path,
    dependency_remap_report_path: Path,
    private_replacement_plan_path: Path,
    bundled_jar: Path,
    official_artifacts: list[Path],
    *,
    java_command: str = "java",
    javac_command: str = "javac",
    include_identifiers: bool = False,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    dependency_remap_report_path = (
        dependency_remap_report_path.resolve()
    )
    private_replacement_plan_path = (
        private_replacement_plan_path.resolve()
    )
    bundled_jar = bundled_jar.resolve()

    if not source_root.is_dir():
        raise DependencySourceBindingError(
            "source root does not exist"
        )
    if not bundled_jar.is_file():
        raise DependencySourceBindingError(
            "bundled JAR does not exist"
        )

    remap = _load_json(
        dependency_remap_report_path,
        kind="dependency_structural_remap_proof",
    )
    replacement = _load_json(
        private_replacement_plan_path,
        kind="dependency_replacement_boundary_plan",
    )

    if replacement.get("dependency_remap_proof_id") != remap.get(
        "dependency_remap_proof_id"
    ):
        raise DependencySourceBindingError(
            "DEPREPLACE is bound to a different DEPREMAP"
        )
    bundled_sha = sha256_file(bundled_jar)
    if remap.get("bundled_jar_sha256") != bundled_sha:
        raise DependencySourceBindingError(
            "DEPREMAP is bound to a different bundled JAR"
        )
    if replacement.get("bundled_jar_sha256") != bundled_sha:
        raise DependencySourceBindingError(
            "DEPREPLACE is bound to a different bundled JAR"
        )

    release = remap.get("java_release")
    if (
        not isinstance(release, int)
        or isinstance(release, bool)
        or release < 1
    ):
        raise DependencySourceBindingError(
            "invalid DEPREMAP java_release"
        )

    try:
        _official, _owners, artifact_rows = _artifact_index(
            official_artifacts,
            java_release=release,
        )
    except DependencyArtifactProofError as exc:
        raise DependencySourceBindingError(str(exc)) from exc

    if replacement.get("official_artifacts") is None:
        raise DependencySourceBindingError(
            "private DEPREPLACE plan lacks official artifact rows"
        )
    if _artifact_key(
        list(replacement.get("official_artifacts", []))
    ) != _artifact_key(artifact_rows):
        raise DependencySourceBindingError(
            "official artifact set disagrees with DEPREPLACE"
        )
    if _artifact_key(
        list(remap.get("official_artifacts", []))
    ) != _artifact_key(artifact_rows):
        raise DependencySourceBindingError(
            "official artifact set disagrees with DEPREMAP"
        )

    owners, members = _mapping_rows(
        remap,
        replacement,
    )

    tree_sha, source_files, source_bytes = source_tree_digest(
        source_root
    )
    java = _require(java_command)
    javac = _require(javac_command)

    classpath = [
        bundled_jar,
        *[path.resolve() for path in official_artifacts],
    ]
    for path in classpath:
        if not path.is_file():
            raise DependencySourceBindingError(
                f"classpath entry missing: {path}"
            )

    with tempfile.TemporaryDirectory(
        prefix="spk-dependency-source-binding-"
    ) as td:
        temp = Path(td)
        classes = temp / "helper-classes"
        mapping = temp / "mapping.tsv"
        _write_mapping(owners, members, mapping)
        _compile_helper(classes, javac=javac)

        proc = subprocess.run(
            [
                java,
                "--add-modules",
                "jdk.compiler",
                "-cp",
                str(classes),
                "DependencySourceBindingScanner",
                str(source_root),
                str(mapping),
                os.pathsep.join(str(path) for path in classpath),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise DependencySourceBindingError(
                "dependency source binding scanner failed:\n"
                + proc.stdout
                + proc.stderr
            )

        rows = _parse_scanner_output(proc.stdout)
        diagnostic_error_count = _diagnostic_error_count(
            proc.stderr
        )

    file_names = sorted(
        {str(row["source_file"]) for row in rows}
    )
    file_ids = {
        name: (
            "SRCFILE_"
            + _stable_digest(
                {
                    "source_tree_sha256": tree_sha,
                    "relative_path": name,
                }
            )[:16].upper()
        )
        for name in file_names
    }

    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        public = {
            "binding_id": f"DEPSRCBIND_{index:06d}",
            "source_file_id": file_ids[row["source_file"]],
            "start": row["start"],
            "end": row["end"],
            "syntax_kind": row["syntax_kind"],
            "element_kind": row["element_kind"],
            "match_status": row["match_status"],
            "mapping_id": row["mapping_id"],
            "owner_classification": row[
                "owner_classification"
            ],
        }
        public_rows.append(public)
        if include_identifiers:
            private_rows.append(
                {
                    **public,
                    "source_file": row["source_file"],
                    "old_owner": row["old_owner"],
                    "old_name": row["old_name"],
                    "old_descriptor": row["old_descriptor"],
                }
            )

    status_counts = Counter(
        row["match_status"] for row in public_rows
    )
    element_counts = Counter(
        row["element_kind"] for row in public_rows
    )
    owner_class_counts = Counter(
        row["owner_classification"] for row in public_rows
    )
    exact_approved_count = sum(
        row["match_status"]
        in {
            "exact_approved_class",
            "exact_approved_member",
        }
        for row in public_rows
    )
    unmatched_approved_member_count = sum(
        row["match_status"]
        == "approved_owner_unmatched_member"
        for row in public_rows
    )

    classpath_rows = [
        {
            "role": (
                "bundled_authority"
                if index == 0
                else "official_artifact"
            ),
            "sha256": sha256_file(path),
        }
        for index, path in enumerate(classpath)
    ]

    public_material = {
        "source_tree_sha256": tree_sha,
        "dependency_remap_proof_id": remap[
            "dependency_remap_proof_id"
        ],
        "replacement_plan_id": replacement[
            "replacement_plan_id"
        ],
        "bundled_jar_sha256": bundled_sha,
        "java_release": release,
        "classpath": classpath_rows,
        "rows": public_rows,
    }

    report = {
        "schema_version": 1,
        "kind": "dependency_source_binding_inventory",
        "binding_inventory_id": (
            "DEPSRCBIND_"
            + _stable_digest(public_material)[:20].upper()
        ),
        "source_tree_sha256": tree_sha,
        "source_java_file_count": len(source_files),
        "source_bytes": source_bytes,
        "dependency_remap_proof_id": remap[
            "dependency_remap_proof_id"
        ],
        "replacement_plan_id": replacement[
            "replacement_plan_id"
        ],
        "bundled_jar_sha256": bundled_sha,
        "java_release": release,
        "classpath": classpath_rows,
        "summary": {
            "binding_count": len(public_rows),
            "source_file_with_binding_count": len(file_ids),
            "match_status_counts": dict(
                sorted(status_counts.items())
            ),
            "element_kind_counts": dict(
                sorted(element_counts.items())
            ),
            "owner_classification_counts": dict(
                sorted(owner_class_counts.items())
            ),
            "exact_approved_binding_count": (
                exact_approved_count
            ),
            "approved_owner_unmatched_member_count": (
                unmatched_approved_member_count
            ),
            "javac_diagnostic_error_count": (
                diagnostic_error_count
            ),
        },
        "bindings": (
            private_rows
            if include_identifiers
            else public_rows
        ),
        "identifiers_included": include_identifiers,
    }
    return report


def write_dependency_source_binding_inventory(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
