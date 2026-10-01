from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .classfile import parse_class
from .indexer import index_jar, sha256_bytes
from .matcher import match_classes


EXACT_V308_SHA256 = (
    "854f26ff9f134b0317572e7ac1688e6f"
    "40a231d5a4c66f8db5d655b7f45ce7c6"
)
DEFAULT_EXTERNAL_REPOSITORY = "i-iz-adam/SpawnPk-Open-Inject"


class ExternalCorpusProbeError(ValueError):
    pass


_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_GENERIC_CLASS_RE = re.compile(r"^(?:Class\d+|[A-Za-z])$")


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _require_revision(value: str) -> str:
    value = str(value).lower()
    if _HEX40_RE.fullmatch(value) is None:
        raise ExternalCorpusProbeError(
            "external revision must be lowercase 40-hex"
        )
    return value


def _require_sha256(value: str, label: str) -> str:
    value = str(value).lower()
    if _HEX64_RE.fullmatch(value) is None:
        raise ExternalCorpusProbeError(
            f"{label} must be lowercase 64-hex"
        )
    return value


def _class_record(parsed: Any) -> dict[str, Any]:
    return {
        "internal_name": parsed.name,
        "major": parsed.major,
        "minor": parsed.minor,
        "access": parsed.access,
        "super_name": parsed.super_name,
        "interfaces": parsed.interfaces,
        "field_count": len(parsed.fields),
        "method_count": len(parsed.methods),
        "fields": parsed.fields,
        "methods": parsed.methods,
        "attributes": parsed.attributes,
        "inner_outer_name": parsed.inner_outer_name,
        "inner_simple_name": parsed.inner_simple_name,
        "enclosing_class_name": parsed.enclosing_class_name,
        "literal_strings": parsed.literal_strings,
        "numeric_constants": parsed.numeric_constants,
        "structural_sha256": parsed.structural_sha256(),
    }


def _directory_digest(rows: list[tuple[str, bytes]]) -> str:
    h = hashlib.sha256()
    for relative, data in rows:
        encoded = relative.encode("utf-8")
        h.update(len(encoded).to_bytes(4, "big"))
        h.update(encoded)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def index_class_directory(path: Path) -> dict[str, Any]:
    root = path.resolve()
    if not root.is_dir():
        raise ExternalCorpusProbeError(
            f"external class directory does not exist: {root}"
        )

    files = sorted(
        (
            candidate
            for candidate in root.rglob("*.class")
            if candidate.is_file()
        ),
        key=lambda candidate: candidate.relative_to(root).as_posix(),
    )
    if not files:
        raise ExternalCorpusProbeError(
            f"external class directory contains no .class files: {root}"
        )

    rows: list[tuple[str, bytes]] = []
    entries: dict[str, dict[str, Any]] = {}
    classes: dict[str, dict[str, Any]] = {}
    parse_errors: dict[str, str] = {}
    casefold_paths: dict[str, list[str]] = {}

    for candidate in files:
        relative = candidate.relative_to(root).as_posix()
        if relative.startswith("../") or relative.startswith("/"):
            raise ExternalCorpusProbeError(
                f"external class path escapes root: {candidate}"
            )
        casefold_paths.setdefault(relative.casefold(), []).append(relative)
        data = candidate.read_bytes()
        rows.append((relative, data))
        entries[relative] = {
            "sha256": sha256_bytes(data),
            "size": len(data),
        }
        try:
            classes[relative] = _class_record(parse_class(data))
        except Exception as exc:
            parse_errors[relative] = (
                f"{type(exc).__name__}: {exc}"
            )

    collisions = sorted(
        sorted(paths)
        for paths in casefold_paths.values()
        if len(paths) > 1
    )
    if collisions:
        formatted = "; ".join(
            ",".join(paths)
            for paths in collisions
        )
        raise ExternalCorpusProbeError(
            "external class directory contains case-fold collisions: "
            + formatted
        )

    rs_classes = sorted(
        path
        for path in classes
        if path.startswith("rs/")
    )
    return {
        "schema_version": 1,
        "kind": "external_class_directory_index",
        "source_name": root.name,
        "sha256": _directory_digest(rows),
        "size_bytes": sum(len(data) for _, data in rows),
        "entries": entries,
        "classes": classes,
        "summary": {
            "entry_count": len(entries),
            "class_count": len(classes),
            "rs_class_count": len(rs_classes),
            "class_parse_error_count": len(parse_errors),
            "class_parse_errors": parse_errors,
            "class_major_versions": sorted(
                {
                    int(classes[path]["major"])
                    for path in classes
                }
            ),
        },
    }


