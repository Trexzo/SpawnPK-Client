from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
import zipfile

from .classfile import ClassFormatError, parse_class
from .source_digest import source_tree_digest


class JavacVariableTriageError(ValueError):
    pass


_PACKAGE_RE = re.compile(
    r"(?m)^\\s*package\\s+([A-Za-z_$][\\w$]*(?:\\.[A-Za-z_$][\\w$]*)*)\\s*;"
)
_IMPORT_RE = re.compile(
    r"(?m)^\\s*import\\s+(?!static\\s+)"
    r"([A-Za-z_$][\\w$]*(?:\\.[A-Za-z_$][\\w$]*)*)(\\.\\*)?\\s*;"
)
_VARIABLE_LOCATION_RE = re.compile(
    r"^.+?\\s+of\\s+type\\s+(.+?)\\s*$"
)


def _erase_type_arguments(value: str) -> str:
    out: list[str] = []
    depth = 0
    for ch in value.strip():
        if ch == "<":
            depth += 1
            continue
        if ch == ">":
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            out.append(ch)
    return "".join(out).strip()


def _normalize_type_token(value: str) -> str | None:
    token = _erase_type_arguments(value)
    while token.endswith("[]"):
        token = token[:-2].strip()

    if token.startswith("? extends "):
        token = token[len("? extends "):].strip()
    elif token.startswith("? super "):
        token = token[len("? super "):].strip()

    if token in {
        "",
        "?",
        "boolean",
        "byte",
        "short",
        "int",
        "long",
        "char",
        "float",
        "double",
        "void",
    }:
        return None

    # Javac sometimes renders captured/intersection types.  Do not guess.
    if (
        token.startswith("capture#")
        or " & " in token
        or " | " in token
    ):
        return None

    return token


def _source_type_context(
    source_root: Path,
    rel: str,
) -> tuple[str | None, dict[str, str], list[str]]:
    path = source_root / Path(rel)
    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    package_match = _PACKAGE_RE.search(text)
    package = package_match.group(1) if package_match else None

    explicit: dict[str, str] = {}
    wildcards: list[str] = []
    for match in _IMPORT_RE.finditer(text):
        dotted = match.group(1)
        is_wildcard = bool(match.group(2))
        if is_wildcard:
            wildcards.append(dotted)
        else:
            explicit[dotted.rsplit(".", 1)[-1]] = dotted

    return package, explicit, wildcards


def _candidate_internal_names_for_type(
    classes: dict[str, dict[str, Any]],
    type_token: str,
    *,
    package: str | None,
    explicit_imports: dict[str, str],
    wildcard_imports: list[str],
) -> list[str]:
    token = _normalize_type_token(type_token)
    if token is None:
        return []

    # Already qualified.  Try exact dotted->internal first, including nested
    # class spelling where javac may use Outer.Inner.
    direct = token.replace(".", "/")
    direct_candidates: list[str] = []
    if direct in classes:
        direct_candidates.append(direct)

    parts = token.split(".")
    for split in range(1, len(parts)):
        left = "/".join(parts[:split])
        right = "$".join(parts[split:])
        candidate = left + "/" + right
        if candidate in classes:
            direct_candidates.append(candidate)

    if direct_candidates:
        return sorted(set(direct_candidates))

    simple = parts[-1]
    candidates: set[str] = set()

    imported = explicit_imports.get(parts[0])
    if imported is not None:
        imported_parts = imported.split(".")
        suffix = parts[1:]
        dotted = "/".join(imported_parts)
        if suffix:
            dotted = dotted + "$" + "$".join(suffix)
        if dotted in classes:
            candidates.add(dotted)

    if package:
        same = package.replace(".", "/") + "/" + token.replace(".", "$")
        if same in classes:
            candidates.add(same)

    java_lang = "java/lang/" + token.replace(".", "$")
    if java_lang in classes:
        candidates.add(java_lang)

    for wildcard in wildcard_imports:
        candidate = wildcard.replace(".", "/") + "/" + token.replace(".", "$")
        if candidate in classes:
            candidates.add(candidate)

    # Fail-closed fallback: only accept a globally unique simple/nested match.
    global_matches = [
        name
        for name in classes
        if _simple_name(name) == simple
    ]
    if len(global_matches) == 1:
        candidates.add(global_matches[0])

    return sorted(candidates)


