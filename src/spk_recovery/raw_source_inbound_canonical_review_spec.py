from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .member_lineage import MemberLineageError
from .raw_source_inbound_canonical_evidence import (
    RawSourceInboundCanonicalEvidenceError,
    _profile_key,
    build_raw_source_inbound_canonical_evidence,
)


class RawSourceInboundCanonicalReviewSpecError(MemberLineageError):
    pass


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _coord(row: dict[str, Any], side: str) -> tuple[str, str, str]:
    owner = str(row.get(f"{side}_owner", "")).removesuffix(".class")
    value = row.get(side)
    if not isinstance(value, dict):
        raise RawSourceInboundCanonicalReviewSpecError(
            f"{side} coordinate must be object"
        )
    name = value.get("name")
    descriptor = value.get("descriptor")
    if (
        not owner
        or not isinstance(name, str)
        or not name
        or not isinstance(descriptor, str)
        or not descriptor
    ):
        raise RawSourceInboundCanonicalReviewSpecError(
            f"invalid {side} coordinate"
        )
    return owner, name, descriptor


def _proof_tokens(
    relationship_id: str,
    value: Any,
) -> set[str]:
    if not isinstance(value, list) or not value:
        raise RawSourceInboundCanonicalReviewSpecError(
            f"{relationship_id}: missing inbound RAW proofs"
        )

    tokens: set[str] = set()
    strategy_modes = {
        "canonical_method_inbound_topology_unique_global":
            "canonical_method_inbound_topology",
        "canonical_class_method_inbound_topology_unique_global":
            "canonical_class_method_inbound_topology",
    }

    for i, proof in enumerate(value):
        if not isinstance(proof, dict):
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{relationship_id}: proof[{i}] must be object"
            )
        strategy = proof.get("strategy")
        mode = strategy_modes.get(strategy)
        token = proof.get("identity_token")
        digest = proof.get("inbound_topology_digest")
        old_source = proof.get("old_source_class")
        new_source = proof.get("new_source_class")
        old_profile = proof.get("old_profile")
        new_profile = proof.get("new_profile")
        if (
            mode is None
            or not isinstance(token, str)
            or not token
            or token in tokens
            or not isinstance(digest, str)
            or len(digest) != 64
            or not isinstance(old_source, str)
            or not old_source.startswith("RAW:")
            or not isinstance(new_source, str)
            or not new_source.startswith("RAW:")
            or not isinstance(old_profile, dict)
            or not isinstance(new_profile, dict)
        ):
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{relationship_id}: invalid proof[{i}]"
            )

        old_key = _profile_key(old_profile, mode=mode)
        new_key = _profile_key(new_profile, mode=mode)
        if old_key is None or old_key != new_key:
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{relationship_id}: inbound profile equality drift"
            )
        expected_digest = _digest(
            {
                "strategy": strategy,
                "inbound_topology": old_key,
            }
        )
        if digest != expected_digest:
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{relationship_id}: inbound topology digest drift"
            )
        if token != f"{strategy}:{digest}":
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{relationship_id}: inbound proof token drift"
            )
        tokens.add(token)

    return tokens


def _validate_topology(
    relationship_id: str,
    rows: Any,
    *,
    proof_tokens: set[str],
) -> None:
    if not isinstance(rows, list) or not rows:
        raise RawSourceInboundCanonicalReviewSpecError(
            f"{relationship_id}: normalized topology must be non-empty"
        )
    seen: set[tuple[str, str]] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{relationship_id}: topology[{i}] must be object"
            )
        source = row.get("source_identity")
        operation = row.get("operation")
        count = row.get("count")
        if (
            not isinstance(source, str)
            or not source
            or operation not in {
                "getstatic",
                "putstatic",
                "getfield",
                "putfield",
            }
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
        ):
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{relationship_id}: invalid topology[{i}]"
            )
        if not source.startswith("CANON:") and source not in proof_tokens:
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{relationship_id}: topology identity lacks inbound proof"
            )
        key = (source, operation)
        if key in seen:
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{relationship_id}: duplicate normalized topology row"
            )
        seen.add(key)


