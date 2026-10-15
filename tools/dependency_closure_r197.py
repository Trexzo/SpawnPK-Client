"""R197: verify exact dependency archives and enumerate supplied binary classes.

Never downloads dependencies or runs archive code. Aggregate output does not
contain original source or class bytes. Approval hashes are mandatory.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import zipfile

def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()

def inspect(jars: list[Path], approved: dict[str, str]) -> dict:
    if not isinstance(approved, dict):
        raise ValueError("Expected approval map")
    results, owners = [], defaultdict(list)
    for archive in jars:
        if archive.is_symlink() or not archive.is_file() or archive.suffix.lower() != ".jar":
            raise ValueError("Dependency must be a regular JAR file")
        expected = approved.get(archive.name)
        if not isinstance(expected, str) or not re.fullmatch("[a-fA-F0-9]{64}", expected):
            raise ValueError("Dependency not SHA approved: " + archive.name)
        data = archive.read_bytes()
        actual = digest(data)
        if actual.lower() != expected.lower():
            raise ValueError("Dependency SHA mismatch: " + archive.name)
        classes, member_names = set(), set()
        with zipfile.ZipFile(archive) as zip_file:
            for item in zip_file.infolist():
                name = item.filename
                if name in member_names or "\\" in name or name.startswith("/") or ".." in name.split("/"):
                    raise ValueError("Duplicate or unsafe ZIP entry")
                member_names.add(name)
                if name.endswith(".class"):
                    if item.file_size > 5_000_000:
                        raise ValueError("Oversized classfile")
                    if name.startswith("rs/") or name.startswith("META-INF/versions/") and "/rs/" in name:
                        raise ValueError("Detected original client namespace in dependency JAR")
                    classes.add(name[:-6].replace("/", "."))
        for symbol in classes:
            owners[symbol].append(archive.name)
        results.append({"archive": archive.name, "sha256": actual, "class_count": len(classes)})
    collisions = {name: sorted(paths) for name, paths in owners.items() if len(paths) > 1}
    return {"schema": "spk.verified-dependency-closure.r197.v1",
            "verified_archives": sorted(results, key=lambda x:x["archive"]),
            "duplicate_binary_classes": collisions,
            "unique_binary_classes": len(owners),
            "limits": ["Direct approved archives only; transitive dependencies not authenticated",
                       "Class availability does not establish linkage/runtime/API correctness",
                       "Relocated original client binaries cannot be excluded solely by namespace"]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jar", type=Path, action="append", default=[])
    parser.add_argument("--approval-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    approvals = json.loads(args.approval_json.read_text(encoding="utf-8"))
    result = inspect(args.jar, approvals)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2, sort_keys=True)
        file.write("\n")

if __name__ == "__main__":
    main()