def _variable_location_owner(
    classes: dict[str, dict[str, Any]],
    source_root: Path,
    rel: str,
    location_value: str | None,
) -> tuple[str | None, list[str], str]:
    if not location_value:
        return None, [], "variable_location_missing"

    match = _VARIABLE_LOCATION_RE.match(location_value.strip())
    if match is None:
        return None, [], "variable_location_malformed"

    type_token = match.group(1).strip()
    normalized = _normalize_type_token(type_token)
    if normalized is None:
        return None, [], "variable_location_type_unsupported"

    package, explicit, wildcards = _source_type_context(
        source_root,
        rel,
    )
    candidates = _candidate_internal_names_for_type(
        classes,
        normalized,
        package=package,
        explicit_imports=explicit,
        wildcard_imports=wildcards,
    )
    if len(candidates) == 1:
        return candidates[0], candidates, "variable_location_owner_exact"
    if len(candidates) > 1:
        return None, candidates, "variable_location_owner_ambiguous"
    return None, [], "variable_location_owner_unbound"


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _normal_path(value: str) -> str:
    return value.replace("\\", "/")


def _relative_source_path(
    source_path: str,
    source_root: Path,
) -> str | None:
    root = _normal_path(str(source_root.resolve())).rstrip("/")
    value = _normal_path(source_path)

    prefix = root + "/"
    if value.startswith(prefix):
        rel = value[len(prefix):]
    elif value.casefold().startswith(prefix.casefold()):
        # Windows drive/root spelling may differ in case.  Preserve the exact
        # suffix spelling from javac; that suffix is the source authority.
        rel = value[len(prefix):]
    elif Path(source_path).is_absolute():
        # Windows temp paths can mix 8.3 short names (RUNNER~1) with the
        # long canonical spelling returned by Path.resolve().  Resolve both
        # sides before giving up on a path that is physically inside root.
        try:
            resolved_value = _normal_path(
                str(Path(source_path).resolve())
            )
        except OSError:
            return None
        if resolved_value.startswith(prefix):
            rel = resolved_value[len(prefix):]
        elif resolved_value.casefold().startswith(
            prefix.casefold()
        ):
            rel = resolved_value[len(prefix):]
        else:
            return None
    else:
        rel = value.lstrip("./")

    pure = PurePosixPath(rel)
    if (
        not rel.endswith(".java")
        or pure.is_absolute()
        or ".." in pure.parts
    ):
        return None
    return pure.as_posix()


def _load_classes(readable_jar: Path) -> dict[str, dict[str, Any]]:
    classes: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(readable_jar) as z:
        for info in z.infolist():
            name = info.filename
            if (
                info.is_dir()
                or not name.endswith(".class")
                or name.startswith("META-INF/versions/")
            ):
                continue
            try:
                parsed = parse_class(z.read(name))
            except ClassFormatError as exc:
                raise JavacVariableTriageError(
                    f"readable class parse failed for {name}: {exc}"
                ) from exc

            if parsed.name in classes:
                raise JavacVariableTriageError(
                    "duplicate readable JVM class identity: "
                    + parsed.name
                )
            classes[parsed.name] = {
                "name": parsed.name,
                "super_name": parsed.super_name,
                "interfaces": list(parsed.interfaces),
                "fields": [
                    {
                        "name": str(field.get("name", "")),
                        "descriptor": str(field.get("descriptor", "")),
                        "access": int(field.get("access", 0)),
                    }
                    for field in parsed.fields
                ],
            }
    return classes


def _simple_name(internal_name: str) -> str:
    tail = internal_name.rsplit("/", 1)[-1]
    return tail.rsplit("$", 1)[-1]


def _diagnostic_owner(
    classes: dict[str, dict[str, Any]],
    top_owner: str,
    location_kind: str | None,
    location_value: str | None,
) -> tuple[str | None, list[str]]:
    if top_owner not in classes:
        return None, []

    if location_kind not in {"class", "interface"} or not location_value:
        return None, []

    raw = location_value.strip()
    dotted = raw.replace(".", "/")
    if dotted in classes and (
        dotted == top_owner or dotted.startswith(top_owner + "$")
    ):
        return dotted, [dotted]

    target = raw.rsplit(".", 1)[-1]
    candidates = [
        name
        for name in classes
        if (
            name == top_owner or name.startswith(top_owner + "$")
        )
        and _simple_name(name) == target
    ]
    candidates.sort()
    if len(candidates) == 1:
        return candidates[0], candidates
    return None, candidates


