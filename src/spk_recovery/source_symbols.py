from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .lineage import validate_lineage
from .member_lineage import validate_member_lineage
from .source_digest import source_tree_digest


class SourceSymbolInventoryError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_tree_digest(root: Path) -> tuple[str, int]:
    digest, files, _total_bytes = source_tree_digest(root)
    return digest, len(files)


def _helper_source() -> Path:
    path = Path(__file__).resolve().parent / "java" / "SourceSymbolScanner.java"
    if not path.is_file():
        raise SourceSymbolInventoryError(f"missing AST helper: {path}")
    return path


def _require(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise SourceSymbolInventoryError(f"required executable not found on PATH: {name}")
    return found


def _decode(value: str) -> str:
    pad = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + pad).encode("ascii")).decode("utf-8")


def _descriptor_arity(descriptor: str) -> int:
    if not descriptor.startswith("("):
        raise SourceSymbolInventoryError(f"invalid method descriptor {descriptor!r}")
    i = 1
    count = 0
    while i < len(descriptor) and descriptor[i] != ")":
        while descriptor[i] == "[":
            i += 1
        if descriptor[i] == "L":
            semi = descriptor.find(";", i)
            if semi < 0:
                raise SourceSymbolInventoryError(f"invalid method descriptor {descriptor!r}")
            i = semi + 1
        else:
            i += 1
        count += 1
    if i >= len(descriptor) or descriptor[i] != ")":
        raise SourceSymbolInventoryError(f"invalid method descriptor {descriptor!r}")
    return count


def _class_readable_map(
    class_lineage: dict[str, Any],
    *,
    build_id: str,
    target_package: str,
) -> tuple[dict[str, str], dict[str, str]]:
    owner_to_logical: dict[str, str] = {}
    logical_to_readable: dict[str, str] = {}
    package = target_package.rstrip("/")

    for record in class_lineage.get("classes", []):
        entry = next(
            (
                row
                for row in record.get("lineage", [])
                if row.get("build_id") == build_id
            ),
            None,
        )
        if entry is None:
            continue

        logical_id = record["logical_id"]
        if record.get("semantic_status") == "ACCEPTED":
            semantic = record.get("semantic_name")
            if not isinstance(semantic, str) or not semantic:
                raise SourceSymbolInventoryError(
                    f"{logical_id}: accepted class lacks semantic_name"
                )
            readable = package + "/" + semantic
        else:
            readable = str(entry["internal_name"])

        if readable in owner_to_logical:
            raise SourceSymbolInventoryError(
                f"readable class owner collision: {readable}"
            )
        owner_to_logical[readable] = logical_id
        logical_to_readable[logical_id] = readable

    return owner_to_logical, logical_to_readable


def _method_readable_map(
    member_lineage: dict[str, Any],
    *,
    build_id: str,
    logical_to_readable_owner: dict[str, str],
) -> dict[tuple[str, str, int], list[str]]:
    out: dict[tuple[str, str, int], list[str]] = {}
    for record in member_lineage.get("members", []):
        if record.get("kind") != "method":
            continue
        entry = next(
            (
                row
                for row in record.get("lineage", [])
                if row.get("build_id") == build_id
            ),
            None,
        )
        if entry is None:
            continue

        owner = logical_to_readable_owner.get(record.get("owner_logical_id"))
        if owner is None:
            continue
        if record.get("semantic_status") == "ACCEPTED":
            name = record.get("semantic_name")
        else:
            name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        arity = _descriptor_arity(str(entry.get("descriptor", "")))
        out.setdefault((owner, name, arity), []).append(record["member_id"])
    return out


