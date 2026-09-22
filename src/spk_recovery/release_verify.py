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
            "verified means the supplied release manifest reproduces exactly "
            "from its authority documents and all explicitly supplied on-disk "
            "artifacts/toolchain checks match their recorded pins."
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