def _field_matches(
    classes: dict[str, dict[str, Any]],
    owner: str,
    field_name: str,
) -> tuple[str, list[dict[str, Any]]]:
    current = classes.get(owner)
    if current is None:
        return "source_owner_missing", []

    current_matches = [
        {
            **field,
            "owner": owner,
            "depth": 0,
            "relation": "current",
        }
        for field in current["fields"]
        if field["name"] == field_name
    ]
    if current_matches:
        if len(current_matches) == 1:
            return "current_class_exact_field", current_matches
        return "current_class_field_ambiguous", current_matches

    queue: list[tuple[str, int, str]] = []
    if current["super_name"]:
        queue.append((current["super_name"], 1, "superclass"))
    queue.extend(
        (name, 1, "interface")
        for name in current["interfaces"]
    )

    visited: set[str] = set()
    inherited: list[dict[str, Any]] = []
    while queue:
        name, depth, relation = queue.pop(0)
        if name in visited:
            continue
        visited.add(name)
        row = classes.get(name)
        if row is None:
            continue

        inherited.extend(
            {
                **field,
                "owner": name,
                "depth": depth,
                "relation": relation,
            }
            for field in row["fields"]
            if field["name"] == field_name
        )

        if row["super_name"]:
            queue.append(
                (row["super_name"], depth + 1, "superclass")
            )
        queue.extend(
            (iface, depth + 1, "interface")
            for iface in row["interfaces"]
        )

    unique = {
        (
            row["owner"],
            row["name"],
            row["descriptor"],
            row["access"],
        )
        for row in inherited
    }
    if not unique:
        return "no_exact_field_in_hierarchy", []
    if len(unique) == 1:
        return "inherited_exact_field", inherited
    return "hierarchy_exact_field_ambiguous", inherited


def _frontier_id_from_report(
    diagnostic_report: dict[str, Any],
) -> str:
    diagnostics = diagnostic_report.get("diagnostics")
    if not isinstance(diagnostics, list):
        raise JavacVariableTriageError(
            "javac diagnostic report lacks diagnostic rows"
        )

    public_rows = []
    for row in diagnostics:
        if not isinstance(row, dict):
            raise JavacVariableTriageError(
                "javac diagnostic row is not an object"
            )
        try:
            public_rows.append(
                {
                    "category": row["category"],
                    "symbol_kind": row["symbol_kind"],
                    "symbol_shape": row["symbol_shape"],
                    "location_kind": row["location_kind"],
                    "shape_cluster_id": row["shape_cluster_id"],
                    "cluster_id": row["cluster_id"],
                    "symbol_id": row["symbol_id"],
                    "location_id": row["location_id"],
                    "file_id": row["file_id"],
                    "line": row["line"],
                }
            )
        except KeyError as exc:
            raise JavacVariableTriageError(
                "javac diagnostic row lacks public frontier fields"
            ) from exc

    return (
        "JAVACFRONTIER_"
        + _stable_digest({"rows": public_rows})[:20].upper()
    )


