from __future__ import annotations

"""Single private exact-JAR preflight for the 26 descriptor and 68 empty-field lanes.

Research-only; no class/member acceptance, and no raw JAR/index persistence.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from .descriptor_class_private_jar_replay import (
    ExactJarDescriptorClassReplayError,
    _read_json_exact,
    write_research_report_no_clobber,
)
from .descriptor_class_verified_replay import build_descriptor_class_verified_replay
from .empty_field_declaration_evidence import build_empty_field_declaration_evidence
from .indexer import index_jar, sha256_file


class V309DualProofReplayError(ValueError):
    pass


def _digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def build_v309_dual_proof_replay(
    old_jar: Path,
    new_jar: Path,
    frontier_path: Path,
    class_lineage_path: Path,
    member_lineage_path: Path,
    global_report_path: Path,
) -> dict[str, Any]:
    frontier = _read_json_exact(frontier_path)
    if (
        frontier.get("kind") != "v309_recovery_frontier"
        or frontier.get("state") != "ACCEPTED_INCOMPLETE"
        or frontier.get("build_id") != "v309"
        or frontier.get("frontier", {}).get("unresolved") != 143
        or frontier["frontier"].get("descriptor_identity_guard_rejected") != 26
        or frontier["frontier"].get("empty_both") != 68
    ):
        raise V309DualProofReplayError("expected pinned 143/26/68 accepted v309 frontier")

    exact = frontier.get("exact_clients", {})
    file_proofs = frontier.get("files", {})
    input_files = {
        "class_lineage": class_lineage_path,
        "member_lineage": member_lineage_path,
        "global_field_usage": global_report_path,
    }
    for name, path in input_files.items():
        expected = file_proofs.get(name, {}).get("sha256")
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or sha256_file(path).lower() != expected.lower()
        ):
            raise V309DualProofReplayError(f"tracked {name} SHA-256 differs from accepted frontier")
    for build_id, jar in (("v308", old_jar), ("v309", new_jar)):
        pinned = exact.get(build_id + "_sha256")
        if (
            not isinstance(pinned, str)
            or len(pinned) != 64
            or sha256_file(jar).lower() != pinned.lower()
        ):
            raise V309DualProofReplayError(f"{build_id} exact client SHA-256 mismatch")

    class_lineage = _read_json_exact(class_lineage_path)
    member_lineage = _read_json_exact(member_lineage_path)
    global_report = _read_json_exact(global_report_path)
    if (
        global_report.get("kind") != "global_field_usage_identity_candidates"
        or global_report.get("canonical") is not False
        or global_report.get("old_build_id") != "v308"
        or global_report.get("new_build_id") != "v309"
        or global_report.get("old_sha256", "").lower() != exact["v308_sha256"].lower()
        or global_report.get("new_sha256", "").lower() != exact["v309_sha256"].lower()
        or global_report.get("report_id") != file_proofs["global_field_usage"].get("report_id")
        or global_report.get("summary", {}).get("empty_both") != 68
        or global_report.get("summary", {}).get("descriptor_identity_guard_rejected") != 26
        or len(global_report.get("review_outcomes", [])) != 143
    ):
        raise V309DualProofReplayError("global report does not match accepted 143/26/68 frontier")

    # Index both JARs exactly once. Pass these same in-memory indexes to BOTH
    # evidence generators. Neither complete index is persisted or returned.
    old_index = index_jar(old_jar)
    new_index = index_jar(new_jar)
    for build_id, index in (("v308", old_index), ("v309", new_index)):
        if index.get("summary", {}).get("class_parse_error_count") != 0:
            raise V309DualProofReplayError(f"{build_id} index has unparsed classes")
        if index.get("sha256", "").lower() != exact[build_id + "_sha256"].lower():
            raise V309DualProofReplayError(f"{build_id} client changed during indexing")

    descriptor_report = build_descriptor_class_verified_replay(
        global_report, class_lineage, old_index, new_index,
    )
    empty_report = build_empty_field_declaration_evidence(
        class_lineage, member_lineage, old_index, new_index, old_jar, new_jar,
        global_report,
    )

    d_summary = descriptor_report.get("summary", {})
    e_summary = empty_report.get("summary", {})
    if (
        descriptor_report.get("canonical") is not False
        or descriptor_report.get("state") != "NO_CLASS_OR_MEMBER_IDENTITY_ACCEPTED"
        or d_summary.get("input_class_dependencies") != 8
        or d_summary.get("candidate_fields_blocked", -1)
           + d_summary.get("still_blocked_fields", -1) != 26
        or empty_report.get("canonical") is not False
        or empty_report.get("kind") != "empty_field_declaration_identity_candidates"
        or empty_report.get("global_usage_report_id") != global_report["report_id"]
        or e_summary.get("input_empty_both_reviews") != 68
        or e_summary.get("candidate_fields", -1)
           + e_summary.get("remaining_without_declaration_proof", -1) != 68
        or empty_report.get("old_sha256", "").lower() != exact["v308_sha256"].lower()
        or empty_report.get("new_sha256", "").lower() != exact["v309_sha256"].lower()
    ):
        raise V309DualProofReplayError("research evidence state or 26/8/68 accounting drift")

    manifest_body = {
        "schema_version": 1,
        "kind": "v309_private_dual_proof_research_bundle",
        "canonical": False,
        "state": "BOTH_LANES_RESEARCH_ONLY_NO_IDENTITIES_ACCEPTED",
        "global_report_id": global_report["report_id"],
        "v308_sha256": exact["v308_sha256"],
        "v309_sha256": exact["v309_sha256"],
        "descriptor_report_id": descriptor_report["report_id"],
        "descriptor_report_digest": _digest(descriptor_report),
        "empty_report_id": empty_report["report_id"],
        "empty_report_digest": _digest(empty_report),
        "descriptor_summary": d_summary,
        "empty_summary": e_summary,
        "unresolved_accepted_frontier": 143,
        "warning": "Independent exact evidence only; all candidates require separate reviewed acceptance.",
    }
    manifest = {"bundle_id": "V309DUAL_" + _digest(manifest_body)[:20].upper(), **manifest_body}
    return {
        "descriptor_class_research": descriptor_report,
        "empty_field_declaration_research": empty_report,
        "manifest": manifest,
    }


def write_v309_dual_proof_bundle(
    reports: dict[str, Any], output_dir: Path, protected_inputs: tuple[Path, ...],
) -> None:
    """Create an exclusive directory; roll back only the directory we created."""
    target = output_dir.resolve()
    if any(target == p.resolve() or target in p.resolve().parents for p in protected_inputs):
        raise V309DualProofReplayError("bundle directory overlaps pinned input")
    # Exclusive mkdir is an atomic no-clobber guard for the output directory.
    output_dir.mkdir(parents=True, exist_ok=False)
    files = {
        "descriptor-class-research.json": reports["descriptor_class_research"],
        "empty-field-declaration-research.json": reports["empty_field_declaration_research"],
        "BUNDLE.json": reports["manifest"],
    }
    try:
        for name, report in files.items():
            write_research_report_no_clobber(
                report, output_dir / name, protected_inputs,
            )
    except Exception:
        # Since mkdir above was exclusive, this directory is ours to roll back.
        shutil.rmtree(output_dir)
        raise


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-private-dual-proof-replay")
    p.add_argument("--v308-jar", type=Path, required=True)
    p.add_argument("--v309-jar", type=Path, required=True)
    p.add_argument("--frontier", type=Path, default=Path("research/v309-field-recovery/frontier.json"))
    p.add_argument("--class-lineage", type=Path, default=Path("research/v309-field-recovery/class-lineage.json"))
    p.add_argument("--member-lineage", type=Path, default=Path("research/v309-field-recovery/member-lineage.json"))
    p.add_argument("--global-field-report", type=Path, default=Path("research/v309-field-recovery/global-field-usage.json"))
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        reports = build_v309_dual_proof_replay(
            args.v308_jar, args.v309_jar, args.frontier, args.class_lineage,
            args.member_lineage, args.global_field_report,
        )
        write_v309_dual_proof_bundle(reports, args.out_dir, (
            args.v308_jar, args.v309_jar, args.frontier, args.class_lineage,
            args.member_lineage, args.global_field_report,
        ))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"SPK_V309_PRIVATE_DUAL_PROOF_REPLAY_FAIL: {exc}")
        return 1
    print("SPK_V309_PRIVATE_DUAL_PROOF_REPLAY_PASS_RESEARCH_ONLY")
    print(f"bundle_id={reports['manifest']['bundle_id']}")
    print(f"out_dir={args.out_dir}")
    for prefix, summary in (
        ("descriptor", reports["manifest"]["descriptor_summary"]),
        ("empty", reports["manifest"]["empty_summary"]),
    ):
        for key, value in summary.items():
            print(f"{prefix}.{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
