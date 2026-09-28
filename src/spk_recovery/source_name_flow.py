from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any


class SourceNameFlowError(ValueError):
    pass


_RELATION_CONFIDENCE = {
    "direct_this_field_assignment": 0.96,
    "direct_this_field_initializer": 0.94,
}


def _source_tree_digest(root: Path) -> str:
    files = sorted(root.rglob("*.java"))
    h = hashlib.sha256()
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def _helper_source() -> Path:
    path = (
        Path(__file__).resolve().parent
        / "java"
        / "SourceNameFlowScanner.java"
    )
    if not path.is_file():
        raise SourceNameFlowError(
            f"missing source-name flow helper: {path}"
        )
    return path


def _require(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise SourceNameFlowError(
            f"required executable not found on PATH: {name}"
        )
    return found


def _decode(value: str) -> str:
    pad = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(
        (value + pad).encode("ascii")
    ).decode("utf-8")


def _scan_direct_this_flows(
    source_root: Path,
    *,
    java_command: str,
    javac_command: str,
) -> list[dict[str, Any]]:
    java = _require(java_command)
    javac = _require(javac_command)

    with tempfile.TemporaryDirectory(
        prefix="spk-source-name-flow-"
    ) as td:
        classes = Path(td) / "classes"
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
            raise SourceNameFlowError(
                "source-name flow helper compilation failed:\n"
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
                "SourceNameFlowScanner",
                str(source_root),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise SourceNameFlowError(
                "source-name flow scan failed:\n"
                + proc.stdout
                + proc.stderr
            )

    rows: list[dict[str, Any]] = []
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) != 9 or parts[0] not in {"A", "I"}:
            raise SourceNameFlowError(
                f"unexpected flow scanner row: {raw!r}"
            )

        relation = (
            "direct_this_field_assignment"
            if parts[0] == "A"
            else "direct_this_field_initializer"
        )
        rows.append(
            {
                "relation": relation,
                "source_file": _decode(parts[1]),
                "owner_internal_name": _decode(parts[2]),
                "method_name": _decode(parts[3]),
                "method_arity": int(parts[4]),
                "method_start": int(parts[5]),
                "field_name": _decode(parts[6]),
                "symbol_name": _decode(parts[7]),
                "position": int(parts[8]),
            }
        )

    rows.sort(
        key=lambda row: (
            row["source_file"],
            row["method_start"],
            row["position"],
            row["relation"],
            row["field_name"],
            row["symbol_name"],
        )
    )
    return rows


def _accepted_fields(
    member_lineage: dict[str, Any],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    out: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ] = {}
    for row in member_lineage.get("members", []):
        if not isinstance(row, dict):
            continue
        if row.get("kind") != "field":
            continue
        if row.get("semantic_status") != "ACCEPTED":
            continue
        owner = row.get("owner_logical_id")
        name = row.get("semantic_name")
        if (
            isinstance(owner, str)
            and owner
            and isinstance(name, str)
            and name
        ):
            out.setdefault((owner, name), []).append(row)
    return out


def build_source_name_flow_evidence(
    inventory: dict[str, Any],
    member_lineage: dict[str, Any],
    source_root: Path,
    *,
    java_command: str = "java",
    javac_command: str = "javac",
) -> dict[str, Any]:
    """Build non-canonical direct-flow evidence for source-name research.

    Supported exact relations are a plain source symbol assigned into
    this.acceptedField and an ordinary local initialized directly from
    this.acceptedField. The field must have ACCEPTED canonical semantics on
    the same canonical owner. Ambiguous relations are withheld.
    """
    if (
        inventory.get("schema_version") != 1
        or inventory.get("kind") != "source_symbol_inventory"
    ):
        raise SourceNameFlowError(
            "unsupported source symbol inventory"
        )
    if (
        member_lineage.get("schema_version") != 1
        or member_lineage.get("kind") != "member_lineage"
    ):
        raise SourceNameFlowError(
            "unsupported member lineage"
        )

    inventory_id = inventory.get("inventory_id")
    tree_sha = inventory.get("source_tree_sha256")
    if not isinstance(inventory_id, str) or not inventory_id:
        raise SourceNameFlowError(
            "source symbol inventory has no inventory_id"
        )
    if not isinstance(tree_sha, str) or not tree_sha:
        raise SourceNameFlowError(
            "source symbol inventory has no source_tree_sha256"
        )

    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise SourceNameFlowError(
            f"source root does not exist: {source_root}"
        )
    actual_tree = _source_tree_digest(source_root)
    if actual_tree.lower() != tree_sha.lower():
        raise SourceNameFlowError(
            "source tree SHA-256 does not match source symbol inventory"
        )

    method_lookup = {
        (
            str(row.get("source_file", "")),
            str(row.get("owner_internal_name", "")),
            str(row.get("name", "")),
            int(row.get("arity", -1)),
            int(row.get("start", -1)),
        ): row
        for row in inventory.get("methods", [])
        if isinstance(row, dict)
        and isinstance(row.get("arity"), int)
        and not isinstance(row.get("arity"), bool)
        and isinstance(row.get("start"), int)
        and not isinstance(row.get("start"), bool)
    }

    symbols_by_method_name: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ] = {}
    symbols_by_method_declaration: dict[
        tuple[str, int, str],
        list[dict[str, Any]],
    ] = {}
    for row in inventory.get("symbols", []):
        if not isinstance(row, dict):
            continue
        source_method_id = row.get("source_method_id")
        current_name = row.get("current_name")
        start = row.get("start")
        if (
            isinstance(source_method_id, str)
            and source_method_id
            and isinstance(current_name, str)
            and current_name
        ):
            symbols_by_method_name.setdefault(
                (source_method_id, current_name),
                [],
            ).append(row)
            if (
                isinstance(start, int)
                and not isinstance(start, bool)
            ):
                symbols_by_method_declaration.setdefault(
                    (
                        source_method_id,
                        start,
                        current_name,
                    ),
                    [],
                ).append(row)

    fields = _accepted_fields(member_lineage)
    scanned = _scan_direct_this_flows(
        source_root,
        java_command=java_command,
        javac_command=javac_command,
    )

    observations_by_symbol: dict[
        str,
        list[dict[str, Any]],
    ] = {}
    unmatched_methods = 0
    unaccepted_or_ambiguous_fields = 0
    ambiguous_or_missing_symbols = 0
    excluded_symbol_kinds = 0

    for row in scanned:
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
            unmatched_methods += 1
            continue

        owner_id = method.get("owner_logical_id")
        if not isinstance(owner_id, str) or not owner_id:
            unmatched_methods += 1
            continue

        field_hits = fields.get(
            (owner_id, row["field_name"]),
            [],
        )
        if len(field_hits) != 1:
            unaccepted_or_ambiguous_fields += 1
            continue
        field = field_hits[0]

        source_method_id = method.get("source_method_id")
        if not isinstance(source_method_id, str):
            unmatched_methods += 1
            continue

        if row["relation"] == "direct_this_field_assignment":
            symbol_hits = symbols_by_method_name.get(
                (
                    source_method_id,
                    row["symbol_name"],
                ),
                [],
            )
            allowed_kinds = {"parameter", "local"}
        else:
            symbol_hits = symbols_by_method_declaration.get(
                (
                    source_method_id,
                    row["position"],
                    row["symbol_name"],
                ),
                [],
            )
            allowed_kinds = {"local"}

        if len(symbol_hits) != 1:
            ambiguous_or_missing_symbols += 1
            continue
        symbol = symbol_hits[0]
        if symbol.get("kind") not in allowed_kinds:
            excluded_symbol_kinds += 1
            continue

        symbol_id = symbol.get("source_symbol_id")
        field_id = field.get("member_id")
        field_name = field.get("semantic_name")
        if (
            not isinstance(symbol_id, str)
            or not symbol_id
            or not isinstance(field_id, str)
            or not field_id
            or not isinstance(field_name, str)
            or not field_name
        ):
            continue

        observations_by_symbol.setdefault(
            symbol_id,
            [],
        ).append(
            {
                "source_symbol_id": symbol_id,
                "source_method_id": source_method_id,
                "canonical_method_id": method.get(
                    "canonical_method_id"
                ),
                "owner_logical_id": owner_id,
                "source_file": row["source_file"],
                "position": row["position"],
                "relation": row["relation"],
                "field_member_id": field_id,
                "field_semantic_name": field_name,
                "source_current_name": row[
                    "symbol_name"
                ],
            }
        )

    bindings: list[dict[str, Any]] = []
    ambiguities: list[dict[str, Any]] = []
    for symbol_id in sorted(observations_by_symbol):
        observations = observations_by_symbol[symbol_id]
        targets = {
            (
                str(row["field_member_id"]),
                str(row["field_semantic_name"]),
            )
            for row in observations
        }
        if len(targets) != 1:
            ambiguities.append(
                {
                    "source_symbol_id": symbol_id,
                    "reason": (
                        "source_symbol_maps_to_multiple_accepted_fields"
                    ),
                    "targets": [
                        {
                            "field_member_id": member_id,
                            "field_semantic_name": semantic,
                        }
                        for member_id, semantic in sorted(
                            targets
                        )
                    ],
                    "observation_count": len(
                        observations
                    ),
                }
            )
            continue

        field_member_id, field_semantic_name = next(
            iter(targets)
        )
        first = observations[0]
        relations = sorted(
            {
                str(row["relation"])
                for row in observations
            }
        )
        confidence = max(
            _RELATION_CONFIDENCE[relation]
            for relation in relations
        )
        bindings.append(
            {
                "source_symbol_id": symbol_id,
                "source_method_id": first[
                    "source_method_id"
                ],
                "canonical_method_id": first[
                    "canonical_method_id"
                ],
                "owner_logical_id": first[
                    "owner_logical_id"
                ],
                "field_member_id": field_member_id,
                "field_semantic_name": (
                    field_semantic_name
                ),
                "source_current_name": first[
                    "source_current_name"
                ],
                "confidence": confidence,
                "relations": relations,
                "observation_count": len(
                    observations
                ),
                "observations": [
                    {
                        "source_file": row[
                            "source_file"
                        ],
                        "position": row["position"],
                        "relation": row["relation"],
                    }
                    for row in observations
                ],
            }
        )

    claims: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ] = {}
    for binding in bindings:
        claims.setdefault(
            (
                str(binding["source_method_id"]),
                str(binding["field_member_id"]),
            ),
            [],
        ).append(binding)

    contested_symbols: set[str] = set()
    for (
        source_method_id,
        field_member_id,
    ), rows in sorted(claims.items()):
        symbols = sorted(
            {
                str(row["source_symbol_id"])
                for row in rows
            }
        )
        if len(symbols) <= 1:
            continue
        contested_symbols.update(symbols)
        ambiguities.append(
            {
                "source_method_id": source_method_id,
                "field_member_id": field_member_id,
                "reason": (
                    "accepted_field_maps_to_multiple_source_symbols"
                ),
                "source_symbol_ids": symbols,
            }
        )

    if contested_symbols:
        bindings = [
            row
            for row in bindings
            if row["source_symbol_id"]
            not in contested_symbols
        ]

    material = {
        "inventory_id": inventory_id,
        "source_tree_sha256": tree_sha,
        "bindings": bindings,
        "ambiguities": ambiguities,
    }
    flow_id = (
        "SRCFLOW_"
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
        "kind": "source_name_flow_evidence",
        "canonical": False,
        "flow_id": flow_id,
        "inventory_id": inventory_id,
        "source_tree_sha256": tree_sha,
        "summary": {
            "direct_this_field_assignments": sum(
                1
                for row in scanned
                if row["relation"]
                == "direct_this_field_assignment"
            ),
            "direct_this_field_initializers": sum(
                1
                for row in scanned
                if row["relation"]
                == "direct_this_field_initializer"
            ),
            "matched_bindings": len(bindings),
            "ambiguous_bindings": len(
                ambiguities
            ),
            "unmatched_methods": unmatched_methods,
            "unaccepted_or_ambiguous_fields": (
                unaccepted_or_ambiguous_fields
            ),
            "ambiguous_or_missing_symbols": (
                ambiguous_or_missing_symbols
            ),
            "excluded_symbol_kinds": (
                excluded_symbol_kinds
            ),
        },
        "bindings": bindings,
        "ambiguities": ambiguities,
    }
