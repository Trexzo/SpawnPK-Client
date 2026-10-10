"""Recompute a private recovered-Java frontier from two SHA-pinned JARs.

This is a measurement / drift veto, not a class or source acceptance gate.
No original class/member coordinates, decompiled Java, or raw bytecode output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from zipfile import BadZipFile, ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .source_class_method_matrix import (
    ClassMethodMatrixError,
    build_class_method_matrix,
)


class SourceFrontierReplayError(ValueError):
    """An original/candidate source frontier cannot be independently proven."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise SourceFrontierReplayError(code)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_hash(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def _classfile_pin(path: Path, entry: str) -> str:
    with ZipFile(path) as archive:
        matches = [i for i in archive.infolist() if i.filename == entry]
        _require(
            len(matches) == 1 and not matches[0].is_dir(),
            "CLASSFILE_ENTRY_MISSING_OR_DUPLICATE",
        )
        data = archive.read(matches[0])
    _require(data[:4] == b"\xca\xfe\xba\xbe", "INVALID_CLASSFILE_MAGIC")
    return _sha(data)


def _recorded_snapshot_check(
    current: dict[str, Any], expected: dict[str, Any]
) -> None:
    """Only compare directly remeasurable properties; never certify history.

    R24's seven historical instruction-level claims used a different
    verification gate. Do not silently equate them to later R31 strict
    StackMapTable method-body parity.
    """
    _require(expected.get("schema_version") == 1, "FRONTIER_SCHEMA_MISMATCH")
    _require(expected.get("owner_lineage_accepted") is False,
             "FRONTIER_AUTHORITY_UNEXPECTED")
    _require(expected.get("source_equivalence_certified") is False,
             "FRONTIER_SOURCE_EQUIVALENCE_UNEXPECTED")
    _require(expected.get("client_source_published") is False,
             "FRONTIER_PUBLICATION_UNEXPECTED")
    _require(
        expected.get("original_client_jar_sha256")
        == current["original_client_jar_sha256"],
        "FRONTIER_ORIGINAL_JAR_PIN_DRIFT",
    )
    source = expected.get("private_candidate", {})
    _require(isinstance(source, dict), "FRONTIER_CANDIDATE_MISSING")
    for key in (
        "compiled_class_sha256",
        "original_field_declarations",
        "candidate_field_declarations",
        "original_method_declarations",
        "candidate_method_declarations",
        "missing_original_field_declarations",
        "extra_candidate_field_declarations",
        "shared_field_declarations",
        "exact_field_declaration_metadata",
        "changed_field_declaration_metadata",
        "original_classfile_major",
        "candidate_classfile_major",
        "class_access_flags_equal",
        "superclass_equal",
        "ordered_interfaces_equal",
    ):
        _require(
            source.get(key) == current["measured"][key],
            "FRONTIER_REMEASURED_DRIFT_" + key.upper(),
        )