def _compile_and_scan(
    source_root: Path,
    *,
    java_command: str,
    javac_command: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    java = _require(java_command)
    javac = _require(javac_command)

    with tempfile.TemporaryDirectory(prefix="spk-source-symbols-") as td:
        root = Path(td)
        classes = root / "classes"
        classes.mkdir()

        compile_proc = subprocess.run(
            [
                javac,
                "--add-modules",
                "jdk.compiler",
                "-d",
                str(classes),
                str(_helper_source()),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if compile_proc.returncode != 0:
            raise SourceSymbolInventoryError(
                "source symbol helper compilation failed:\n"
                + compile_proc.stdout
                + compile_proc.stderr
            )

        proc = subprocess.run(
            [
                java,
                "--add-modules",
                "jdk.compiler",
                "-cp",
                str(classes),
                "SourceSymbolScanner",
                str(source_root),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise SourceSymbolInventoryError(
                "source symbol scan failed:\n" + proc.stdout + proc.stderr
            )

    methods: list[dict[str, Any]] = []
    variables: list[dict[str, Any]] = []
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if parts[0] == "M" and len(parts) == 7:
            methods.append(
                {
                    "source_file": _decode(parts[1]),
                    "owner_internal_name": _decode(parts[2]),
                    "name": _decode(parts[3]),
                    "arity": int(parts[4]),
                    "start": int(parts[5]),
                    "end": int(parts[6]),
                }
            )
        elif parts[0] == "V" and len(parts) == 12:
            variables.append(
                {
                    "source_file": _decode(parts[1]),
                    "owner_internal_name": _decode(parts[2]),
                    "method_name": _decode(parts[3]),
                    "method_arity": int(parts[4]),
                    "method_start": int(parts[5]),
                    "kind": _decode(parts[6]),
                    "current_name": _decode(parts[7]),
                    "declared_type": _decode(parts[8]),
                    "parameter_index": int(parts[9]),
                    "start": int(parts[10]),
                    "end": int(parts[11]),
                }
            )
        else:
            raise SourceSymbolInventoryError(f"unexpected scanner row: {raw!r}")

    methods.sort(
        key=lambda row: (
            row["source_file"],
            row["start"],
            row["owner_internal_name"],
            row["name"],
            row["arity"],
        )
    )
    variables.sort(
        key=lambda row: (
            row["source_file"],
            row["method_start"],
            row["start"],
            row["end"],
            row["current_name"],
        )
    )
    return methods, variables


def _stable_id(prefix: str, material: str) -> str:
    return prefix + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20].upper()


def build_source_symbol_inventory(
    recovered_manifest: dict[str, Any],
    source_root: Path,
    class_lineage: dict[str, Any],
    member_lineage: dict[str, Any],
    *,
    build_id: str,
    target_package: str = "recovered/spawnpk/client",
    java_command: str = "java",
    javac_command: str = "javac",
) -> dict[str, Any]:
    if (
        recovered_manifest.get("schema_version") != 1
        or recovered_manifest.get("kind")
        != "recovered_source_workspace_manifest"
    ):
        raise SourceSymbolInventoryError("unsupported recovered source manifest")
    if recovered_manifest.get("build_id") != build_id:
        raise SourceSymbolInventoryError(
            "recovered source manifest build_id does not match requested build"
        )

    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise SourceSymbolInventoryError(f"source root does not exist: {source_root}")

    tree_sha, java_count = _source_tree_digest(source_root)
    expected_tree = str(recovered_manifest.get("source_tree_sha256", "")).lower()
    if tree_sha.lower() != expected_tree:
        raise SourceSymbolInventoryError(
            f"source tree SHA-256 {tree_sha} does not match recovered manifest {expected_tree}"
        )
    if java_count != int(recovered_manifest.get("java_file_count", -1)):
        raise SourceSymbolInventoryError(
            "source Java file count does not match recovered manifest"
        )

    validate_lineage(class_lineage)
    validate_member_lineage(member_lineage, class_lineage=class_lineage)

    owner_to_logical, logical_to_readable = _class_readable_map(
        class_lineage,
        build_id=build_id,
        target_package=target_package,
    )
    method_map = _method_readable_map(
        member_lineage,
        build_id=build_id,
        logical_to_readable_owner=logical_to_readable,
    )

    methods, variables = _compile_and_scan(
        source_root,
        java_command=java_command,
        javac_command=javac_command,
    )

    method_rows: list[dict[str, Any]] = []
    method_lookup: dict[
        tuple[str, str, str, int, int], dict[str, Any]
    ] = {}
    ambiguous_method_count = 0

    for row in methods:
        owner = row["owner_internal_name"]
        candidates = method_map.get((owner, row["name"], row["arity"]), [])
        canonical_member_id = candidates[0] if len(candidates) == 1 else None
        if len(candidates) > 1:
            ambiguous_method_count += 1

        material = "|".join(
            [
                str(recovered_manifest.get("workspace_id")),
                row["source_file"],
                owner,
                row["name"],
                str(row["arity"]),
                str(row["start"]),
            ]
        )
        source_method_id = _stable_id("SRC_METHOD_", material)
        item = {
            **row,
            "source_method_id": source_method_id,
            "owner_logical_id": owner_to_logical.get(owner),
            "canonical_method_id": canonical_member_id,
            "canonical_match_candidates": sorted(candidates),
        }
        method_rows.append(item)
        method_lookup[
            (
                row["source_file"],
                owner,
                row["name"],
                row["arity"],
                row["start"],
            )
        ] = item

    grouped: dict[str, list[dict[str, Any]]] = {}
    orphan_variables: list[dict[str, Any]] = []
    for row in variables:
        method = method_lookup.get(
            (
                row["source_file"],
                row["owner_internal_name"],
                row["method_name"],
                row["method_arity"],
                row["method_start"],
            )
        )
        if method is None:
            orphan_variables.append(row)
            continue
        grouped.setdefault(method["source_method_id"], []).append(
            {**row, "_method": method}
        )

    symbols: list[dict[str, Any]] = []
    for source_method_id in sorted(grouped):
        values = sorted(
            grouped[source_method_id],
            key=lambda row: (
                row["start"],
                row["end"],
                row["current_name"],
            ),
        )
        local_ordinal = 0
        for row in values:
            method = row.pop("_method")
            kind = row["kind"]
            if kind == "parameter":
                ordinal = row["parameter_index"]
                prefix = "SRC_PARAM_"
            else:
                ordinal = local_ordinal
                local_ordinal += 1
                prefix = {
                    "catch": "SRC_CATCH_",
                    "resource": "SRC_RESOURCE_",
                    "enhanced_for": "SRC_ENHFOR_",
                    "lambda_parameter": "SRC_LAMBDA_PARAM_",
                }.get(kind, "SRC_LOCAL_")

            anchor = method["canonical_method_id"] or source_method_id
            material = "|".join(
                [
                    anchor,
                    kind,
                    str(ordinal),
                    row["declared_type"],
                    str(row["start"]),
                ]
            )
            symbols.append(
                {
                    "source_symbol_id": _stable_id(prefix, material),
                    "source_method_id": source_method_id,
                    "canonical_method_id": method["canonical_method_id"],
                    "owner_logical_id": method["owner_logical_id"],
                    "source_file": row["source_file"],
                    "owner_internal_name": row["owner_internal_name"],
                    "method_name": row["method_name"],
                    "method_arity": row["method_arity"],
                    "kind": kind,
                    "ordinal": ordinal,
                    "current_name": row["current_name"],
                    "declared_type": row["declared_type"],
                    "start": row["start"],
                    "end": row["end"],
                    "semantic_name": None,
                    "semantic_status": "UNKNOWN",
                    "semantic_confidence": 0.0,
                    "semantic_provenance": [],
                }
            )

    symbols.sort(
        key=lambda row: (
            row["source_file"],
            row["start"],
            row["source_symbol_id"],
        )
    )

    material = {
        "workspace_id": recovered_manifest.get("workspace_id"),
        "source_tree_sha256": tree_sha,
        "build_id": build_id,
        "target_package": target_package.rstrip("/"),
        "method_count": len(method_rows),
        "symbol_count": len(symbols),
        "method_ids": [row["source_method_id"] for row in method_rows],
        "symbol_ids": [row["source_symbol_id"] for row in symbols],
    }
    inventory_id = (
        "SRCINV_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "source_symbol_inventory",
        "inventory_id": inventory_id,
        "workspace_id": recovered_manifest.get("workspace_id"),
        "build_id": build_id,
        "source_authority_sha256": recovered_manifest.get(
            "source_authority_sha256"
        ),
        "readable_jar_sha256": recovered_manifest.get(
            "readable_jar_sha256"
        ),
        "namespace_id": recovered_manifest.get("namespace_id"),
        "source_tree_sha256": tree_sha,
        "target_package": target_package.rstrip("/"),
        "summary": {
            "java_files": java_count,
            "methods": len(method_rows),
            "methods_canonical": sum(
                1
                for row in method_rows
                if row["canonical_method_id"] is not None
            ),
            "methods_ambiguous": ambiguous_method_count,
            "source_symbols": len(symbols),
            "parameters": sum(
                1 for row in symbols if row["kind"] == "parameter"
            ),
            "locals": sum(
                1
                for row in symbols
                if row["kind"] not in {
                    "parameter",
                    "catch",
                    "resource",
                    "enhanced_for",
                    "lambda_parameter",
                }
            ),
            "catch_variables": sum(
                1 for row in symbols if row["kind"] == "catch"
            ),
            "resource_variables": sum(
                1 for row in symbols if row["kind"] == "resource"
            ),
            "enhanced_for_variables": sum(
                1 for row in symbols if row["kind"] == "enhanced_for"
            ),
            "lambda_parameters": sum(
                1
                for row in symbols if row["kind"] == "lambda_parameter"
            ),
            "orphan_variables": len(orphan_variables),
        },
        "methods": method_rows,
        "symbols": symbols,
        "orphan_variables": orphan_variables,
    }


def write_source_symbol_inventory(
    inventory: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            inventory,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
