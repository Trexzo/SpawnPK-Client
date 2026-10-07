from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .lineage import LineageValidationError
from .member_lineage import MemberLineageError
from .raw_source_structural_topology_evidence import (
    RawSourceStructuralTopologyEvidenceError,
    build_raw_source_structural_topology_evidence,
)


class RawSourceStructuralTopologyReviewSpecError(MemberLineageError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _candidate_coord(
    row: dict[str, Any],
    *,
    side: str,
) -> tuple[str, str, str]:
    owner = str(row.get(f"{side}_owner", "")).removesuffix(".class")
    coord = row.get(side)
    if not isinstance(coord, dict):
        raise RawSourceStructuralTopologyReviewSpecError(
            f"candidate {side} coordinate must be an object"
        )
    name = coord.get("name")
    descriptor = coord.get("descriptor")
    if (
        not owner
        or not isinstance(name, str)
        or not name
        or not isinstance(descriptor, str)
        or not descriptor
    ):
        raise RawSourceStructuralTopologyReviewSpecError(
            f"candidate {side} coordinate is invalid"
        )
    return owner, name, descriptor


def _validate_proofs(
    relationship_id: str,
    proofs: Any,
) -> set[str]:
    if not isinstance(proofs, list) or not proofs:
        raise RawSourceStructuralTopologyReviewSpecError(
            f"{relationship_id}: RAW source identity proofs are missing"
        )

    allowed = {
        "exact_sha256_unique_global",
        "structural_sha256_unique_global",
    }
    tokens: set[str] = set()

    for i, proof in enumerate(proofs):
        if not isinstance(proof, dict):
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{relationship_id}: proof[{i}] must be an object"
            )
        strategy = proof.get("strategy")
        token = proof.get("identity_token")
        old_source = proof.get("old_source_class")
        new_source = proof.get("new_source_class")
        old_entry = proof.get("old_entry")
        new_entry = proof.get("new_entry")
        old_entry_sha = proof.get("old_entry_sha256")
        new_entry_sha = proof.get("new_entry_sha256")
        old_structural = proof.get("old_structural_sha256")
        new_structural = proof.get("new_structural_sha256")

        if (
            strategy not in allowed
            or not isinstance(token, str)
            or not token
            or token in tokens
            or not isinstance(old_source, str)
            or not old_source.startswith("RAW:")
            or not isinstance(new_source, str)
            or not new_source.startswith("RAW:")
            or not isinstance(old_entry, str)
            or not old_entry.endswith(".class")
            or not isinstance(new_entry, str)
            or not new_entry.endswith(".class")
            or not isinstance(old_entry_sha, str)
            or len(old_entry_sha) != 64
            or not isinstance(new_entry_sha, str)
            or len(new_entry_sha) != 64
            or not isinstance(old_structural, str)
            or len(old_structural) != 64
            or not isinstance(new_structural, str)
            or len(new_structural) != 64
        ):
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{relationship_id}: proof[{i}] is invalid"
            )

        if strategy == "exact_sha256_unique_global":
            if old_entry_sha != new_entry_sha:
                raise RawSourceStructuralTopologyReviewSpecError(
                    f"{relationship_id}: exact-SHA proof has SHA drift"
                )
            expected = "exact_sha256_unique_global:" + old_entry_sha
        else:
            if old_structural != new_structural:
                raise RawSourceStructuralTopologyReviewSpecError(
                    f"{relationship_id}: structural proof has digest drift"
                )
            expected = (
                "structural_sha256_unique_global:" + old_structural
            )

        if token != expected:
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{relationship_id}: proof token does not bind proof material"
            )
        tokens.add(token)

    return tokens


def _validate_normalized_topology(
    relationship_id: str,
    rows: Any,
    *,
    allowed_proof_tokens: set[str],
) -> None:
    if not isinstance(rows, list) or not rows:
        raise RawSourceStructuralTopologyReviewSpecError(
            f"{relationship_id}: normalized topology must be non-empty"
        )

    seen: set[tuple[str, str]] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{relationship_id}: topology[{i}] must be an object"
            )
        source_identity = row.get("source_identity")
        operation = row.get("operation")
        count = row.get("count")
        if (
            not isinstance(source_identity, str)
            or not source_identity
            or not isinstance(operation, str)
            or operation not in {
                "getfield",
                "putfield",
                "getstatic",
                "putstatic",
            }
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
        ):
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{relationship_id}: topology[{i}] is invalid"
            )

        if source_identity.startswith("CANON:"):
            if len(source_identity) <= len("CANON:"):
                raise RawSourceStructuralTopologyReviewSpecError(
                    f"{relationship_id}: empty canonical topology identity"
                )
        elif source_identity not in allowed_proof_tokens:
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{relationship_id}: topology identity lacks RAW proof"
            )

        key = (source_identity, operation)
        if key in seen:
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{relationship_id}: duplicate normalized topology row"
            )
        seen.add(key)