def replay_frontier(
    original_jar: Path, candidate_jar: Path, *,
    original_sha256: str, candidate_sha256: str, class_entry: str,
    frontier_path: Path | None = None,
) -> dict[str, Any]:
    """Recompute strict method/field/header evidence, check recorded pins.

    All inputs stay local and are never modified. The class name is an
    explicit caller input, never recovered or accepted automatically.
    """
    paths = (Path(original_jar), Path(candidate_jar))
    for path, expected in zip(paths, (original_sha256, candidate_sha256)):
        _require(
            type(expected) is str
            and re.fullmatch(r"[0-9a-fA-F]{64}", expected) is not None,
            "INVALID_JAR_PIN",
        )
        _require(path.is_file() and not path.is_symlink(), "MISSING_OR_SYMLINK_JAR")
        _require(_file_hash(path).lower() == expected.lower(),
                 "ORIGINAL_OR_CANDIDATE_JAR_PIN_MISMATCH")
    _require(
        isinstance(class_entry, str)
        and class_entry.endswith(".class")
        and not class_entry.startswith("/")
        and "\\" not in class_entry
        and all(p not in ("", ".", "..") and ":" not in p
                for p in class_entry.split("/")),
        "INVALID_CLASS_ENTRY",
    )
    try:
        original_class_sha = _classfile_pin(paths[0], class_entry)
        candidate_class_sha = _classfile_pin(paths[1], class_entry)
        matrix = build_class_method_matrix(
            paths[0], paths[1],
            original_sha256=original_sha256,
            candidate_sha256=candidate_sha256,
            class_entry=class_entry,
        )
        original_profile = profile_jar_class(paths[0], class_entry)
        candidate_profile = profile_jar_class(paths[1], class_entry)
    except (
        BadZipFile, OSError, BytecodeProfileError,
        ClassMethodMatrixError, KeyError, IndexError,
    ) as exc:
        raise SourceFrontierReplayError("FRONTIER_MATRIX_OR_JAR_UNEVALUABLE") from None
    _require(
        _file_hash(paths[0]).lower() == original_sha256.lower()
        and _file_hash(paths[1]).lower() == candidate_sha256.lower(),
        "FRONTIER_INPUT_CHANGED_DURING_REPLAY",
    )

    fields = matrix["field_counts"]
    header = matrix["class_header"]
    _require(
        "original_declared_field_count" in matrix
        and "candidate_declared_field_count" in matrix
        and "class_header_exact" in header,
        "FRONTIER_REQUIRED_EVIDENCE_MISSING",
    )
    measured = {
        "compiled_class_sha256": candidate_class_sha,
        "original_class_sha256": original_class_sha,
        "original_field_declarations": matrix["original_declared_field_count"],
        "candidate_field_declarations": matrix["candidate_declared_field_count"],
        "original_method_declarations": matrix["original_declared_method_count"],
        "candidate_method_declarations": matrix["candidate_declared_method_count"],
        "missing_original_field_declarations": fields["missing_field"],
        "extra_candidate_field_declarations": fields["extra_field"],
        "shared_field_declarations": (
            fields["shared_exact"] + fields["shared_metadata_difference"]
        ),
        "exact_field_declaration_metadata": fields["shared_exact"],
        "changed_field_declaration_metadata": fields["shared_metadata_difference"],
        "original_classfile_major": original_profile["classfile_major"],
        "candidate_classfile_major": candidate_profile["classfile_major"],
        "class_access_flags_equal": header["checks"]["access_flags"],
        "superclass_equal": header["checks"]["direct_superclass"],
        "ordered_interfaces_equal": header["checks"]["ordered_interfaces"],
        "strict_method_body_instruction_parity_count": matrix["counts"]["instruction_parity"],
        "strict_method_body_difference_count": matrix["counts"]["body_difference"],
        "method_declarations_missing": matrix["counts"]["missing_method"],
        "method_declarations_extra": matrix["counts"]["extra_method"],
    }
    core = {
        "schema_version": 1,
        "kind": "v309_private_recovery_frontier_replay",
        "research_only": True,
        "original_client_jar_sha256": original_sha256.lower(),
        "candidate_jar_sha256": candidate_sha256.lower(),
        "canonical_identity_accepted": False,
        "source_equivalence_certified": False,
        "runtime_equivalence_certified": False,
        "class_header": header,
        "method_counts": matrix["counts"],
        "field_counts": fields,
        "measured": measured,
        "historical_R24_seven_method_claims_recertified": False,
    }
    if frontier_path is not None:
        path = Path(frontier_path)
        _require(path.is_file() and not path.is_symlink(),
                 "FRONTIER_RECORD_NOT_FOUND")
        try:
            expected = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SourceFrontierReplayError("FRONTIER_RECORD_INVALID") from None
        _recorded_snapshot_check(core, expected)
        core["recorded_frontier_remeasurable_dimensions_match"] = True
    fingerprint = _sha(json.dumps(
        core, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8"))[:20].upper()
    return {"report_id": "SOURCEFRONTIER_" + fingerprint, **core}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("candidate_jar", type=Path)
    parser.add_argument("class_entry")
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--frontier", type=Path,
                        help="Optional current R37 research frontier JSON")
    parser.add_argument("--out", type=Path, help="New private JSON; no overwrite")
    args = parser.parse_args(argv)
    try:
        report = replay_frontier(
            args.original_jar, args.candidate_jar,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
            class_entry=args.class_entry,
            frontier_path=args.frontier,
        )
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as fh:
                json.dump(report, fh, sort_keys=True, indent=2)
                fh.write("\n")
        # Public terminal output contains only aggregate research evidence.
        print(json.dumps({
            "report_id": report["report_id"],
            "measured": {
                k: v for k, v in report["measured"].items()
                if "sha256" not in k
            },
            "recorded_frontier_remeasurable_dimensions_match":
                report.get("recorded_frontier_remeasurable_dimensions_match", False),
            "source_equivalence_certified": False,
        }, sort_keys=True))
    except SourceFrontierReplayError as exc:
        parser.error(str(exc))
    except (OSError, ValueError):
        parser.error("FRONTIER_REPLAY_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
