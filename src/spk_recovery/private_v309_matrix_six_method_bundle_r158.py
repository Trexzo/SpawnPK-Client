"""R158: exact private six-method original matrix Java source bundle check.

Original full-JAR and private source digests are required. Source code and
scaffold implementations are not published by this module.
"""
from __future__ import annotations
from .private_v309_matrix_source_method_parity_r150 import verify_private_matrix_source_subset

EXPECTED_MATRIX_SHA256 = "52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030"


def verify_six_matrix_methods(original_jar, recovered_java_zip, helper_java_zip,
                              method_selection_json, *, original_sha256,
                              source_sha256, helper_sha256, selection_sha256,
                              matrix_owner="com/a/b/a/b",
                              expected_matrix_sha256=EXPECTED_MATRIX_SHA256,
                              expected_method_count=6,
                              expected_instructions=602,
                              expected_helper_count=3,
                              expected_self_calls=2):
    report = verify_private_matrix_source_subset(
        original_jar, recovered_java_zip, method_selection_json,
        original_sha256=original_sha256,
        recovered_source_sha256=source_sha256,
        selection_sha256=selection_sha256,
        original_owner=matrix_owner,
        private_scaffold_java_zip=helper_java_zip,
        private_scaffold_sha256=helper_sha256,
        require_selected_self_call_closure=True)
    expectations = {
        "original_matrix_owner_class_sha256": expected_matrix_sha256,
        "verified_selected_method_count": expected_method_count,
        "matched_opcode_count": expected_instructions,
        "private_compilation_only_helper_source_count": expected_helper_count,
        "selected_original_self_call_edges_closed_and_checked": expected_self_calls,
        "all_selected_core_method_code_equal": True,
        "source_compiled_with_empty_original_external_classpath": True,
        "original_game_class_binary_fallback_used": False,
        "original_helper_binary_classfiles_placed_on_classpath": False,
        "helper_java_source_class_bodies_verified_original": False,
        "complete_original_matrix_java_source_restored": False,
    }
    for key, expected in expectations.items():
        if report.get(key) != expected:
            raise ValueError("R158_SOURCE_ONLY_MATRIX_BUNDLE_PROOF_FAILED:" + key)
    return {
        "schema_version": 1,
        "kind": "original_v309_six_matrix_method_java_bundle_r158",
        "original_client_sha256": original_sha256,
        "recovered_source_sha256": source_sha256,
        "helper_source_sha256": helper_sha256,
        "method_selection_sha256": selection_sha256,
        "original_matrix_class_sha256": expected_matrix_sha256,
        "verified_matrix_method_count": expected_method_count,
        "verified_jvm_instruction_count": expected_instructions,
        "verified_internal_source_call_edges": expected_self_calls,
        "private_source_method_witness_sha256":
            report["private_selected_method_manifest_sha256"],
        "stackmap_representation_equivalent":
            report["all_selected_stackmap_representations_equal"],
        "helper_java_bodies_original_proven": False,
        "full_matrix_or_client_original_source_complete": False,
        "original_source_publication_authorized": False,
    }
