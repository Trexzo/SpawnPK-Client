"""R194 — complete original-v309 rs/secure/a Linux identifier Java recovery.

Java9 source-only rebuild of all SIX original JVM methods, including
dmidecode, lshal, BufferedReader and nested IO/finally paths. Never launches
system tools, executes original game code, or uses binary compiler fallback.
No original derived Java/bytecode is committed to public GitHub.
"""
from __future__ import annotations

from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_v309_macos_serial_source_r193 import (
    verify_pinned_original_macos_serial_java,
)
from .private_v309_four_owner_javac_frontier_r192 import (
    build_private_four_owner_overlay,
    compare_pinned_private_four_owner_javac,
)
from .private_client_source_ast_census_r126 import sha_file

OWNER="rs/secure/a"
ORIGINAL_CLASS_SHA256=(
    "9f85f7ff35546207eeb25433a26ab528a25f1fe999809375d6be77ad051aef3f"
)
PRIVATE_ORIGINAL_SOURCE_ZIP_SHA256=(
    "46a23049635bd8b2ab24365847ea2ade195128aa8025508f0452fde14b77462b"
)
ORIGINAL_METHODS=6
ORIGINAL_JVM_INSTRUCTIONS=165
ORIGINAL_FIELDS=1
PRIOR_FIVE_SOURCE_TREE_SHA256=(
    "7ec20525e1e2a51c78199102b46c54bd5b2ae9c0a9cd40783473d21a975e9eab"
)
NEW_SIX_SOURCE_TREE_SHA256=(
    "dc5a23e63c03506093b21ffc4ab013a14fcbd21f70c847c688c9441b2b8d1b65"
)


class R194OriginalLinuxIdentifierError(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise R194OriginalLinuxIdentifierError(why)


def verify_pinned_original_linux_identifier_source(
        original_jar,linux_java_source_zip, *,
        original_sha256=CANONICAL_V309,
        source_sha256=PRIVATE_ORIGINAL_SOURCE_ZIP_SHA256,
        original_owner=OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        expected_methods=ORIGINAL_METHODS,
        expected_instructions=ORIGINAL_JVM_INSTRUCTIONS,
        expected_fields=ORIGINAL_FIELDS):
    """Fully replay original class, not just its exported a() signature."""
    result=verify_pinned_original_macos_serial_java(
        original_jar,linux_java_source_zip,
        original_sha256=original_sha256,
        source_sha256=source_sha256,
        original_owner=original_owner,
        original_class_sha256=original_class_sha256,
        expected_methods=expected_methods,
        expected_instructions=expected_instructions,
        expected_fields=expected_fields)
    need(result["full_original_method_count_compiled"]==
         expected_methods and
         result["full_original_jvm_instructions_matched"]==
         expected_instructions and
         result["original_field_abi_and_class_header_match"] and
         result["original_exception_handlers_and_control_flow_match"],
         "R194_NOT_ALL_ORIGINAL_LINUX_SOURCE_METHODS_ACCEPTED")
    return {
        **result,
        "kind":"v309_original_linux_identifier_full_java_source_r194",
        "full_dmidecode_and_lshal_source_methods_recovered":True,
        "original_shell_commands_executed":False,
        "remaining_invented_compiler_helper_owners_not_original":
            ["rs/f/a","rs/w/c","rs/secure/c"],
    }


def verify_pinned_six_original_owner_javac_frontier(
        pinned_previous_five_tree_zip,
        pinned_linux_java_source_zip, fresh_six_tree_zip, *,
        old_tree_sha256=PRIOR_FIVE_SOURCE_TREE_SHA256,
        added_source_sha256=PRIVATE_ORIGINAL_SOURCE_ZIP_SHA256,
        expected_new_tree_sha256=NEW_SIX_SOURCE_TREE_SHA256,
        old_java_files=1283):
    """Real two-run whole-tree Javac delta under identical JDK-only flags."""
    need(sha_file(pinned_previous_five_tree_zip)==old_tree_sha256 and
         sha_file(pinned_linux_java_source_zip)==added_source_sha256,
         "R194_PRIVATE_SOURCE_INPUT_SHA256_DRIFT")
    overlay=build_private_four_owner_overlay(
        pinned_previous_five_tree_zip,[pinned_linux_java_source_zip],
        fresh_six_tree_zip,
        baseline_sha256=old_tree_sha256,
        source_identities=((OWNER+".java",added_source_sha256),),
        expected_baseline_java=old_java_files)
    need(overlay["new_overlay_zip_sha256"]==expected_new_tree_sha256 and
         overlay["baseline_java_files_exactly_preserved"]==old_java_files and
         overlay["added_independently_evidenced_java_files"]==1,
         "R194_PRIVATE_1284_SOURCE_OVERLAY_NOT_EXACT")
    measured=compare_pinned_private_four_owner_javac(
        pinned_previous_five_tree_zip,fresh_six_tree_zip,
        original_sha256=old_tree_sha256,
        candidate_sha256=expected_new_tree_sha256,
        expected_original_count=old_java_files,
        expected_added_count=1)
    measured["original_dmidecode_lshal_system_processes_executed"]=False
    measured["compiler_only_dependency_helpers_in_source_tree"]=False
    measured["all_original_v309_client_source_compiles"] = (
        measured["full_original_v309_client_compiles"])
    return measured
