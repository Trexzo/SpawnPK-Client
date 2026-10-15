"""R198: full direct-import coverage against SHA-approved dependency JARs.

Read-only private analysis: no downloading, source publication, class loading,
or original-client binary fallback. Every explicit non-static import is tracked;
unresolved wildcards/static imports are separately marked ambiguous.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
import re
import zipfile
from pathlib import Path

from dependency_closure_r197 import inspect
from source_import_frontier_r196 import IMPORT, PACKAGE, JDK_PREFIXES, digest

def _class_inventory(source_zip: Path, prefix: str) -> tuple[dict, list]:
    declared: set[str] = set()
    source_entries = []
    with zipfile.ZipFile(source_zip) as z:
        names = [x for x in z.namelist() if x.startswith(prefix) and x.endswith(".java")]
        if len(names) != len(set(names)) or not names:
            raise ValueError("Duplicate or absent source files")
        for name in sorted(names):
            rel = name[len(prefix):]
            if rel.startswith("/") or "\\" in rel or ".." in rel.split("/"):
                raise ValueError("Unsafe source path")
            body = z.read(name).decode("utf-8-sig")
            package = PACKAGE.search(body)
            package = package.group(1) if package else ""
            simple = Path(rel).stem
            if simple in ("package-info", "module-info"):
                pass
            else:
                declared.add(package + "." + simple if package else simple)
            source_entries.append((rel, body))
    return declared, source_entries

def analyze_coverage(source_zip: Path, jars: list[Path], approved: dict,
                     prefix: str = "src/") -> dict:
    pins = inspect(jars, approved)
    declared, source_entries = _class_inventory(source_zip, prefix)
    external = set()
    for path in jars:
        with zipfile.ZipFile(path) as jar:
            external.update(n[:-6].replace("/", ".") for n in jar.namelist()
                            if n.endswith(".class"))
    status_counts = Counter()
    by_owner = defaultdict(lambda: Counter())
    by_package = defaultdict(lambda: Counter())
    ambiguous = Counter()
    for rel, body in source_entries:
        for m in IMPORT.finditer(body):
            name = m.group(2)
            static = bool(m.group(1))
            if static or name.endswith(".*"):
                ambiguous["static_or_wildcard"] += 1
                continue
            if name in declared:
                status = "internal_source"
            elif name in external:
                status = "approved_dependency"
            elif name.startswith(JDK_PREFIXES):
                # Namespace prefix alone is not proof; only treat as candidate.
                status = "jdk_namespace_candidate"
            elif name.startswith(("java.", "javax.", "jdk.", "sun.", "com.sun.")):
                status = "platform_unknown"
            else:
                status = "unresolved"
            status_counts[status] += 1
            by_owner[rel][status] += 1
            by_package[name.rpartition(".")[0]][status] += 1
    owner_rows = [{"source_path": key, **dict(sorted(cnt.items()))}
                  for key, cnt in sorted(by_owner.items())
                  if cnt["unresolved"]]
    packages = [{"package": key, **dict(sorted(cnt.items()))}
                for key, cnt in sorted(by_package.items(),
                                       key=lambda item: (-item[1]["unresolved"], item[0]))
                if cnt["unresolved"]]
    return {
        "schema": "spk.direct-import-coverage.r198.v1",
        "private_source_archive_sha256": digest(source_zip.read_bytes()),
        "source_count": len(source_entries),
        "approved_binary_archive_count": len(pins["verified_archives"]),
        "direct_import_counts": dict(sorted(status_counts.items())),
        "ambiguous_imports": dict(sorted(ambiguous.items())),
        "unresolved_by_package": packages,
        "unresolved_by_source": owner_rows,
        "limitations": [
            "Explicit imports only; implicit same-package, nested, static, wildcard and reflection unresolved",
            "JDK namespace is not validated against the selected Java platform modules",
            "Class presence is not Java method/field ABI or transitive dependency proof",
            "Unresolved import is not proof that the Java source is faulty",
        ],
    }

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", required=True, type=Path)
    parser.add_argument("--source-prefix", default="src/")
    parser.add_argument("--jar", action="append", type=Path, default=[])
    parser.add_argument("--approval-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    a = parser.parse_args()
    approvals = json.loads(a.approval_json.read_text(encoding="utf-8"))
    result = analyze_coverage(a.source_zip, a.jar, approvals, a.source_prefix)
    with a.output.open("x", encoding="utf-8") as out:
        json.dump(result, out, indent=2, sort_keys=True)
        out.write("\n")

if __name__ == "__main__":
    main()
