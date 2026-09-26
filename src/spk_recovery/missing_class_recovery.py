from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .decompiler import DecompilerError, run_decompiler
from .javac_class_triage import (
    JavacClassTriageError,
    _readable_kind,
    _readable_structure,
    _source_declared_types,
    analyze_unresolved_classes,
)
from .javac_variable_triage import _load_classes, _sha256_file, _stable_digest
from .source_digest import source_tree_digest
from .source_normalization import (
    SourceNormalizationError,
    normalize_procyon_source,
)
from .source_workspace import (
    SourceWorkspaceError,
    _extract_class_context,
    _project_prefixes,
)


class MissingClassRecoveryError(ValueError):
    pass


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _candidate_is_project(
    internal_name: str,
    prefixes: list[str],
) -> bool:
    entry = internal_name + ".class"
    return any(entry.startswith(prefix) for prefix in prefixes)


def build_missing_class_recovery_plan(
    diagnostic_report: dict[str, Any],
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    source_root: Path,
    *,
    expected_candidate_count: int | None = None,
    include_identifiers: bool = False,
) -> dict[str, Any]:
    readable_jar = readable_jar.resolve()
    source_root = source_root.resolve()

    if readable_manifest.get("kind") != "readable_client_build_manifest":
        raise MissingClassRecoveryError(
            "unsupported readable-client manifest"
        )
    expected_jar_sha = str(
        readable_manifest.get("output_sha256", "")
    ).lower()
    actual_jar_sha = _sha256_file(readable_jar)
    if expected_jar_sha != actual_jar_sha.lower():
        raise MissingClassRecoveryError(
            "readable JAR SHA-256 does not match manifest"
        )

    try:
        prefixes = _project_prefixes(readable_manifest)
        triage = analyze_unresolved_classes(
            diagnostic_report,
            readable_jar,
            source_root,
            include_identifiers=True,
        )
    except (SourceWorkspaceError, JavacClassTriageError) as exc:
        raise MissingClassRecoveryError(str(exc)) from exc

    classes = _load_classes(readable_jar)
    source_declared, _source_declared_files = _source_declared_types(
        source_root
    )

    evidence: dict[str, dict[str, Any]] = {}
    for row in triage["diagnostics"]:
        if (
            row.get("proof_class") != "java_visible_exact_class"
            or row.get("source_materialization")
            != "missing_exact_declaration"
        ):
            continue

        candidates = row.get("visible_candidates")
        if not isinstance(candidates, list) or len(candidates) != 1:
            raise MissingClassRecoveryError(
                "missing declaration row is not bound to one exact class"
            )
        candidate = str(candidates[0])
        bucket = evidence.setdefault(
            candidate,
            {
                "diagnostic_count": 0,
                "file_ids": set(),
                "symbol_ids": set(),
            },
        )
        bucket["diagnostic_count"] += 1
        if row.get("file_id") is not None:
            bucket["file_ids"].add(str(row["file_id"]))
        if row.get("symbol_id") is not None:
            bucket["symbol_ids"].add(str(row["symbol_id"]))

    candidates = sorted(evidence)
    if expected_candidate_count is not None and (
        len(candidates) != expected_candidate_count
    ):
        raise MissingClassRecoveryError(
            "missing class candidate count mismatch: "
            f"{len(candidates)} != {expected_candidate_count}"
        )
    if not candidates:
        raise MissingClassRecoveryError(
            "no exact missing class declarations found"
        )

    private_rows: list[dict[str, Any]] = []
    public_rows: list[dict[str, Any]] = []

    with zipfile.ZipFile(readable_jar) as z:
        names = set(z.namelist())
        for ordinal, candidate in enumerate(candidates, start=1):
            class_row = classes.get(candidate)
            if class_row is None:
                raise MissingClassRecoveryError(
                    "candidate missing from readable class inventory"
                )

            structure = _readable_structure(class_row)
            kind = _readable_kind(class_row)
            synthetic = bool(int(class_row.get("access", 0)) & 0x1000)
            if structure != "top_level":
                raise MissingClassRecoveryError(
                    "R8Q candidate is not top-level"
                )
            if synthetic:
                raise MissingClassRecoveryError(
                    "R8Q candidate is synthetic"
                )
            if kind not in {"class", "interface"}:
                raise MissingClassRecoveryError(
                    "R8Q candidate kind is not class/interface"
                )
            if candidate in source_declared:
                raise MissingClassRecoveryError(
                    "R8Q candidate unexpectedly exists in source declarations"
                )

            entry = candidate + ".class"
            if entry not in names:
                raise MissingClassRecoveryError(
                    "candidate class entry missing from readable JAR"
                )
            class_bytes = z.read(entry)
            class_sha = _sha256_bytes(class_bytes)

            target_rel = candidate + ".java"
            target = source_root / Path(target_rel)
            if target.is_file():
                target_state = "occupied_missing_exact_declaration"
                target_sha = _sha256_file(target)
            elif target.exists():
                raise MissingClassRecoveryError(
                    "expected source target exists but is not a file"
                )
            else:
                target_state = "absent"
                target_sha = None

            is_project = _candidate_is_project(
                candidate,
                prefixes,
            )
            candidate_id = f"MCLASS_{ordinal:06d}"
            evidence_row = evidence[candidate]

            public_rows.append(
                {
                    "candidate_id": candidate_id,
                    "diagnostic_count": int(
                        evidence_row["diagnostic_count"]
                    ),
                    "affected_files": len(evidence_row["file_ids"]),
                    "symbol_ids": sorted(evidence_row["symbol_ids"]),
                    "structure": structure,
                    "kind": kind,
                    "synthetic": synthetic,
                    "project_candidate": is_project,
                    "target_state": target_state,
                }
            )
            private_rows.append(
                {
                    **public_rows[-1],
                    "internal_name": candidate,
                    "class_entry": entry,
                    "class_entry_sha256": class_sha,
                    "expected_target_path": target_rel,
                    "target_sha256": target_sha,
                }
            )

    target_states = Counter(
        row["target_state"]
        for row in public_rows
    )
    kinds = Counter(row["kind"] for row in public_rows)
    project_count = sum(
        1 for row in public_rows if row["project_candidate"]
    )

    identity_material = [
        {
            "internal_name": row["internal_name"],
            "class_entry_sha256": row["class_entry_sha256"],
            "expected_target_path": row["expected_target_path"],
            "target_state": row["target_state"],
            "target_sha256": row["target_sha256"],
        }
        for row in private_rows
    ]
    material = {
        "diagnostic_frontier_id": triage["diagnostic_frontier_id"],
        "readable_jar_sha256": actual_jar_sha,
        "source_tree_sha256": triage["source_tree_sha256"],
        "project_source_prefixes": prefixes,
        "candidate_identity_material": identity_material,
    }
    plan_id = (
        "MISSINGCLASSPLAN_"
        + _stable_digest(material)[:20].upper()
    )

    report = {
        "schema_version": 1,
        "kind": "missing_top_level_class_recovery_plan",
        "plan_id": plan_id,
        "diagnostic_frontier_id": triage[
            "diagnostic_frontier_id"
        ],
        "class_triage_report_id": triage["report_id"],
        "readable_jar_sha256": actual_jar_sha,
        "source_tree_sha256": triage["source_tree_sha256"],
        "project_source_prefixes": prefixes,
        "summary": {
            "candidate_count": len(public_rows),
            "project_candidate_count": project_count,
            "nonproject_candidate_count": (
                len(public_rows) - project_count
            ),
            "target_states": dict(sorted(target_states.items())),
            "kinds": dict(sorted(kinds.items())),
            "synthetic_count": sum(
                1 for row in public_rows if row["synthetic"]
            ),
            "diagnostic_count": sum(
                int(row["diagnostic_count"])
                for row in public_rows
            ),
        },
        "candidates": (
            private_rows if include_identifiers else public_rows
        ),
        "identifiers_included": include_identifiers,
    }
    return report


