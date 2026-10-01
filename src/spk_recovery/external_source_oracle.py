from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .classfile import parse_class
from .indexer import index_jar, sha256_bytes, sha256_file
from .matcher import match_classes


EXACT_V308_SHA256 = (
    "854f26ff9f134b0317572e7ac1688e6"
    "f40a231d5a4c66f8db5d655b7f45ce7c6"
)
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class ExternalSourceOracleError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _class_record(data: bytes) -> dict[str, Any]:
    c = parse_class(data)
    return {
        "internal_name": c.name,
        "major": c.major,
        "minor": c.minor,
        "access": c.access,
        "super_name": c.super_name,
        "interfaces": c.interfaces,
        "field_count": len(c.fields),
        "method_count": len(c.methods),
        "fields": c.fields,
        "methods": c.methods,
        "attributes": c.attributes,
        "inner_outer_name": c.inner_outer_name,
        "inner_simple_name": c.inner_simple_name,
        "enclosing_class_name": c.enclosing_class_name,
        "literal_strings": c.literal_strings,
        "numeric_constants": c.numeric_constants,
        "structural_sha256": c.structural_sha256(),
    }


def index_class_directory(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise ExternalSourceOracleError(
            f"external class root is not a directory: {root}"
        )

    entries: dict[str, Any] = {}
    classes: dict[str, Any] = {}
    parse_errors: dict[str, str] = {}

    for candidate in sorted(root.rglob("*.class")):
        if candidate.is_symlink():
            raise ExternalSourceOracleError(
                f"external class file may not be a symlink: {candidate}"
            )
        resolved = candidate.resolve()
        if root not in resolved.parents:
            raise ExternalSourceOracleError(
                f"external class path escapes class root: {candidate}"
            )
        if not resolved.is_file():
            continue

        rel = resolved.relative_to(root).as_posix()
        data = resolved.read_bytes()
        entries[rel] = {
            "sha256": sha256_bytes(data),
            "size": len(data),
        }
        try:
            record = _class_record(data)
        except Exception as exc:
            parse_errors[rel] = f"{type(exc).__name__}: {exc}"
            continue

        expected_entry = record["internal_name"] + ".class"
        if rel != expected_entry:
            raise ExternalSourceOracleError(
                "external class path/internal-name mismatch: "
                f"{rel} != {expected_entry}"
            )
        classes[rel] = record

    if parse_errors:
        first = sorted(parse_errors)[0]
        raise ExternalSourceOracleError(
            "external class parse errors are not allowed: "
            f"{first}: {parse_errors[first]}"
        )

    rs_classes = sorted(
        path for path in classes if path.startswith("rs/")
    )
    if not rs_classes:
        raise ExternalSourceOracleError(
            "external class corpus has no rs/** classes"
        )

    digest_material = [
        {
            "path": path,
            "sha256": entries[path]["sha256"],
            "size": entries[path]["size"],
        }
        for path in sorted(entries)
    ]
    directory_sha256 = _stable_digest(digest_material)

    return {
        "schema_version": 1,
        "kind": "external_class_directory_index",
        "source_name": root.name,
        "sha256": directory_sha256,
        "entries": entries,
        "classes": classes,
        "summary": {
            "entry_count": len(entries),
            "class_count": len(classes),
            "rs_class_count": len(rs_classes),
            "class_parse_error_count": 0,
            "class_parse_errors": {},
            "class_major_versions": sorted(
                {classes[path]["major"] for path in classes}
            ),
        },
    }


def build_external_source_oracle(
    *,
    external_classes: Path,
    external_revision: str,
    exact_v308_jar: Path,
    expected_v308_sha256: str = EXACT_V308_SHA256,
) -> dict[str, Any]:
    external_revision = external_revision.strip().lower()
    expected_v308_sha256 = expected_v308_sha256.strip().lower()

    if _COMMIT_RE.fullmatch(external_revision) is None:
        raise ExternalSourceOracleError(
            "external revision must be an exact lowercase 40-hex commit"
        )
    if _HEX64_RE.fullmatch(expected_v308_sha256) is None:
        raise ExternalSourceOracleError(
            "expected exact-v308 SHA-256 must be lowercase 64-hex"
        )

    exact_v308_jar = exact_v308_jar.resolve()
    if not exact_v308_jar.is_file():
        raise ExternalSourceOracleError(
            f"exact v308 JAR is missing: {exact_v308_jar}"
        )
    actual_v308_sha256 = sha256_file(exact_v308_jar)
    if actual_v308_sha256 != expected_v308_sha256:
        raise ExternalSourceOracleError(
            "exact-v308 SHA-256 mismatch: "
            f"expected={expected_v308_sha256} "
            f"actual={actual_v308_sha256}"
        )

    external_index = index_class_directory(external_classes)
    exact_index = index_jar(exact_v308_jar)
    parse_error_count = int(
        exact_index.get("summary", {}).get(
            "class_parse_error_count",
            0,
        )
    )
    if parse_error_count:
        raise ExternalSourceOracleError(
            "exact-v308 JAR contains class parse errors"
        )

    match_report = match_classes(
        external_index,
        exact_index,
        prefix="rs/",
    )

    matches = match_report.get("matches", [])
    exact_targets = [str(row["new"]) for row in matches]
    if len(exact_targets) != len(set(exact_targets)):
        raise ExternalSourceOracleError(
            "duplicate exact-v308 target detected in oracle matches"
        )

    corpus_material = {
        "external_revision": external_revision,
        "external_directory_sha256": external_index["sha256"],
        "external_rs_class_count": external_index["summary"][
            "rs_class_count"
        ],
    }
    corpus_id = (
        "EXTCORPUS_"
        + _stable_digest(corpus_material)[:20].upper()
    )

    candidates = []
    strong_strategies = {
        "exact_sha256",
        "structural_unique",
    }
    for row in matches:
        external_entry = str(row["old"])
        exact_entry = str(row["new"])
        external_class = external_index["classes"][external_entry]
        internal_name = str(external_class["internal_name"])
        simple_name = internal_name.rsplit("/", 1)[-1]
        strategy = str(row["strategy"])
        candidates.append(
            {
                "external_entry": external_entry,
                "external_internal_name": internal_name,
                "external_simple_name": simple_name,
                "exact_v308_entry": exact_entry,
                "strategy": strategy,
                "evidence_tier": (
                    "strong"
                    if strategy in strong_strategies
                    else "inferred"
                ),
                "score": row["score"],
                "confidence": row["confidence"],
                "research_name_candidate": True,
                "semantic_name_accepted": False,
            }
        )

    candidates.sort(
        key=lambda row: (
            row["exact_v308_entry"],
            row["external_entry"],
        )
    )
    strategy_counts = dict(
        sorted(
            match_report.get("summary", {}).items()
        )
    )

    probe_material = {
        "corpus_id": corpus_id,
        "exact_v308_sha256": actual_v308_sha256,
        "scope_prefix": "rs/",
        "matches": [
            {
                "external": row["external_entry"],
                "exact": row["exact_v308_entry"],
                "strategy": row["strategy"],
            }
            for row in candidates
        ],
        "unmatched_external": match_report.get(
            "unmatched_old",
            [],
        ),
        "unmatched_exact": match_report.get(
            "unmatched_new",
            [],
        ),
    }
    probe_id = (
        "EXTORACLE_"
        + _stable_digest(probe_material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "external_readable_v308_structural_oracle",
        "oracle_id": probe_id,
        "corpus_id": corpus_id,
        "research_only": True,
        "source_authority": False,
        "semantic_authority": False,
        "source_mutation_allowed": False,
        "external": {
            "revision": external_revision,
            "directory_sha256": external_index["sha256"],
            "rs_class_count": external_index["summary"][
                "rs_class_count"
            ],
        },
        "exact_v308": {
            "sha256": actual_v308_sha256,
            "rs_class_count": exact_index["summary"][
                "rs_class_count"
            ],
        },
        "summary": {
            **strategy_counts,
            "strong_candidates": sum(
                1
                for row in candidates
                if row["evidence_tier"] == "strong"
            ),
            "inferred_candidates": sum(
                1
                for row in candidates
                if row["evidence_tier"] == "inferred"
            ),
        },
        "candidates": candidates,
        "ambiguous": match_report.get("ambiguous", []),
        "unmatched_external": match_report.get(
            "unmatched_old",
            [],
        ),
        "unmatched_exact_v308": match_report.get(
            "unmatched_new",
            [],
        ),
        "package_anchors": match_report.get(
            "package_anchors",
            {},
        ),
        "truth_boundary": {
            "exact_v308_is_sole_binary_authority": True,
            "external_names_are_research_candidates_only": True,
            "automatic_semantic_promotion": False,
            "automatic_source_rewrite": False,
        },
    }
