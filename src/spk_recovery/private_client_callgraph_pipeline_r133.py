"""R133: single private execution of R127 → R130 → R131 → R132.

Exact SHA-pinned v309 original client and decompiled source are parsed only.
Original JAR is NEVER launched; candidate source is NEVER generated/run. The
source-symbol resolver must succeed with an empty project classpath. If any
lane fails, no partial graph evidence is accepted or published.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_source_jvm_shape_singletons_r127 import (
    source_vs_original_shape_research,
)
from .private_original_jvm_call_edges_r130 import (
    extract_jvm_call_edges, sha256_file,
)
from .private_source_ast_call_edges_r131 import extract_private_source_call_edges
from .private_callgraph_evidence_replay_r132 import (
    replay_private_call_graph_evidence,
)
from .private_client_source_ast_census_r126 import sha_file


class PrivateCallGraphPipelineR133Error(ValueError):
    pass


def require(ok, why):
    if not ok:
        raise PrivateCallGraphPipelineR133Error(why)


def replay_original_source_callgraph(source_zip, original_jar, *,
                                     source_sha256,
                                     original_sha256=CANONICAL_V309,
                                     minimum_anchors=2,
                                     include_private_rows=False):
    """Full guarded research replay, NOT class/semantic/source acceptance."""
    src = Path(source_zip)
    jar = Path(original_jar)
    require(src.is_file() and jar.is_file()
            and not src.is_symlink() and not jar.is_symlink(),
            "PRIVATE_CLIENT_INPUT_FILES_REQUIRED")
    require(sha_file(src) == source_sha256
            and sha256_file(jar) == original_sha256,
            "PRIVATE_CLIENT_INPUT_SHA256_MISMATCH")
    # Do not materialize any original/decompiled source in public GitHub.
    shape = source_vs_original_shape_research(
        src, jar, source_sha256=source_sha256,
        original_sha256=original_sha256, include_identifiers=True)
    original = extract_jvm_call_edges(
        jar, original_sha256=original_sha256,
        include_private_edges=True)
    source = extract_private_source_call_edges(
        src, source_sha256=source_sha256,
        include_private_edges=True)
    report = replay_private_call_graph_evidence(
        shape, original, source, minimum_anchors=minimum_anchors,
        include_private_rows=include_private_rows)
    require(sha_file(src) == source_sha256
            and sha256_file(jar) == original_sha256,
            "PRIVATE_CLIENT_INPUT_CHANGED_DURING_REPLAY")
    report.update({
        "schema_version": 1,
        "kind": "private_v309_full_source_original_callgraph_pipeline_r133",
        "source_java_files_parsed": source["source_java_file_count"],
        "source_ast_declared_types": shape["source_ast_named_declarations"],
        "original_rs_classfiles_parsed": original["parsed_rs_class_count"],
        "original_rs_methods_parsed": original["parsed_rs_method_count"],
        "source_symbol_resolution_completed": True,
        "original_invokedynamic_owners_inferred": False,
        "candidate_source_executed": False,
        "original_client_jar_executed": False,
        "class_lineage_accepted": False,
        "whole_client_deobfuscated_source_built": False,
    })
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_decompiled_source_zip")
    p.add_argument("private_original_v309_jar")
    p.add_argument("fresh_private_report")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--minimum-anchors", type=int, default=2)
    p.add_argument("--private-rows", action="store_true")
    args = p.parse_args(argv)
    out = Path(args.fresh_private_report)
    try:
        require(not out.exists() and not out.is_symlink()
                and out.parent.is_dir() and not out.parent.is_symlink(),
                "FRESH_PRIVATE_REPORT_REQUIRED")
        report = replay_original_source_callgraph(
            args.private_decompiled_source_zip,
            args.private_original_v309_jar,
            source_sha256=args.source_sha256,
            original_sha256=args.original_sha256,
            minimum_anchors=args.minimum_anchors,
            include_private_rows=args.private_rows)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
        print(json.dumps({
            k: v for k, v in report.items()
            if k != "private_review_only_rows"
        }, sort_keys=True))
    except Exception:
        p.error("PRIVATE_R133_FULL_CALLGRAPH_PIPELINE_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
