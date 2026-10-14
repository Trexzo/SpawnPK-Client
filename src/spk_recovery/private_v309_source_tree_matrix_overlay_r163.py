"""R163: overlay a verified original-linked Java class into PRIVATE v309 source tree.

Replays R162 exact original class source proof before any overlay. Copies all
existing candidate client Java files verbatim, then adds ONE recovered game-
linked original Java class under recovered-source/v309/src. Compiler-only
Packet/math scaffolds are NOT included in canonical recovered source.
Private ZIP and report only; never publish original-derived client Java.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file, source_members
from .private_v309_complete_matrix_java_r162 import (
    verify_complete_original_matrix_java,
    MATRIX_SHA,
)


class PrivateSourceOverlayR163Error(ValueError):
    pass


def require(ok,reason):
    if not ok:
        raise PrivateSourceOverlayR163Error(reason)


def make_private_matrix_source_overlay(
        original_jar, decompiled_client_zip, recovered_matrix_zip,
        compile_only_helper_java_zip, original_methods_json,
        fresh_private_source_zip, *, original_sha256=CANONICAL_V309,
        decompiled_source_sha256, recovered_matrix_sha256,
        helper_source_sha256, methods_sha256,
        matrix_owner="com/a/b/a/b", packet_owner="rs/x/e",
        matrix_class_sha256=MATRIX_SHA,
        expected_original_java=1271, expected_methods=24,
        expected_instructions=3780, expected_helpers=5,
        expected_self_calls=12):
    inputs=[(original_jar,original_sha256),
            (decompiled_client_zip,decompiled_source_sha256),
            (recovered_matrix_zip,recovered_matrix_sha256),
            (compile_only_helper_java_zip,helper_source_sha256),
            (original_methods_json,methods_sha256)]
    require(all(sha_file(p)==digest for p,digest in inputs),
            "R163_ALL_ORIGINAL_SOURCE_HASHES_MUST_MATCH")
    output=Path(fresh_private_source_zip)
    require(not output.exists() and not output.is_symlink()
            and output.parent.is_dir() and not output.parent.is_symlink(),
            "R163_OUTPUT_MUST_BE_FRESH_PRIVATE_ZIP")
    proof=verify_complete_original_matrix_java(
        original_jar,recovered_matrix_zip,compile_only_helper_java_zip,
        original_methods_json,
        original_sha256=original_sha256,
        matrix_source_sha256=recovered_matrix_sha256,
        helper_source_sha256=helper_source_sha256,
        selection_sha256=methods_sha256,
        matrix_owner=matrix_owner,packet_owner=packet_owner,
        expected_matrix_sha256=matrix_class_sha256,
        expected_members=expected_methods,
        expected_instructions=expected_instructions,
        expected_helper_classes=expected_helpers,
        expected_self_calls=expected_self_calls)
    require(proof["all_original_matrix_method_ids_present"]
            and proof["original_matrix_field_abi_exact"]
            and proof["isolated_source_only_java_compilation_passed"]
            and proof["original_recompiled_jvm_instruction_count"]==
                expected_instructions
            and proof["packet_and_external_helper_bodies_proven_original"] is False,
            "R163_SOURCE_OVERLAY_REQUIRES_EXACT_R162_ORIGINAL_PROOF")
    baseline=source_members(decompiled_client_zip,decompiled_source_sha256)
    matrix=source_members(recovered_matrix_zip,recovered_matrix_sha256)
    require(len(baseline)==expected_original_java
            and len(matrix)==1 and matrix[0][0]==matrix_owner+".java",
            "R163_ONLY_ONE_NEW_RECOVERED_JAVA_OWNER_ALLOWED")
    paths=[p for p,_ in baseline]
    require(len(paths)==len(set(p.casefold() for p in paths))
            and matrix[0][0].casefold() not in
                {p.casefold() for p in paths},
            "R163_PROTECT_ORIGINAL_JAVA_SOURCE_FROM_OVERWRITE")
    # A compiler scaffold may be needed for source javac, but never becomes
    # a canonical recovered Java source without its own provenance proof.
    scaffolds=source_members(compile_only_helper_java_zip,
                            helper_source_sha256)
    names={p.casefold() for p,_ in scaffolds}
    require(not any(p.casefold() in names for p,_ in [*baseline,*matrix]),
            "R163_COMPILER_SCAFFOLD_CONFLICTS_WITH_CANONICAL_SOURCE")
    target="recovered-source/v309/src/"
    with ZipFile(output,"w",ZIP_DEFLATED,compresslevel=6) as archive:
        for relative,source in sorted([*baseline,*matrix]):
            require(relative.endswith(".java")
                    and "\\" not in relative and ".." not in relative.split("/"),
                    "R163_INVALID_JAVA_RELATIVE_SOURCE_PATH")
            archive.writestr(target+relative,source)
    with ZipFile(output) as archive:
        written=archive.namelist()
        require(len(written)==expected_original_java+1
                and len(written)==len(set(n.casefold() for n in written))
                and target+matrix[0][0] in written
                and not any(target+p in written for p,_ in scaffolds),
                "R163_CANONICAL_CLIENT_SOURCE_TREE_NOT_VERIFIED")
        for relative,source in baseline:
            require(archive.read(target+relative)==source,
                    "R163_ORIGINAL_CLIENT_JAVA_SOURCE_CHANGED")
        require(archive.read(target+matrix[0][0])==matrix[0][1],
                "R163_RECOVERED_MATRIX_JAVA_OWNER_CHANGED")
    require(all(sha_file(p)==digest for p,digest in inputs),
            "R163_INPUT_CHANGED_DURING_RECOVERY_OVERLAY")
    return {
        "schema_version":1,
        "kind":"v309_private_source_tree_one_matrix_owner_overlay_r163",
        "original_client_sha256":original_sha256,
        "original_decompiled_source_zip_sha256":decompiled_source_sha256,
        "private_recovered_matrix_java_zip_sha256":recovered_matrix_sha256,
        "private_source_only_helper_zip_sha256":helper_source_sha256,
        "r162_all_original_method_selection_sha256":methods_sha256,
        "original_java_sources_preserved_exact":expected_original_java,
        "one_proven_original_matrix_java_file_added":True,
        "private_canonical_client_java_file_count":expected_original_java+1,
        "private_canonical_source_tree_zip_sha256":sha_file(output),
        "all_original_matrix_method_instructions_verified":
            expected_instructions,
        "original_matrix_field_and_method_abi_verified":True,
        "compiler_only_scaffolds_in_canonical_source_tree":False,
        "compiler_only_packet_and_helper_bodies_proven_original":False,
        "whole_v309_client_javac_compilation_accepted":False,
        "original_derived_source_publication_authorized":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("original_jar","candidate_client_zip","matrix_java_zip",
                 "helper_source_zip","selection_json",
                 "fresh_private_canonical_zip","fresh_private_report"):
        p.add_argument(name)
    for name in ("source-sha256","matrix-sha256",
                 "helpers-sha256","selection-sha256"):
        p.add_argument("--"+name,required=True)
    args=p.parse_args(argv)
    report=Path(args.fresh_private_report)
    try:
        require(not report.exists() and not report.is_symlink()
                and report.parent.is_dir() and not report.parent.is_symlink(),
                "R163_SANITIZED_PRIVATE_REPORT_MUST_BE_FRESH")
        proof=make_private_matrix_source_overlay(
            args.original_jar,args.candidate_client_zip,
            args.matrix_java_zip,args.helper_source_zip,args.selection_json,
            args.fresh_private_canonical_zip,
            decompiled_source_sha256=args.source_sha256,
            recovered_matrix_sha256=args.matrix_sha256,
            helper_source_sha256=args.helpers_sha256,
            methods_sha256=args.selection_sha256)
        report.write_text(json.dumps(proof,indent=2,sort_keys=True)+"\n",
                          encoding="utf-8")
        print("R163_PRIVATE_RECOVERED_CLIENT_JAVA_TREE_SOURCE_OVERLAY_CREATED")
        print("private_report_sha256="+sha_file(report))
    except Exception:
        p.error("R163_CANONICAL_JAVA_SOURCE_OVERLAY_NOT_ACCEPTED")


if __name__=="__main__":
    main()
