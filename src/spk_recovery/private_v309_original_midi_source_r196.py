"""R196: real v309 original MIDI audio client source (rs/w/c.java).

All 11 original Java9 JVM methods must compile from the exact SHA-pinned
private source without the original JAR, fake class declarations, or external
classfile fallbacks. The original synthesizer, sequencer, mixer-volume,
controlChange loops, MetaEventListener lambda, and ShortMessage handlers are
never EXECUTED by the verifier. This is original method Code recovery, not
a runnable client or a guarantee of Java Sound device compatibility.
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

OWNER="rs/w/c"
ORIGINAL_CLASS_SHA256=(
    "5583878cbaa84b8a34013a19605d3e1cc53f840a35d711abdb64a2a31df85ff5"
)
PRIVATE_ORIGINAL_JAVA_SOURCE_SHA256=(
    "48989772d86d2014aaa86179962a8d5c0d5fe8323476b46b0806797e511cc2dc"
)
ORIGINAL_METHODS=11
ORIGINAL_JVM_INSTRUCTIONS=263
ORIGINAL_FIELDS=6
PREVIOUS_SEVEN_JAVA_TREE_SHA256=(
    "99b852851b198d526596c9feb43a41572bf8519ad40245b2e7a221255c22a9a9"
)
NEW_EIGHT_JAVA_TREE_SHA256=(
    "f248c92c9bea9047a2282b826b8003095935093680f4ba25c6d3dee435a5b00f"
)


class R196OriginalMidiJavaError(ValueError):
    pass


def need(ok,reason):
    if not ok:
        raise R196OriginalMidiJavaError(reason)


def verify_pinned_original_v309_midi_java(
        original_jar,original_midi_java_source_zip, *,
        original_sha256=CANONICAL_V309,
        original_source_sha256=PRIVATE_ORIGINAL_JAVA_SOURCE_SHA256,
        original_owner=OWNER,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        expected_methods=ORIGINAL_METHODS,
        expected_instructions=ORIGINAL_JVM_INSTRUCTIONS,
        expected_fields=ORIGINAL_FIELDS):
    """Full source-only original JVM Code, including Java9 lambda bootstrap."""
    result=verify_pinned_original_macos_serial_java(
        original_jar,original_midi_java_source_zip,
        original_sha256=original_sha256,
        source_sha256=original_source_sha256,
        original_owner=original_owner,
        original_class_sha256=original_class_sha256,
        expected_methods=expected_methods,
        expected_instructions=expected_instructions,
        expected_fields=expected_fields)
    need(result["full_original_method_count_compiled"]==expected_methods and
         result["full_original_jvm_instructions_matched"]==
            expected_instructions and
         result["original_field_abi_and_class_header_match"] and
         result["original_exception_handlers_and_control_flow_match"],
         "R196_ORIGINAL_JAVA_SOUND_JVM_SOURCE_NOT_FULLY_VERIFIED")
    return {
        **result,
        "kind":"v309_original_midi_audio_java_source_r196",
        "all_original_midi_method_bodies_recovered":True,
        "original_synthesizer_channel_volume_loops_recovered":True,
        "original_meta_event_listener_lambda_recovered":True,
        "source_compiled_without_any_fake_class_helpers":True,
        "original_audio_device_or_game_code_executed":False,
        "remaining_direct_signlink_compiler_only_helper":
            "rs/f/a",
    }


def measure_pinned_eight_original_java_owner_frontier(
        prior_seven_owner_tree_zip,original_midi_java_source_zip,
        fresh_eight_owner_tree_zip, *,
        prior_tree_sha256=PREVIOUS_SEVEN_JAVA_TREE_SHA256,
        midi_source_sha256=PRIVATE_ORIGINAL_JAVA_SOURCE_SHA256,
        new_tree_sha256=NEW_EIGHT_JAVA_TREE_SHA256,
        old_java_files=1285):
    """JDK-only private 1286-file overlay, old-source byte preservation."""
    need(sha_file(prior_seven_owner_tree_zip)==prior_tree_sha256 and
         sha_file(original_midi_java_source_zip)==midi_source_sha256,
         "R196_EXACT_PRIVATE_SOURCE_INPUTS_REQUIRED")
    overlay=build_private_four_owner_overlay(
        prior_seven_owner_tree_zip,[original_midi_java_source_zip],
        fresh_eight_owner_tree_zip,
        baseline_sha256=prior_tree_sha256,
        source_identities=((OWNER+".java",midi_source_sha256),),
        expected_baseline_java=old_java_files)
    need(overlay["baseline_java_files_exactly_preserved"]==
            old_java_files and
         overlay["new_overlay_zip_sha256"]==new_tree_sha256,
         "R196_PRIVATE_EIGHT_ORIGINAL_OWNER_SOURCE_TREE_SHA_DRIFT")
    measured=compare_pinned_private_four_owner_javac(
        prior_seven_owner_tree_zip,fresh_eight_owner_tree_zip,
        original_sha256=prior_tree_sha256,
        candidate_sha256=new_tree_sha256,
        expected_original_count=old_java_files,
        expected_added_count=1)
    measured["original_midi_audio_code_executed"]=False
    measured["invented_audio_or_game_helpers_added_to_tree"]=False
    measured["whole_original_client_runtime_validated"]=False
    return measured
