"""Fail-closed, read-only JVM source-method parity research.

This is NOT a canonical identity proof or full source equivalence. It
compares resolved StackMapTable frames but does not certify JVM verifier
semantics, annotations, implementation dependencies or other Code attributes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class


class MethodParityError(ValueError):
    """Malformed or unsupported evidence must be rejected, not compared."""


_CP_LOCATION_KEYS = frozenset({
    "constant_pool_index", "reference_index", "bootstrap_method_ref", "index",
})
_SAFE_LDC_TAGS = frozenset({3, 4, 5, 6, 7, 8})
_SAFE_BSM_ARGUMENT_KINDS = frozenset({
    "method_handle", "method_type", "class", "string", "constant",
})
_LOCAL_OPS = set(range(0x15, 0x1A)) | set(range(0x36, 0x3B))
_BRANCH_OPS = set(range(0x99, 0xA9)) | {0xC6, 0xC7, 0xC8, 0xC9}
_FIELD_OPS = set(range(0xB2, 0xB6))
_INVOKE_OPS = set(range(0xB6, 0xBA))
_TYPE_OPS = {0xBB, 0xBD, 0xC0, 0xC1, 0xC5}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MethodParityError(message)


def _strip_cp_locations(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_cp_locations(item)
            for key, item in sorted(value.items())
            if key not in _CP_LOCATION_KEYS
        }
    if isinstance(value, list):
        return [_strip_cp_locations(item) for item in value]
    return value


def _bootstrap_at(profile: dict, index: Any) -> dict:
    _require(type(index) is int and index >= 0, "INVALID_BOOTSTRAP_INDEX")
    rows = profile.get("bootstrap_methods", [])
    _require(isinstance(rows, list), "MALFORMED_BOOTSTRAP_TABLE")
    _require(index < len(rows), "MISSING_BOOTSTRAP_METHOD")
    bootstrap = rows[index]
    _require(
        isinstance(bootstrap, dict) and bootstrap.get("index") == index,
        "AMBIGUOUS_BOOTSTRAP_METHOD",
    )
    handle = bootstrap.get("bootstrap_method")
    _require(
        isinstance(handle, dict)
        and handle.get("target_kind") in ("method", "interface_method")
        and isinstance(handle.get("owner"), str)
        and isinstance(handle.get("name"), str)
        and isinstance(handle.get("descriptor"), str)
        and type(handle.get("reference_kind")) is int,
        "UNRESOLVED_BOOTSTRAP_HANDLE",
    )
    arguments = bootstrap.get("arguments")
    _require(isinstance(arguments, list), "MALFORMED_BOOTSTRAP_ARGUMENTS")
    for arg in arguments:
        _require(
            isinstance(arg, dict)
            and arg.get("kind") in _SAFE_BSM_ARGUMENT_KINDS,
            "UNSUPPORTED_BOOTSTRAP_ARGUMENT",
        )
        if arg["kind"] == "method_handle":
            target = arg.get("method_handle")
            _require(
                isinstance(target, dict)
                and isinstance(target.get("owner"), str)
                and isinstance(target.get("name"), str)
                and isinstance(target.get("descriptor"), str)
                and type(target.get("reference_kind")) is int,
                "UNRESOLVED_BOOTSTRAP_ARGUMENT_HANDLE",
            )
    return _strip_cp_locations({
        "bootstrap_method": handle,
        "arguments": arguments,
    })


def _normalized_instructions(profile: dict, method: dict) -> list[dict]:
    rows = method.get("instructions")
    _require(isinstance(rows, list) and bool(rows), "NO_DECODED_INSTRUCTIONS")
    _require(
        type(method.get("code_length")) is int and method["code_length"] > 0,
        "NO_CODE_ATTRIBUTE",
    )
    normalized = []
    offset = 0
    for row in rows:
        _require(isinstance(row, dict), "MALFORMED_INSTRUCTION")
        _require(
            row.get("offset") == offset
            and type(row.get("length")) is int
            and row["length"] > 0,
            "MALFORMED_INSTRUCTION_LAYOUT",
        )
        opcode_text = row.get("opcode")
        _require(
            isinstance(opcode_text, str)
            and len(opcode_text) == 4
            and opcode_text.startswith("0x"),
            "INVALID_INSTRUCTION_OPCODE",
        )
        try:
            opcode = int(opcode_text, 16)
        except ValueError as exc:
            raise MethodParityError("INVALID_INSTRUCTION_OPCODE") from exc
        _require(0 <= opcode <= 0xC9 and opcode != 0xA9, "UNSUPPORTED_OPCODE")
        # The existing parser emits a decoded operand for every supported
        # multi-byte opcode; a bare opcode/offset is never a safe witness.
        operand_keys = set(row)
        if row["length"] > 1:
            expected = set()
            if opcode in (0x10, 0x11):
                expected = {"int_constant"}
            elif opcode in (0x12, 0x13, 0x14):
                expected = {"constant_pool_tag"}
                _require(
                    row.get("constant_pool_tag") in _SAFE_LDC_TAGS,
                    "UNSUPPORTED_LDC_CONSTANT",
                )
                expected.add("constant")
                if row["constant_pool_tag"] in (3, 4, 5, 6):
                    expected = {"constant_pool_tag", "constant_raw_bits"}
            elif opcode in _LOCAL_OPS:
                expected = {"local_index"}
            elif opcode == 0x84:
                expected = {"local_index", "increment"}
            elif opcode in _BRANCH_OPS:
                expected = {"branch_target_offset"}
            elif opcode in _FIELD_OPS | _INVOKE_OPS:
                expected = {"owner", "name", "descriptor", "member_constant_pool_tag"}
            elif opcode == 0xBA:
                expected = {
                    "name", "descriptor", "bootstrap_method_attr_index",
                    "invokedynamic_reserved",
                }
            elif opcode in _TYPE_OPS:
                expected = {"type"}
                if opcode == 0xC5:
                    expected.add("array_dimensions")
            elif opcode == 0xBC:
                expected = {"array_primitive_atype"}
            elif opcode == 0xC4:
                expected = {"wide_opcode", "local_index"}
            elif opcode == 0xAA:
                expected = {
                    "switch_default_target_offset", "switch_low",
                    "switch_high", "switch_targets",
                }
            elif opcode == 0xAB:
                expected = {"switch_default_target_offset", "switch_pairs"}
            _require(bool(expected) and expected <= operand_keys,
                     "UNDECODED_INSTRUCTION_OPERAND")
        item = _strip_cp_locations(row)
        if opcode == 0xBA:
            _require(row["invokedynamic_reserved"] == 0,
                     "INVALID_INVOKEDYNAMIC_RESERVED")
            item["resolved_bootstrap"] = _bootstrap_at(
                profile, row["bootstrap_method_attr_index"]
            )
            item.pop("bootstrap_method_attr_index", None)
        normalized.append(item)
        offset += row["length"]

    _require(offset == method["code_length"], "INCOMPLETE_METHOD_DECODE")
    boundaries = {r["offset"] for r in rows}
    for row in normalized:
        if row["opcode"] in {f"0x{x:02x}" for x in _BRANCH_OPS}:
            _require(row["branch_target_offset"] in boundaries,
                     "INVALID_BRANCH_TARGET")
        if row["opcode"] in ("0xaa", "0xab"):
            targets = [row["switch_default_target_offset"]]
            if row["opcode"] == "0xaa":
                targets.extend(row["switch_targets"])
            else:
                targets.extend(t for _, t in row["switch_pairs"])
            _require(all(t in boundaries for t in targets),
                     "INVALID_SWITCH_TARGET")
    return normalized


def _exact_method(profile: dict, name: str, descriptor: str) -> dict:
    methods = profile.get("methods", [])
    _require(isinstance(methods, list), "MALFORMED_METHOD_TABLE")
    matches = [m for m in methods if m.get("name") == name
               and m.get("descriptor") == descriptor]
    _require(len(matches) == 1, "METHOD_NOT_UNIQUE")
    _require(matches[0].get("code_length") is not None, "METHOD_HAS_NO_CODE")
    return matches[0]


def compare_profiles(
    original: dict, candidate: dict, method_name: str, descriptor: str
) -> dict[str, Any]:
    """Return aggregate research findings, never a transferable mapping.

    Method and owner names, literals, CP tables, and source are excluded from
    the output. For internal research, run against explicitly chosen owners;
    this routine does NOT prove that those owners have accepted lineage.
    """
    _require(
        original.get("internal_name") == candidate.get("internal_name"),
        "OWNER_NAME_DIFFERS_NO_ACCEPTED_ALIAS",
    )
    old = _exact_method(original, method_name, descriptor)
    new = _exact_method(candidate, method_name, descriptor)
    for method in (old, new):
        for key in ("max_stack", "max_locals"):
            value = method.get(key)
            _require(
                type(value) is int and 0 <= value <= 65535,
                "MISSING_OR_INVALID_JVM_CODE_LIMIT",
            )
        _require(
            type(method.get("stackmap_table_present")) is bool
            and isinstance(method.get("stackmap_frames"), list),
            "STACKMAP_EVIDENCE_MISSING",
        )
    old_ops = _normalized_instructions(original, old)
    new_ops = _normalized_instructions(candidate, new)
    for method in (old, new):
        _require(isinstance(method.get("exception_handlers"), list),
                 "MISSING_EXCEPTION_HANDLERS")
    tests = {
        "access": old.get("access") == new.get("access"),
        "code_length": old["code_length"] == new["code_length"],
        "max_stack": old["max_stack"] == new["max_stack"],
        "max_locals": old["max_locals"] == new["max_locals"],
        "stackmap_table_present": (
            old["stackmap_table_present"] == new["stackmap_table_present"]
        ),
        "resolved_stackmap_frames": (
            old["stackmap_frames"] == new["stackmap_frames"]
        ),
        "decoded_instructions_and_resolved_cp": old_ops == new_ops,
        "exception_handlers": (
            old["exception_handlers"] == new["exception_handlers"]
        ),
    }
    core = {
        "schema_version": 1,
        "research_only": True,
        "canonical_identity_accepted": False,
        "full_method_equivalence_certified": False,
        # Keep the legacy *combined* uncertainty flag conservative:
        # parsing StackMapTable does not certify other Code attributes.
        "code_subattributes_and_stackmaps_unverified": True,
        "stackmap_frame_metadata_compared": True,
        "other_code_subattributes_unverified": True,
        "stackmap_frame_semantics_unverified": True,
        "original_instruction_count": len(old_ops),
        "candidate_instruction_count": len(new_ops),
        "checks": tests,
        "classification": (
            "CANDIDATE_INSTRUCTION_PARITY"
            if all(tests.values()) else "BYTECODE_DIFFERENCE"
        ),
    }
    digest = hashlib.sha256(json.dumps(
        core, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest().upper()[:20]
    return {"report_id": "SOURCEMETHOD_" + digest, **core}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_entry(entry: str) -> None:
    _require(
        isinstance(entry, str) and entry.endswith(".class")
        and not entry.startswith("/")
        and "\\" not in entry and ".." not in entry.split("/"),
        "INVALID_CLASS_ENTRY",
    )


def build_report(
    original_jar: Path, candidate_jar: Path, *,
    original_sha256: str, candidate_sha256: str,
    entry_path: str, method_name: str, descriptor: str,
) -> dict[str, Any]:
    """Mandatory exact JAR pins, duplicate-entry rejection, no writes."""
    _safe_entry(entry_path)
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        _require(
            len(pin) == 64 and all(c in "0123456789abcdefABCDEF" for c in pin),
            "INVALID_JAR_SHA256_PIN",
        )
        _require(path.is_file() and _sha256(path).lower() == pin.lower(),
                 "JAR_SHA256_MISMATCH")
        with ZipFile(path) as archive:
            _require(sum(i.filename == entry_path for i in archive.infolist()) == 1,
                     "MISSING_OR_DUPLICATE_CLASS_ENTRY")
    try:
        old = profile_jar_class(original_jar, entry_path)
        new = profile_jar_class(candidate_jar, entry_path)
    except (BytecodeProfileError, KeyError, IndexError) as exc:
        raise MethodParityError("UNSUPPORTED_OR_MALFORMED_CLASSFILE") from exc
    return compare_profiles(old, new, method_name, descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("candidate_jar", type=Path)
    parser.add_argument("entry_path")
    parser.add_argument("method_name")
    parser.add_argument("descriptor")
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--out", type=Path, help="New private JSON path; never overwrite")
    args = parser.parse_args()
    try:
        result = build_report(
            args.original_jar, args.candidate_jar,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
            entry_path=args.entry_path,
            method_name=args.method_name,
            descriptor=args.descriptor,
        )
        encoded = json.dumps(result, sort_keys=True, indent=2) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as stream:
                stream.write(encoded)
        else:
            print(encoded, end="")
    except (MethodParityError, OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
