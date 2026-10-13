"""R118: one exact original-v309 post-javac owner passes R95/R94/R58/R88.

Input must ALREADY be a separately source-compiled Java9 owner with all ten
original method bodies and BOTH independently repaired large-method verifier
tables (R116 364-op ten original frames, R117 697-op 161 symbolic frames).
R106->R105->R104->R95 repairs one enum StackMap and two synthetic accessor
method names/callsites, then R94 checks nine owner ordinary methods, R58
checks 93 original class initializer writes/213 operands, and R88 checks all
126 fields, 10 methods, and four nested classfiles on SAME final JAR.

This is bytecode/classfile parity only, NEVER original external helper bodies,
authorial Java source identity, configuration effects, or client gameplay.
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

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .clinit_operand_semantic_witness import (
    ClinitOperandWitnessError, compare_clinit_operand_semantics,
)
from .private_original_fourth_enum_accessors import digest
from .private_large_owner_methods_inventory_r112 import (
    TwoLargeOwnerMethodInventoryError, unique_unrecovered,
)
from .private_recompiled_v309_saver_r113 import (
    OriginalSaverMethodAcceptanceError, original_saver_method_profile_proof,
)
from .private_v309_loader_symbolic_frames_r117 import (
    LoaderSymbolicFramesR117Error, frames_at_ordinals, semantic_frame,
)
from .private_v309_enum_stackmap_repair_r106 import (
    VerifiedEnumStackMapError, repair_then_require_r105_r95,
)
from .private_all_owner_methods_parity import (
    AllOwnerMethodsParityError, replay_all_original_methods,
)
from .private_owner_metadata_frontier import (
    OriginalOwnerFrontierError, private_owner_frontier, _nested,
)
from .private_complete_postjavac_v309_owner_r107 import (
    PostJavacCompleteOwnerAcceptanceError, unique_four_before_postprocess,
)
from .whole_method_operand_parity import (
    WholeMethodOperandError, compare_all_method_operands,
)


class OneFinalOriginalOwnerR118Error(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise OneFinalOriginalOwnerR118Error(reason)


def original_93_identity_aliases(original):
    owner=original.get("internal_name")
    methods=[m for m in original.get("methods", [])
             if m.get("name")=="<clinit>" and m.get("descriptor")=="()V"]
    need(len(methods)==1 and methods[0].get("access")==8
         and len(methods[0].get("instructions") or [])==213,
         "ORIGINAL_V309_213_OP_CLINIT_REQUIRED")
    fieldset={(f.get("name"),f.get("descriptor")):f
              for f in original.get("fields",[])}
    need(len(fieldset)==126,
         "ORIGINAL_V309_126_FIELD_DECLARATION_IDENTITY_REQUIRED")
    written=[]
    for row in methods[0]["instructions"]:
        if row.get("opcode") != "0xb3":
            continue
        need(row.get("owner")==owner
             and (row.get("name"),row.get("descriptor")) in fieldset,
             "ORIGINAL_CLINIT_HAS_UNVERIFIED_EXTERNAL_OR_UNKNOWN_WRITE")
        written.append((row["name"],row["descriptor"]))
    need(len(written)==len(set(written))==93,
         "ORIGINAL_NINETY_THREE_INJECTIVE_STATIC_WRITES_REQUIRED")
    return [
        {"original":{"name":n,"descriptor":d},
         "candidate":{"name":n,"descriptor":d}}
        for n,d in written
    ]


def exact_original_large_methods_before_or_after(original, candidate):
    try:
        large=unique_unrecovered(original)
        saver=original_saver_method_profile_proof(original,candidate)
    except (TwoLargeOwnerMethodInventoryError,
            OriginalSaverMethodAcceptanceError,KeyError,TypeError) as exc:
        raise OneFinalOriginalOwnerR118Error(
            "R113_ORIGINAL_SAVER_364_TEN_FRAMES_MISSING") from exc
    need(saver.get("original_saver_R66_R81_all_operands_passed") is True
         and saver.get("original_saver_jvm_StackMapTable_frames_equal")==10,
         "ORIGINAL_SAVER_R113_PROOF_FLAGS_INCOMPLETE")
    loader=large[697]
    matches=[m for m in candidate.get("methods",[])
             if (m.get("name"),m.get("descriptor"))==
                (loader.get("name"),loader.get("descriptor"))]
    need(len(matches)==1 and matches[0].get("access")==loader.get("access")==9,
         "ORIGINAL_LOADER_697_JVM_DECLARATION_NOT_EXACT")
    try:
        operands=compare_all_method_operands(
            original,loader["name"],"()V",
            candidate,loader["name"],"()V",
            [],[],[])
    except (WholeMethodOperandError,ValueError,KeyError,TypeError,
            IndexError) as exc:
        raise OneFinalOriginalOwnerR118Error(
            "ORIGINAL_LOADER_697_R81_OPERANDS_OR_CFG_NOT_EXACT") from exc
    need(operands.get(
             "original_instructions_with_all_semantic_operands_compared")==697
         and operands.get("original_explicit_branches")==120
         and operands.get("original_ordered_typed_exception_entries")==44
         and operands.get("original_ordered_static_writes")==78
         and operands.get("all_parsed_JVM_operands_equal_with_private_aliases")
              is True,
         "ORIGINAL_LOADER_697_R81_EVIDENCE_INCOMPLETE")
    old_ord,old_index=frames_at_ordinals(loader)
    new_ord,new_index=frames_at_ordinals(matches[0])
    need(old_ord==new_ord and len(old_ord)==161,
         "ORIGINAL_LOADER_161_FRAME_ORDINALS_DIFFERENT")
    for old,new in zip(loader["stackmap_frames"],matches[0]["stackmap_frames"]):
        need(semantic_frame(old,old_index,matches[0]["instructions"])
             ==semantic_frame(new,new_index,matches[0]["instructions"]),
             "ORIGINAL_LOADER_FRAME_VERIFICATION_STATE_DIFFERS")
    return True


def accept_one_final_v309_source_compiled_owner(
    original_jar, candidate_jar, owner_entry, surrogate_simple,
    output, *, original_sha256, candidate_sha256,
):
    original_jar,candidate_jar,output=(
        Path(original_jar),Path(candidate_jar),Path(output))
    need(not output.exists() and not output.is_symlink()
         and output.parent.is_dir() and not output.parent.is_symlink(),
         "FRESH_PRIVATE_COMPLETE_OWNER_OUTPUT_REQUIRED")
    need(type(owner_entry) is str and owner_entry.endswith(".class")
         and not owner_entry.startswith("/") and "\\" not in owner_entry
         and all(x not in ("",".","..") for x in owner_entry.split("/"))
         and type(surrogate_simple) is str and
         re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*",surrogate_simple),
         "ORIGINAL_OWNER_OR_SOURCE_SURROGATE_UNSAFE")
    need(original_jar.resolve()!=candidate_jar.resolve(),
         "ORIGINAL_COMPLETE_JAR_MUST_NOT_BE_SOURCE_CANDIDATE")
    for jar,pin in ((original_jar,original_sha256),
                    (candidate_jar,candidate_sha256)):
        need(jar.is_file() and not jar.is_symlink()
             and type(pin) is str
             and re.fullmatch(r"[A-Fa-f0-9]{64}",pin)
             and digest(jar)==pin.lower(),
             "ORIGINAL_OR_SOURCE_JAR_SHA256_PIN_MISMATCH")
        with ZipFile(jar) as z:
            items=z.namelist()
            need(items.count(owner_entry)==1
                 and len(items)==len(set(items)),
                 "ORIGINAL_OR_SOURCE_OWNER_ARCHIVE_NOT_UNIQUE")
    original=profile_jar_class(original_jar,owner_entry)
    candidate=profile_jar_class(candidate_jar,owner_entry)
    need(original.get("internal_name")==candidate.get("internal_name")
         and original.get("classfile_major")==candidate.get("classfile_major")==53
         and original.get("class_access")==candidate.get("class_access")
         and original.get("super_name")==candidate.get("super_name")
         and len(original.get("methods",[]))==
             len(candidate.get("methods",[]))==10
         and len(original.get("fields",[]))==
             len(candidate.get("fields",[]))==126,
         "EXACT_ORIGINAL_SOURCE_126_FIELD_TEN_METHOD_PREIMAGE_REQUIRED")
    need(set((x["name"],x["descriptor"],x["access"]) for x in original["methods"])
         ==set((x["name"],x["descriptor"],x["access"])
              for x in candidate["methods"]),
         "ORIGINAL_ALL_TEN_OWNER_METHOD_DECLARATIONS_NOT_EXACT")
    try:
        unique_four_before_postprocess(
            original_jar,candidate_jar,owner_entry,surrogate_simple)
    except (PostJavacCompleteOwnerAcceptanceError,OSError,ValueError) as exc:
        raise OneFinalOriginalOwnerR118Error(
            "EXACT_ONE_SOURCE_INVALID_FOURTH_ENUM_NAME_REQUIRED") from exc
    aliases=original_93_identity_aliases(original)
    exact_original_large_methods_before_or_after(original,candidate)

    with tempfile.TemporaryDirectory(
        prefix="v309-final-one-candidate-r118-",dir=output.parent,
    ) as td:
        root=Path(td)
        try:
            accepted=repair_then_require_r105_r95(
                original_jar,candidate_jar,owner_entry,surrogate_simple,
                root/"r106",original_sha256=original_sha256,
                candidate_sha256=candidate_sha256)
        except (VerifiedEnumStackMapError,ValueError,OSError,
                IndexError,KeyError,TypeError) as exc:
            raise OneFinalOriginalOwnerR118Error(
                "R106_R105_R104_R95_FOUR_ENUMS_NOT_ACCEPTED") from exc
        need(accepted.get("original_four_nested_enums_R95_accepted") is True
             and accepted.get(
                 "original_case_insensitive_lookup_method_frames_identical")
                 is True
             and accepted.get("candidate_method_code_bytes_preserved") is True
             and accepted.get(
                 "original_lookups_method_code_bytes_transferred") is False,
             "EXACT_ORIGINAL_FOUR_ENUM_R95_REPAIR_PROVENANCE_MISSING")
        final=root/"r106"/"all-four-R95-after-StackMap.private.jar"
        final_pin=accepted.get("r95_accepted_candidate_sha256")
        need(isinstance(final_pin,str)
             and re.fullmatch(r"[a-f0-9]{64}",final_pin)
             and final.is_file() and not final.is_symlink()
             and digest(final)==final_pin
             and final_pin!=candidate_sha256.lower(),
             "FINAL_FOUR_ENUM_ORIGINAL_JVM_CANDIDATE_HASH_MISMATCH")
        final_profile=profile_jar_class(final,owner_entry)
        exact_original_large_methods_before_or_after(
            original,final_profile)
        try:
            ordinary=replay_all_original_methods(
                original_jar,final,owner_entry,owner_entry,
                root/"r94",original_sha256=original_sha256,
                candidate_sha256=final_pin)
        except (AllOwnerMethodsParityError,ValueError,OSError,
                IndexError,KeyError,TypeError) as exc:
            raise OneFinalOriginalOwnerR118Error(
                "R94_FINAL_NINE_OWNER_METHODS_NOT_ACCEPTED") from exc
        need(ordinary.get(
                "R66_and_R81_parity_passed_all_nine_ordinary_methods") is True
             and ordinary.get(
                 "original_ordinary_methods_parity_checked")==9
             and ordinary.get(
                 "original_ordinary_jvm_instruction_operands_compared")==1135,
             "NINE_ORIGINAL_OWNER_METHOD_OPCODES_R94_NOT_ALL_PROVEN")
        try:
            init=compare_clinit_operand_semantics(
                original,final_profile,aliases)
            fields=private_owner_frontier(
                original,final_profile,
                _nested(original_jar,owner_entry),
                _nested(final,owner_entry))
        except (ClinitOperandWitnessError,OriginalOwnerFrontierError,
                IndexError,KeyError,ValueError,TypeError,OSError) as exc:
            raise OneFinalOriginalOwnerR118Error(
                "R58_OR_R88_COMPLETE_FINAL_OWNER_JVM_NOT_ACCEPTED") from exc
        need(init.get(
                "identical_normalized_initializer_operand_semantics") is True
             and init.get("original_owner_static_writes_in_order")==93
             and init.get("original_initializer_instructions")==213,
             "R58_FINAL_ORIGINAL_93_WRITE_213_OP_INIT_NOT_EQUAL")
        need(fields.get("original_fields")==126
             and fields.get("candidate_fields")==126
             and fields.get("original_methods")==10
             and fields.get("candidate_methods")==10
             and fields.get("original_nested_classes")==4
             and fields.get("candidate_nested_classes")==4
             and all(fields.get(k)==0 for k in (
                 "missing_original_fields",
                 "extra_candidate_fields",
                 "shared_field_declaration_mismatches",
                 "missing_original_methods",
                 "extra_candidate_methods",
                 "shared_method_declaration_mismatches",
                 "missing_original_nested_classes",
                 "extra_candidate_nested_classes",
             ))
             and all(fields.get(k) is True for k in (
                 "original_candidate_major_equal",
                 "original_candidate_super_equal",
                 "original_candidate_class_access_equal",
                 "original_candidate_class_signature_equal",
                 "original_candidate_interface_list_equal",
             )),
             "R88_FINAL_126_FIELDS_TEN_METHODS_FOUR_ENUMS_NOT_EQUAL")
        need(digest(original_jar)==original_sha256.lower()
             and digest(candidate_jar)==candidate_sha256.lower()
             and digest(final)==final_pin,
             "ORIGINAL_OR_PREIMAGE_FINAL_POSTIMAGE_HASH_CHANGED")
        report={
            "schema_version":1,
            "kind":"private_v309_one_java9_source_postimage_original_owner_and_four_enums",
            "research_only":True,
            "original_complete_jar_sha256":original_sha256.lower(),
            "source_compiled_verified_preimage_sha256":candidate_sha256.lower(),
            "final_all_original_gates_candidate_sha256":final_pin,
            "original_owner_fields_verified":126,
            "original_owner_ten_methods_verified":10,
            "original_owner_nonclinit_method_operands_verified":1135,
            "original_owner_213_initializer_instructions_verified":213,
            "original_initializer_static_writes_verified":93,
            "original_nested_enums_verified":4,
            "original_loader_161_verification_states_equal":True,
            "original_saver_ten_stackmap_frames_exact":True,
            "R95_original_four_enums_passed":True,
            "R94_original_nine_ordinary_owner_methods_passed":True,
            "R58_original_clinit_operand_semantics_passed":True,
            "R88_original_owner_all_declarations_passed":True,
            "original_external_helper_implementation_equivalence":False,
            "original_filesystem_and_callback_side_effects_proven":False,
            "original_java_authorial_source_identity_proven":False,
            "whole_original_client_runtime_equivalence_certified":False,
        }
        stage=root/"accepted"
        stage.mkdir()
        shutil.copyfile(final,stage/"candidate.private.jar")
        (stage/"original-one-final-owner.aggregate.json").write_text(
            json.dumps(report,sort_keys=True,indent=2)+"\n",
            encoding="utf-8")
        need(not output.exists(),
             "PRIVATE_FINAL_OWNER_OUTPUT_OCCUPIED_AFTER_ACCEPTANCE")
        os.rename(stage,output)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for item in ("original_jar","candidate_jar","owner_entry",
                 "surrogate_simple","new_private_output"):
        p.add_argument(item)
    p.add_argument("--original-sha256",required=True)
    p.add_argument("--candidate-sha256",required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(accept_one_final_v309_source_compiled_owner(
            args.original_jar,args.candidate_jar,args.owner_entry,
            args.surrogate_simple,args.new_private_output,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256),sort_keys=True))
    except (OneFinalOriginalOwnerR118Error,BytecodeProfileError,
            OSError,ValueError,IndexError,KeyError,TypeError):
        p.error("PRIVATE_V309_COMPLETE_ORIGINAL_OWNER_R118_NOT_ACCEPTED")


if __name__=="__main__":
    main()
