from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .source_digest import source_tree_digest
from .source_milestone import (
    SourceMilestoneError,
    build_source_milestone_manifest,
)


class SourceMilestoneVerificationError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_source_milestone(
    milestone_manifest: dict[str, Any],
    authority_index: dict[str, Any],
    readable_manifest: dict[str, Any],
    recovered_manifest: dict[str, Any],
    clean_rebuild_report: dict[str, Any],
    *,
    authority_commit: str,
    source_root: Path | None = None,
    exported_repository_root: Path | None = None,
) -> dict[str, Any]:
    try:
        recomputed = build_source_milestone_manifest(
            authority_index,
            readable_manifest,
            recovered_manifest,
            clean_rebuild_report,
            authority_commit=authority_commit,
            expected_build_id=str(
                milestone_manifest.get("build_id") or "v308"
            ),
        )
    except SourceMilestoneError as exc:
        raise SourceMilestoneVerificationError(str(exc)) from exc

    checks: list[dict[str, Any]] = []

    def check(name: str, expected: Any, actual: Any) -> None:
        checks.append(
            {
                "name": name,
                "expected": expected,
                "actual": actual,
                "passed": expected == actual,
            }
        )

    check(
        "milestone_manifest_exact_reproduction",
        milestone_manifest,
        recomputed,
    )

    expected_tree = milestone_manifest.get("source", {}).get(
        "source_tree_sha256"
    )

    if source_root is not None:
        tree_sha, java_count, source_bytes = source_tree_digest(
            source_root.resolve()
        )
        check("source_tree_sha256", expected_tree, tree_sha)
        check(
            "source_java_file_count",
            milestone_manifest.get("source", {}).get(
                "java_file_count"
            ),
            java_count,
        )
        check(
            "source_bytes",
            milestone_manifest.get("source", {}).get(
                "source_bytes"
            ),
            source_bytes,
        )

    if exported_repository_root is not None:
        root = exported_repository_root.resolve()
        export_json = root / "SOURCE-EXPORT.json"
        milestone_json = root / "SOURCE-MILESTONE.json"
        provenance_json = root / "SOURCE-PROVENANCE.json"
        export_source = root / "src"
        for path in (
            export_json,
            milestone_json,
            provenance_json,
            export_source,
        ):
            if not path.exists():
                raise SourceMilestoneVerificationError(
                    f"export is missing required artifact: {path.name}"
                )

        export_report = json.loads(
            export_json.read_text(encoding="utf-8")
        )
        exported_milestone = json.loads(
            milestone_json.read_text(encoding="utf-8")
        )
        provenance = json.loads(
            provenance_json.read_text(encoding="utf-8")
        )
        export_tree, export_count, export_bytes = source_tree_digest(
            export_source
        )

        check(
            "export_milestone_exact_copy",
            milestone_manifest,
            exported_milestone,
        )
        check(
            "export_source_tree_sha256",
            expected_tree,
            export_tree,
        )
        check(
            "export_java_file_count",
            milestone_manifest.get("source", {}).get(
                "java_file_count"
            ),
            export_count,
        )
        check(
            "export_source_bytes",
            milestone_manifest.get("source", {}).get(
                "source_bytes"
            ),
            export_bytes,
        )
        check(
            "export_authority_commit",
            milestone_manifest.get("provenance", {}).get(
                "spawnpk_client_authority_commit"
            ),
            export_report.get("authority_commit"),
        )
        check(
            "export_milestone_id",
            milestone_manifest.get("milestone_id"),
            export_report.get("milestone_id"),
        )
        check(
            "provenance_milestone_id",
            milestone_manifest.get("milestone_id"),
            provenance.get("milestone_id"),
        )

    failed = [row for row in checks if not row["passed"]]
    material = {
        "milestone_id": milestone_manifest.get("milestone_id"),
        "checks": [
            (row["name"], row["passed"])
            for row in checks
        ],
    }
    verification_id = (
        "SOURCE_M1_VERIFY_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "spawnpk_source_milestone_verification",
        "verification_id": verification_id,
        "milestone_id": milestone_manifest.get("milestone_id"),
        "verified": len(failed) == 0,
        "publishable": (
            len(failed) == 0
            and milestone_manifest.get("publishable") is True
        ),
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "checks": checks,
    }


def write_source_milestone_verification(
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
