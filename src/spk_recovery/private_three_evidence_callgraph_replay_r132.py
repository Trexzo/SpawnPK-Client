"""R132: combine independently pinned source, original JVM and shape evidence.

Consumes private R127/R130/R131 report files; never executes either game
binary or Java source and never accepts inferred class identities. An incomplete
source symbol graph remains explicitly incomplete even if some edges match.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from .private_client_callgraph_corroboration_r129 import (
    CallGraphCorroborationR129Error,
    corroborate_source_original_call_edges,
)


class PrivateThreeEvidenceR132Error(ValueError):
    pass


def need(value, why):
    if not value:
        raise PrivateThreeEvidenceR132Error(why)


def _digest(payload, *, ascii_only=True):
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=ascii_only).encode("utf-8")).hexdigest()


def _read_private_report(path, expected_kind):
    path = Path(path)
    need(path.is_file() and not path.is_symlink()
         and 0 < path.stat().st_size <= 32_000_000,
         "PRIVATE_EVIDENCE_REPORT_FILE_REQUIRED")
    try:
        raw = path.read_bytes()
        doc = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PrivateThreeEvidenceR132Error(
            "PRIVATE_EVIDENCE_JSON_INVALID") from exc
    need(type(doc) is dict and doc.get("schema_version") == 1
         and doc.get("kind") == expected_kind,
         "PRIVATE_EVIDENCE_REPORT_KIND_INVALID")
    return doc, hashlib.sha256(raw).hexdigest()


def replay_three_private_call_evidences(source_shape_doc, original_jvm_doc,
                                        source_ast_doc, *, require_no_errors=False,
                                        include_identifiers=False):
    need(source_shape_doc.get("kind")
         == "private_v309_java_ast_jvm_structural_singleton_proposals_r127"
         and original_jvm_doc.get("kind")
         == "private_original_v309_jvm_invoke_edges_r130"
         and source_ast_doc.get("kind")
         == "private_v309_source_ast_attributed_call_edges_r131",
         "THREE_EVIDENCE_REPORT_KINDS_INVALID")
    need(all(doc.get("schema_version") == 1
             for doc in (source_shape_doc, original_jvm_doc, source_ast_doc)),
         "THREE_EVIDENCE_SCHEMAS_INVALID")
    need(all(doc.get("private_class_names_included",
                     doc.get("private_identifiers_included")) is True
             for doc in (source_shape_doc, original_jvm_doc, source_ast_doc)),
         "THREE_EVIDENCE_PRIVATE_IDENTIFIERS_REQUIRED")
    source_sha = source_shape_doc.get("source_zip_sha256")
    original_sha = source_shape_doc.get("original_v309_jar_sha256")
    need(type(source_sha) is str and
         re.fullmatch(r"[a-f0-9]{64}", source_sha) is not None
         and type(original_sha) is str and
         re.fullmatch(r"[a-f0-9]{64}", original_sha) is not None,
         "SOURCE_AND_ORIGINAL_PINS_INVALID")
    need(source_ast_doc.get("source_archive_sha256") == source_sha
         and original_jvm_doc.get("original_client_sha256") == original_sha,
         "THREE_EVIDENCE_INPUT_SHA256_MISMATCH")

    proposals = source_shape_doc.get("private_review_only_proposals")
    source_edges = source_ast_doc.get("private_source_call_edges")
    original_edges = original_jvm_doc.get("private_original_call_edges")
    need(isinstance(proposals, list) and isinstance(source_edges, list)
         and isinstance(original_edges, list),
         "THREE_EVIDENCE_PRIVATE_EDGE_LISTS_MISSING")
    need(_digest(proposals) == source_shape_doc.get(
            "private_proposal_manifest_sha256"),
         "R127_PROPOSAL_MANIFEST_SHA256_INVALID")
    need(_digest(source_edges) == source_ast_doc.get(
            "private_edge_manifest_sha256"),
         "R131_SOURCE_EDGE_MANIFEST_SHA256_INVALID")
    need(_digest(original_edges, ascii_only=False) == original_jvm_doc.get(
            "edge_manifest_sha256"),
         "R130_ORIGINAL_EDGE_MANIFEST_SHA256_INVALID")
    need(type(require_no_errors) is bool, "STRICT_COMPILER_OPTION_INVALID")
    errors = source_ast_doc.get("java_symbol_attribution_errors")
    unresolved = source_ast_doc.get("unresolved_source_method_invocations")
    need(type(errors) is int and errors >= 0
         and type(unresolved) is int and unresolved >= 0,
         "SOURCE_SYMBOL_RESOLUTION_COVERAGE_MISSING")
    if require_no_errors:
        need(errors == 0 and unresolved == 0,
             "SOURCE_SYMBOL_UNRESOLVED_STRICT_REPLAY_BLOCKED")

    try:
        classification = corroborate_source_original_call_edges(
            proposals, source_edges, original_edges,
            required_anchors=2)
    except CallGraphCorroborationR129Error as exc:
        raise PrivateThreeEvidenceR132Error(
            "R129_CLASS_GRAPH_NOT_COMPARABLE") from exc
    report = {
        "schema_version": 1,
        "kind": "private_v309_three_evidence_callgraph_replay_r132",
        "source_archive_sha256": source_sha,
        "original_client_sha256": original_sha,
        "r127_proposal_manifest_sha256":
            source_shape_doc["private_proposal_manifest_sha256"],
        "r130_original_graph_manifest_sha256":
            original_jvm_doc["edge_manifest_sha256"],
        "r131_source_graph_manifest_sha256":
            source_ast_doc["private_edge_manifest_sha256"],
        "source_java_attribution_error_count": errors,
        "source_java_unresolved_method_call_count": unresolved,
        "source_symbol_resolution_exhaustive":
            errors == 0 and unresolved == 0,
        "source_graph_semantically_equivalent_to_jvm": False,
        "review_only_candidate_pair_count":
            classification["proposal_count"],
        "two_anchor_review_tier_counts":
            classification["tier_counts"],
        "private_review_manifest_sha256":
            classification["review_only_manifest_sha256"],
        "original_jar_executed": False,
        "source_java_executed": False,
        "accepted_client_class_mappings": 0,
        "source_tree_rewritten_or_compiled": False,
        "fully_deobfuscated_client_certified": False,
        "private_identifiers_included": bool(include_identifiers),
    }
    if include_identifiers:
        report["private_callgraph_review_rows"] = classification[
            "private_review_only_rows"]
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_r127_report")
    p.add_argument("private_r130_report")
    p.add_argument("private_r131_report")
    p.add_argument("fresh_private_result")
    p.add_argument("--require-no-source-errors", action="store_true")
    p.add_argument("--private-identifiers", action="store_true")
    args = p.parse_args(argv)
    target = Path(args.fresh_private_result)
    try:
        need(not target.exists() and not target.is_symlink()
             and target.parent.is_dir() and not target.parent.is_symlink(),
             "FRESH_PRIVATE_RESULT_REQUIRED")
        x, xsha = _read_private_report(
            args.private_r127_report,
            "private_v309_java_ast_jvm_structural_singleton_proposals_r127")
        y, ysha = _read_private_report(
            args.private_r130_report,
            "private_original_v309_jvm_invoke_edges_r130")
        z, zsha = _read_private_report(
            args.private_r131_report,
            "private_v309_source_ast_attributed_call_edges_r131")
        result = replay_three_private_call_evidences(
            x, y, z,
            require_no_errors=args.require_no_source_errors,
            include_identifiers=args.private_identifiers)
        result["r127_private_report_sha256"] = xsha
        result["r130_private_report_sha256"] = ysha
        result["r131_private_report_sha256"] = zsha
        target.write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        print(json.dumps({
            k: v for k, v in result.items()
            if k != "private_callgraph_review_rows"
        }, sort_keys=True))
    except Exception:
        p.error("PRIVATE_THREE_EVIDENCE_V309_R132_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
