"""R132: bind private R127 class candidates and R130/R131 call edges to R129.

Recomputes each private manifest, enforces independent exact input pins,
rejects accepted-lineage/partial-source claims and invokes the R129
review-only graph classifier. Never promotes a mapping, copies original
source/classfiles or executes a private client.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from .private_client_callgraph_corroboration_r129 import (
    corroborate_source_original_call_edges,
)


class CallGraphReplayR132Error(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise CallGraphReplayR132Error(reason)


def _json_sha(rows):
    return hashlib.sha256(json.dumps(
        rows, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def _no_duplicate_keys(pairs):
    result = {}
    for name, value in pairs:
        need(name not in result, "DUPLICATE_PRIVATE_REPORT_JSON_KEY")
        result[name] = value
    return result


def _private_report(path, kind):
    file = Path(path)
    need(file.is_file() and not file.is_symlink()
         and file.stat().st_size <= 40_000_000,
         "PRIVATE_EVIDENCE_FILE_INVALID")
    try:
        report = json.loads(
            file.read_text(encoding="utf-8"),
            object_pairs_hook=_no_duplicate_keys)
    except (OSError, UnicodeError, ValueError) as exc:
        raise CallGraphReplayR132Error(
            "PRIVATE_EVIDENCE_JSON_INVALID") from exc
    need(type(report) is dict
         and report.get("schema_version") == 1
         and report.get("kind") == kind,
         "PRIVATE_EVIDENCE_KIND_INVALID")
    return report


def _sha(value):
    return (type(value) is str
            and re.fullmatch(r"[a-f0-9]{64}", value) is not None)


def _rows_with_exact_digest(report, *, field, digest_field):
    rows = report.get(field)
    need(type(rows) is list and len(rows) <= 100_000,
         "PRIVATE_EVIDENCE_ROWS_MISSING")
    need(_sha(report.get(digest_field))
         and _json_sha(rows) == report[digest_field],
         "PRIVATE_EVIDENCE_MANIFEST_SHA_MISMATCH")
    return rows


def replay_private_call_graph_evidence(shape, jvm, source, *,
                                       minimum_anchors=2,
                                       include_private_rows=False):
    """Pure verified bundle comparison, no network or local client execution."""
    need(all(type(x) is dict for x in (shape, jvm, source)),
         "INVALID_PRIVATE_EVIDENCE_DOCUMENTS")
    kinds = [
        "private_v309_java_ast_jvm_structural_singleton_proposals_r127",
        "private_original_v309_jvm_invoke_edges_r130",
        "private_source_ast_symbol_resolved_calls_r131",
    ]
    for obj, kind in zip((shape, jvm, source), kinds):
        need(obj.get("schema_version") == 1
             and obj.get("kind") == kind, "EVIDENCE_KIND_MISMATCH")
    source_sha = shape.get("source_zip_sha256")
    original_sha = shape.get("original_v309_jar_sha256")
    need(_sha(source_sha) and _sha(original_sha),
         "SHAPE_SOURCE_ORIGINAL_PINS_MISSING")
    need(jvm.get("original_client_sha256") == original_sha
         and source.get("source_archive_sha256") == source_sha,
         "INDEPENDENT_INPUT_SHA256_PINS_DISAGREE")

    need(shape.get("candidate_proposals_are_identity_accepted") is False
         and shape.get("whole_client_deobfuscation_complete") is False
         and shape.get("source_files_rewritten_or_built") is False,
         "R127_UNSUPPORTED_ACCEPTANCE_CLAIM")
    need(jvm.get("original_client_executed") is False
         and jvm.get("invokedynamic_callees_guessed") is False
         and jvm.get("original_source_identity_accepted") is False,
         "R130_JVM_CALL_PROVENANCE_INVALID")
    need(source.get("source_call_owners_symbol_resolved") is True
         and source.get("source_symbols_missing_or_ambiguous") is False
         and source.get("ambient_project_classpath_disabled") is True
         and source.get("original_game_binary_used_as_fallback") is False
         and source.get("source_game_code_executed") is False
         and source.get("source_game_classes_generated") is False,
         "R131_SOURCE_SYMBOL_AUTHORITY_INCOMPLETE")
    proposals = _rows_with_exact_digest(
        shape, field="private_review_only_proposals",
        digest_field="private_proposal_manifest_sha256")
    orig_edges = _rows_with_exact_digest(
        jvm, field="private_original_call_edges",
        digest_field="private_edge_manifest_sha256")
    source_edges = _rows_with_exact_digest(
        source, field="private_source_call_edges",
        digest_field="private_source_call_edge_manifest_sha256")

    need(shape.get("unique_undecided_shape_proposals") == len(proposals)
         and jvm.get("direct_rs_owner_edge_count") == len(orig_edges)
         and source.get("source_direct_rs_call_edge_count") ==
            len(source_edges),
         "REPORTED_COUNTS_DISAGREE_WITH_PRIVATE_ROWS")
    need(sum(r.get("count", 0) for r in orig_edges) ==
         jvm.get("direct_rs_callsite_count")
         and sum(r.get("count", 0) for r in source_edges) ==
         source.get("source_direct_rs_callsite_count"),
         "REPORTED_CALLSITE_COUNTS_DISAGREE")
    for rows in (orig_edges, source_edges):
        need(rows == sorted(rows, key=lambda r: (
            r.get("caller", ""), r.get("callee", ""))),
            "EDGE_MANIFEST_NOT_CANONICALLY_ORDERED")
    evidence = corroborate_source_original_call_edges(
        proposals, source_edges, orig_edges,
        required_anchors=minimum_anchors)
    published = {
        "schema_version": 1,
        "kind": "private_v309_source_jvm_callgraph_replay_r132",
        "source_archive_sha256": source_sha,
        "original_client_sha256": original_sha,
        "r127_proposal_manifest_sha256":
            shape["private_proposal_manifest_sha256"],
        "r130_original_edge_manifest_sha256":
            jvm["private_edge_manifest_sha256"],
        "r131_source_edge_manifest_sha256":
            source["private_source_call_edge_manifest_sha256"],
        "proposal_count": evidence["proposal_count"],
        "original_jvm_edge_count": len(orig_edges),
        "source_ast_edge_count": len(source_edges),
        "minimum_independent_anchors": minimum_anchors,
        "review_tier_counts": evidence["tier_counts"],
        "private_result_manifest_sha256":
            evidence["review_only_manifest_sha256"],
        "class_member_identity_accepted": False,
        "callgraph_equivalence_certified": False,
        "method_opcode_operand_parity_proven": False,
        "complete_client_deobfuscated_source_built": False,
        "original_client_executed": False,
        "private_rows_included": bool(include_private_rows),
    }
    if include_private_rows:
        published["private_review_only_rows"] = (
            evidence["private_review_only_rows"])
    return published


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_r127_proposals")
    p.add_argument("private_r130_original_edges")
    p.add_argument("private_r131_source_edges")
    p.add_argument("fresh_private_report")
    p.add_argument("--minimum-anchors", type=int, default=2)
    p.add_argument("--private-rows", action="store_true")
    args = p.parse_args(argv)
    out = Path(args.fresh_private_report)
    try:
        need(not out.exists() and not out.is_symlink()
             and out.parent.is_dir() and not out.parent.is_symlink(),
             "FRESH_PRIVATE_REPORT_REQUIRED")
        shape = _private_report(
            args.private_r127_proposals,
            "private_v309_java_ast_jvm_structural_singleton_proposals_r127")
        original = _private_report(
            args.private_r130_original_edges,
            "private_original_v309_jvm_invoke_edges_r130")
        source = _private_report(
            args.private_r131_source_edges,
            "private_source_ast_symbol_resolved_calls_r131")
        result = replay_private_call_graph_evidence(
            shape, original, source,
            minimum_anchors=args.minimum_anchors,
            include_private_rows=args.private_rows)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items()
                          if k != "private_review_only_rows"},
                         sort_keys=True))
    except Exception:
        p.error("PRIVATE_R132_INDEPENDENT_CALLGRAPH_REPLAY_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
