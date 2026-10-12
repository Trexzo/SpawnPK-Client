"""R96: one private Java 9 candidate must pass R90, R94 and R95.

Fail closed: no accepted candidate or summary is published when any original
method, initializer, field or nested enum comparison fails. Passing these
bytecode gates does NOT imply executable helper or client runtime equivalence.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

from .mutable_scalar_initializer_source import _digest
from .private_owner_initializer_triple_gate import (
    FullOwnerCandidateGateError,
    accept_original_v309_owner_methods_and_initializer,
)
from .private_all_owner_methods_parity import (
    AllOwnerMethodsParityError,
    replay_all_original_methods,
)
from .private_four_nested_enum_acceptance import (
    FourNestedEnumAcceptanceError,
    replay_private_four_enum_gate,
)


class CompleteOwnerAcceptanceError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise CompleteOwnerAcceptanceError(reason)


def accept_complete_private_v309_owner(
    original_jar, owner_entry, original_loader, original_saver,
    private_java_source_root, candidate_owner_entry, candidate_loader,
    candidate_saver, loader_aliases, saver_aliases, clinit_aliases, output,
    *, original_sha256, javac="javac", compile_classpath=None,
):
    original_jar, output = Path(original_jar), Path(output)
    require(owner_entry == candidate_owner_entry and
            isinstance(owner_entry, str) and owner_entry.endswith(".class"),
            "ORIGINAL_AND_CANDIDATE_OWNER_IDENTITY_MUST_MATCH")
    require(isinstance(original_sha256, str) and len(original_sha256) == 64
            and all(c in "0123456789abcdefABCDEF" for c in original_sha256),
            "ORIGINAL_PIN_NOT_SHA256")
    original_sha256 = original_sha256.lower()
    require(original_jar.is_file() and not original_jar.is_symlink() and
            _digest(original_jar) == original_sha256,
            "ORIGINAL_JAR_PIN_MISMATCH")
    require(not output.exists() and not output.is_symlink() and
            output.parent.is_dir() and not output.parent.is_symlink(),
            "PRIVATE_OUTPUT_PATH_UNAVAILABLE")

    with tempfile.TemporaryDirectory(
        prefix="v309-owner-all-gates-", dir=output.parent,
    ) as work:
        root = Path(work)
        try:
            triple = accept_original_v309_owner_methods_and_initializer(
                original_jar, owner_entry, original_loader, original_saver,
                private_java_source_root, candidate_owner_entry,
                candidate_loader, candidate_saver, loader_aliases,
                saver_aliases, clinit_aliases, root / "r90",
                original_sha256=original_sha256, javac=javac,
                compile_classpath=compile_classpath,
            )
        except (FullOwnerCandidateGateError, OSError, ValueError) as exc:
            raise CompleteOwnerAcceptanceError("R90_OWNER_GATE_FAILED") from exc

        require(triple.get("both_R87_methods_passed") is True and
                triple.get("R58_initializer_operand_semantics_passed") is True and
                triple.get("R88_original_owner_field_metadata_passed") is True and
                triple.get("original_field_declarations") == 126 and
                triple.get("candidate_field_declarations") == 126 and
                triple.get("original_field_declaration_differences") == 0 and
                triple.get("original_initializer_static_writes") == 93 and
                triple.get("original_unrecovered_method_declarations") == 0 and
                triple.get("original_unrecovered_nested_class_entries") == 0,
                "R90_WHOLE_OWNER_DECLARATION_OR_INITIALIZER_INCOMPLETE")
        candidate_jar = root / "r90" / "candidate.private.jar"
        candidate_sha = triple.get("candidate_compiled_jar_sha256")
        require(isinstance(candidate_sha, str) and len(candidate_sha) == 64
                and candidate_jar.is_file() and not candidate_jar.is_symlink()
                and _digest(candidate_jar) == candidate_sha,
                "R90_COMPILED_CANDIDATE_PIN_MISMATCH")

        try:
            methods = replay_all_original_methods(
                original_jar, candidate_jar, owner_entry,
                candidate_owner_entry, root / "r94",
                original_sha256=original_sha256,
                candidate_sha256=candidate_sha,
            )
        except (AllOwnerMethodsParityError, OSError, ValueError) as exc:
            raise CompleteOwnerAcceptanceError("R94_NINE_METHOD_GATE_FAILED") from exc
        require(methods.get("R66_and_R81_parity_passed_all_nine_ordinary_methods")
                is True and methods.get("original_ordinary_methods_parity_checked")
                == 9 and methods.get("original_ordinary_jvm_instruction_operands_compared")
                == 1135,
                "R94_COMPLETE_NINE_METHOD_EVIDENCE_MISSING")

        try:
            enums = replay_private_four_enum_gate(
                original_jar, candidate_jar, owner_entry, root / "r95",
                original_sha256=original_sha256,
                candidate_sha256=candidate_sha,
            )
        except (FourNestedEnumAcceptanceError, OSError, ValueError) as exc:
            raise CompleteOwnerAcceptanceError("R95_FOUR_ENUM_GATE_FAILED") from exc
        require(enums.get("original_nested_enum_classes_verified") == 4 and
                enums.get("symbolic_InnerClasses_tables_identical_all_four") is True
                and enums.get("original_candidate_owner_InnerClasses_tables_identical")
                is True,
                "R95_NESTED_METADATA_NOT_EXACT")

        require(_digest(original_jar) == original_sha256 and
                _digest(candidate_jar) == candidate_sha,
                "PINNED_JAR_CHANGED_DURING_COMBINED_GATE")
        # A private-only deliverable: no originals, identifiers or keys in the report.
        report = {
            "schema_version": 1,
            "kind": "private_v309_one_java9_candidate_all_owner_and_nested_gates",
            "research_only": True,
            "original_complete_jar_sha256": original_sha256,
            "candidate_compiled_jar_sha256": candidate_sha,
            "original_fields_checked": 126,
            "original_initializer_static_writes_checked": 93,
            "original_ordinary_methods_checked": 9,
            "original_ordinary_jvm_operands_checked": 1135,
            "original_nested_enums_checked": 4,
            "R90_owner_initializer_and_fields_passed": True,
            "R94_all_ordinary_methods_passed": True,
            "R95_four_nested_enums_and_InnerClasses_passed": True,
            "original_external_helpers_runtime_proven": False,
            "original_filesystem_and_configuration_side_effects_proven": False,
            "whole_original_client_runtime_equivalence_certified": False,
        }
        stage = root / "stage"
        stage.mkdir()
        shutil.copyfile(candidate_jar, stage / "candidate.private.jar")
        require(_digest(stage / "candidate.private.jar") == candidate_sha,
                "PRIVATE_CANDIDATE_COPY_PIN_MISMATCH")
        with (stage / "all-owner-gates.aggregate.json").open(
            "x", encoding="utf-8", newline="\n",
        ) as f:
            json.dump(report, f, indent=2, sort_keys=True)
            f.write("\n")
        require(not output.exists() and not output.is_symlink(),
                "OUTPUT_OCCUPIED_DURING_FINAL_PROMOTION")
        os.rename(stage, output)
        return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in (
        "original_jar", "owner_class", "original_loader", "original_saver",
        "private_java_source_root", "candidate_owner_class",
        "candidate_loader", "candidate_saver", "loader_aliases",
        "saver_aliases", "clinit_aliases", "new_private_output",
    ):
        parser.add_argument(arg)
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--javac", default="javac")
    parser.add_argument("--compile-classpath", type=Path)
    args = parser.parse_args(argv)
    try:
        result = accept_complete_private_v309_owner(
            args.original_jar, args.owner_class, args.original_loader,
            args.original_saver, args.private_java_source_root,
            args.candidate_owner_class, args.candidate_loader,
            args.candidate_saver, args.loader_aliases, args.saver_aliases,
            args.clinit_aliases, args.new_private_output,
            original_sha256=args.original_sha256, javac=args.javac,
            compile_classpath=args.compile_classpath,
        )
    except CompleteOwnerAcceptanceError as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
