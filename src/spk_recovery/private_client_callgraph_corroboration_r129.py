"""R129: fail-closed call-graph corroboration for R127/R128 source candidates.

The input edge sets must be obtained by independent source-AST and original
JVM bytecode parsers. This module does not derive edges or certify lineage.
Edges are owner-to-owner call relationships, not method equivalence.
"""
from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re

class CallGraphCorroborationR129Error(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise CallGraphCorroborationR129Error(reason)


def _digest(obj):
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _identity(name):
    return (type(name) is str and 0 < len(name) <= 512
            and "\\" not in name and not name.startswith("/")
            and all(part not in ("", ".", "..") for part in name.split("/")))


def _edges(rows, kind):
    need(isinstance(rows, list) and len(rows) <= 2_000_000,
         kind + "_EDGES_INVALID")
    result = Counter()
    for row in rows:
        need(isinstance(row, dict) and set(row) == {"caller", "callee", "count"},
             kind + "_EDGE_SCHEMA_INVALID")
        a, b, n = row["caller"], row["callee"], row["count"]
        need(_identity(a) and _identity(b) and type(n) is int
             and 0 < n <= 1_000_000, kind + "_EDGE_INVALID")
        need((a, b) not in result, kind + "_EDGE_DUPLICATE")
        result[a, b] = n
    return result


def corroborate_source_original_call_edges(proposals, source_edges,
                                           original_edges, *,
                                           required_anchors=2):
    """Count matched anchored calls; never turn proposals into acceptance."""
    need(type(required_anchors) is int and 1 <= required_anchors <= 16,
         "REQUIRED_ANCHOR_BOUND_INVALID")
    need(isinstance(proposals, list) and len(proposals) <= 20000,
         "PROPOSALS_INVALID")
    source_to_original = {}
    claimed_originals = set()
    for row in proposals:
        need(isinstance(row, dict)
             and set(row) >= {"source_java_type", "original_jvm_class"},
             "PROPOSAL_SCHEMA_INVALID")
        s, o = row["source_java_type"], row["original_jvm_class"]
        need(_identity(s) and _identity(o)
             and s.startswith("rs/") and o.startswith("rs/"),
             "PROPOSAL_NAME_INVALID")
        need(s not in source_to_original and o not in claimed_originals,
             "PROPOSALS_NOT_ONE_TO_ONE")
        source_to_original[s] = o
        claimed_originals.add(o)
    src = _edges(source_edges, "SOURCE")
    orig = _edges(original_edges, "ORIGINAL")
    reports = []
    totals = Counter()
    for source, target in sorted(source_to_original.items()):
        applicable = [(other, count)
                      for (owner, other), count in src.items()
                      if owner == source and other in source_to_original
                      and other != source]
        # This is *only* corroboration among already reviewed candidate
        # edges, never a new edge-based assignment or name inference.
        matched = 0
        contradicted = 0
        for other, source_count in applicable:
            original_key = (target, source_to_original[other])
            original_count = orig.get(original_key, 0)
            if original_count >= source_count:
                matched += 1
            else:
                contradicted += 1
        # Unrelated calls (third-party, unresolved source symbols and
        # unknown JVM invoke targets) are deliberately excluded.
        if not applicable:
            tier = "no_anchored_source_calls"
        elif contradicted:
            tier = "anchored_call_contradiction"
        elif matched >= required_anchors:
            tier = "multi_anchor_call_corrob"
        else:
            tier = "insufficient_anchored_calls"
        totals[tier] += 1
        reports.append({
            "source_java_type": source,
            "original_jvm_class": target,
            "matched_anchored_callees": matched,
            "contradicted_anchored_callees": contradicted,
            "eligible_anchored_callees": len(applicable),
            "call_graph_evidence_tier": tier,
            "original_identity_accepted": False,
        })
    need(sum(totals.values()) == len(proposals),
         "CALLGRAPH_CLASSIFICATION_INCOMPLETE")
    return {
        "schema_version": 1,
        "kind": "private_source_jvm_callgraph_corroboration_r129",
        "proposal_count": len(proposals),
        "source_edge_count": len(src),
        "original_edge_count": len(orig),
        "minimum_independent_anchors": required_anchors,
        "tier_counts": dict(sorted(totals.items())),
        "review_only_manifest_sha256": _digest(reports),
        "source_original_names_accepted": False,
        "call_graph_equivalence_certified": False,
        "method_operand_parity_proven": False,
        "whole_client_compiles_from_source": False,
        "private_review_only_rows": reports,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_evidence_json")
    p.add_argument("fresh_private_report")
    a = p.parse_args(argv)
    source = Path(a.private_evidence_json)
    target = Path(a.fresh_private_report)
    try:
        need(source.is_file() and not source.is_symlink()
             and source.stat().st_size <= 16_000_000,
             "PRIVATE_EVIDENCE_FILE_REQUIRED")
        need(not target.exists() and not target.is_symlink()
             and target.parent.is_dir() and not target.parent.is_symlink(),
             "FRESH_REPORT_PATH_REQUIRED")
        envelope = json.loads(source.read_text(encoding="utf-8"))
        need(type(envelope) is dict
             and envelope.get("kind") == "private_source_jvm_callgraph_evidence_r129"
             and envelope.get("schema_version") == 1,
             "EVIDENCE_SCHEMA_INVALID")
        for key in ("source_archive_sha256", "original_client_sha256",
                    "source_parser_evidence_sha256", "original_parser_evidence_sha256"):
            need(type(envelope.get(key)) is str
                 and re.fullmatch(r"[a-f0-9]{64}", envelope[key]),
                 "EVIDENCE_SHA256_PIN_MISSING")
        report = corroborate_source_original_call_edges(
            envelope["proposals"], envelope["source_call_edges"],
            envelope["original_call_edges"],
            required_anchors=envelope.get("minimum_independent_anchors", 2))
        report["source_archive_sha256"] = envelope["source_archive_sha256"]
        report["original_client_sha256"] = envelope["original_client_sha256"]
        report["source_parser_evidence_sha256"] = envelope["source_parser_evidence_sha256"]
        report["original_parser_evidence_sha256"] = envelope["original_parser_evidence_sha256"]
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
        print(json.dumps({
            k: v for k, v in report.items() if k != "private_review_only_rows"
        }, sort_keys=True))
    except Exception:
        p.error("PRIVATE_R129_CALLGRAPH_EVIDENCE_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
