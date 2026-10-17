"""R196: read-only full Java source dependency frontier, no invented libraries.

Inputs are private source ZIPs. Output is aggregate package/class-reference evidence;
it does not use, execute, or publish original client binaries or source code.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import PurePosixPath, Path
import re
import zipfile

JDK_PREFIXES = ("java.", "javax.swing.", "javax.crypto.", "javax.imageio.",
                "javax.sound.", "javax.xml.", "javax.naming.", "javax.net.",
                "javax.security.", "javax.management.", "org.w3c.dom.",
                "org.xml.sax.", "com.sun.net.httpserver.")
IMPORT = re.compile(r"(?m)^\s*import\s+(static\s+)?([\w.*]+)\s*;")
PACKAGE = re.compile(r"(?m)^\s*package\s+([\w.]+)\s*;")

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def analyze(archive: Path, prefix: str = "src/") -> dict:
    packages: dict[str, set[str]] = defaultdict(set)
    sources = []
    with zipfile.ZipFile(archive) as z:
        names = [n for n in z.namelist() if n.startswith(prefix) and n.endswith(".java")]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate Java ZIP entries")
        if not names:
            raise ValueError("No Java source files")
        for name in sorted(names):
            relative = name[len(prefix):]
            parts = PurePosixPath(relative).parts
            if "\\" in relative or not parts or ".." in parts:
                raise ValueError("Unsafe source name")
            body = z.read(name).decode("utf-8-sig")
            package_match = PACKAGE.search(body)
            declared = package_match.group(1) if package_match else ""
            class_name = PurePosixPath(relative).stem
            packages[declared].add(class_name)
            sources.append((relative, declared, body))
    missing = Counter()
    affected = defaultdict(set)
    qualified = Counter()
    external_examples = defaultdict(set)
    ambiguous = Counter()
    for filename, source_package, body in sources:
        for match in IMPORT.finditer(body):
            symbol = match.group(2)
            is_static = bool(match.group(1))
            if symbol.startswith(JDK_PREFIXES):
                continue
            if symbol.startswith("javax.") or symbol.startswith("sun.") or symbol.startswith("jdk."):
                ambiguous["unclassified_platform_namespace"] += 1
                continue
            pieces = symbol.split(".")
            # Static imports add a field or method suffix. Wildcard imports
            # can cover a package or nested members. Don't claim resolution.
            if is_static or pieces[-1] == "*":
                ambiguous["static_or_wildcard_import"] += 1
                continue
            owner_package = ".".join(pieces[:-1])
            owner_class = pieces[-1]
            if owner_class in packages.get(owner_package, set()):
                continue
            missing[owner_package] += 1
            affected[owner_package].add(filename)
            qualified[symbol] += 1
            if len(external_examples[owner_package]) < 6:
                external_examples[owner_package].add(symbol)
    rows = [{"package": pkg, "unresolved_direct_imports": count,
             "affected_source_files": len(affected[pkg]),
             "sample_imports": sorted(external_examples[pkg])}
            for pkg, count in missing.items()]
    rows.sort(key=lambda x: (-x["affected_source_files"], -x["unresolved_direct_imports"], x["package"]))
    return {
        "schema": "spk.source-import-frontier.r196.v1",
        "archive_sha256": digest(archive.read_bytes()),
        "source_count": len(sources),
        "unresolved_direct_import_count": sum(missing.values()),
        "affected_source_count": len(set.union(set(), *affected.values())),
        "unresolved_packages": rows,
        "ambiguous_imports": dict(sorted(ambiguous.items())),
        "interpretation": [
            "Import-level evidence only; Java wildcard/static imports are not conclusively resolved",
            "Nested classes, source-derived symbols, and JDK module providers may be misclassified",
            "Missing import does not prove absent dependency or broken source",
            "No source or classfile bytecode equivalence established",
        ],
    }

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip", required=True, type=Path)
    p.add_argument("--prefix", default="src/")
    p.add_argument("--report", required=True, type=Path)
    a = p.parse_args()
    result = analyze(a.source_zip, a.prefix)
    with a.report.open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2, sort_keys=True)
        file.write("\n")

if __name__ == "__main__":
    main()
