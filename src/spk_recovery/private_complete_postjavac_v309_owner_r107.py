"""R107: one POST-javac candidate must pass exact original-v309 owner + enums.

R90 compiles source with ONE unavoidable nested-enum simple-name collision.
R106 applies strict metadata/verified accessor rebinding -> R105/R104/R95.
The resulting single SHA-pinned final candidate must then pass R94 (all nine
ordinary owner methods), R58 clinit semantics and R88 full owner frontier.
Only the final postimage may be called the combined accepted candidate.

Never copy original Code. No published original class IDs or private source.
No external helper/runtime/gameplay equivalence certification.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile

from .mutable_scalar_initializer_source import _digest
from .private_owner_initializer_triple_gate import (
    FullOwnerCandidateGateError,
    accept_original_v309_owner_methods_and_initializer,
    read_initializer_aliases,
)
from .private_v309_enum_stackmap_repair_r106 import (
    VerifiedEnumStackMapError, repair_then_require_r105_r95,
)
from .private_all_owner_methods_parity import (
    AllOwnerMethodsParityError, replay_all_original_methods,
)
from .clinit_store_order_witness import _verified_class
from .clinit_operand_semantic_witness import (
    ClinitOperandWitnessError, compare_clinit_operand_semantics,
)
from .private_owner_metadata_frontier import (
    OriginalOwnerFrontierError, private_owner_frontier, _nested,
)


class PostJavacCompleteOwnerAcceptanceError(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise PostJavacCompleteOwnerAcceptanceError(code)


def unique_four_before_postprocess(original_jar, source_jar, owner_entry,
                                   surrogate_simple):
    """Only known illegal Java source name may differ, never a missing enum."""
    owner = owner_entry[:-6]
    original_fourth = owner + "$" + owner.rsplit("/", 1)[-1] + ".class"
    candidate_fourth = owner + "$" + surrogate_simple + ".class"
    with ZipFile(original_jar) as a, ZipFile(source_jar) as b:
        an, bn = a.namelist(), b.namelist()
        need(len(an) == len(set(an)) and len(bn) == len(set(bn)) and
             an.count(owner_entry) == 1 and bn.count(owner_entry) == 1,
             "ORIGINAL_OR_PREIMAGE_OWNER_ARCHIVE_ENTRIES_NOT_UNIQUE")
        originals = {x for x in an if x.startswith(owner + "$")
                     and x.endswith(".class")}
        candidates = {x for x in bn if x.startswith(owner + "$")
                      and x.endswith(".class")}
        need(len(originals) == len(candidates) == 4 and
             original_fourth in originals and
             candidate_fourth in candidates and
             original_fourth not in candidates and
             candidate_fourth not in originals and
             originals - {original_fourth} ==
                 candidates - {candidate_fourth},
             "EXACT_ONE_SOURCE_INVALID_ORIGINAL_ENUM_COLLISION_REQUIRED")
    return True


def accept_private_v309_postjavac_owner(
    original_jar, owner_entry, original_loader, original_saver,
    private_java_source_root, candidate_owner_entry,
    candidate_loader, candidate_saver,
    loader_aliases, saver_aliases, clinit_aliases,
    surrogate_simple, output, *, original_sha256,
    javac="javac", compile_classpath=None,
):
    original_jar, output = Path(original_jar), Path(output)
    need(type(owner_entry) is str and owner_entry.endswith(".class")
         and owner_entry == candidate_owner_entry
         and not owner_entry.startswith("/") and "\\" not in owner_entry
         and all(part not in ("", ".", "..")
                 for part in owner_entry.split("/")),
         "ORIGINAL_CANDIDATE_OWNER_BINARY_IDENTITY_NOT_EXACT")
    name = owner_entry[:-6].rsplit("/", 1)[-1]
    need(type(surrogate_simple) is str and
         re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", surrogate_simple)
         and surrogate_simple != name,
         "SOURCE_COLLIDING_ENUM_SURROGATE_IDENTITY_UNSAFE")
    need(isinstance(original_sha256, str) and
         re.fullmatch(r"[0-9a-fA-F]{64}", original_sha256)
         and original_jar.is_file() and not original_jar.is_symlink()
         and _digest(original_jar) == original_sha256.lower(),
         "ORIGINAL_V309_COMPLETE_JAR_SHA256_MISMATCH")
    original_sha256 = original_sha256.lower()
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "FRESH_PRIVATE_COMPOSITE_OUTPUT_REQUIRED")

    with tempfile.TemporaryDirectory(
        prefix="v309-owner-postjavac-r107-", dir=output.parent
    ) as directory:
        root = Path(directory)
        try:
            compiled = accept_original_v309_owner_methods_and_initializer(
                original_jar, owner_entry, original_loader, original_saver,
                private_java_source_root, candidate_owner_entry,
                candidate_loader, candidate_saver,
                loader_aliases, saver_aliases, clinit_aliases, root / "r90",
                original_sha256=original_sha256, javac=javac,
                compile_classpath=compile_classpath,
            )
        except (FullOwnerCandidateGateError, ValueError, OSError) as exc:
            raise PostJavacCompleteOwnerAcceptanceError(
                "R90_JAVA9_OWNER_SOURCE_NOT_ACCEPTED") from exc

        need(compiled.get("both_R87_methods_passed") is True and
             compiled.get("R58_initializer_operand_semantics_passed") is True and
             compiled.get("R88_original_owner_field_metadata_passed") is True and
             compiled.get("original_field_declarations") == 126 and
             compiled.get("candidate_field_declarations") == 126 and
             compiled.get("original_field_declaration_differences") == 0 and
             compiled.get("original_initializer_static_writes") == 93 and
             compiled.get("original_unrecovered_method_declarations") == 0 and
             compiled.get("original_unrecovered_nested_class_entries") == 1,
             "R90_SOURCE_FRONTIER_NOT_EXACT_ONE_NAME_COLLISION")
        source_jar = root / "r90" / "candidate.private.jar"
        source_pin = compiled.get("candidate_compiled_jar_sha256")
        need(isinstance(source_pin, str) and
             re.fullmatch(r"[0-9a-f]{64}", source_pin)
             and source_jar.is_file() and not source_jar.is_symlink()
             and _digest(source_jar) == source_pin,
             "SOURCE_COMPILED_CANDIDATE_SHA256_MISMATCH")
        unique_four_before_postprocess(
            original_jar, source_jar, owner_entry, surrogate_simple)

        # R106 must apply the exact one-frame repair BEFORE R105/R104/R95.
        # It returns a different, freshly SHA-pinned, final postimage JAR.
        try:
            enums = repair_then_require_r105_r95(
                original_jar, source_jar, owner_entry,
                surrogate_simple, root / "r106",
                original_sha256=original_sha256, candidate_sha256=source_pin)
        except (VerifiedEnumStackMapError, ValueError, OSError) as exc:
            raise PostJavacCompleteOwnerAcceptanceError(
                "R106_R105_R104_R95_FOUR_ENUM_SOURCE_NOT_ACCEPTED") from exc
        need(enums.get("original_four_nested_enums_R95_accepted") is True and
             enums.get("original_case_insensitive_lookup_method_frames_identical")
             is True and
             enums.get("candidate_method_code_bytes_preserved") is True and
             enums.get("original_lookups_method_code_bytes_transferred") is not True,
             "FINAL_FOUR_ENUM_R95_ACCEPTANCE_FLAGS_INCOMPLETE")
        final_jar = root / "r106" / "all-four-R95-after-StackMap.private.jar"
        final_pin = enums.get("r95_accepted_candidate_sha256")
        need(isinstance(final_pin, str) and
             re.fullmatch(r"[0-9a-f]{64}", final_pin)
             and final_jar.is_file() and not final_jar.is_symlink()
             and _digest(final_jar) == final_pin
             and final_pin != source_pin,
             "FINAL_POSTJAVAC_CANDIDATE_SHA256_MISMATCH")

        # Deliberately run R94 only AFTER class/method/owner CP rebinding.
        # The raw source JAR is not accepted as the final candidate.
        try:
            methods = replay_all_original_methods(
                original_jar, final_jar, owner_entry, owner_entry,
                root / "r94", original_sha256=original_sha256,
                candidate_sha256=final_pin)
        except (AllOwnerMethodsParityError, ValueError, OSError) as exc:
            raise PostJavacCompleteOwnerAcceptanceError(
                "R94_FINAL_NINE_OWNER_METHODS_NOT_EXACT") from exc
        need(methods.get(
                "R66_and_R81_parity_passed_all_nine_ordinary_methods") is True
             and methods.get("original_ordinary_methods_parity_checked") == 9
             and methods.get(
                 "original_ordinary_jvm_instruction_operands_compared") == 1135,
             "R94_FINAL_NINE_METHOD_ACCEPTANCE_COUNTS_NOT_EXACT")

        # Recheck original <clinit> and ALL owner declarations on final
        # postimage, not the pre-rebind source JAR.
        try:
            original_profile = _verified_class(
                original_jar, owner_entry, original_sha256)
            final_profile = _verified_class(
                final_jar, owner_entry, final_pin)
            aliases = read_initializer_aliases(clinit_aliases)
            clinit = compare_clinit_operand_semantics(
                original_profile, final_profile, aliases)
            frontier = private_owner_frontier(
                original_profile, final_profile,
                _nested(original_jar, owner_entry),
                _nested(final_jar, owner_entry))
        except (ClinitOperandWitnessError, OriginalOwnerFrontierError,
                ValueError, OSError, IndexError, KeyError, TypeError) as exc:
            raise PostJavacCompleteOwnerAcceptanceError(
                "R58_R88_FINAL_OWNER_POSTIMAGE_NOT_VERIFIABLE") from exc
        need(clinit.get("identical_normalized_initializer_operand_semantics")
             is True and
             clinit.get("original_owner_static_writes_in_order") == 93 and
             clinit.get("original_initializer_instructions") == 213,
             "R58_FINAL_OWNER_CLINIT_OPERANDS_NOT_EXACT")
        need(frontier.get("original_fields") == 126 and
             frontier.get("candidate_fields") == 126 and
             frontier.get("original_methods") == 10 and
             frontier.get("candidate_methods") == 10 and
             frontier.get("missing_original_fields") == 0 and
             frontier.get("extra_candidate_fields") == 0 and
             frontier.get("shared_field_declaration_mismatches") == 0 and
             frontier.get("missing_original_methods") == 0 and
             frontier.get("extra_candidate_methods") == 0 and
             frontier.get("shared_method_declaration_mismatches") == 0 and
             frontier.get("original_nested_classes") == 4 and
             frontier.get("candidate_nested_classes") == 4 and
             frontier.get("missing_original_nested_classes") == 0 and
             frontier.get("extra_candidate_nested_classes") == 0 and
             all(frontier.get(k) is True for k in (
                 "original_candidate_major_equal",
                 "original_candidate_super_equal",
                 "original_candidate_class_access_equal",
                 "original_candidate_class_signature_equal",
                 "original_candidate_interface_list_equal")),
             "R88_FINAL_OWNER_FIELD_METHOD_ENUM_DECLARATIONS_NOT_EXACT")
        need(_digest(original_jar) == original_sha256 and
             _digest(source_jar) == source_pin and
             _digest(final_jar) == final_pin,
             "PINNED_ORIGINAL_SOURCE_OR_POSTIMAGE_CHANGED_DURING_REPLAY")
        report = {
            "schema_version": 1,
            "kind": "private_v309_postjavac_126field_owner_and_four_enum_composite",
            "research_only": True,
            "original_complete_jar_sha256": original_sha256,
            "compiled_source_candidate_sha256": source_pin,
            "final_postjavac_candidate_sha256": final_pin,
            "original_source_name_collision_pending_before_rebind": 1,
            "unresolved_nested_enum_identities_after_rebind": 0,
            "original_owner_fields_checked": 126,
            "original_owner_initializer_static_writes_checked": 93,
            "original_owner_initializer_instructions_checked": 213,
            "original_owner_ordinary_methods_checked": 9,
            "original_owner_ordinary_method_operands_checked": 1135,
            "original_nested_enums_R95_checked": 4,
            "R90_original_fields_and_source_initializer_passed": True,
            "R106_R105_R104_R95_original_four_nested_enums_passed": True,
            "R94_final_postimage_nine_owner_methods_passed": True,
            "R58_final_postimage_initializer_passed": True,
            "R88_final_postimage_owner_declarations_passed": True,
            "original_external_helper_implementations_equivalent": False,
            "original_filesystem_and_callback_side_effects_proven": False,
            "whole_original_client_runtime_equivalence_certified": False,
        }
        stage = root / "accepted"
        stage.mkdir()
        shutil.copyfile(final_jar, stage / "candidate.private.jar")
        need(_digest(stage / "candidate.private.jar") == final_pin,
             "FINAL_POSTIMAGE_COPY_SHA256_MISMATCH")
        with (stage / "all-owner-postjavac-gates.aggregate.json").open(
            "x", encoding="utf-8", newline="\n",
        ) as stream:
            json.dump(report, stream, sort_keys=True, indent=2)
            stream.write("\n")
        need(not output.exists() and not output.is_symlink(),
             "PRIVATE_COMPOSITE_OUTPUT_OCCUPIED_AFTER_PROOF")
        os.rename(stage, output)
        return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for item in (
        "original_jar", "owner_entry", "original_loader", "original_saver",
        "private_java_source_root", "candidate_owner_entry",
        "candidate_loader", "candidate_saver", "loader_aliases",
        "saver_aliases", "clinit_aliases", "surrogate_simple",
        "new_private_output",
    ):
        p.add_argument(item)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--javac", default="javac")
    p.add_argument("--compile-classpath", type=Path)
    args = p.parse_args(argv)
    try:
        report = accept_private_v309_postjavac_owner(
            args.original_jar, args.owner_entry, args.original_loader,
            args.original_saver, args.private_java_source_root,
            args.candidate_owner_entry, args.candidate_loader,
            args.candidate_saver, args.loader_aliases, args.saver_aliases,
            args.clinit_aliases, args.surrogate_simple,
            args.new_private_output, original_sha256=args.original_sha256,
            javac=args.javac, compile_classpath=args.compile_classpath)
        print(json.dumps(report, sort_keys=True))
    except (PostJavacCompleteOwnerAcceptanceError, ValueError, OSError):
        p.error("PRIVATE_R107_REAL_ORIGINAL_POSTJAVAC_OWNER_NOT_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
