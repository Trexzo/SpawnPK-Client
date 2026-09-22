from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from .member_safety import (
    MemberSafetyError,
    build_member_safety_report,
)
from .repack import RepackError, remap_jar, write_result
from .remap_plan import remap_risk_scan
from .semantic_namespace import (
    SemanticNamespaceError,
    build_semantic_namespace,
)
from .verification import (
    VerificationError,
    verify_transformed_jar,
)


class ReadableBuildError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _write_json(doc: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _manifest(
    *,
    namespace: dict[str, Any],
    status: str,
    output_sha256: str | None,
    verification_pass: bool | None,
    blocker: dict[str, Any] | None,
) -> dict[str, Any]:
    target_package = str(namespace.get("target_package", "")).strip("/")
    project_source_prefixes = ["rs/"]
    if target_package:
        project_source_prefixes.append(target_package + "/")

    source_safe_fallback = bool(
        namespace.get("source_safe_fallback", False)
    )
    fallback_package = str(
        namespace.get("fallback_package", "")
    ).strip("/")
    if source_safe_fallback and fallback_package:
        project_source_prefixes.append(fallback_package + "/")
    project_source_prefixes = sorted(set(project_source_prefixes))

    material = {
        "namespace_id": namespace["namespace_id"],
        "source_sha256": namespace["source_sha256"],
        "class_plan_digest": namespace["class_plan_digest"],
        "member_plan_digest": namespace["member_plan_digest"],
        "status": status,
        "output_sha256": output_sha256,
        "verification_pass": verification_pass,
        "project_source_prefixes": project_source_prefixes,
        "blocker": blocker,
    }
    return {
        "schema_version": 1,
        "kind": "readable_client_build_manifest",
        "build_id": namespace["build_id"],
        "namespace_id": namespace["namespace_id"],
        "source_sha256": namespace["source_sha256"],
        "target_package": namespace["target_package"],
        "source_safe_fallback": source_safe_fallback,
        "fallback_package": (
            fallback_package if source_safe_fallback else None
        ),
        "project_source_prefixes": project_source_prefixes,
        "class_plan_digest": namespace["class_plan_digest"],
        "member_plan_digest": namespace["member_plan_digest"],
        "status": status,
        "output_sha256": output_sha256,
        "verification_pass": verification_pass,
        "semantic_summary": namespace["summary"],
        "blocker": blocker,
        "artifact_names": {
            "namespace": "semantic-namespace.json",
            "class_plan": "class-remap-plan.json",
            "member_plan": "member-remap-plan.json",
            "class_risk": "class-risk-report.json",
            "member_safety": "member-safety-report.json",
            "readable_jar": "readable-client.jar",
            "remap_result": "remap-result.json",
            "verification": "verification.json",
        },
        "manifest_id": "READABLE_"
        + _stable_digest(material)[:20].upper(),
    }


def build_readable_client(
    source_jar: Path,
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    source_index: dict[str, Any],
    *,
    build_id: str,
    out_dir: Path,
    target_package: str = "recovered/spawnpk/client",
    source_safe_fallback: bool = False,
    fallback_package: str = "recovered/spawnpk/fallback",
    member_safety_acceptance: dict[str, Any] | None = None,
    allow_package_resource_risk: bool = False,
    rewrite_class_name_strings: bool = False,
) -> dict[str, Any]:
    """Materialize one accepted semantic namespace into a verified readable JAR.

    This function never accepts semantic names. It consumes only ACCEPTED canonical
    class/member state. Member name-safety remains a separate explicit gate.
    """
    source_jar = source_jar.resolve()
    out_dir = out_dir.resolve()
    if not source_jar.is_file():
        raise ReadableBuildError(f"source JAR does not exist: {source_jar}")

    if out_dir.exists() and any(out_dir.iterdir()):
        raise ReadableBuildError(
            "output directory must be empty for a reproducible readable-client build"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        namespace, class_plan, member_plan = build_semantic_namespace(
            class_lineage,
            member_lineage,
            source_index,
            build_id=build_id,
            target_package=target_package,
            source_safe_fallback=source_safe_fallback,
            fallback_package=fallback_package,
        )
    except SemanticNamespaceError as exc:
        raise ReadableBuildError(str(exc)) from exc

    _write_json(namespace, out_dir / "semantic-namespace.json")
    _write_json(class_plan, out_dir / "class-remap-plan.json")
    _write_json(member_plan, out_dir / "member-remap-plan.json")

    class_risk = remap_risk_scan(source_index, class_plan)
    _write_json(class_risk, out_dir / "class-risk-report.json")

    total_remaps = int(class_plan.get("class_count", 0)) + int(
        member_plan.get("member_count", 0)
    )
    if total_remaps == 0:
        blocker = {
            "code": "no_accepted_remaps",
            "detail": (
                "Canonical state contains no accepted class/member names that "
                "would change this exact build."
            ),
        }
        manifest = _manifest(
            namespace=namespace,
            status="blocked",
            output_sha256=None,
            verification_pass=None,
            blocker=blocker,
        )
        _write_json(manifest, out_dir / "readable-client-manifest.json")
        return manifest

    package_hits = int(
        class_risk.get("summary", {}).get("package_resource_hit_count", 0)
    )
    literal_hits = int(
        class_risk.get("summary", {}).get("literal_class_name_hit_count", 0)
    )
    if package_hits and not allow_package_resource_risk:
        blocker = {
            "code": "class_package_resource_review_required",
            "count": package_hits,
            "detail": (
                "Accepted class remaps overlap package resources. Review the "
                "class risk report and rerun with explicit acknowledgement."
            ),
        }
        manifest = _manifest(
            namespace=namespace,
            status="blocked",
            output_sha256=None,
            verification_pass=None,
            blocker=blocker,
        )
        _write_json(manifest, out_dir / "readable-client-manifest.json")
        return manifest

    if literal_hits and not rewrite_class_name_strings:
        blocker = {
            "code": "class_name_literal_review_required",
            "count": literal_hits,
            "detail": (
                "Exact class-name string literals are present. Review the class "
                "risk report and explicitly opt into literal rewriting."
            ),
        }
        manifest = _manifest(
            namespace=namespace,
            status="blocked",
            output_sha256=None,
            verification_pass=None,
            blocker=blocker,
        )
        _write_json(manifest, out_dir / "readable-client-manifest.json")
        return manifest

    member_safety_report = None
    if int(member_plan.get("member_count", 0)):
        try:
            member_safety_report = build_member_safety_report(
                source_jar,
                source_index,
                member_plan,
            )
        except MemberSafetyError as exc:
            raise ReadableBuildError(str(exc)) from exc
        _write_json(
            member_safety_report,
            out_dir / "member-safety-report.json",
        )
        if member_safety_acceptance is None:
            blocker = {
                "code": "member_safety_acceptance_required",
                "report_id": member_safety_report["report_id"],
                "member_count": member_safety_report["member_count"],
                "detail": (
                    "Accepted semantic member names exist, but bytecode member "
                    "rewriting requires an explicit safety acceptance bound to "
                    "this exact report."
                ),
            }
            manifest = _manifest(
                namespace=namespace,
                status="blocked",
                output_sha256=None,
                verification_pass=None,
                blocker=blocker,
            )
            _write_json(manifest, out_dir / "readable-client-manifest.json")
            return manifest

    output_jar = out_dir / "readable-client.jar"
    try:
        result = remap_jar(
            source_jar,
            source_index,
            class_plan,
            output_jar,
            member_plan=member_plan,
            allow_package_resource_risk=allow_package_resource_risk,
            rewrite_class_name_strings=rewrite_class_name_strings,
            member_safety_report=member_safety_report,
            member_safety_acceptance=member_safety_acceptance,
        )
    except RepackError as exc:
        raise ReadableBuildError(str(exc)) from exc
    write_result(result, out_dir / "remap-result.json")

    try:
        verification = verify_transformed_jar(
            source_index,
            output_jar,
            class_plan=class_plan,
            member_plan=member_plan,
        )
    except VerificationError as exc:
        raise ReadableBuildError(str(exc)) from exc
    _write_json(verification, out_dir / "verification.json")

    if not verification.get("pass"):
        blocker = {
            "code": "independent_verification_failed",
            "issues": verification.get("issues", []),
        }
        manifest = _manifest(
            namespace=namespace,
            status="failed",
            output_sha256=result["output_sha256"],
            verification_pass=False,
            blocker=blocker,
        )
        _write_json(manifest, out_dir / "readable-client-manifest.json")
        return manifest

    manifest = _manifest(
        namespace=namespace,
        status="complete",
        output_sha256=result["output_sha256"],
        verification_pass=True,
        blocker=None,
    )
    _write_json(manifest, out_dir / "readable-client-manifest.json")
    return manifest