def build_raw_source_structural_topology_review_spec(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
    topology_report: dict[str, Any],
) -> dict[str, Any]:
    if (
        topology_report.get("schema_version") != 1
        or topology_report.get("kind")
        != "raw_source_structural_topology_declaration_identity_candidates"
        or topology_report.get("canonical") is not False
    ):
        raise RawSourceStructuralTopologyReviewSpecError(
            "unsupported RAW structural-topology report"
        )

    recomputed = build_raw_source_structural_topology_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )
    if _stable_digest(recomputed) != _stable_digest(topology_report):
        raise RawSourceStructuralTopologyReviewSpecError(
            "RAW structural-topology report does not equal exact-JAR recomputation"
        )

    report_id = topology_report.get("report_id")
    old_build_id = topology_report.get("old_build_id")
    new_build_id = topology_report.get("new_build_id")
    old_sha = str(topology_report.get("old_sha256", "")).lower()
    new_sha = str(topology_report.get("new_sha256", "")).lower()
    member_digest = topology_report.get("member_lineage_digest")
    global_report_id = topology_report.get("global_usage_report_id")
    base_report_id = topology_report.get("base_raw_source_report_id")
    base_report_digest = topology_report.get(
        "base_raw_source_report_digest"
    )

    if (
        not isinstance(report_id, str)
        or not report_id
        or not isinstance(old_build_id, str)
        or not old_build_id
        or not isinstance(new_build_id, str)
        or not new_build_id
        or old_build_id == new_build_id
        or len(old_sha) != 64
        or len(new_sha) != 64
        or not isinstance(member_digest, str)
        or len(member_digest) != 64
        or not isinstance(global_report_id, str)
        or not global_report_id
        or not isinstance(base_report_id, str)
        or not base_report_id
        or not isinstance(base_report_digest, str)
        or len(base_report_digest) != 64
    ):
        raise RawSourceStructuralTopologyReviewSpecError(
            "RAW structural-topology report binding is invalid"
        )

    summary = topology_report.get("summary")
    candidates = topology_report.get("candidates")
    rejected = topology_report.get("rejected")
    if (
        not isinstance(summary, dict)
        or not isinstance(candidates, list)
        or not isinstance(rejected, list)
    ):
        raise RawSourceStructuralTopologyReviewSpecError(
            "RAW structural-topology report detail shape is invalid"
        )

    rejection_keys = (
        "raw_source_identity_unproven",
        "normalized_source_topology_mismatch",
        "missing_two_sided_canonical_anchor",
        "canonical_anchor_identity_mismatch",
        "declaration_interval_length_mismatch",
        "declaration_interval_shape_mismatch",
        "target_interval_offset_mismatch",
        "target_declaration_signature_not_unique",
    )
    input_count = summary.get("input_raw_source_topology_mismatches")
    candidate_count = summary.get("candidate_fields")
    remaining_count = summary.get(
        "remaining_without_structural_topology_proof"
    )
    exact_used = summary.get("unique_exact_sha_source_identities_used")
    structural_used = summary.get(
        "unique_structural_source_identities_used"
    )
    rejection_counts = [summary.get(key) for key in rejection_keys]
    values = [
        input_count,
        candidate_count,
        remaining_count,
        exact_used,
        structural_used,
        *rejection_counts,
    ]
    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        for value in values
    ):
        raise RawSourceStructuralTopologyReviewSpecError(
            "RAW structural-topology summary accounting is invalid"
        )
    if candidate_count + remaining_count != input_count:
        raise RawSourceStructuralTopologyReviewSpecError(
            "candidate+remaining RAW structural-topology accounting mismatch"
        )
    if len(candidates) != candidate_count:
        raise RawSourceStructuralTopologyReviewSpecError(
            "candidate detail count mismatch"
        )
    if len(rejected) != remaining_count:
        raise RawSourceStructuralTopologyReviewSpecError(
            "rejected detail count mismatch"
        )
    if sum(rejection_counts) != remaining_count:
        raise RawSourceStructuralTopologyReviewSpecError(
            "rejection reason accounting mismatch"
        )

    rejected_ids: set[str] = set()
    rejected_tally = {key: 0 for key in rejection_keys}
    used_exact_tokens: set[str] = set()
    used_structural_tokens: set[str] = set()

    def tally_proof_tokens(tokens: set[str]) -> None:
        for token in tokens:
            if token.startswith("exact_sha256_unique_global:"):
                used_exact_tokens.add(token)
            elif token.startswith("structural_sha256_unique_global:"):
                used_structural_tokens.add(token)
            else:
                raise RawSourceStructuralTopologyReviewSpecError(
                    "unsupported RAW proof token prefix"
                )

    for i, row in enumerate(rejected):
        if not isinstance(row, dict):
            raise RawSourceStructuralTopologyReviewSpecError(
                f"rejected[{i}] must be an object"
            )
        relationship_id = row.get("relationship_id")
        reason = row.get("reason")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in rejected_ids
            or reason not in rejected_tally
        ):
            raise RawSourceStructuralTopologyReviewSpecError(
                f"rejected[{i}] has invalid id/reason"
            )
        rejected_ids.add(relationship_id)
        rejected_tally[reason] += 1

        proofs = row.get("raw_source_identity_proofs")
        if proofs is not None:
            tally_proof_tokens(
                _validate_proofs(relationship_id, proofs)
            )

    for key in rejection_keys:
        if rejected_tally[key] != summary[key]:
            raise RawSourceStructuralTopologyReviewSpecError(
                f"rejected detail accounting mismatch for {key}"
            )

    relationship_ids: list[str] = []
    seen_ids: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()

    for i, row in enumerate(candidates):
        label = f"candidates[{i}]"
        if not isinstance(row, dict):
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{label} must be an object"
            )
        if (
            row.get("strategy")
            != (
                "globally_unique_raw_source_identity_and_"
                "canonical_anchor_declaration_interval_exact"
            )
            or row.get("supports_existing_review") is not True
            or row.get("confidence") != "INFERRED_HIGH"
            or float(row.get("score", 0.0)) != 0.999
        ):
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{label} is not trusted RAW structural-topology evidence"
            )

        relationship_id = row.get("relationship_id")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in seen_ids
            or relationship_id in rejected_ids
        ):
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{label} has invalid/duplicate/overlapping relationship_id"
            )
        seen_ids.add(relationship_id)

        old_coord = _candidate_coord(row, side="old")
        new_coord = _candidate_coord(row, side="new")
        if old_coord in seen_old:
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{relationship_id}: duplicate old coordinate"
            )
        if new_coord in seen_new:
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{relationship_id}: duplicate new coordinate"
            )
        seen_old.add(old_coord)
        seen_new.add(new_coord)

        proof_tokens = _validate_proofs(
            relationship_id,
            row.get("raw_source_identity_proofs"),
        )
        tally_proof_tokens(proof_tokens)

        _validate_normalized_topology(
            relationship_id,
            row.get("normalized_global_source_class_topology"),
            allowed_proof_tokens=proof_tokens,
        )

        left_anchor = row.get("left_anchor_member_id")
        right_anchor = row.get("right_anchor_member_id")
        interval_digest = row.get("interval_digest")
        interval_length = row.get("interval_length")
        interval_offset = row.get("interval_offset")
        old_ordinal = row.get("old_field_ordinal")
        new_ordinal = row.get("new_field_ordinal")
        if (
            not isinstance(left_anchor, str)
            or not left_anchor
            or not isinstance(right_anchor, str)
            or not right_anchor
            or left_anchor == right_anchor
            or not isinstance(interval_digest, str)
            or len(interval_digest) != 64
            or not isinstance(interval_length, int)
            or isinstance(interval_length, bool)
            or interval_length <= 0
            or not isinstance(interval_offset, int)
            or isinstance(interval_offset, bool)
            or interval_offset < 0
            or interval_offset >= interval_length
            or not isinstance(old_ordinal, int)
            or isinstance(old_ordinal, bool)
            or old_ordinal < 0
            or not isinstance(new_ordinal, int)
            or isinstance(new_ordinal, bool)
            or new_ordinal < 0
        ):
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{relationship_id}: anchor/interval evidence is invalid"
            )

        if row.get("base_raw_source_report_id") != base_report_id:
            raise RawSourceStructuralTopologyReviewSpecError(
                f"{relationship_id}: base RAW-source report drift"
            )

        relationship_ids.append(relationship_id)

    if len(used_exact_tokens) != exact_used:
        raise RawSourceStructuralTopologyReviewSpecError(
            "candidate exact-SHA identity accounting mismatch"
        )
    if len(used_structural_tokens) != structural_used:
        raise RawSourceStructuralTopologyReviewSpecError(
            "candidate structural identity accounting mismatch"
        )
    if not relationship_ids:
        raise RawSourceStructuralTopologyReviewSpecError(
            "RAW structural-topology report contains no reviewable candidates"
        )

    report_digest = _stable_digest(topology_report)
    global_report_digest = _stable_digest(global_usage_report)

    return {
        "schema_version": 1,
        "kind": "reviewed_member_identity_acceptance_spec",
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "note": (
            f"Explicitly reviewed from {report_id}: every RAW source identity "
            "was independently bound through a globally unique exact-entry or "
            "name-insensitive structural SHA-256, complete normalized "
            "source-class/read-write/count topology matched exactly, and the "
            "two-sided canonical field-anchor declaration interval proof "
            "independently re-verified. Every rejected row remains unresolved."
        ),
        "evidence": [
            f"report_id={report_id}",
            f"report_digest_sha256={report_digest}",
            f"global_usage_report_id={global_report_id}",
            f"global_usage_report_digest_sha256={global_report_digest}",
            f"base_raw_source_report_id={base_report_id}",
            f"base_raw_source_report_digest_sha256={base_report_digest}",
            f"member_lineage_digest_sha256={member_digest}",
            (
                "strategy=globally_unique_raw_source_identity_and_"
                "canonical_anchor_declaration_interval_exact"
            ),
            f"reviewed_candidates={len(relationship_ids)}",
            (
                "remaining_without_structural_topology_proof="
                f"{remaining_count}"
            ),
            f"unique_exact_sha_source_identities_used={exact_used}",
            (
                "unique_structural_source_identities_used="
                f"{structural_used}"
            ),
        ],
        "relationship_ids": sorted(relationship_ids),
    }


def write_spec(spec: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            spec,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
