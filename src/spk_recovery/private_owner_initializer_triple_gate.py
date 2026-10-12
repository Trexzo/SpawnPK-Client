"""R90: one compiled private v309 owner must pass load, save, field and clinit gates.

Composes R87's two-method Java9 gate, R58's ordered initializer operand
parity, and R88's field declaration inventory. Missing original methods or
nested enum implementations remain reported and block runtime certification.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

from .clinit_operand_semantic_witness import (
    ClinitOperandWitnessError, compare_clinit_operand_semantics,
)
from .clinit_store_order_witness import _verified_class
from .mutable_scalar_initializer_source import _digest
from .private_dual_method_java9_acceptance import (
    DualMethodAcceptanceError, accept_dual_method_java9,
)
from .private_owner_metadata_frontier import (
    OriginalOwnerFrontierError, private_owner_frontier, _nested,
)

class FullOwnerCandidateGateError(ValueError):
    pass

def need(condition, code):
    if not condition:
        raise FullOwnerCandidateGateError(code)

def read_initializer_aliases(path):
    path = Path(path)
    need(path.is_file() and not path.is_symlink() and
         path.stat().st_size <= 131072, "INIT_ALIAS_FILE_MISSING_OR_UNSAFE")
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FullOwnerCandidateGateError("INIT_ALIAS_JSON_UNREADABLE") from exc
    need(isinstance(data,dict) and data.get("schema_version")==1 and
         isinstance(data.get("aliases"),list), "INIT_ALIAS_SCHEMA_INVALID")
    return data["aliases"]

def accept_original_v309_owner_methods_and_initializer(
    original_jar, owner_class, loader, saver, source_root,
    candidate_owner, candidate_loader, candidate_saver,
    loader_aliases, saver_aliases, clinit_aliases, output, *,
    original_sha256, javac="javac", compile_classpath=None,
    expected_fields=126, expected_initializer_writes=93,
    required_method_counts=(697,364),
):
    output = Path(output)
    need(not output.exists() and not output.is_symlink(),
         "OUTPUT_ALREADY_EXISTS")
    need(output.parent.is_dir() and not output.parent.is_symlink(),
         "OUTPUT_PARENT_UNAVAILABLE")
    init_alias = read_initializer_aliases(clinit_aliases)
    with tempfile.TemporaryDirectory(
            prefix="v309-owner-triple-", dir=output.parent) as temporary:
        tmp=Path(temporary)
        try:
            dual=accept_dual_method_java9(
                original_jar, owner_class,
                loader,"()V",saver,"()V",
                source_root,candidate_owner,
                candidate_loader,"()V",candidate_saver,"()V",
                loader_aliases,saver_aliases,tmp/"dual",
                original_sha256=original_sha256,javac=javac,
                compile_classpath=compile_classpath,
                required_counts=required_method_counts)
        except (DualMethodAcceptanceError, OSError, ValueError) as exc:
            raise FullOwnerCandidateGateError(
                "R87_BOTH_METHODS_NOT_ACCEPTED") from exc
        candidate_jar=tmp/"dual"/"candidate.private.jar"
        candidate_sha=dual["compiled_candidate_jar_sha256"]
        try:
            original=_verified_class(
                Path(original_jar),owner_class,original_sha256)
            candidate=_verified_class(
                candidate_jar,candidate_owner,candidate_sha)
            clinit=compare_clinit_operand_semantics(
                original,candidate,init_alias)
        except (ClinitOperandWitnessError,OSError,ValueError,
                KeyError,IndexError,TypeError) as exc:
            raise FullOwnerCandidateGateError(
                "R58_ORIGINAL_INITIALIZER_PARITY_NOT_ACCEPTED") from exc
        need(clinit["original_owner_static_writes_in_order"]
             == expected_initializer_writes,
             "EXPECTED_ORIGINAL_INITIALIZER_WRITE_COUNT_NOT_MET")
        need(clinit["identical_normalized_initializer_operand_semantics"],
             "R58_INITIALIZER_OPERAND_SEMANTICS_NOT_EQUAL")
        try:
            frontier=private_owner_frontier(
                original,candidate,
                _nested(Path(original_jar),owner_class),
                _nested(candidate_jar,candidate_owner))
        except (OriginalOwnerFrontierError,OSError,ValueError,
                KeyError,IndexError,TypeError) as exc:
            raise FullOwnerCandidateGateError(
                "R88_OWNER_DECLARATION_INVENTORY_UNVERIFIABLE") from exc
        need(frontier["original_fields"]==expected_fields and
             frontier["candidate_fields"]==expected_fields and
             frontier["missing_original_fields"]==0 and
             frontier["extra_candidate_fields"]==0 and
             frontier["shared_field_declaration_mismatches"]==0,
             "R88_ORIGINAL_FIELD_METADATA_NOT_EXACT")
        need(all(frontier[k] for k in (
             "original_candidate_major_equal",
             "original_candidate_super_equal",
             "original_candidate_class_access_equal",
             "original_candidate_class_signature_equal",
             "original_candidate_interface_list_equal")),
             "R88_OWNER_CLASS_HEADER_NOT_EXACT")
        need(_digest(Path(original_jar))==original_sha256.lower()
             and _digest(candidate_jar)==candidate_sha,
             "PINNED_ORIGINAL_OR_CANDIDATE_JAR_CHANGED")
        report={
            "schema_version":1,
            "kind":"private_original_v309_two_method_and_initializer_owner_gate",
            "original_complete_jar_sha256":original_sha256.lower(),
            "candidate_compiled_jar_sha256":candidate_sha,
            "research_only":True,
            "loader_jvm_instructions":dual["loader_original_jvm_instructions"],
            "saver_jvm_instructions":dual["saver_original_jvm_instructions"],
            "original_initializer_instructions":
                clinit["original_initializer_instructions"],
            "original_initializer_static_writes":
                clinit["original_owner_static_writes_in_order"],
            "original_field_declarations":frontier["original_fields"],
            "candidate_field_declarations":frontier["candidate_fields"],
            "original_field_declaration_differences":0,
            "both_R87_methods_passed":True,
            "R58_initializer_operand_semantics_passed":True,
            "R88_original_owner_field_metadata_passed":True,
            "original_unrecovered_method_declarations":
                frontier["missing_original_methods"],
            "original_unrecovered_nested_class_entries":
                frontier["missing_original_nested_classes"],
            "all_original_method_implementations_proven":False,
            "original_nested_enum_and_helper_behavior_proven":False,
            "original_file_config_and_runtime_behavior_proven":False,
            "whole_original_client_runtime_equivalence_certified":False,
        }
        stage=tmp/"stage"
        stage.mkdir()
        shutil.copyfile(candidate_jar,stage/"candidate.private.jar")
        with (stage/"owner-triple-gate.aggregate.json").open(
                "x",encoding="utf-8",newline="\n") as f:
            json.dump(report,f,sort_keys=True,indent=2)
            f.write("\n")
        need(not output.exists() and not output.is_symlink(),
             "OUTPUT_OCCUPIED_DURING_CHECKS")
        os.rename(stage,output)
        return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for a in (
        "original_jar","original_owner_class","original_loader",
        "original_saver","private_java_source_root",
        "candidate_owner_class","candidate_loader","candidate_saver",
        "loader_aliases","saver_aliases","clinit_aliases",
        "new_private_output",
    ):p.add_argument(a)
    p.add_argument("--original-sha256",required=True)
    p.add_argument("--javac",default="javac")
    p.add_argument("--compile-classpath",type=Path)
    a=p.parse_args(argv)
    try:
        result=accept_original_v309_owner_methods_and_initializer(
            a.original_jar,a.original_owner_class,
            a.original_loader,a.original_saver,a.private_java_source_root,
            a.candidate_owner_class,a.candidate_loader,a.candidate_saver,
            a.loader_aliases,a.saver_aliases,a.clinit_aliases,
            a.new_private_output,original_sha256=a.original_sha256,
            javac=a.javac,compile_classpath=a.compile_classpath)
        print(json.dumps(result,sort_keys=True))
    except FullOwnerCandidateGateError as exc:
        p.error(str(exc))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
