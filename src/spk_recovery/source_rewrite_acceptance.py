from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .source_digest import source_tree_digest
from .build_authority import (
    BuildAuthorityError,
    build_build_authority,
    write_build_authority,
)
from .clean_rebuild import CleanRebuildError, clean_project_rebuild
from .roundtrip_verify import (
    RoundTripVerificationError,
    verify_clean_round_trip,
    write_roundtrip_report,
)
from .source_readiness import (
    SourceReadinessError,
    audit_source_workspace,
    write_source_readiness_report,
)


class SourceRewriteAcceptanceError(ValueError):
    pass


def _source_tree_digest(root: Path) -> tuple[str, int, int]:
    digest, files, total = source_tree_digest(root)
    return digest, len(files), total


def _write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            doc,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _derived_source_manifest(
    recovered_manifest: dict[str, Any],
    rewrite_manifest: dict[str, Any],
    rewritten_source_root: Path,
) -> dict[str, Any]:
    if (
        recovered_manifest.get("schema_version") != 1
        or recovered_manifest.get("kind")
        != "recovered_source_workspace_manifest"
    ):
        raise SourceRewriteAcceptanceError(
            "unsupported original recovered-source manifest"
        )
    if (
        rewrite_manifest.get("schema_version") != 1
        or rewrite_manifest.get("kind") != "source_rewrite_manifest"
    ):
        raise SourceRewriteAcceptanceError(
            "unsupported source rewrite manifest"
        )
    if rewrite_manifest.get("semantic_analysis_pass") is not True:
        raise SourceRewriteAcceptanceError(
            "source rewrite did not pass semantic analysis"
        )

    if (
        rewrite_manifest.get("workspace_id")
        != recovered_manifest.get("workspace_id")
    ):
        raise SourceRewriteAcceptanceError(
            "source rewrite workspace_id does not match original recovered workspace"
        )
    if (
        rewrite_manifest.get("build_id")
        != recovered_manifest.get("build_id")
    ):
        raise SourceRewriteAcceptanceError(
            "source rewrite build_id does not match recovered workspace"
        )
    if (
        str(rewrite_manifest.get("input_source_tree_sha256", "")).lower()
        != str(recovered_manifest.get("source_tree_sha256", "")).lower()
    ):
        raise SourceRewriteAcceptanceError(
            "source rewrite input tree does not match recovered workspace authority"
        )

    tree_sha, java_count, source_bytes = _source_tree_digest(
        rewritten_source_root
    )
    if (
        tree_sha.lower()
        != str(
            rewrite_manifest.get(
                "output_source_tree_sha256",
                "",
            )
        ).lower()
    ):
        raise SourceRewriteAcceptanceError(
            "rewritten source tree SHA-256 does not match source rewrite manifest"
        )
    if java_count != int(
        rewrite_manifest.get(
            "java_file_count",
            -1,
        )
    ):
        raise SourceRewriteAcceptanceError(
            "rewritten Java file count does not match source rewrite manifest"
        )

    material = {
        "parent_workspace_id": recovered_manifest.get("workspace_id"),
        "rewrite_id": rewrite_manifest.get("rewrite_id"),
        "source_tree_sha256": tree_sha,
        "namespace_id": recovered_manifest.get("namespace_id"),
        "build_id": recovered_manifest.get("build_id"),
    }
    workspace_id = (
        "SRCWSR_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    derived = dict(recovered_manifest)
    derived.update(
        {
            "workspace_id": workspace_id,
            "source_tree_sha256": tree_sha,
            "java_file_count": java_count,
            "source_bytes": source_bytes,
            "source_directory": "src",
            "derived_from_workspace_id": recovered_manifest.get(
                "workspace_id"
            ),
            "source_rewrite_id": rewrite_manifest.get("rewrite_id"),
            "source_rename_plan_id": rewrite_manifest.get("plan_id"),
            "source_name_origin": "EXPLICITLY_ACCEPTED_INFERRED_REPLACEMENTS",
        }
    )
    return derived


def accept_rewritten_source(
    recovered_manifest: dict[str, Any],
    rewrite_manifest: dict[str, Any],
    rewritten_source_root: Path,
    source_authority_jar: Path,
    source_authority_index: dict[str, Any],
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    *,
    out_dir: Path,
    javac_command: str = "javac",
    java_command: str = "java",
    class_prefix: str = "rs/",
    source_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    """Run the complete static acceptance chain for one rewritten source tree."""
    rewritten_source_root = rewritten_source_root.resolve()
    source_authority_jar = source_authority_jar.resolve()
    readable_jar = readable_jar.resolve()
    if not rewritten_source_root.is_dir():
        raise SourceRewriteAcceptanceError(
            f"rewritten source root does not exist: {rewritten_source_root}"
        )

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SourceRewriteAcceptanceError(
            "rewrite acceptance output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    derived = _derived_source_manifest(
        recovered_manifest,
        rewrite_manifest,
        rewritten_source_root,
    )
    _write_json(
        derived,
        out_dir / "rewritten-source-manifest.json",
    )

    try:
        readiness = audit_source_workspace(
            derived,
            rewritten_source_root,
        )
    except SourceReadinessError as exc:
        raise SourceRewriteAcceptanceError(str(exc)) from exc
    write_source_readiness_report(
        readiness,
        out_dir / "source-readiness.json",
    )

    try:
        build_authority = build_build_authority(
            source_authority_jar,
            source_authority_index,
            source_readiness=readiness,
            class_prefix=class_prefix,
            java_command=java_command,
            javac_command=javac_command,
        )
    except BuildAuthorityError as exc:
        raise SourceRewriteAcceptanceError(str(exc)) from exc
    write_build_authority(
        build_authority,
        out_dir / "build-authority.json",
    )

    rebuild_dir = out_dir / "clean-rebuild"
    try:
        rebuild = clean_project_rebuild(
            derived,
            readiness,
            readable_manifest,
            readable_jar,
            build_authority,
            rewritten_source_root,
            out_dir=rebuild_dir,
            javac_command=javac_command,
            source_prefixes=source_prefixes,
        )
    except CleanRebuildError as exc:
        raise SourceRewriteAcceptanceError(str(exc)) from exc

    roundtrip: dict[str, Any] | None = None
    accepted = False
    blocker: dict[str, Any] | None = None

    if rebuild.get("clean_project_build") is not True:
        blocker = {
            "stage": "clean_rebuild",
            "code": str(rebuild.get("status", "unknown")),
            "detail": (
                "Rewritten source did not produce a complete zero-project-fallback build."
            ),
        }
    else:
        rebuilt_path = rebuild_dir / "rebuilt-client.jar"
        try:
            roundtrip = verify_clean_round_trip(
                rebuild,
                readable_jar,
                rebuilt_path,
            )
        except RoundTripVerificationError as exc:
            raise SourceRewriteAcceptanceError(str(exc)) from exc
        write_roundtrip_report(
            roundtrip,
            out_dir / "roundtrip-verification.json",
        )

        candidate = roundtrip.get(
            "rebuild_authority_candidate",
            {},
        )
        fallback = rebuild.get(
            "project_classes",
            {},
        ).get("binary_fallback_count")
        accepted = (
            candidate.get("ready") is True
            and fallback == 0
            and rebuild.get("status") == "complete"
        )
        if not accepted:
            blocker = {
                "stage": "roundtrip",
                "code": "semantic_surface_blockers",
                "count": candidate.get(
                    "semantic_surface_blockers"
                ),
                "detail": (
                    "Rewritten source rebuilt, but R5E did not accept the rebuilt "
                    "project surface as a static authority candidate."
                ),
            }

    material = {
        "rewrite_id": rewrite_manifest.get("rewrite_id"),
        "derived_workspace_id": derived["workspace_id"],
        "readiness_id": readiness.get("audit_id"),
        "build_authority_id": build_authority.get("authority_id"),
        "rebuild_id": rebuild.get("rebuild_id"),
        "roundtrip_id": (
            roundtrip.get("verification_id")
            if roundtrip is not None
            else None
        ),
        "accepted": accepted,
        "blocker": blocker,
    }
    acceptance_id = (
        "SRCACCEPT_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    report = {
        "schema_version": 1,
        "kind": "source_rewrite_acceptance_report",
        "acceptance_id": acceptance_id,
        "accepted": accepted,
        "rewrite_id": rewrite_manifest.get("rewrite_id"),
        "source_rename_plan_id": rewrite_manifest.get("plan_id"),
        "parent_workspace_id": recovered_manifest.get("workspace_id"),
        "workspace_id": derived["workspace_id"],
        "build_id": derived.get("build_id"),
        "source_authority_sha256": derived.get(
            "source_authority_sha256"
        ),
        "readable_jar_sha256": derived.get(
            "readable_jar_sha256"
        ),
        "input_source_tree_sha256": rewrite_manifest.get(
            "input_source_tree_sha256"
        ),
        "rewritten_source_tree_sha256": derived.get(
            "source_tree_sha256"
        ),
        "source_readiness": {
            "audit_id": readiness.get("audit_id"),
            "static_readiness_pass": readiness.get(
                "summary",
                {},
            ).get("static_readiness_pass"),
            "high_issue_count": readiness.get(
                "summary",
                {},
            ).get("high_issue_count"),
        },
        "build_authority_id": build_authority.get(
            "authority_id"
        ),
        "clean_rebuild": {
            "rebuild_id": rebuild.get("rebuild_id"),
            "status": rebuild.get("status"),
            "clean_project_build": rebuild.get(
                "clean_project_build"
            ),
            "project_binary_fallback_count": rebuild.get(
                "project_classes",
                {},
            ).get("binary_fallback_count"),
            "rebuilt_jar_sha256": rebuild.get(
                "rebuilt_client",
                {},
            ).get("sha256"),
        },
        "roundtrip": (
            {
                "verification_id": roundtrip.get(
                    "verification_id"
                ),
                "ready": roundtrip.get(
                    "rebuild_authority_candidate",
                    {},
                ).get("ready"),
                "semantic_surface_blockers": roundtrip.get(
                    "rebuild_authority_candidate",
                    {},
                ).get("semantic_surface_blockers"),
                "comparison_summary": roundtrip.get(
                    "comparison",
                    {},
                ).get("summary"),
            }
            if roundtrip is not None
            else None
        ),
        "blocker": blocker,
        "artifacts": {
            "rewritten_source_manifest": "rewritten-source-manifest.json",
            "source_readiness": "source-readiness.json",
            "build_authority": "build-authority.json",
            "clean_rebuild": "clean-rebuild/clean-rebuild.json",
            "rebuilt_client": (
                "clean-rebuild/rebuilt-client.jar"
                if rebuild.get("clean_project_build") is True
                else None
            ),
            "roundtrip": (
                "roundtrip-verification.json"
                if roundtrip is not None
                else None
            ),
        },
        "note": (
            "accepted=true means the explicitly inferred source-name rewrite survived "
            "the clean zero-project-fallback rebuild and the current R5E static "
            "round-trip gate. It does not convert inferred names into recovered "
            "original identifiers."
        ),
    }
    _write_json(
        report,
        out_dir / "source-rewrite-acceptance.json",
    )
    return report
