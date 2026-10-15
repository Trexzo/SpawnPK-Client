"""R182 private source/dependency manifest builder, without code execution.

Manifest contents are private, potentially including source paths. Nothing here
certifies original-v309 source parity, licensing, or safe runtime behavior.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import zipfile
from pathlib import Path, PurePosixPath

SHA = re.compile(r"^[0-9a-fA-F]{64}$")
FORBIDDEN_PROJECT_PREFIXES = ("rs/", "com/jagex/")

def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def inventory_source(root: Path) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Source root must be a directory")
    entries = []
    casefold = {}
    for path in sorted(root.rglob("*.java")):
        if path.is_symlink():
            raise ValueError(f"Symlink source prohibited: {path}")
        rel = path.relative_to(root).as_posix()
        folded = rel.casefold()
        casefold.setdefault(folded, []).append(rel)
        entries.append({"path": rel, "sha256": digest_bytes(path.read_bytes())})
    if not entries:
        raise ValueError("Empty Java source inventory")
    collisions = [names for names in casefold.values() if len(names) > 1]
    if collisions:
        raise ValueError("Windows casefold source collision: " + repr(collisions[:4]))
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {"file_count": len(entries), "files": entries,
            "source_scope_sha256": digest_bytes(encoded)}

def inspect_dependencies(paths: list[Path], approved: dict) -> dict:
    results = []
    for path in paths:
        if path.suffix.lower() not in (".jar", ".zip"):
            raise ValueError("Expected JAR or ZIP dependency")
        if path.is_symlink() or not path.is_file():
            raise ValueError("Untrusted dependency path")
        actual = digest_bytes(path.read_bytes())
        if not SHA.fullmatch(approved.get(path.name, "")) or approved[path.name].lower() != actual:
            raise ValueError("Unapproved dependency SHA: " + path.name)
        try:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)):
                    raise ValueError("Duplicate ZIP dependency members")
                normalized = []
                for name in names:
                    norm = PurePosixPath(name)
                    if name.startswith("/") or "\\" in name or ".." in norm.parts:
                        raise ValueError("Unsafe dependency archive entry")
                    normalized.append(name.casefold())
                    if name.endswith(".class") and (
                        name.startswith(FORBIDDEN_PROJECT_PREFIXES) or
                        (name.startswith("META-INF/versions/") and
                         "/rs/" in name)
                    ):
                        raise ValueError("Forbidden original/project class in dependency")
                if len(normalized) != len(set(normalized)):
                    raise ValueError("Casefold dependency member collision")
        except zipfile.BadZipFile as exc:
            raise ValueError("Invalid dependency archive") from exc
        results.append({"name": path.name, "sha256": actual})
    results.sort(key=lambda x: (x["name"].casefold(), x["name"]))
    if len({x["name"].casefold() for x in results}) != len(results):
        raise ValueError("Duplicate dependency basenames")
    return {"dependencies": results, "dependency_manifest_sha256":
            digest_bytes(json.dumps(results, sort_keys=True, separators=(",", ":")).encode())}

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--deps", nargs="*", type=Path, default=[])
    p.add_argument("--approved-deps-json", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    approved = json.loads(a.approved_deps_json.read_text(encoding="utf-8"))
    if not isinstance(approved, dict):
        raise ValueError("Approved dependency SHA mapping must be an object")
    report = {"schema": "spk.source-manifest.r182.v1",
              **inventory_source(a.source_root), **inspect_dependencies(a.deps, approved)}
    with a.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")

if __name__ == "__main__":
    main()
