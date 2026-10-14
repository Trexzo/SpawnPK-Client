"""R153: exact original-v309 linked matrix method coverage and Packet frontier.

Read-only original JVM evidence with SHA-pinned private selected-method JSON.
No guessed Java source, private method identifiers, binary bytes or source
archive are published. A selected method is only *previously reported* by
the caller, never silently certified by this coverage inventory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file
from .private_v309_dependency_closure_r136 import audit_pinned_original_jar


class MatrixCoverageR153Error(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise MatrixCoverageR153Error(reason)


def matrix_original_method_coverage(original_jar, private_selection_json, *,
                                   original_sha256=CANONICAL_V309,
                                   selection_sha256,
                                   original_owner="com/a/b/a/b",
                                   original_packet="rs/x/e"):
    need(sha_file(original_jar) == original_sha256 and
         sha_file(private_selection_json) == selection_sha256,
         "R153_PINNED_INPUT_HASH_MISMATCH")
    graph = audit_pinned_original_jar(
        original_jar, original_sha256=original_sha256,
        include_private_names=True)
    partition = graph["private_dependency_partition"]
    need(original_owner in set(partition["direct_rs_dependent_non_rs"]),
         "R153_OWNER_NOT_ORIGINAL_RS_LINKED_EXCLUDED")
    raw_selection = Path(private_selection_json).read_bytes()
    need(len(raw_selection) <= 100000,
         "R153_SELECTION_TOO_LARGE")
    selected_raw = json.loads(raw_selection)
    need(isinstance(selected_raw, list) and 1 <= len(selected_raw) <= 64,
         "R153_SELECTION_NOT_BOUNDED_LIST")
    selections = []
    for entry in selected_raw:
        need(isinstance(entry, dict) and
             set(entry) == {"name", "descriptor"} and
             all(isinstance(value, str) for value in entry.values()),
             "R153_SELECTION_NOT_EXACT_MEMBER_ID")
        selections.append((entry["name"], entry["descriptor"]))
    need(len(selections) == len(set(selections)),
         "R153_DUPLICATE_SELECTED_MEMBER")
    with ZipFile(original_jar) as jar:
        path = original_owner + ".class"
        need(jar.namelist().count(path) == 1,
             "R153_ORIGINAL_MATRIX_NOT_UNIQUE")
        original_raw = jar.read(path)
    parsed = parse_class(original_raw)
    need(parsed.name == original_owner, "R153_JVM_OWNER_MISMATCH")
    profile = profile_class_field_accesses(original_raw)
    need(profile["internal_name"] == original_owner,
         "R153_PROFILE_OWNER_DRIFT")
    original = {}
    for m in profile["methods"]:
        identity = (m["name"], m["descriptor"])
        need(identity not in original, "R153_DUPLICATE_ORIGINAL_METHOD")
        original[identity] = m
    need(set(selections).issubset(original),
         "R153_SELECTION_REFERENCES_MISSING_ORIGINAL_MEMBER")
    # A direct Packet dependency may be present only in a method descriptor,
    # even when there is no separately emitted CONSTANT_Class entry.
    packet_descriptor = "L" + original_packet + ";"
    classified = {"selected": 0, "unselected_packet_direct": 0,
                  "unselected_other_rs_direct": 0,
                  "unselected_no_direct_rs_reference": 0}
    packet_invocations = 0
    method_count_with_packet_ref = 0
    unselected_instruction_count = 0
    for identity, m in original.items():
        invocations = m.get("method_invocations", [])
        field_accesses = m.get("field_accesses", [])
        packet_calls = sum(
            c.get("owner") == original_packet for c in invocations)
        packet_mention = bool(
            packet_descriptor in identity[1] or packet_calls or
            any(f.get("owner") == original_packet or
                packet_descriptor in f.get("descriptor", "")
                for f in field_accesses) or
            any(packet_descriptor in c.get("descriptor", "")
                for c in invocations))
        other_rs = (any(
            c.get("owner", "").startswith("rs/") or
            "Lrs/" in c.get("descriptor", "")
            for c in invocations) or
            any(f.get("owner", "").startswith("rs/") or
                "Lrs/" in f.get("descriptor", "")
                for f in field_accesses) or
            "Lrs/" in identity[1])
        if identity in selections:
            classified["selected"] += 1
        else:
            packet_invocations += packet_calls
            method_count_with_packet_ref += int(packet_mention)
            unselected_instruction_count += len(m.get("instructions", []))
            if packet_mention:
                classified["unselected_packet_direct"] += 1
            elif other_rs:
                classified["unselected_other_rs_direct"] += 1
            else:
                classified["unselected_no_direct_rs_reference"] += 1
    need(sum(classified.values()) == len(original),
         "R153_ORIGINAL_METHOD_COVERAGE_NOT_EXHAUSTIVE")
    report = {
        "schema_version": 1,
        "kind": "private_v309_original_matrix_source_method_frontier_r153",
        "original_client_sha256": original_sha256,
        "original_matrix_class_sha256": hashlib.sha256(original_raw).hexdigest(),
        "private_selected_method_ids_sha256": selection_sha256,
        "original_declared_method_count": len(original),
        "selected_earlier_method_ids_not_reverified_by_this_tool":
            classified["selected"],
        "remaining_method_count": len(original) - classified["selected"],
        "remaining_direct_original_packet_referencing_methods":
            classified["unselected_packet_direct"],
        "remaining_other_rs_direct_referencing_methods":
            classified["unselected_other_rs_direct"],
        "remaining_methods_without_direct_rs_descriptor_or_member_reference":
            classified["unselected_no_direct_rs_reference"],
        "remaining_direct_packet_method_invocations": packet_invocations,
        "remaining_methods_directly_referencing_packet": method_count_with_packet_ref,
        "remaining_decoded_jvm_instruction_count": unselected_instruction_count,
        "all_original_declared_methods_accounted_for": True,
        "selected_prior_methods_jvm_parity_reverified": False,
        "original_matrix_source_recovery_complete": False,
        "indirect_or_reflection_dependent_game_calls_ruled_out": False,
        "original_game_binary_fallback_allowed": False,
        "private_member_identifiers_exposed": False,
        "recovered_source_publication_authorized": False,
    }
    need(sha_file(original_jar) == original_sha256 and
         sha_file(private_selection_json) == selection_sha256,
         "R153_PINNED_INPUT_CHANGED_DURING_SCAN")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_v309_jar")
    p.add_argument("private_original_selected_method_ids_json")
    p.add_argument("fresh_private_sanitized_report")
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--selection-sha256", required=True)
    p.add_argument("--original-owner", default="com/a/b/a/b")
    p.add_argument("--original-packet", default="rs/x/e")
    args = p.parse_args(argv)
    output = Path(args.fresh_private_sanitized_report)
    try:
        need(not output.exists() and not output.is_symlink()
             and output.parent.is_dir() and not output.parent.is_symlink(),
             "R153_PRIVATE_REPORT_MUST_BE_FRESH")
        report = matrix_original_method_coverage(
            args.private_original_v309_jar,
            args.private_original_selected_method_ids_json,
            original_sha256=args.original_sha256,
            selection_sha256=args.selection_sha256,
            original_owner=args.original_owner,
            original_packet=args.original_packet)
        output.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n",
                          encoding="utf-8")
        print("R153_PRIVATE_ORIGINAL_MATRIX_COVERAGE_NOT_SOURCE_CERTIFICATION")
        print("private_report_sha256="+sha_file(output))
    except Exception:
        p.error("R153_ORIGINAL_METHOD_COVERAGE_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