def stage_missing_class_recovery(
    diagnostic_report: dict[str, Any],
    readable_manifest: dict[str, Any],
    readable_jar: Path,
    source_root: Path,
    decompiler_jar: Path,
    *,
    expected_decompiler_sha256: str,
    stage_dir: Path,
    expected_candidate_count: int | None = None,
    java_command: str = "java",
    include_identifiers: bool = False,
) -> dict[str, Any]:
    private_plan = build_missing_class_recovery_plan(
        diagnostic_report,
        readable_manifest,
        readable_jar,
        source_root,
        expected_candidate_count=expected_candidate_count,
        include_identifiers=True,
    )
    summary = private_plan["summary"]
    if (
        summary["project_candidate_count"]
        != summary["candidate_count"]
    ):
        raise MissingClassRecoveryError(
            "R8Q source recovery includes non-project candidates"
        )

    stage_dir = stage_dir.resolve()
    if stage_dir.exists() and any(stage_dir.iterdir()):
        raise MissingClassRecoveryError(
            "R8Q stage directory must be empty"
        )
    stage_dir.mkdir(parents=True, exist_ok=True)

    context_dir = stage_dir / "class-context"
    source_dir = stage_dir / "source"

    try:
        prefixes = _project_prefixes(readable_manifest)
        _all_project_files, _all_project_entries = (
            _extract_class_context(
                readable_jar,
                context_dir,
                prefixes,
            )
        )
    except SourceWorkspaceError as exc:
        raise MissingClassRecoveryError(str(exc)) from exc

    selected_files: list[Path] = []
    selected_entries: list[str] = []
    for row in private_plan["candidates"]:
        entry = str(row["class_entry"])
        path = context_dir / Path(entry)
        if not path.is_file():
            raise MissingClassRecoveryError(
                "candidate class missing from extracted resolver context"
            )
        selected_files.append(path)
        selected_entries.append(entry)

    try:
        result = run_decompiler(
            readable_jar,
            decompiler_jar,
            expected_decompiler_sha256=expected_decompiler_sha256,
            engine="procyon",
            out_dir=source_dir,
            clean_out=False,
            java_command=java_command,
            input_class_files=selected_files,
        )
    except DecompilerError as exc:
        raise MissingClassRecoveryError(str(exc)) from exc

    expected_count = int(summary["candidate_count"])
    if int(result.get("selected_class_file_count", -1)) != expected_count:
        raise MissingClassRecoveryError(
            "selective Procyon input count drifted"
        )
    if int(result.get("java_file_count", -1)) != expected_count:
        raise MissingClassRecoveryError(
            "selective Procyon did not materialize one source per candidate"
        )

    try:
        normalization = normalize_procyon_source(
            source_dir,
            readable_jar,
        )
    except SourceNormalizationError as exc:
        raise MissingClassRecoveryError(str(exc)) from exc

    declared, declared_files = _source_declared_types(source_dir)
    stage_rows: list[dict[str, Any]] = []
    private_stage_rows: list[dict[str, Any]] = []

    for public_row, private_row in zip(
        build_missing_class_recovery_plan(
            diagnostic_report,
            readable_manifest,
            readable_jar,
            source_root,
            expected_candidate_count=expected_candidate_count,
            include_identifiers=False,
        )["candidates"],
        private_plan["candidates"],
        strict=True,
    ):
        candidate = str(private_row["internal_name"])
        if candidate not in declared:
            raise MissingClassRecoveryError(
                "selective Procyon output lacks exact candidate declaration"
            )
        declared_rel = declared_files.get(candidate)
        expected_rel = str(private_row["expected_target_path"])
        if declared_rel != expected_rel:
            raise MissingClassRecoveryError(
                "selective Procyon declaration path does not match expected target"
            )
        staged_path = source_dir / Path(expected_rel)
        if not staged_path.is_file():
            raise MissingClassRecoveryError(
                "verified staged declaration file is missing"
            )
        staged_sha = _sha256_file(staged_path)

        stage_rows.append(
            {
                "candidate_id": public_row["candidate_id"],
                "materialized": True,
                "target_state": public_row["target_state"],
                "kind": public_row["kind"],
                "project_candidate": True,
            }
        )
        private_stage_rows.append(
            {
                **stage_rows[-1],
                "internal_name": candidate,
                "staged_source_path": expected_rel,
                "staged_source_sha256": staged_sha,
            }
        )

    tree_sha, java_count, source_bytes = source_tree_digest(
        source_dir
    )
    stage_material = {
        "plan_id": private_plan["plan_id"],
        "decompiler_sha256": result["decompiler_sha256"],
        "normalization_id": normalization["normalization_id"],
        "staged_source_tree_sha256": tree_sha,
        "candidate_material": [
            {
                "internal_name": row["internal_name"],
                "staged_source_path": row["staged_source_path"],
                "staged_source_sha256": row["staged_source_sha256"],
            }
            for row in private_stage_rows
        ],
    }
    stage_id = (
        "MISSINGCLASSSTAGE_"
        + _stable_digest(stage_material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "missing_top_level_class_recovery_stage",
        "stage_id": stage_id,
        "plan_id": private_plan["plan_id"],
        "readable_jar_sha256": private_plan[
            "readable_jar_sha256"
        ],
        "source_tree_sha256": private_plan[
            "source_tree_sha256"
        ],
        "decompiler_sha256": result["decompiler_sha256"],
        "normalization_id": normalization["normalization_id"],
        "summary": {
            "candidate_count": expected_count,
            "materialized_count": len(stage_rows),
            "java_file_count": java_count,
            "source_bytes": source_bytes,
            "decompiler_batch_count": int(
                result.get("batch_count", -1)
            ),
            "normalization_action_count": int(
                normalization.get("summary", {}).get(
                    "action_count",
                    -1,
                )
            ),
            "target_states": private_plan["summary"][
                "target_states"
            ],
        },
        "candidates": (
            private_stage_rows
            if include_identifiers
            else stage_rows
        ),
        "identifiers_included": include_identifiers,
    }


def write_recovery_report(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
