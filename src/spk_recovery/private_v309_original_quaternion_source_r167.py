"""R167: verify the complete original-v309 quaternion Java class from source.

Proves all original method JVM instructions, constructor/pooling monitor handlers,
field and method ABI and Java9 StringConcat recipe. One exact original-named
Java owner, no original class/binary fallbacks, and no unverified helpers copied
into the canonical private client-source tree.
"""
from __future__ import annotations

from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_v309_original_transform_source_r166 import (
    verify_original_transform_java,
)
from .private_v309_original_vector_source_r164 import (
    private_vector_source_overlay,
)

QUATERNION_SHA="37ffe0bbc272b080bcede9b975f99f877da05375089b256c656566d8790c41df"


def verify_original_quaternion_java(original_jar, quaternion_source_zip, *,
                                    original_sha256=CANONICAL_V309,
                                    quaternion_source_sha256,
                                    owner="com/a/b/a/c",
                                    original_class_sha256=QUATERNION_SHA,
                                    expected_methods=11,
                                    expected_fields=7,
                                    expected_instructions=314):
    core=verify_original_transform_java(
        original_jar, quaternion_source_zip,
        original_sha256=original_sha256,
        transform_source_sha256=quaternion_source_sha256,
        owner=owner,
        original_class_sha256=original_class_sha256,
        expected_methods=expected_methods,
        expected_fields=expected_fields,
        expected_instructions=expected_instructions)
    return {
        "schema_version":1,
        "kind":"private_v309_original_quaternion_complete_java_r167",
        "original_class_sha256":original_class_sha256,
        "private_original_java_source_sha256":quaternion_source_sha256,
        "original_field_count":expected_fields,
        "original_jvm_method_count":expected_methods,
        "original_jvm_instruction_count":expected_instructions,
        "pool_acquire_release_monitor_and_handlers_checked_in_code":True,
        "original_class_flags_and_supertype_identical":
            core["original_class_flags_super_and_interfaces_equal"],
        "original_string_concat_bootstrap_equal":
            core["original_string_concatenation_bootstrap_recipe_equal"],
        "all_original_code_verified_from_java_source":True,
        "original_binary_used_as_compiler_dependency":False,
        "complete_client_source_compilation_verified":False,
        "recovered_source_publication_authorized":False,
    }


def verify_and_overlay_quaternion(original_jar, quaternion_source_zip,
                                  prior_canonical_zip, fresh_private_zip, *,
                                  original_sha256=CANONICAL_V309,
                                  quaternion_source_sha256,
                                  prior_canonical_sha256,
                                  owner="com/a/b/a/c",
                                  original_class_sha256=QUATERNION_SHA,
                                  expected_methods=11,expected_fields=7,
                                  expected_instructions=314,
                                  expected_prior_java=1275):
    proof=verify_original_quaternion_java(
        original_jar, quaternion_source_zip,
        original_sha256=original_sha256,
        quaternion_source_sha256=quaternion_source_sha256,
        owner=owner,
        original_class_sha256=original_class_sha256,
        expected_methods=expected_methods,
        expected_fields=expected_fields,
        expected_instructions=expected_instructions)
    overlay=private_vector_source_overlay(
        prior_canonical_zip,quaternion_source_zip,fresh_private_zip,
        baseline_sha256=prior_canonical_sha256,
        vector_source_sha256=quaternion_source_sha256,
        expected_original_files=expected_prior_java,
        expected_vector_source_rel=owner+".java")
    return {"original_quaternion_source":proof,
            "private_source_overlay":overlay,
            "full_original_v309_client_compiled":False}
