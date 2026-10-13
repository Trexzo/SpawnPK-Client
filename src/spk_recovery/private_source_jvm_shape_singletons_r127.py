"""R127: conservative source AST ↔ original JVM class-shape singleton proposals.

No original/source Java binaries are executed, compiled or copied. Matching
coarse shapes is NOT class identity, semantic equivalence or deobfuscation
acceptance. The full class identity graph still requires bytecode proof.
"""
from __future__ import annotations

from collections import defaultdict
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import (
    CANONICAL_V309, original_class_inventory,
)
from .private_client_source_ast_census_r126 import (
    source_members, sha_file,
)


class PrivateSourceShapeR127Error(ValueError):
    pass


def need(value, message):
    if not value:
        raise PrivateSourceShapeR127Error(message)


def _decode(s):
    return base64.urlsafe_b64decode(
        s + "=" * (-len(s) % 4)).decode("utf-8")


def _descriptor(desc):
    return re.sub(r"L[^;]+;", "L;", desc)


def _class_kind(access):
    if access & 0x2000:
        return "ANNOTATION_TYPE"
    if access & 0x4000:
        return "ENUM"
    if access & 0x0200:
        return "INTERFACE"
    return "CLASS"


def _profile_original_class(parsed):
    fields = [
        ("S:" if (f["access"] & 0x0008) else "I:")
        + _descriptor(f["descriptor"])
        for f in parsed.fields if not (f["access"] & 0x1000)
    ]
    methods = [
        ("S:" if (m["access"] & 0x0008) else "I:")
        + _descriptor(m["descriptor"])
        for m in parsed.methods
        if m["name"] != "<clinit>"
        and not (m["access"] & (0x1000 | 0x0040))
    ]
    return (_class_kind(parsed.access), tuple(sorted(fields)),
            tuple(sorted(methods)))


def _profile_source_row(row):
    name, kind, fields, methods = row
    return (kind, tuple(sorted(fields)), tuple(sorted(methods)))