def build_raw_source_inbound_canonical_review_spec(
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    old_jar: Path,
    new_jar: Path,
    global_usage_report: dict[str, Any],
    inbound_report: dict[str, Any],
) -> dict[str, Any]:
    if (
        inbound_report.get("schema_version") != 1
        or inbound_report.get("kind")
        != (
            "raw_source_inbound_canonical_topology_"
            "declaration_identity_candidates"
        )
        or inbound_report.get("canonical") is not False
    ):
        raise RawSourceInboundCanonicalReviewSpecError(
            "unsupported RAW inbound-canonical report"
        )

    recomputed = build_raw_source_inbound_canonical_evidence(
        class_lineage,
        member_lineage,
        old_index,
        new_index,
        old_jar,
        new_jar,
        global_usage_report,
    )
    if _digest(recomputed) != _digest(inbound_report):
        raise RawSourceInboundCanonicalReviewSpecError(
            "RAW inbound-canonical report does not equal exact-JAR recomputation"
        )

    report_id = inbound_report.get("report_id")
    old_build_id = inbound_report.get("old_build_id")
    new_build_id = inbound_report.get("new_build_id")
    old_sha = str(inbound_report.get("old_sha256", "")).lower()
    new_sha = str(inbound_report.get("new_sha256", "")).lower()
    member_digest = inbound_report.get("member_lineage_digest")
    global_report_id = inbound_report.get("global_usage_report_id")
    base_ref_id = inbound_report.get(
        "base_canonical_reference_report_id"
    )
    base_ref_digest = inbound_report.get(
        "base_canonical_reference_report_digest"
    )
    base_struct_id = inbound_report.get(
        "base_structural_topology_report_id"
    )
    base_struct_digest = inbound_report.get(
        "base_structural_topology_report_digest"
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
        or not isinstance(base_ref_id, str)
        or not base_ref_id
        or not isinstance(base_ref_digest, str)
        or len(base_ref_digest) != 64
        or not isinstance(base_struct_id, str)
        or not base_struct_id
        or not isinstance(base_struct_digest, str)
        or len(base_struct_digest) != 64
    ):
        raise RawSourceInboundCanonicalReviewSpecError(
            "RAW inbound-canonical report binding is invalid"
        )

    summary = inbound_report.get("summary")
    candidates = inbound_report.get("candidates")
    rejected = inbound_report.get("rejected")
    if (
        not isinstance(summary, dict)
        or not isinstance(candidates, list)
        or not isinstance(rejected, list)
    ):
        raise RawSourceInboundCanonicalReviewSpecError(
            "RAW inbound-canonical detail shape is invalid"
        )

    rejection_keys = (
        "inbound_canonical_identity_unproven",
        "normalized_source_topology_mismatch",
        "missing_two_sided_canonical_anchor",
        "canonical_anchor_identity_mismatch",
        "declaration_interval_length_mismatch",
        "declaration_interval_shape_mismatch",
        "target_interval_offset_mismatch",
        "target_declaration_signature_not_unique",
    )
    values = {
        key: summary.get(key)
        for key in (
            "input_canonical_reference_identity_unproven",
            "candidate_fields",
            "remaining_without_inbound_canonical_proof",
            "global_unique_method_inbound_identities",
            "global_unique_class_method_inbound_identities",
            "used_method_inbound_identities",
            "used_class_method_inbound_identities",
            *rejection_keys,
        )
    }
    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        for value in values.values()
    ):
        raise RawSourceInboundCanonicalReviewSpecError(
            "RAW inbound-canonical summary accounting is invalid"
        )

    input_count = values["input_canonical_reference_identity_unproven"]
    candidate_count = values["candidate_fields"]
    remaining = values["remaining_without_inbound_canonical_proof"]
    if candidate_count + remaining != input_count:
        raise RawSourceInboundCanonicalReviewSpecError(
            "candidate+remaining inbound accounting mismatch"
        )
    if len(candidates) != candidate_count or len(rejected) != remaining:
        raise RawSourceInboundCanonicalReviewSpecError(
            "inbound detail count mismatch"
        )
    if sum(values[key] for key in rejection_keys) != remaining:
        raise RawSourceInboundCanonicalReviewSpecError(
            "inbound rejection accounting mismatch"
        )
    if (
        values["used_method_inbound_identities"]
        > values["global_unique_method_inbound_identities"]
        or values["used_class_method_inbound_identities"]
        > values["global_unique_class_method_inbound_identities"]
    ):
        raise RawSourceInboundCanonicalReviewSpecError(
            "used inbound identities exceed globally unique identities"
        )

    rejected_ids: set[str] = set()
    reason_tally = {key: 0 for key in rejection_keys}
    used_method: set[str] = set()
    used_combined: set[str] = set()

    def tally(tokens: set[str]) -> None:
        for token in tokens:
            if token.startswith(
                "canonical_method_inbound_topology_unique_global:"
            ):
                used_method.add(token)
            elif token.startswith(
                "canonical_class_method_inbound_topology_unique_global:"
            ):
                used_combined.add(token)
            else:
                raise RawSourceInboundCanonicalReviewSpecError(
                    "unsupported inbound proof token prefix"
                )

    for i, row in enumerate(rejected):
        if not isinstance(row, dict):
            raise RawSourceInboundCanonicalReviewSpecError(
                f"rejected[{i}] must be object"
            )
        relationship_id = row.get("relationship_id")
        reason = row.get("reason")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in rejected_ids
            or reason not in reason_tally
        ):
            raise RawSourceInboundCanonicalReviewSpecError(
                f"rejected[{i}] has invalid id/reason"
            )
        rejected_ids.add(relationship_id)
        reason_tally[reason] += 1
        proofs = row.get("raw_source_identity_proofs")
        if proofs is not None:
            tally(_proof_tokens(relationship_id, proofs))

    for key in rejection_keys:
        if reason_tally[key] != values[key]:
            raise RawSourceInboundCanonicalReviewSpecError(
                f"rejected detail accounting mismatch for {key}"
            )

    relationship_ids: list[str] = []
    seen_ids: set[str] = set()
    seen_old: set[tuple[str, str, str]] = set()
    seen_new: set[tuple[str, str, str]] = set()

    for i, row in enumerate(candidates):
        label = f"candidates[{i}]"
        if not isinstance(row, dict):
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{label} must be object"
            )
        if (
            row.get("strategy")
            != (
                "globally_unique_inbound_canonical_identity_and_"
                "canonical_anchor_declaration_interval_exact"
            )
            or row.get("supports_existing_review") is not True
            or row.get("confidence") != "INFERRED_HIGH"
            or float(row.get("score", 0.0)) != 0.9993
        ):
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{label} is not trusted inbound evidence"
            )

        relationship_id = row.get("relationship_id")
        if (
            not isinstance(relationship_id, str)
            or not relationship_id
            or relationship_id in seen_ids
            or relationship_id in rejected_ids
        ):
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{label} has invalid/duplicate/overlapping id"
            )
        seen_ids.add(relationship_id)

        old_coord = _coord(row, "old")
        new_coord = _coord(row, "new")
        if old_coord in seen_old or new_coord in seen_new:
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{relationship_id}: duplicate candidate coordinate"
            )
        seen_old.add(old_coord)
        seen_new.add(new_coord)

        tokens = _proof_tokens(
            relationship_id,
            row.get("raw_source_identity_proofs"),
        )
        tally(tokens)
        _validate_topology(
            relationship_id,
            row.get("normalized_global_source_class_topology"),
            proof_tokens=tokens,
        )

        left = row.get("left_anchor_member_id")
        right = row.get("right_anchor_member_id")
        digest = row.get("interval_digest")
        length = row.get("interval_length")
        offset = row.get("interval_offset")
        old_ordinal = row.get("old_field_ordinal")
        new_ordinal = row.get("new_field_ordinal")
        if (
            not isinstance(left, str)
            or not left
            or not isinstance(right, str)
            or not right
            or left == right
            or not isinstance(digest, str)
            or len(digest) != 64
            or not isinstance(length, int)
            or isinstance(length, bool)
            or length <= 0
            or not isinstance(offset, int)
            or isinstance(offset, bool)
            or offset < 0
            or offset >= length
            or not isinstance(old_ordinal, int)
            or isinstance(old_ordinal, bool)
            or old_ordinal < 0
            or not isinstance(new_ordinal, int)
            or isinstance(new_ordinal, bool)
            or new_ordinal < 0
        ):
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{relationship_id}: invalid anchor/interval evidence"
            )
        if row.get("base_canonical_reference_report_id") != base_ref_id:
            raise RawSourceInboundCanonicalReviewSpecError(
                f"{relationship_id}: base canonical-reference report drift"
            )
        relationship_ids.append(relationship_id)

    if len(used_method) != values["used_method_inbound_identities"]:
        raise RawSourceInboundCanonicalReviewSpecError(
            "used method-inbound identity accounting mismatch"
        )
    if (
        len(used_combined)
        != values["used_class_method_inbound_identities"]
    ):
        raise RawSourceInboundCanonicalReviewSpecError(
            "used combined-inbound identity accounting mismatch"
        )
    if not relationship_ids:
        raise RawSourceInboundCanonicalReviewSpecError(
            "RAW inbound-canonical report contains no reviewable candidates"
        )

    return {
        "schema_version": 1,
        "kind": "reviewed_member_identity_acceptance_spec",
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "note": (
            f"Explicitly reviewed from {report_id}: RAW caller identity was "
            "independently proven through globally unique exact inbound "
            "topology from already-canonical classes/methods, with RAW member "
            "names and reference-type names excluded. Complete normalized "
            "source topology and two-sided declaration proof were recomputed "
            "exactly. Rejected rows remain unresolved."
        ),
        "evidence": [
            f"report_id={report_id}",
            f"report_digest_sha256={_digest(inbound_report)}",
            f"global_usage_report_id={global_report_id}",
            (
                "global_usage_report_digest_sha256="
                f"{_digest(global_usage_report)}"
            ),
            f"base_canonical_reference_report_id={base_ref_id}",
            f"base_canonical_reference_report_digest_sha256={base_ref_digest}",
            f"base_structural_topology_report_id={base_struct_id}",
            f"base_structural_topology_report_digest_sha256={base_struct_digest}",
            f"member_lineage_digest_sha256={member_digest}",
            (
                "strategy=globally_unique_inbound_canonical_identity_and_"
                "canonical_anchor_declaration_interval_exact"
            ),
            f"reviewed_candidates={len(relationship_ids)}",
            f"remaining_without_inbound_canonical_proof={remaining}",
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