def index_external_classes(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved.is_dir():
        return index_class_directory(resolved)
    if resolved.is_file():
        try:
            result = index_jar(resolved)
        except Exception as exc:
            raise ExternalCorpusProbeError(
                f"external class archive could not be indexed: {exc}"
            ) from exc
        result = copy.deepcopy(result)
        result["kind"] = "external_class_archive_index"
        return result
    raise ExternalCorpusProbeError(
        f"external classes input does not exist: {resolved}"
    )


def _scope_count(
    index: dict[str, Any],
    scope_prefix: str,
) -> int:
    return sum(
        1
        for path in index.get("classes", {})
        if path.startswith(scope_prefix)
    )


def _validate_scoped_internal_names(
    index: dict[str, Any],
    *,
    label: str,
    scope_prefix: str,
) -> None:
    for path, row in sorted(
        index.get("classes", {}).items()
    ):
        if not path.startswith(scope_prefix):
            continue
        expected = path[:-6] if path.endswith(".class") else path
        actual = str(row.get("internal_name", ""))
        if actual != expected:
            raise ExternalCorpusProbeError(
                f"{label} class path/internal-name mismatch: "
                f"{path} != {actual!r}"
            )


def _readable_name(path: str) -> str:
    internal = path[:-6] if path.endswith(".class") else path
    return internal.rsplit("/", 1)[-1]


def _candidate_row(
    match: dict[str, Any],
) -> dict[str, Any]:
    external_path = str(match["old"])
    exact_path = str(match["new"])
    readable_name = _readable_name(external_path)
    strategy = str(match["strategy"])
    return {
        "external_path": external_path,
        "external_readable_name": readable_name,
        "external_name_is_descriptive": (
            _GENERIC_CLASS_RE.fullmatch(readable_name) is None
        ),
        "exact_v308_path": exact_path,
        "strategy": strategy,
        "score": match["score"],
        "confidence": match["confidence"],
        "evidence": copy.deepcopy(match["evidence"]),
        "candidate_only": True,
        "promoted": False,
        "strength": (
            "structural"
            if strategy in {"exact_sha256", "structural_unique"}
            else "inferred"
        ),
    }


def build_external_corpus_probe(
    *,
    external_index: dict[str, Any],
    exact_index: dict[str, Any],
    external_revision: str,
    expected_exact_sha256: str = EXACT_V308_SHA256,
    external_repository: str = DEFAULT_EXTERNAL_REPOSITORY,
    scope_prefix: str = "rs/",
) -> dict[str, Any]:
    external_revision = _require_revision(external_revision)
    expected_exact_sha256 = _require_sha256(
        expected_exact_sha256,
        "expected exact v308 SHA-256",
    )
    if not external_repository.strip():
        raise ExternalCorpusProbeError(
            "external repository must be non-empty"
        )
    if not isinstance(scope_prefix, str) or not scope_prefix:
        raise ExternalCorpusProbeError(
            "scope prefix must be non-empty"
        )

    exact_sha256 = _require_sha256(
        str(exact_index.get("sha256", "")),
        "exact index SHA-256",
    )
    if exact_sha256 != expected_exact_sha256:
        raise ExternalCorpusProbeError(
            "exact index does not match pinned v308 authority"
        )

    for label, index in (
        ("external", external_index),
        ("exact", exact_index),
    ):
        summary = index.get("summary", {})
        parse_errors = int(
            summary.get("class_parse_error_count", 0)
        )
        if parse_errors != 0:
            raise ExternalCorpusProbeError(
                f"{label} index contains class parse errors: "
                f"{parse_errors}"
            )
        scoped = _scope_count(index, scope_prefix)
        if scoped == 0:
            raise ExternalCorpusProbeError(
                f"{label} index contains no classes under "
                f"{scope_prefix!r}"
            )
        _validate_scoped_internal_names(
            index,
            label=label,
            scope_prefix=scope_prefix,
        )

    match_report = match_classes(
        external_index,
        exact_index,
        prefix=scope_prefix,
    )
    candidates = [
        _candidate_row(match)
        for match in match_report.get("matches", [])
    ]

    exact_targets = [
        row["exact_v308_path"]
        for row in candidates
    ]
    if len(exact_targets) != len(set(exact_targets)):
        raise ExternalCorpusProbeError(
            "matcher produced duplicate exact-v308 targets"
        )

    structural = [
        row
        for row in candidates
        if row["strength"] == "structural"
    ]
    inferred = [
        row
        for row in candidates
        if row["strength"] == "inferred"
    ]
    descriptive = [
        row
        for row in candidates
        if row["external_name_is_descriptive"]
    ]

    external_sha256 = _require_sha256(
        str(external_index.get("sha256", "")),
        "external corpus SHA-256",
    )
    corpus_material = {
        "repository": external_repository,
        "revision": external_revision,
        "corpus_sha256": external_sha256,
        "scope_prefix": scope_prefix,
        "scoped_class_count": _scope_count(
            external_index,
            scope_prefix,
        ),
    }
    corpus_id = (
        "EXTCORPUS_"
        + hashlib.sha256(
            _stable_json(corpus_material)
        ).hexdigest()[:20].upper()
    )

    probe_material = {
        "corpus_id": corpus_id,
        "exact_v308_sha256": exact_sha256,
        "scope_prefix": scope_prefix,
        "match_summary": match_report["summary"],
        "candidates": [
            {
                "external_path": row["external_path"],
                "exact_v308_path": row["exact_v308_path"],
                "strategy": row["strategy"],
                "score": row["score"],
            }
            for row in candidates
        ],
    }
    probe_id = (
        "EXTCORPUSPROBE_"
        + hashlib.sha256(
            _stable_json(probe_material)
        ).hexdigest()[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "external_class_corpus_probe",
        "probe_id": probe_id,
        "corpus_id": corpus_id,
        "authority": {
            "exact_build": "v308",
            "exact_v308_sha256": exact_sha256,
            "scope_prefix": scope_prefix,
        },
        "external_corpus": {
            **corpus_material,
            "source_kind": external_index.get(
                "kind",
                "jar_index",
            ),
            "class_count": int(
                external_index.get(
                    "summary",
                    {},
                ).get("class_count", 0)
            ),
            "rs_class_count": int(
                external_index.get(
                    "summary",
                    {},
                ).get("rs_class_count", 0)
            ),
        },
        "policy": {
            "research_only": True,
            "promotes_names": False,
            "copies_external_source": False,
            "changes_source_m1_authority": False,
            "requires_separate_semantic_review": True,
        },
        "summary": {
            "external_scoped_classes": _scope_count(
                external_index,
                scope_prefix,
            ),
            "exact_scoped_classes": _scope_count(
                exact_index,
                scope_prefix,
            ),
            "matched": len(candidates),
            "structural_matches": len(structural),
            "inferred_matches": len(inferred),
            "descriptive_name_candidates": len(
                descriptive
            ),
            "ambiguous": len(
                match_report.get("ambiguous", [])
            ),
            "unmatched_external": len(
                match_report.get(
                    "unmatched_old",
                    [],
                )
            ),
            "unmatched_exact_v308": len(
                match_report.get(
                    "unmatched_new",
                    [],
                )
            ),
        },
        "match_summary": copy.deepcopy(
            match_report["summary"]
        ),
        "candidates": candidates,
        "ambiguous": copy.deepcopy(
            match_report.get("ambiguous", [])
        ),
        "unmatched_external": copy.deepcopy(
            match_report.get("unmatched_old", [])
        ),
        "unmatched_exact_v308": copy.deepcopy(
            match_report.get("unmatched_new", [])
        ),
        "note": (
            "External readable names and repaired bytecode are "
            "research evidence only. This report never promotes "
            "semantic names, never copies external source into the "
            "recovered tree, and never changes exact-v308 authority."
        ),
    }


def run_external_corpus_probe(
    *,
    external_classes: Path,
    exact_v308_jar: Path,
    external_revision: str,
    expected_exact_sha256: str = EXACT_V308_SHA256,
    external_repository: str = DEFAULT_EXTERNAL_REPOSITORY,
    scope_prefix: str = "rs/",
) -> dict[str, Any]:
    exact_v308_jar = exact_v308_jar.resolve()
    if not exact_v308_jar.is_file():
        raise ExternalCorpusProbeError(
            f"exact v308 JAR does not exist: {exact_v308_jar}"
        )
    external_index = index_external_classes(
        external_classes
    )
    exact_index = index_jar(exact_v308_jar)
    return build_external_corpus_probe(
        external_index=external_index,
        exact_index=exact_index,
        external_revision=external_revision,
        expected_exact_sha256=expected_exact_sha256,
        external_repository=external_repository,
        scope_prefix=scope_prefix,
    )