def _fingerprint(profile):
    return hashlib.sha256(
        json.dumps(profile, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def conservative_singletons(source, original):
    """Pure, review-only matching: only unique top-level shapes on both sides."""
    def eligible(name, shape):
        return (type(name) is str and name.startswith("rs/")
                and "$" not in name.rsplit("/", 1)[-1]
                and shape[0] in ("CLASS", "INTERFACE"))

    left = defaultdict(list)
    right = defaultdict(list)
    for name, shape in source.items():
        if eligible(name, shape):
            left[_fingerprint(shape)].append(name)
    for name, shape in original.items():
        if eligible(name, shape):
            right[_fingerprint(shape)].append(name)
    common = sorted(set(left) & set(right))
    proposals = []
    unresolved_collisions = 0
    for shape in common:
        if len(left[shape]) == 1 and len(right[shape]) == 1:
            proposals.append({
                "source_java_type": left[shape][0],
                "original_jvm_class": right[shape][0],
                "shape_sha256": shape,
            })
        else:
            unresolved_collisions += 1
    return {
        "source_eligible_top_level_types": sum(map(len, left.values())),
        "original_eligible_top_level_classes": sum(map(len, right.values())),
        "shared_structural_shape_buckets": len(common),
        "ambiguous_shared_shape_buckets": unresolved_collisions,
        "unique_undecided_shape_proposals": len(proposals),
        "proposals": sorted(proposals,
                            key=lambda r: (r["source_java_type"],
                                           r["original_jvm_class"])),
    }


def _parse_source_shapes(entries, scratch):
    javac, java = shutil.which("javac"), shutil.which("java")
    need(javac is not None and java is not None, "JDK_REQUIRED")
    source_root = scratch / "input"
    compiled = scratch / "trusted-scanner"
    source_root.mkdir()
    compiled.mkdir()
    helper = (Path(__file__).resolve().parent / "java" /
              "ClientAstStructuralShapesR127.java")
    need(helper.is_file(), "R127_JAVA_HELPER_NOT_PACKAGED")
    for rel, data in entries:
        target = source_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    jobs = [
        [javac, "-encoding", "UTF-8", "-d", str(compiled), str(helper)],
        [java, "-cp", str(compiled),
         "ClientAstStructuralShapesR127", str(source_root)]
    ]
    raw = b""
    for job in jobs:
        try:
            result = subprocess.run(job, cwd=scratch, capture_output=True,
                                    stdin=subprocess.DEVNULL, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PrivateSourceShapeR127Error(
                "AST_SOURCE_SCAN_DID_NOT_COMPLETE") from exc
        need(result.returncode == 0,
             "AST_SOURCE_SCAN_OR_JAVA_PARSE_FAILED")
        raw = result.stdout
    need(len(raw) <= 8_000_000, "AST_SOURCE_SHAPE_OUTPUT_TOO_LARGE")
    rows = {}
    for line in raw.decode("utf-8").splitlines():
        parts = line.split("\t")
        need(len(parts) == 4, "AST_SHAPE_PROTOCOL_INVALID")
        name = _decode(parts[0])
        kind = parts[1]
        need(name and kind in ("CLASS", "INTERFACE", "ANNOTATION_TYPE",
                              "ENUM", "RECORD"),
             "AST_SHAPE_KIND_OR_NAME_INVALID")
        fields = _decode(parts[2]).split("|") if parts[2] else []
        methods = _decode(parts[3]).split("|") if parts[3] else []
        need(name not in rows, "AST_SHAPE_DUPLICATE_DECLARED_TYPE")
        rows[name] = (kind, tuple(sorted(fields)),
                      tuple(sorted(methods)))
    return rows


def source_vs_original_shape_research(source_zip, original_jar, *,
                                      source_sha256,
                                      original_sha256=CANONICAL_V309,
                                      include_identifiers=False):
    entries = source_members(source_zip, source_sha256)
    names = original_class_inventory(original_jar, original_sha256)
    with tempfile.TemporaryDirectory(prefix="spk-r127-ast-private-") as td:
        source_shapes = _parse_source_shapes(entries, Path(td))
    jvm_shapes = {}
    with ZipFile(original_jar) as jar:
        for name in sorted(names):
            if not name.startswith("rs/"):
                continue
            try:
                parsed = parse_class(jar.read(name + ".class"))
            except Exception as exc:
                raise PrivateSourceShapeR127Error(
                    "PRIVATE_ORIGINAL_RS_CLASSFILE_PARSE_FAILED") from exc
            need(parsed.name == name, "ORIGINAL_CLASS_ENTRY_NAME_INVALID")
            jvm_shapes[name] = _profile_original_class(parsed)
    result = conservative_singletons(source_shapes, jvm_shapes)
    aggregate = {
        "schema_version": 1,
        "kind": "private_v309_java_ast_jvm_structural_singleton_proposals_r127",
        "source_zip_sha256": source_sha256,
        "original_v309_jar_sha256": original_sha256,
        "source_ast_named_declarations": len(source_shapes),
        "original_rs_jvm_classfiles": len(jvm_shapes),
        **{k: v for k, v in result.items() if k != "proposals"},
        "candidate_proposals_are_identity_accepted": False,
        "unique_shape_proposals_need_independent_bytecode_proof": True,
        "whole_client_deobfuscation_complete": False,
        "source_files_rewritten_or_built": False,
        "runtime_equivalence_proven": False,
        "private_class_names_included": bool(include_identifiers),
    }
    rows = result["proposals"]
    material = json.dumps(rows, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    aggregate["private_proposal_manifest_sha256"] = (
        hashlib.sha256(material).hexdigest())
    if include_identifiers:
        aggregate["private_review_only_proposals"] = rows
    return aggregate


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_decompiled_source_zip")
    p.add_argument("private_original_v309_jar")
    p.add_argument("fresh_private_report")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--original-sha256", default=CANONICAL_V309)
    p.add_argument("--private-identifiers", action="store_true")
    a = p.parse_args(argv)
    output = Path(a.fresh_private_report)
    try:
        need(not output.exists() and not output.is_symlink()
             and output.parent.is_dir() and not output.parent.is_symlink(),
             "FRESH_PRIVATE_REPORT_REQUIRED")
        report = source_vs_original_shape_research(
            a.private_decompiled_source_zip, a.private_original_v309_jar,
            source_sha256=a.source_sha256,
            original_sha256=a.original_sha256,
            include_identifiers=a.private_identifiers)
        output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        print("R127_PRIVATE_AST_JVM_SHAPE_PROPOSALS_COMPLETE")
        print("private_report_sha256=" + sha_file(output))
    except Exception:
        p.error("PRIVATE_R127_AST_JVM_SHAPE_GATE_NOT_ACCEPTED")


if __name__ == "__main__":
    main()
