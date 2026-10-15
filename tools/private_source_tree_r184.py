"""Private Java source-tree assembler for v309 recovery.

Combines a full private decompiled-source ZIP with a reviewed recovery overlay.
Writes no original-derived code to GitHub, and never uses original client binaries.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_sources(archive: Path, prefix: str) -> dict[str, bytes]:
    if not archive.is_file():
        raise ValueError("Missing archive")
    out: dict[str, bytes] = {}
    folded: set[str] = set()
    with zipfile.ZipFile(archive) as z:
        seen = set()
        for member in z.infolist():
            name = member.filename
            if name in seen: raise ValueError("Duplicate archive member")
            seen.add(name)
            if not name.startswith(prefix) or not name.endswith(".java"):
                continue
            rel = name[len(prefix):]
            parts = PurePosixPath(rel).parts
            if not parts or any(x in ("", ".", "..") for x in parts) or "\\" in rel:
                raise ValueError("Unsafe Java source path")
            if rel.casefold() in folded:
                raise ValueError("Windows-casefold Java source collision")
            folded.add(rel.casefold())
            if member.file_size > 4 * 1024 * 1024:
                raise ValueError("Oversized source file")
            out[rel] = z.read(member)
    if not out: raise ValueError("No Java files")
    return dict(sorted(out.items()))

def assemble(baseline: dict[str, bytes], overlay: dict[str, bytes],
             approvals: dict[str, dict]) -> tuple[dict[str, bytes], list[dict]]:
    merged = dict(baseline)
    modifications = []
    for path, content in sorted(overlay.items()):
        gate = approvals.get(path)
        if not isinstance(gate, dict):
            raise ValueError("Missing reviewed approval for " + path)
        if path in baseline:
            old = sha(baseline[path])
            if gate.get("baseline_sha256") != old:
                raise ValueError("Stale or incorrect original source witness: " + path)
        else:
            if gate.get("baseline_sha256") is not None:
                raise ValueError("Expected new source but specified baseline: " + path)
            old = None
        if gate.get("replacement_sha256") != sha(content):
            raise ValueError("Stale replacement source witness: " + path)
        if gate.get("status") != "reviewed-private-recovery":
            raise ValueError("Unreviewed overlay status: " + path)
        merged[path] = content
        modifications.append({"path": path, "baseline_sha256": old,
                              "replacement_sha256": sha(content)})
    all_casefold = [p.casefold() for p in merged]
    if len(all_casefold) != len(set(all_casefold)):
        raise ValueError("Merged Java paths clash on Windows")
    return merged, modifications

def write_private_tree(dest: Path, sources: dict[str, bytes],
                       modifications: list[dict]) -> dict:
    if dest.exists(): raise FileExistsError("Refusing existing destination")
    dest.mkdir(parents=True)
    try:
        for rel, content in sources.items():
            path = dest / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        index = [{"path": p, "sha256": sha(x)} for p, x in sources.items()]
        manifest = {
            "schema": "spk.v309.private-source-tree.r184.v1",
            "java_count": len(index),
            "overlay_count": len(modifications),
            "tree_sha256": sha(json.dumps(index, sort_keys=True, separators=(",", ":")).encode()),
            "files": index, "reviewed_overlays": modifications,
            "full_original_binary_parity": False,
            "source_only_full_build_verified": False
        }
        (dest / "PRIVATE_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise

def classify_javac_text(text: str) -> dict:
    counts: dict[str, int] = {}
    owners: dict[str, int] = {}
    sample = []
    line_re = re.compile(r"^(.+\.java):(\d+): error: (.+)$")
    for raw in text.splitlines():
        m = line_re.match(raw)
        if not m: continue
        file, _, reason = m.groups()
        counts[reason] = counts.get(reason, 0) + 1
        owner = PurePosixPath(file.replace("\\", "/")).name
        owners[owner] = owners.get(owner, 0) + 1
        if len(sample) < 30:
            sample.append({"file_name": owner, "reason": reason})
    return {"reported_error_occurrences": sum(counts.values()),
            "by_reason": dict(sorted(counts.items(), key=lambda p: (-p[1], p[0]))),
            "top_file_names": sorted(owners.items(), key=lambda p: (-p[1], p[0]))[:50],
            "sample": sample, "root_cause_verified": False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline-zip", type=Path, required=True)
    p.add_argument("--baseline-prefix", required=True)
    p.add_argument("--overlay-zip", type=Path)
    p.add_argument("--overlay-prefix", default="src/")
    p.add_argument("--approvals", type=Path)
    p.add_argument("--private-output", type=Path, required=True)
    args = p.parse_args()
    baseline = read_sources(args.baseline_zip, args.baseline_prefix)
    overlay, approvals = {}, {}
    if bool(args.overlay_zip) != bool(args.approvals):
        p.error("Overlay and approvals must be provided together")
    if args.overlay_zip:
        overlay = read_sources(args.overlay_zip, args.overlay_prefix)
        approvals = json.loads(args.approvals.read_text(encoding="utf-8"))
    merged, modifications = assemble(baseline, overlay, approvals)
    info = write_private_tree(args.private_output, merged, modifications)
    print(json.dumps({"sources": info["java_count"],
                      "reviewed_overlays": info["overlay_count"],
                      "private_tree_sha256": info["tree_sha256"]}, sort_keys=True))

if __name__ == "__main__":
    main()
