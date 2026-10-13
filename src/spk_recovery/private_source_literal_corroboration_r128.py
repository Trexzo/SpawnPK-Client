"""R128: original class constant-pool string cross-check for R127 source shapes.

A second, independently decoded witness to prioritize source recovery.
Literal overlap (even exhaustive overlap) is NOT proof of original class
identity. No candidate is accepted, rewritten, published or executed here.
"""
from __future__ import annotations

from collections import defaultdict
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .classfile import parse_class
from .private_client_source_ast_census_r126 import source_members, sha_file
from .private_source_jvm_shape_singletons_r127 import (
    source_vs_original_shape_research,
)
from .private_client_namespace_legalizer_r125 import CANONICAL_V309


class PrivateLiteralCorroborationR128Error(ValueError):
    pass


def need(value, message):
    if not value:
        raise PrivateLiteralCorroborationR128Error(message)


def _decode(value):
    return base64.urlsafe_b64decode(
        value + "=" * ((-len(value)) % 4)).decode("utf-8")


def literal_witnesses(entries):
    """Trusted AST helper parses text; never executes candidate source."""
    javac, java = shutil.which("javac"), shutil.which("java")
    need(javac is not None and java is not None,
         "JDK_REQUIRED_FOR_PRIVATE_LITERAL_SCAN")
    helper = (Path(__file__).resolve().parent / "java" /
              "ClientAstStringLiteralWitnessR128.java")
    need(helper.is_file(), "R128_JAVA_LITERAL_HELPER_MISSING")
    with tempfile.TemporaryDirectory(prefix="v309-r128-ast-private-") as td:
        root = Path(td)
        inputs = root / "source"
        compiled = root / "trusted-scanner"
        inputs.mkdir()
        compiled.mkdir()
        for rel, data in entries:
            target = inputs / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        runs = (
            [javac, "-encoding", "UTF-8", "-d",
             str(compiled), str(helper)],
            [java, "-cp", str(compiled),
             "ClientAstStringLiteralWitnessR128", str(inputs)],
        )
        stdout = b""
        for args in runs:
            try:
                process = subprocess.run(
                    args, cwd=root, stdin=subprocess.DEVNULL,
                    capture_output=True, timeout=180)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise PrivateLiteralCorroborationR128Error(
                    "SOURCE_LITERAL_SCAN_NOT_COMPLETED") from exc
            need(process.returncode == 0,
                 "SOURCE_LITERAL_AST_PARSE_OR_HELPER_FAILED")
            stdout = process.stdout
        need(len(stdout) <= 20_000_000,
             "PRIVATE_SOURCE_LITERAL_OUTPUT_EXCEEDS_LIMIT")
    records = defaultdict(set)
    for line in stdout.decode("utf-8").splitlines():
        pair = line.split("\t")
        need(len(pair) == 2, "AST_LITERAL_PROTOCOL_INVALID")
        name, value = _decode(pair[0]), _decode(pair[1])
        need(name and len(name) < 512, "AST_LITERAL_OWNER_INVALID")
        records[name].add(value)
    return dict(records)


