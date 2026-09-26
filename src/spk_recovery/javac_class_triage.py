from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from .javac_variable_triage import (
    JavacVariableTriageError,
    _erase_type_arguments,
    _frontier_id_from_report,
    _load_classes,
    _relative_source_path,
    _sha256_file,
    _simple_name,
    _source_type_context,
    _stable_digest,
)
from .source_digest import source_tree_digest
from .source_readiness import (
    _PACKAGE_RE as _READINESS_PACKAGE_RE,
    _TOP_TYPE_RE,
    _code_mask_and_depths,
)


class JavacClassTriageError(ValueError):
    pass


def _class_token(value: str) -> str | None:
    token = _erase_type_arguments(value).strip()
    while token.endswith("[]"):
        token = token[:-2].strip()
    if not token or token in {"?", "var"}:
        return None
    return token


def _visible_class_candidates(
    classes: dict[str, dict[str, Any]],
    token: str,
    *,
    package: str | None,
    explicit_imports: dict[str, str],
    wildcard_imports: list[str],
    top_owner: str | None,
) -> tuple[list[str], list[str]]:
    candidates: set[str] = set()
    channels: list[str] = []

    direct = token.replace(".", "/")
    if direct in classes:
        candidates.add(direct)
        channels.append("qualified")

    parts = token.split(".")
    for split in range(1, len(parts)):
        left = "/".join(parts[:split])
        right = "$".join(parts[split:])
        candidate = left + "/" + right
        if candidate in classes:
            candidates.add(candidate)
            channels.append("qualified_nested")

    if top_owner:
        nested = top_owner + "$" + token.replace(".", "$")
        if nested in classes:
            candidates.add(nested)
            channels.append("same_source_nested")

    imported = explicit_imports.get(parts[0])
    if imported is not None:
        candidate = imported.replace(".", "/")
        suffix = parts[1:]
        if suffix:
            candidate += "$" + "$".join(suffix)
        if candidate in classes:
            candidates.add(candidate)
            channels.append("explicit_import")

    if package:
        candidate = (
            package.replace(".", "/")
            + "/"
            + token.replace(".", "$")
        )
        if candidate in classes:
            candidates.add(candidate)
            channels.append("same_package")

    java_lang = "java/lang/" + token.replace(".", "$")
    if java_lang in classes:
        candidates.add(java_lang)
        channels.append("java_lang")

    for wildcard in wildcard_imports:
        candidate = (
            wildcard.replace(".", "/")
            + "/"
            + token.replace(".", "$")
        )
        if candidate in classes:
            candidates.add(candidate)
            channels.append("wildcard_import")

    return sorted(candidates), sorted(set(channels))


def _global_class_candidates(
    classes: dict[str, dict[str, Any]],
    token: str,
) -> list[str]:
    direct = token.replace(".", "/")
    matches: set[str] = set()
    if direct in classes:
        matches.add(direct)

    simple = token.rsplit(".", 1)[-1]
    for name in classes:
        if _simple_name(name) == simple:
            matches.add(name)
        rendered = name.replace("/", ".").replace("$", ".")
        if rendered.endswith("." + token) or rendered == token:
            matches.add(name)
    return sorted(matches)


def _brace_pairs(masked: str) -> dict[int, int]:
    stack: list[int] = []
    pairs: dict[int, int] = {}
    for index, ch in enumerate(masked):
        if ch == "{":
            stack.append(index)
        elif ch == "}" and stack:
            start = stack.pop()
            pairs[start] = index
    return pairs


def _source_declared_types(
    source_root: Path,
) -> tuple[set[str], dict[str, str]]:
    declared: set[str] = set()
    owners: dict[str, str] = {}

    for path in sorted(
        source_root.rglob("*.java"),
        key=lambda p: p.relative_to(source_root).as_posix(),
    ):
        rel = path.relative_to(source_root).as_posix()
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        package_match = _READINESS_PACKAGE_RE.search(text)
        package = package_match.group(1) if package_match else ""
        masked, _depths = _code_mask_and_depths(text)
        pairs = _brace_pairs(masked)

        declarations: list[dict[str, Any]] = []
        for match in _TOP_TYPE_RE.finditer(masked):
            body_start = masked.find("{", match.end())
            if body_start < 0:
                continue
            body_end = pairs.get(body_start)
            if body_end is None:
                continue

            parent = None
            for candidate in declarations:
                if (
                    candidate["body_start"] < match.start()
                    < candidate["body_end"]
                ):
                    if (
                        parent is None
                        or candidate["body_start"]
                        > parent["body_start"]
                    ):
                        parent = candidate

            name = match.group(1)
            if parent is None:
                internal = (
                    package.replace(".", "/") + "/" + name
                    if package
                    else name
                )
            else:
                internal = parent["internal"] + "$" + name

            declarations.append(
                {
                    "internal": internal,
                    "body_start": body_start,
                    "body_end": body_end,
                }
            )
            if internal in owners and owners[internal] != rel:
                raise JavacClassTriageError(
                    "source declaration identity collision: "
                    + internal
                )
            owners[internal] = rel
            declared.add(internal)

    return declared, owners


