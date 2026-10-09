from __future__ import annotations

"""Public-safe external source intake: NEVER a class identity acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile


class SourceIntakeError(ValueError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(z: ZipFile) -> list[str]:
    names = []
    for item in z.infolist():
        parts = item.filename.split("/")
        if (item.filename.startswith("/") or chr(92) in item.filename
            or any(x in ("", ".", "..") for x in parts[:-1])
            or item.flag_bits & 1 or item.file_size > 100000000
            or (item.external_attr >> 16) & 0o170000 == 0o120000):
            raise SourceIntakeError("unsafe original archive")
        names.append(item.filename)
    if not names or len(set(names)) != len(names):
        raise SourceIntakeError("empty/duplicate archive")
    return names


def measure(source: Path, original: Path, oldsha: str, newsha: str,
            expected_classes: int = 10502) -> dict:
    if any(not re.fullmatch(r"[0-9a-f]{64}", sha) for sha in (oldsha, newsha)):
        raise SourceIntakeError("invalid exact SHA256")
    if digest(source) != oldsha or digest(original) != newsha:
        raise SourceIntakeError("exact input SHA256 drift")
    with ZipFile(source) as src, ZipFile(original) as jar:
        names = inventory(src)
        classes = {s for s in inventory(jar) if s.endswith(".class")}
        roots = {p.split("/")[0] for p in names if "/" in p}
        if len(roots) != 1 or len(classes) != expected_classes:
            raise SourceIntakeError("class inventory/source root drift")
        root = next(iter(roots)) + "/"
        prefix = root + "src/main/java/"
        java = [p[len(prefix):] for p in names
                if p.startswith(prefix) and p.endswith(".java")]
        if not java:
            raise SourceIntakeError("missing Java files")
        conf = prefix + "rs/Configuration.java"
        if conf not in names or re.findall(
            r"\bbuildNumber\s*=\s*(\d+)\s*;", src.read(conf).decode("utf-8")
        ) != ["309"]:
            raise SourceIntakeError("candidate source build mismatch")
        docs = root + "docs/LOOT_TRACKER_COMPARISON.md"
        evidence = re.findall(
            r"^\|\s*"+chr(96)+r"(rs\.s\.l\.[a-z])"+chr(96)+r"\s*\|",
            src.read(docs).decode("utf-8"), re.M,
        ) if docs in names else []
        if len(evidence) != len(set(evidence)):
            raise SourceIntakeError("ambiguous source mapping evidence")
        summary = {
            "java_source_files": len(java),
            "rs_java_source_files": sum(p.startswith("rs/") for p in java),
            "resource_files": sum(p.startswith(root+"src/main/resources/")
                                  and not p.endswith("/") for p in names),
            "original_class_entries": len(classes),
            "direct_class_path_overlap_not_identity_proof": sum(
                p[:-5]+".class" in classes for p in java),
            "documented_raw_class_candidates_not_accepted": len(evidence),
            "documented_original_paths_found": sum(
                p.replace(".", "/")+".class" in classes for p in evidence),
            "clean_rebuild_verified": False,
            "original_class_set_verified": False,
            "new_accepted_class_identities": 0,
        }
    if digest(source) != oldsha or digest(original) != newsha:
        raise SourceIntakeError("input mutated during scan")
    core = {
        "schema_version": 1,
        "kind": "external_v309_source_corpus_intake_research",
        "canonical": False,
        "state": "SOURCE_CANDIDATE_ONLY_NO_BUILD_OR_MAPPING_ACCEPTANCE",
        "source_zip_sha256": oldsha,
        "client_jar_sha256": newsha,
        "summary": summary,
    }
    content = json.dumps(core, sort_keys=True, separators=(",", ":"))
    return {"report_id": "SPKEXTSRC_"+hashlib.sha256(content.encode()).hexdigest()[:20].upper(), **core}


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-zip", required=True, type=Path)
    p.add_argument("--original-jar", required=True, type=Path)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args(argv)
    try:
        if a.out.exists() or a.out.is_symlink() or a.out.resolve() in (
            a.source_zip.resolve(), a.original_jar.resolve()
        ):
            raise SourceIntakeError("unsafe output")
        report = measure(a.source_zip, a.original_jar,
                         a.source_sha256, a.original_sha256)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("x", encoding="utf-8") as f:
            f.write(json.dumps(report, indent=2, sort_keys=True)+"\n")
    except Exception as error:
        print("SPK_EXTERNAL_SOURCE_INTAKE_FAIL_CLOSED")
        print("category="+type(error).__name__)
        return 1
    print("SPK_EXTERNAL_SOURCE_INTAKE_PASS_RESEARCH_ONLY")
    print("report_id="+report["report_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