def corroborate_literal_witnesses(proposals, source_literals,
                                  original_literals, minimum_chars=6):
    """A positive CP witness is additional evidence, never acceptance."""
    need(type(minimum_chars) is int and 4 <= minimum_chars <= 64,
         "LITERAL_INFORMATIVENESS_THRESHOLD_INVALID")
    summary = {
        "unique_source_jvm_shape_proposals": len(proposals),
        "with_any_source_string_literal": 0,
        "with_informative_source_literals": 0,
        "all_informative_literals_in_original_class_constant_pool": 0,
        "some_but_not_all_informative_literals_in_original_pool": 0,
        "no_informative_source_literal_in_original_pool": 0,
        "no_informative_source_literal_available": 0,
    }
    private = []
    seen = set()
    for proposal in proposals:
        source = proposal["source_java_type"]
        original = proposal["original_jvm_class"]
        need((source, original) not in seen,
             "DUPLICATE_SHAPE_MATCH_PROPOSAL")
        seen.add((source, original))
        src = source_literals.get(source, set())
        pool = original_literals.get(original)
        need(pool is not None, "ORIGINAL_JVM_CP_MISSING_FOR_PROPOSAL")
        if src:
            summary["with_any_source_string_literal"] += 1
        informative = {x for x in src if len(x) >= minimum_chars}
        if not informative:
            tier = "no_informative_literal"
            summary["no_informative_source_literal_available"] += 1
            matched = 0
        else:
            summary["with_informative_source_literals"] += 1
            matched = len(informative & pool)
            if matched == len(informative):
                tier = "all_informative_literals_in_constant_pool"
                summary[
                    "all_informative_literals_in_original_class_constant_pool"
                ] += 1
            elif matched:
                tier = "partial_literal_overlap"
                summary[
                    "some_but_not_all_informative_literals_in_original_pool"
                ] += 1
            else:
                tier = "no_literal_overlap"
                summary[
                    "no_informative_source_literal_in_original_pool"
                ] += 1
        private.append({
            "source_java_type": source,
            "original_jvm_class": original,
            "source_informative_literal_count": len(informative),
            "original_literal_witness_count": matched,
            "literal_evidence_tier": tier,
            "class_identity_accepted": False,
        })
    need(sum(summary[k] for k in (
            "all_informative_literals_in_original_class_constant_pool",
            "some_but_not_all_informative_literals_in_original_pool",
            "no_informative_source_literal_in_original_pool",
            "no_informative_source_literal_available",
         )) == len(proposals),
         "LITERAL_BUCKET_PARTITION_INVALID")
    return summary, private


def private_literal_corroboration(source_zip, original_jar, *,
                                 source_sha256,
                                 original_sha256=CANONICAL_V309,
                                 include_identifiers=False):
    shape = source_vs_original_shape_research(
        source_zip, original_jar,
        source_sha256=source_sha256,
        original_sha256=original_sha256,
        include_identifiers=True)
    rows = shape["private_review_only_proposals"]
    entries = source_members(source_zip, source_sha256)
    ast_literals = literal_witnesses(entries)
    cp_literals = {}
    with ZipFile(original_jar) as jar:
        for original in sorted({
                row["original_jvm_class"] for row in rows}):
            need(original.startswith("rs/"),
                 "NON_GAME_CLIENT_CLASS_PROPOSAL")
            try:
                parsed = parse_class(jar.read(original + ".class"))
            except Exception as exc:
                raise PrivateLiteralCorroborationR128Error(
                    "ORIGINAL_JVM_CLASS_CONSTANT_POOL_PARSE_FAILED") from exc
            need(parsed.name == original,
                 "ORIGINAL_CLASS_IDENTITY_CHANGED")
            cp_literals[original] = set(parsed.literal_strings)
    counts, detailed = corroborate_literal_witnesses(
        rows, ast_literals, cp_literals)
    material = json.dumps(detailed, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    report = {
        "schema_version": 1,
        "kind": "private_v309_ast_source_vs_jvm_literal_evidence_r128",
        "private_source_zip_sha256": source_sha256,
        "pinned_original_jar_sha256": original_sha256,
        "structural_proposal_manifest_sha256":
            shape["private_proposal_manifest_sha256"],
        "private_literal_tiers_sha256": hashlib.sha256(material).hexdigest(),
        **counts,
        "original_client_executed": False,
        "candidate_java_source_executed": False,
        "literal_evidence_alone_accepts_class_identity": False,
        "original_class_lineage_accepted": False,
        "complete_deobfuscated_client_source_tree": False,
        "private_identifiers_included": bool(include_identifiers),
    }
    if include_identifiers:
        report["private_review_only_literal_evidence"] = detailed
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_decompiled_source_zip")
    p.add_argument("private_original_v309_jar")
    p.add_argument("fresh_private_report")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--private-identifiers", action="store_true")
    a = p.parse_args(argv)
    output = Path(a.fresh_private_report)
    try:
        need(not output.exists() and not output.is_symlink()
             and output.parent.is_dir() and not output.parent.is_symlink(),
             "FRESH_PRIVATE_REPORT_REQUIRED")
        report = private_literal_corroboration(
            a.private_decompiled_source_zip, a.private_original_v309_jar,
            source_sha256=a.source_sha256,
            original_sha256=a.original_sha256,
            include_identifiers=a.private_identifiers)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        print("R128_CLIENT_LITERAL_CORROBORATION_COMPLETE")
        print("private_report_sha256=" + sha_file(output))
    except Exception:
        p.error("PRIVATE_CLIENT_LITERAL_R128_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