def analyze_unresolved_variables(
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
        raise JavacVariableTriageError(
            "unsupported javac diagnostic report"
        )
    if diagnostic_report.get("identifiers_included") is not True:
        raise JavacVariableTriageError(
            "R8O requires a private diagnostic report generated with "
            "--include-identifiers"
        )

    derived_frontier_id = _frontier_id_from_report(
        diagnostic_report
    )
    frontier_id = diagnostic_report.get("frontier_id")
    frontier_derived_from_legacy_report = frontier_id is None
    if frontier_id is None:
        frontier_id = derived_frontier_id
    elif (
        not isinstance(frontier_id, str)
        or not frontier_id.startswith("JAVACFRONTIER_")
        or frontier_id != derived_frontier_id
    ):
        raise JavacVariableTriageError(
            "javac diagnostic frontier authority is invalid"
        )

    readable_jar = readable_jar.resolve()
    source_root = source_root.resolve()
    if not readable_jar.is_file():
        raise JavacVariableTriageError(
            f"readable JAR does not exist: {readable_jar}"
        )
    if not source_root.is_dir():
        raise JavacVariableTriageError(
            f"source root does not exist: {source_root}"
        )

    tree_sha, source_files, _source_bytes = source_tree_digest(
        source_root
    )
    jar_sha = _sha256_file(readable_jar)
    classes = _load_classes(readable_jar)

    rows: list[dict[str, Any]] = []
    for diagnostic in diagnostic_report.get("diagnostics", []):
        if (
            diagnostic.get("category") != "cannot_find_symbol"
            or diagnostic.get("symbol_kind") != "variable"
        ):
            continue

        source_path = diagnostic.get("source_path")
        symbol = diagnostic.get("symbol")
        location_kind = diagnostic.get("location_kind")
        location_value = diagnostic.get("location")
        if not isinstance(source_path, str) or not isinstance(symbol, str):
            raise JavacVariableTriageError(
                "private variable diagnostic is missing identifiers"
            )

        rel = _relative_source_path(source_path, source_root)
        top_owner = (
            rel[:-5]
            if rel is not None
            else None
        )
        owner: str | None = None
        owner_candidates: list[str] = []
        matches: list[dict[str, Any]] = []

        owner_resolution = None
        if top_owner is None:
            proof_class = "source_path_unbound"
        elif top_owner not in classes:
            proof_class = "source_owner_missing"
        elif location_kind in {"class", "interface"}:
            owner, owner_candidates = _diagnostic_owner(
                classes,
                top_owner,
                str(location_kind),
                (
                    str(location_value)
                    if location_value is not None
                    else None
                ),
            )
            if owner is None:
                if len(owner_candidates) > 1:
                    proof_class = "diagnostic_owner_ambiguous"
                else:
                    proof_class = "diagnostic_owner_unbound"
            else:
                owner_resolution = "source_class_location"
                proof_class, matches = _field_matches(
                    classes,
                    owner,
                    symbol,
                )
        elif location_kind == "variable":
            owner, owner_candidates, owner_resolution = (
                _variable_location_owner(
                    classes,
                    source_root,
                    rel,
                    (
                        str(location_value)
                        if location_value is not None
                        else None
                    ),
                )
            )
            if owner is None:
                proof_class = owner_resolution
            else:
                proof_class, matches = _field_matches(
                    classes,
                    owner,
                    symbol,
                )
        else:
            proof_class = "unsupported_location_kind"

        public = {
            "file_id": diagnostic.get("file_id"),
            "symbol_id": diagnostic.get("symbol_id"),
            "location_id": diagnostic.get("location_id"),
            "line": diagnostic.get("line"),
            "location_kind": location_kind,
            "owner_resolution": owner_resolution,
            "proof_class": proof_class,
            "match_count": len(matches),
        }
        if len(matches) == 1:
            public["match_relation"] = matches[0]["relation"]
            public["match_depth"] = matches[0]["depth"]
            public["match_static"] = bool(matches[0]["access"] & 0x0008)
        else:
            public["match_relation"] = None
            public["match_depth"] = None
            public["match_static"] = None

        if include_identifiers:
            public.update(
                {
                    "source_path": source_path,
                    "relative_source_path": rel,
                    "top_owner": top_owner,
                    "diagnostic_owner": owner,
                    "owner_candidates": owner_candidates,
                    "symbol": symbol,
                    "location": location_value,
                    "matches": matches,
                }
            )
        rows.append(public)

    proof_counts = Counter(row["proof_class"] for row in rows)
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
            },
        )
        bucket["count"] += 1
        if row.get("file_id") is not None:
            bucket["files"].add(str(row["file_id"]))
        bucket["proof_classes"][row["proof_class"]] += 1

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
                "owner_resolution",
                "proof_class",
                "match_count",
                "match_relation",
                "match_depth",
                "match_static",
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
        "kind": "javac_unresolved_variable_bytecode_triage_report",
        "report_id": (
            "JVARTRIAGE_"
            + _stable_digest(material)[:20].upper()
        ),
        "diagnostic_report_id": diagnostic_report.get("report_id"),
        "diagnostic_frontier_id": frontier_id,
        "diagnostic_frontier_derived_from_legacy_report": (
            frontier_derived_from_legacy_report
        ),
        "diagnostic_input_sha256": diagnostic_report.get(
            "input_sha256"
        ),
        "readable_jar_sha256": jar_sha,
        "source_tree_sha256": tree_sha,
        "source_java_file_count": len(source_files),
        "summary": {
            "variable_diagnostic_count": len(rows),
            "proof_classes": dict(sorted(proof_counts.items())),
            "symbol_clusters": clusters,
        },
        "diagnostics": rows,
        "identifiers_included": include_identifiers,
    }
    return report


def write_unresolved_variable_triage(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
