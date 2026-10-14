"""R164 standalone private source acceptance and overlay."""
import argparse
from pathlib import Path
import json
from .private_v309_original_vector_source_r164 import (
    verify_original_vector_java, private_vector_source_overlay)
from .private_client_source_ast_census_r126 import sha_file


def main(argv=None):
    p=argparse.ArgumentParser()
    for name in ("original_jar","vector_java_zip","baseline_source_zip",
                 "new_source_zip","new_report"):
        p.add_argument(name)
    p.add_argument("--source-sha256",required=True)
    p.add_argument("--baseline-sha256",required=True)
    args=p.parse_args(argv)
    report=Path(args.new_report)
    if report.exists() or not report.parent.is_dir():
        p.error("R164_REPORT_DESTINATION_NOT_FRESH")
    proof=verify_original_vector_java(
        args.original_jar,args.vector_java_zip,
        vector_source_sha256=args.source_sha256)
    tree=private_vector_source_overlay(
        args.baseline_source_zip,args.vector_java_zip,args.new_source_zip,
        baseline_sha256=args.baseline_sha256,
        vector_source_sha256=args.source_sha256,
        expected_original_files=1272)
    report.write_text(json.dumps(
        {"recovered_vector":proof,"source_tree":tree,
         "client_full_compile_accepted":False},
        indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("R164_PRIVATE_VECTOR_SOURCE_TREE_OVERLAY_VERIFIED")
    print("private_report_sha256="+sha_file(report))


if __name__=="__main__":
    main()
