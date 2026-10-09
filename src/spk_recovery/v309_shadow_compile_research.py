from __future__ import annotations

"""Research-only Java package/class collision resolution; no mapping acceptance.

All shadow owner paths are derived from exact source imports and SHA-pinned
original bytecode. No private obfuscated identifiers are embedded or exported.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile

from .v309_external_compile_capsule import (
    EXACT_V309_SHA256,
    SOURCE_ARCHIVE_SHA256,
    _safe_names,
    _zip_write_stable,
)
from .v309_external_source_corpus_intake import digest as sha256_file


class V309ShadowResearchError(ValueError):
    pass


EXPECTED_PARENT_CAPSULE_SHA256 = (
    "f847f941077b715307f61f1602aee89c8981be2675b3ffd5747cd019d8fd9ce2"
)
EXPECTED_PARENT_REPORT_ID = "SPKDEPCAPSULE_D90FA6691284459A8DDD"


def _package_shadow_imports(imports: list[str], class_entries: set[str]) -> Counter:
    """A type import is shadowed when one of its package segments is a class.

    Java can resolve an intermediate component as a type rather than a package
    in an obfuscated binary namespace. Require the *full imported type* to be
    present in the exact capsule; never infer from a string alone.
    """
    shadows: Counter = Counter()
    for dotted in imports:
        segments = dotted.split(".")
        if dotted.replace(".", "/") + ".class" not in class_entries:
            continue
        for length in range(1, len(segments)):
            prefix = "/".join(segments[:length]) + ".class"
            if prefix in class_entries:
                shadows[prefix] += 1
    return shadows


def _verify_parent_report(report: dict, original: str, source: str,
                          capsule: str, expected_classes: int) -> None:
    if (
        report.get("kind") != "v309_external_namespace_compile_capsule_research"
        or report.get("canonical") is not False
        or report.get("report_id") != EXPECTED_PARENT_REPORT_ID
        or report.get("original_client_sha256") != original
        or report.get("external_source_archive_sha256") != source
        or report.get("summary", {}).get("exact_compile_capsule_sha256") != capsule
        or report.get("summary", {}).get("external_namespace_candidate_classes") != expected_classes
    ):
        raise V309ShadowResearchError("parent candidate capsule provenance drift")
    core = {key: value for key, value in report.items() if key != "report_id"}
    digest = hashlib.sha256(json.dumps(
        core, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()[:20].upper()
    if report["report_id"] != "SPKDEPCAPSULE_" + digest:
        raise V309ShadowResearchError("parent capsule report identity mismatch")


def build_v309_shadow_compile_research(*,
    parent_capsule: Path, parent_report: Path,
    source_archive: Path, original_jar: Path, out_dir: Path,
    expected_capsule_sha256: str = EXPECTED_PARENT_CAPSULE_SHA256,
    expected_source_sha256: str = SOURCE_ARCHIVE_SHA256,
    expected_original_sha256: str = EXACT_V309_SHA256,
    expected_parent_classes: int = 9333,
    expected_source_java: int = 1270,
    expected_shadow_classes: int = 7,
    expected_shadow_imports: int = 86,
) -> dict:
    protected = (parent_capsule, parent_report, source_archive, original_jar)
    if out_dir.exists() or out_dir.is_symlink():
        raise V309ShadowResearchError("output already exists")
    if out_dir.resolve() in {p.resolve() for p in protected}:
        raise V309ShadowResearchError("output overlaps original input")
    for file, sha in (
        (parent_capsule, expected_capsule_sha256),
        (source_archive, expected_source_sha256),
        (original_jar, expected_original_sha256),
    ):
        if not re.fullmatch("[0-9a-f]{64}", sha) or sha256_file(file) != sha:
            raise V309ShadowResearchError("exact original SHA256 mismatch")
    parent = json.loads(parent_report.read_text(encoding="utf-8"))
    _verify_parent_report(parent, expected_original_sha256,
                          expected_source_sha256, expected_capsule_sha256,
                          expected_parent_classes)
    protected_report_sha = sha256_file(parent_report)

    with ZipFile(parent_capsule) as capsule, ZipFile(source_archive) as source, \
         ZipFile(original_jar) as original:
        classes = _safe_names(capsule)
        source_names = _safe_names(source)
        original_names = set(_safe_names(original))
        if len(classes) != expected_parent_classes or any(
            not p.endswith(".class") for p in classes
        ):
            raise V309ShadowResearchError("parent class count/type drift")
        roots = {p.split("/")[0] for p in source_names if "/" in p}
        if len(roots) != 1:
            raise V309ShadowResearchError("ambiguous source archive root")
        prefix = next(iter(roots)) + "/src/main/java/"
        java_files = [p for p in source_names
                      if p.startswith(prefix) and p.endswith(".java")]
        if len(java_files) != expected_source_java:
            raise V309ShadowResearchError("source coverage drift")
        regex = re.compile(r"(?m)^\s*import\s+([\w.$]+)\s*;")
        imported = []
        for path in java_files:
            try:
                imported.extend(regex.findall(source.read(path).decode("utf-8")))
            except UnicodeDecodeError as exc:
                raise V309ShadowResearchError("non-UTF8 source") from exc
        present = set(classes)
        witnesses = _package_shadow_imports(imported, present)
        suppressed = set(witnesses)
        if (len(suppressed) != expected_shadow_classes
            or sum(witnesses.values()) != expected_shadow_imports
            or any(p not in original_names or capsule.read(p) != original.read(p)
                   for p in suppressed)):
            raise V309ShadowResearchError("unverified collision evidence")
        if any(p.replace(".", "/") + ".class" in suppressed for p in imported):
            raise V309ShadowResearchError("candidate directly imports excluded class")

        out_dir.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".v309-shadow-research-", dir=out_dir.parent))
        try:
            jar_path = stage / "shadow-filtered-compile-candidate.jar"
            with ZipFile(jar_path, "w") as output:
                for path in sorted(classes):
                    if path not in suppressed:
                        _zip_write_stable(output, path, capsule.read(path))
            with ZipFile(jar_path) as output:
                produced = _safe_names(output)
                if (len(produced) != len(classes) - len(suppressed)
                    or any(p in produced for p in suppressed)
                    or any(p.startswith("rs/") for p in produced)):
                    raise V309ShadowResearchError("filtered class-set accounting drift")
            body = {
                "schema_version": 1,
                "kind": "v309_shadow_filtered_compile_only_research",
                "canonical": False,
                "state": "PACKAGE_CLASS_SHADOW_DIAGNOSTIC_ONLY",
                "original_client_sha256": expected_original_sha256,
                "source_archive_sha256": expected_source_sha256,
                "parent_capsule_sha256": expected_capsule_sha256,
                "parent_capsule_report_id": EXPECTED_PARENT_REPORT_ID,
                "parent_report_file_sha256": protected_report_sha,
                "summary": {
                    "preimage_candidate_classes": len(classes),
                    "shadow_class_entries_suppressed": len(suppressed),
                    "shadowing_source_import_occurrences": sum(witnesses.values()),
                    "remaining_compilation_candidate_classes": len(produced),
                    "source_java_files_checked": len(java_files),
                    "verified_shadow_original_class_bytes": len(suppressed),
                    "direct_imports_of_excluded_classes": 0,
                    "filtered_capsule_sha256": sha256_file(jar_path),
                    "complete_external_dependency_ownership_proven": False,
                    "clean_java_source_build_passed": False,
                    "source_or_class_identities_accepted": 0,
                },
                "limits": (
                    "This is only a compile diagnostic. Binary namespace alone cannot "
                    "establish third-party ownership or absence of non-imported "
                    "runtime references. Do not publish or use as a canonical "
                    "dependency capsule or recovered-source release."
                ),
            }
            raw = json.dumps(body, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode("utf-8")
            result = {
                "report_id": "SPKSHADOW7_" + hashlib.sha256(raw).hexdigest()[:20].upper(),
                **body,
            }
            (stage / "SHADOW-FILTER-COMPILE-RESEARCH.json").write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            for path, sha in (
                (parent_capsule, expected_capsule_sha256),
                (source_archive, expected_source_sha256),
                (original_jar, expected_original_sha256),
                (parent_report, protected_report_sha),
            ):
                if sha256_file(path) != sha:
                    raise V309ShadowResearchError("original input changed during research")
            if out_dir.exists() or out_dir.is_symlink():
                raise V309ShadowResearchError("output appeared during research")
            stage.rename(out_dir)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-shadow-compile-research")
    p.add_argument("--parent-capsule", required=True, type=Path)
    p.add_argument("--parent-report", required=True, type=Path)
    p.add_argument("--source-zip", required=True, type=Path)
    p.add_argument("--original-v309", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        report = build_v309_shadow_compile_research(
            parent_capsule=args.parent_capsule,
            parent_report=args.parent_report,
            source_archive=args.source_zip,
            original_jar=args.original_v309,
            out_dir=args.out_dir,
        )
    except Exception as exc:
        print("SPK_V309_SHADOW_COMPILE_FAIL_CLOSED")
        print("error_category=" + type(exc).__name__)
        return 1
    print("SPK_V309_SHADOW_COMPILE_PASS_RESEARCH_ONLY")
    print("report_id=" + report["report_id"])
    print("canonical_changes=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
