"""R87: one Java9 compilation, original v309 load AND save parity.

Research-only. R86 compiles and validates loader using R66/R81; R87 checks
the saver against that SAME candidate and only then publishes private output.
All helper/runtime/complete-owner source identity claims remain false.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
from .clinit_store_order_witness import _verified_class
from .mutable_scalar_initializer_source import _digest
from .private_java9_compile_acceptance import (
    PrivateJava9AcceptanceError, _input_sources, compile_and_accept_private_java9,
)
from .whole_method_operand_parity import WholeMethodOperandError, compare_all_method_operands

class DualMethodAcceptanceError(ValueError):
    pass

def need(ok, code):
    if not ok:
        raise DualMethodAcceptanceError(code)

def aliases_at(path):
    path = Path(path)
    need(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1048576,
         "SAVER_ALIAS_FILE_MISSING_OR_UNSAFE")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DualMethodAcceptanceError("SAVER_ALIAS_JSON_UNREADABLE") from exc
    need(isinstance(value, dict) and value.get("schema_version") == 1
         and isinstance(value.get("aliases"), list)
         and isinstance(value.get("read_only_field_aliases", []), list)
         and isinstance(value.get("method_aliases", []), list),
         "SAVER_ALIAS_SCHEMA_INVALID")
    return value

def accept_dual_method_java9(
    original_jar, original_entry, loader_name, loader_desc,
    saver_name, saver_desc, source_root, candidate_entry,
    candidate_loader, candidate_loader_desc, candidate_saver,
    candidate_saver_desc, loader_alias_file, saver_alias_file,
    output, *, original_sha256, javac="javac", compile_classpath=None,
    required_counts=(697, 364),
):
    original_jar, source_root, output = map(Path, (original_jar, source_root, output))
    need(not output.exists() and not output.is_symlink(),
         "OUTPUT_ALREADY_EXISTS")
    need(output.parent.is_dir() and not output.parent.is_symlink(),
         "OUTPUT_PARENT_UNAVAILABLE")
    need((loader_name, loader_desc) != (saver_name, saver_desc)
         and (candidate_loader, candidate_loader_desc)
             != (candidate_saver, candidate_saver_desc),
         "ORIGINAL_AND_CANDIDATE_METHODS_MUST_BE_DISTINCT")
    need(type(required_counts) is tuple and len(required_counts) == 2
         and all(type(x) is int and x > 0 for x in required_counts),
         "REQUIRED_INSTRUCTION_COUNTS_INVALID")
    saver_aliases = aliases_at(saver_alias_file)
    source_sha = _input_sources(source_root)[1]
    with tempfile.TemporaryDirectory(prefix="v309-dual-", dir=output.parent) as td:
        tmp = Path(td)
        try:
            loader = compile_and_accept_private_java9(
                original_jar, original_entry, loader_name, loader_desc,
                source_root, candidate_entry, candidate_loader,
                candidate_loader_desc, Path(loader_alias_file),
                tmp / "loader", original_sha256=original_sha256,
                javac=javac, compile_classpath=compile_classpath)
        except (PrivateJava9AcceptanceError, ValueError, OSError) as exc:
            raise DualMethodAcceptanceError("LOADER_R86_R66_R81_REJECTED") from exc
        need(loader["original_instructions_with_all_semantic_operands_compared"]
             == required_counts[0], "LOADER_ORIGINAL_697_INSTRUCTION_COUNT_MISMATCH")
        candidate_jar = tmp / "loader" / "candidate.private.jar"
        candidate_sha = loader["candidate_compiled_jar_sha256"]
        try:
            original = _verified_class(original_jar, original_entry, original_sha256)
            candidate = _verified_class(candidate_jar, candidate_entry, candidate_sha)
            saver = compare_all_method_operands(
                original, saver_name, saver_desc,
                candidate, candidate_saver, candidate_saver_desc,
                saver_aliases["aliases"],
                saver_aliases.get("read_only_field_aliases", []),
                saver_aliases.get("method_aliases", []))
        except (WholeMethodOperandError, ValueError, OSError,
                KeyError, IndexError, TypeError) as exc:
            raise DualMethodAcceptanceError("SAVER_R66_R81_REJECTED") from exc
        need(saver["original_instructions_with_all_semantic_operands_compared"]
             == required_counts[1], "SAVER_ORIGINAL_364_INSTRUCTION_COUNT_MISMATCH")
        need(_input_sources(source_root)[1] == source_sha,
             "SOURCE_TREE_CHANGED_DURING_COMPILE")
        need(_digest(original_jar) == original_sha256.lower()
             and _digest(candidate_jar) == candidate_sha,
             "ORIGINAL_OR_CANDIDATE_BINARY_CHANGED")
        report = {
            "schema_version": 1, "kind": "private_v309_dual_java9_method_acceptance",
            "research_only": True,
            "original_complete_jar_sha256": original_sha256.lower(),
            "compiled_candidate_jar_sha256": candidate_sha,
            "private_source_tree_sha256": source_sha,
            "java_release": 9,
            "loader_original_jvm_instructions": required_counts[0],
            "saver_original_jvm_instructions": required_counts[1],
            "loader_ordered_typed_handlers":
                loader["original_ordered_typed_exception_entries"],
            "saver_ordered_typed_handlers":
                saver["original_ordered_typed_exception_entries"],
            "loader_explicit_branches": loader["original_explicit_branches"],
            "saver_explicit_branches": saver["original_explicit_branches"],
            "both_R66_R81_method_parity_gates_pass": True,
            "same_private_candidate_binary_checked_for_both": True,
            "complete_owner_static_initializer_proven": False,
            "external_helpers_and_nested_enum_bodies_proven": False,
            "original_configuration_filesystem_side_effects_proven": False,
            "whole_client_runtime_equivalence_certified": False,
        }
        stage = tmp / "stage"
        stage.mkdir()
        shutil.copyfile(candidate_jar, stage / "candidate.private.jar")
        with (stage / "dual-method.aggregate.json").open(
                "x", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, indent=2, sort_keys=True)
            f.write("\n")
        need(not output.exists() and not output.is_symlink(),
             "OUTPUT_OCCUPIED_DURING_GATES")
        os.rename(stage, output)
        return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for arg in (
        "original_jar", "original_owner", "original_loader", "original_loader_desc",
        "original_saver", "original_saver_desc", "source_root", "candidate_owner",
        "candidate_loader", "candidate_loader_desc", "candidate_saver",
        "candidate_saver_desc", "loader_aliases", "saver_aliases", "new_output"):
        p.add_argument(arg)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--javac", default="javac")
    p.add_argument("--compile-classpath", type=Path)
    a=p.parse_args(argv)
    try:
        proof=accept_dual_method_java9(
            a.original_jar,a.original_owner,a.original_loader,
            a.original_loader_desc,a.original_saver,a.original_saver_desc,
            a.source_root,a.candidate_owner,a.candidate_loader,
            a.candidate_loader_desc,a.candidate_saver,a.candidate_saver_desc,
            a.loader_aliases,a.saver_aliases,a.new_output,
            original_sha256=a.original_sha256,javac=a.javac,
            compile_classpath=a.compile_classpath)
        print(json.dumps(proof,sort_keys=True))
    except DualMethodAcceptanceError as e:
        p.error(str(e))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
