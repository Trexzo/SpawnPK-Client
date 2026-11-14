#!/usr/bin/env python3
"""Offline, read-only classpath closure audit. No client launch or network actions.

This file is public-safe. It accepts local private JARs, but never uploads bytes.
Constant-pool Class references and a BFS are conservative approximations, NOT a
Java linker, proof of executability, or proof that a method is reachable.
"""
from __future__ import annotations
import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import struct
import zipfile

PLATFORM_ROOTS = ("java/", "javax/", "sun/", "jdk/", "com/sun/", "org/w3c/", "org/xml/", "com/apple/")

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def constant_class_refs(data: bytes) -> set[str]:
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("not a classfile")
    count = int.from_bytes(data[8:10], "big")
    if count < 1 or count > 65535:
        raise ValueError("invalid constant pool")
    off = 10
    utf8: dict[int, str] = {}
    class_indices: list[int] = []
    i = 1
    while i < count:
        if off >= len(data):
            raise ValueError("truncated constant pool")
        tag = data[off]
        off += 1
        if tag == 1:
            if off + 2 > len(data):
                raise ValueError("truncated UTF8 size")
            size = int.from_bytes(data[off:off+2], "big")
            off += 2
            if off + size > len(data):
                raise ValueError("truncated UTF8 value")
            utf8[i] = data[off:off+size].decode("utf-8", "replace")
            off += size
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            off += 4
        elif tag in (5, 6):
            off += 8
            i += 1
        elif tag in (7, 8, 16, 19, 20):
            if off + 2 > len(data):
                raise ValueError("truncated index")
            index = int.from_bytes(data[off:off+2], "big")
            off += 2
            if tag == 7:
                class_indices.append(index)
        elif tag == 15:
            off += 3
        else:
            raise ValueError(f"invalid constant-pool tag {tag}")
        if off > len(data):
            raise ValueError("truncated constant pool")
        i += 1
    result = set()
    for idx in class_indices:
        name = utf8.get(idx)
        if not name:
            raise ValueError("unresolved class name index")
        while name.startswith("["):
            name = name[1:]
        if not name or len(name) == 1:
            continue
        if name.startswith("L") and name.endswith(";"):
            name = name[1:-1]
        if "." in name or ";" in name or name.startswith("/"):
            raise ValueError("invalid class path")
        result.add(name + ".class")
    return result

def load_classes(path: Path, expected: str | None = None) -> dict[str, bytes]:
    data = path.read_bytes()
    if expected and sha256(data) != expected.lower():
        raise ValueError(f"SHA256_MISMATCH {path.name}")
    entries = {}
    with zipfile.ZipFile(path) as jar:
        for item in jar.infolist():
            name = item.filename
            if name in entries:
                raise ValueError(f"DUPLICATE_CLASS {name}")
            if name.endswith(".class"):
                if name.startswith("/") or "\\" in name or ".." in name.split("/"):
                    raise ValueError("UNSAFE_CLASS_PATH")
                entries[name] = jar.read(item)
    return entries

def closure(refs: dict[str, set[str]], entry: str) -> tuple[set[str], dict[str, set[str]]]:
    seen = set()
    missing: dict[str, set[str]] = {}
    queue = deque([entry])
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        for target in refs.get(current, ()):
            if target in refs:
                if target not in seen:
                    queue.append(target)
            elif not target.startswith(PLATFORM_ROOTS):
                missing.setdefault(target, set()).add(current)
    return seen, missing

def audit(candidate: dict[str, bytes], primary: dict[str, bytes], alternate: dict[str, bytes], entry: str) -> dict:
    collision = set(candidate) & set(primary)
    common = set(primary) & set(alternate)
    differing = sorted(name for name in common if sha256(primary[name]) != sha256(alternate[name]))
    runtime = {**primary, **candidate}
    graph = {name: constant_class_refs(data) for name, data in runtime.items()}
    candidate_missing = sorted({ref for name in candidate for ref in graph[name]
                               if ref not in runtime and not ref.startswith(PLATFORM_ROOTS)})
    all_missing = {target for values in graph.values() for target in values
                   if target not in runtime and not target.startswith(PLATFORM_ROOTS)}
    visited, reached_missing = closure(graph, entry)
    return {
        "entrypoint": entry,
        "entry_present": entry in runtime,
        "candidate_classes": len(candidate),
        "primary_classes": len(primary),
        "alternate_classes": len(alternate),
        "candidate_primary_collisions": len(collision),
        "common_dependency_class_paths": len(common),
        "dependency_common_byte_differences": len(differing),
        "primary_only_paths": sorted(set(primary) - set(alternate)),
        "alternate_only_paths": sorted(set(alternate) - set(primary)),
        "static_candidate_missing_nonplatform": candidate_missing,
        "static_all_runtime_missing_nonplatform": sorted(all_missing),
        "constant_pool_reachable_classes": len(visited),
        "constant_pool_reachable_missing_nonplatform": sorted(reached_missing),
        "advisory_only": True,
        "warning": "Static constant-pool approximation; NOT runtime/GUI/login, power-loss, or original-binary equivalence."
    }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--primary", type=Path, required=True)
    p.add_argument("--alternate", type=Path, required=True)
    p.add_argument("--entry", default="rs/gui/Launcher.class")
    p.add_argument("--expect-candidate-sha256")
    p.add_argument("--expect-primary-sha256")
    p.add_argument("--expect-alternate-sha256")
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    report = audit(load_classes(a.candidate, a.expect_candidate_sha256),
                   load_classes(a.primary, a.expect_primary_sha256),
                   load_classes(a.alternate, a.expect_alternate_sha256), a.entry)
    rendered = json.dumps(report, indent=2) + "\n"
    if a.out:
        if a.out.exists():
            raise ValueError("REFUSE_TO_OVERWRITE_REPORT")
        a.out.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