def _readable_structure(
    row: dict[str, Any],
) -> str:
    inner_outer = row.get("inner_outer_name")
    inner_simple = row.get("inner_simple_name")
    enclosing = row.get("enclosing_class_name")

    if enclosing:
        if inner_simple:
            return "named_local"
        return "anonymous_or_local_unnamed"
    if inner_outer:
        if inner_simple:
            return "named_member"
        return "anonymous_member_metadata"
    if "$" in str(row.get("name", "")):
        return "dollar_named_without_inner_metadata"
    return "top_level"


def _readable_kind(
    row: dict[str, Any],
) -> str:
    access = int(row.get("access", 0))
    if access & 0x2000:
        return "annotation"
    if access & 0x4000:
        return "enum"
    if access & 0x0200:
        return "interface"
    if "Record" in row.get("attributes", []):
        return "record"
    return "class"


def analyze_unresolved_classes(
    diagnostic_report: dict[str, Any],
    readable_jar: Path,
    source_root: Path,
    *,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    if (
        diagnostic_report.get("schema_version") != 1
        or diagnostic_report.get("kind")
        != "javac_diagnostic_classification_report"
    ):
        raise JavacClassTriageError(
            "unsupported javac diagnostic report"
        )
    if diagnostic_report.get("identifiers_included") is not True:
        raise JavacClassTriageError(
            "R8P requires a private diagnostic report generated with "
            "--include-identifiers"
        )

    try:
        derived_frontier_id = _frontier_id_from_report(
            diagnostic_report
        )
    except JavacVariableTriageError as exc:
        raise JavacClassTriageError(str(exc)) from exc

    frontier_id = diagnostic_report.get("frontier_id")
    frontier_derived = frontier_id is None
    if frontier_id is None:
        frontier_id = derived_frontier_id
    elif (
        not isinstance(frontier_id, str)
        or not frontier_id.startswith("JAVACFRONTIER_")
        or frontier_id != derived_frontier_id
    ):
        raise JavacClassTriageError(
            "javac diagnostic frontier authority is invalid"
        )

    readable_jar = readable_jar.resolve()
    source_root = source_root.resolve()
    if not readable_jar.is_file():
        raise JavacClassTriageError(
            f"readable JAR does not exist: {readable_jar}"
        )
    if not source_root.is_dir():
        raise JavacClassTriageError(
            f"source root does not exist: {source_root}"
        )

    tree_sha, source_files, _source_bytes = source_tree_digest(
        source_root
    )
    jar_sha = _sha256_file(readable_jar)
    classes = _load_classes(readable_jar)
    source_declared, source_declared_files = _source_declared_types(
        source_root
    )

    rows: list[dict[str, Any]] = []
    for diagnostic in diagnostic_report.get("diagnostics", []):
        if (
            diagnostic.get("category") != "cannot_find_symbol"
            or diagnostic.get("symbol_kind") != "class"
        ):
            continue

        source_path = diagnostic.get("source_path")
        symbol = diagnostic.get("symbol")
        if not isinstance(source_path, str) or not isinstance(symbol, str):
            raise JavacClassTriageError(
                "private class diagnostic is missing identifiers"
            )

        rel = _relative_source_path(source_path, source_root)
        top_owner = rel[:-5] if rel and rel.endswith(".java") else None
        token = _class_token(symbol)

        visible: list[str] = []
        channels: list[str] = []
        global_candidates: list[str] = []
        source_materialization = "not_applicable"
        source_declared_candidate_count = 0
        candidate_structure = "not_applicable"
        candidate_kind = "not_applicable"
        candidate_synthetic = False

        if rel is None:
            proof_class = "source_path_unbound"
        elif top_owner not in classes:
            proof_class = "source_owner_missing"
        elif token is None:
            proof_class = "class_symbol_unsupported"
        else:
            package, explicit, wildcards = _source_type_context(
                source_root,
                rel,
            )
            visible, channels = _visible_class_candidates(
                classes,
                token,
                package=package,
                explicit_imports=explicit,
                wildcard_imports=wildcards,
                top_owner=top_owner,
            )
            if len(visible) == 1:
                proof_class = "java_visible_exact_class"
            elif len(visible) > 1:
                proof_class = "java_visible_class_ambiguous"
            else:
                global_candidates = _global_class_candidates(
                    classes,
                    token,
                )
                if len(global_candidates) == 1:
                    proof_class = "readable_class_not_java_visible"
                elif len(global_candidates) > 1:
                    proof_class = "readable_class_name_ambiguous"
                else:
                    proof_class = "class_absent_from_readable"

            candidate_pool = (
                visible
                if visible
                else global_candidates
            )
            source_declared_candidate_count = sum(
                1
                for candidate in candidate_pool
                if candidate in source_declared
            )
            if len(candidate_pool) == 1:
                candidate = candidate_pool[0]
                class_row = classes.get(candidate)
                if class_row is not None:
                    candidate_structure = _readable_structure(
                        class_row
                    )
                    candidate_kind = _readable_kind(class_row)
                    candidate_synthetic = bool(
                        int(class_row.get("access", 0)) & 0x1000
                    )
                if candidate in source_declared:
                    source_materialization = "declared_exact"
                else:
                    source_materialization = (
                        "missing_exact_declaration"
                    )
            elif len(candidate_pool) > 1:
                if source_declared_candidate_count == 0:
                    source_materialization = (
                        "ambiguous_none_declared"
                    )
                elif source_declared_candidate_count == 1:
                    source_materialization = (
                        "ambiguous_one_declared"
                    )
                else:
                    source_materialization = (
                        "ambiguous_multiple_declared"
                    )
            elif proof_class == "class_absent_from_readable":
                source_materialization = "readable_absent"

        public: dict[str, Any] = {
            "file_id": diagnostic.get("file_id"),
            "symbol_id": diagnostic.get("symbol_id"),
            "location_id": diagnostic.get("location_id"),
            "line": diagnostic.get("line"),
            "location_kind": diagnostic.get("location_kind"),
            "proof_class": proof_class,
            "visible_candidate_count": len(visible),
            "global_candidate_count": len(global_candidates),
            "visibility_channel_count": len(channels),
            "source_materialization": source_materialization,
            "source_declared_candidate_count": (
                source_declared_candidate_count
            ),
            "candidate_structure": candidate_structure,
            "candidate_kind": candidate_kind,
            "candidate_synthetic": candidate_synthetic,
        }
        if include_identifiers:
            public.update(
                {
                    "source_path": source_path,
                    "relative_source_path": rel,
                    "top_owner": top_owner,
                    "symbol": symbol,
                    "visible_candidates": visible,
                    "visibility_channels": channels,
                    "global_candidates": global_candidates,
                    "source_declared_candidate_files": {
                        candidate: source_declared_files.get(candidate)
                        for candidate in (
                            visible or global_candidates
                        )
                        if candidate in source_declared_files
                    },
                    "location": diagnostic.get("location"),
                }
            )
        rows.append(public)

    proof_counts = Counter(row["proof_class"] for row in rows)
    materialization_counts = Counter(
        row["source_materialization"]
        for row in rows
    )
    visible_exact_source_declared_count = sum(
        1
        for row in rows
        if (
            row["proof_class"] == "java_visible_exact_class"
            and row["source_materialization"] == "declared_exact"
        )
    )
    visible_exact_source_missing_count = sum(
        1
        for row in rows
        if (
            row["proof_class"] == "java_visible_exact_class"
            and row["source_materialization"]
            == "missing_exact_declaration"
        )
    )
    missing_structure_diagnostics = Counter(
        row["candidate_structure"]
        for row in rows
        if row["source_materialization"]
        == "missing_exact_declaration"
    )
    missing_kind_diagnostics = Counter(
        row["candidate_kind"]
        for row in rows
        if row["source_materialization"]
        == "missing_exact_declaration"
    )
    missing_synthetic_diagnostic_count = sum(
        1
        for row in rows
        if (
            row["source_materialization"]
            == "missing_exact_declaration"
            and row["candidate_synthetic"]
        )
    )
    missing_candidate_rows: dict[str, dict[str, Any]] = {}
    for row in rows:
        if (
            row["source_materialization"]
            != "missing_exact_declaration"
        ):
            continue
        private_candidates = (
            row.get("visible_candidates")
            or row.get("global_candidates")
            or []
        )
        if len(private_candidates) == 1:
            candidate = private_candidates[0]
        else:
            # Public mode intentionally lacks identities.  Reconstruct the
            # same unique key from the already-resolved candidate metadata
            # by stable symbol identity; an exact-visible class symbol has
            # one candidate per symbol spelling.
            candidate = "symbol:" + str(row.get("symbol_id") or "none")
        missing_candidate_rows.setdefault(
            candidate,
            {
                "structure": row["candidate_structure"],
                "kind": row["candidate_kind"],
                "synthetic": row["candidate_synthetic"],
            },
        )

    missing_unique_structure = Counter(
        value["structure"]
        for value in missing_candidate_rows.values()
    )
    missing_unique_kind = Counter(
        value["kind"]
        for value in missing_candidate_rows.values()
    )
    missing_unique_synthetic_count = sum(
        1
        for value in missing_candidate_rows.values()
        if value["synthetic"]
    )

    symbol_buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol_id = str(row.get("symbol_id") or "none")
        bucket = symbol_buckets.setdefault(
            symbol_id,
            {
                "symbol_id": symbol_id,
                "count": 0,
                "files": set(),
                "proof_classes": Counter(),
                "source_materialization": Counter(),
                "candidate_structures": Counter(),
            },
        )
        bucket["count"] += 1
        if row.get("file_id") is not None:
            bucket["files"].add(str(row["file_id"]))
        bucket["proof_classes"][row["proof_class"]] += 1
        bucket["source_materialization"][
            row["source_materialization"]
        ] += 1
        bucket["candidate_structures"][
            row["candidate_structure"]
        ] += 1

    clusters = []
    for bucket in symbol_buckets.values():
        clusters.append(
            {
                "symbol_id": bucket["symbol_id"],
                "count": bucket["count"],
                "affected_files": len(bucket["files"]),
                "proof_classes": dict(
                    sorted(bucket["proof_classes"].items())
                ),
                "source_materialization": dict(
                    sorted(
                        bucket["source_materialization"].items()
                    )
                ),
                "candidate_structures": dict(
                    sorted(bucket["candidate_structures"].items())
                ),
            }
        )
    clusters.sort(
        key=lambda row: (-int(row["count"]), row["symbol_id"])
    )

    public_rows = [
        {
            key: row[key]
            for key in (
                "file_id",
                "symbol_id",
                "location_id",
                "line",
                "location_kind",
                "proof_class",
                "visible_candidate_count",
                "global_candidate_count",
                "visibility_channel_count",
                "source_materialization",
                "source_declared_candidate_count",
                "candidate_structure",
                "candidate_kind",
                "candidate_synthetic",
            )
        }
        for row in rows
    ]

    material = {
        "diagnostic_frontier_id": frontier_id,
        "readable_jar_sha256": jar_sha,
        "source_tree_sha256": tree_sha,
        "rows": public_rows,
    }
    report = {
        "schema_version": 1,
        "kind": "javac_unresolved_class_bytecode_triage_report",
        "report_id": (
            "JCLASSTRIAGE_"
            + _stable_digest(material)[:20].upper()
        ),
        "diagnostic_report_id": diagnostic_report.get("report_id"),
        "diagnostic_frontier_id": frontier_id,
        "diagnostic_frontier_derived_from_legacy_report": frontier_derived,
        "diagnostic_input_sha256": diagnostic_report.get("input_sha256"),
        "readable_jar_sha256": jar_sha,
        "source_tree_sha256": tree_sha,
        "source_java_file_count": len(source_files),
        "summary": {
            "class_diagnostic_count": len(rows),
            "proof_classes": dict(sorted(proof_counts.items())),
            "source_materialization": dict(
                sorted(materialization_counts.items())
            ),
            "source_declared_type_count": len(source_declared),
            "visible_exact_source_declared_count": (
                visible_exact_source_declared_count
            ),
            "visible_exact_source_missing_count": (
                visible_exact_source_missing_count
            ),
            "missing_declaration_structure_diagnostics": dict(
                sorted(missing_structure_diagnostics.items())
            ),
            "missing_declaration_kind_diagnostics": dict(
                sorted(missing_kind_diagnostics.items())
            ),
            "missing_declaration_synthetic_diagnostic_count": (
                missing_synthetic_diagnostic_count
            ),
            "missing_declaration_unique_class_count": (
                len(missing_candidate_rows)
            ),
            "missing_unique_class_structures": dict(
                sorted(missing_unique_structure.items())
            ),
            "missing_unique_class_kinds": dict(
                sorted(missing_unique_kind.items())
            ),
            "missing_unique_synthetic_class_count": (
                missing_unique_synthetic_count
            ),
            "repair_candidate_diagnostic_count": (
                proof_counts.get("readable_class_not_java_visible", 0)
            ),
            "visible_exact_diagnostic_count": (
                proof_counts.get("java_visible_exact_class", 0)
            ),
            "ambiguous_diagnostic_count": (
                proof_counts.get("java_visible_class_ambiguous", 0)
                + proof_counts.get("readable_class_name_ambiguous", 0)
            ),
            "absent_diagnostic_count": (
                proof_counts.get("class_absent_from_readable", 0)
            ),
            "symbol_clusters": clusters,
        },
        "diagnostics": rows,
        "identifiers_included": include_identifiers,
    }
    return report


def write_unresolved_class_triage(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
