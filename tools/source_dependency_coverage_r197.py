"""Private-only direct-import versus approved-JAR class coverage (R197).

Uses existing SHA-pinned JAR validator. Reports import-level evidence only;
no original code or binary is copied to a public location.
"""
from __future__ import annotations
import argparse
import json
import zipfile
from pathlib import Path
from dependency_closure_r197 import inspect
from source_import_frontier_r196 import analyze

def compare(source_zip: Path, jars: list[Path], approvals: dict, prefix="src/") -> dict:
    source = analyze(source_zip, prefix)
    verified = inspect(jars, approvals)
    classes = set()
    for jar in jars:
        with zipfile.ZipFile(jar) as archive:
            classes.update(n[:-6].replace("/", ".") for n in archive.namelist()
                           if n.endswith(".class"))
    groups = []
    for entry in source["unresolved_packages"]:
        examples = entry["sample_imports"]
        hits = [symbol for symbol in examples if symbol in classes]
        groups.append({
            "package": entry["package"],
            "affected_source_files": entry["affected_source_files"],
            "unresolved_direct_imports": entry["unresolved_direct_imports"],
            "sampled_import_matches": len(hits),
            "sampled_import_total": len(examples),
            "complete_package_coverage_proven": False,
        })
    return {
        "schema": "spk.source-archive-sample-coverage.r197.v1",
        "source_archive_sha256": source["archive_sha256"],
        "verified_dependencies": verified["verified_archives"],
        "sampled_groups": groups,
        "limits": [
            "Source analyzer only samples imports per package",
            "Coverage is not complete Java linkage, ABI, or compilation proof",
            "No binary resolution for static and wildcard imports",
        ],
    }

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip", type=Path, required=True)
    p.add_argument("--source-prefix", default="src/")
    p.add_argument("--jar", type=Path, action="append", default=[])
    p.add_argument("--approval-json", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    approvals = json.loads(args.approval_json.read_text(encoding="utf-8"))
    result = compare(args.source_zip, args.jar, approvals, args.source_prefix)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(result, file, sort_keys=True, indent=2)
        file.write("\n")

if __name__ == "__main__":
    main()
