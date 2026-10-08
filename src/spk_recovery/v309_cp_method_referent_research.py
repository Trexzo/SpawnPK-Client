from __future__ import annotations

"""Exact private v309 CP-referent method research: NEVER identity acceptance.

This deliberately compares only the eight descriptor-derived proposed class
pairs. It does NOT assert whole-archive class uniqueness or accept field lineage.
It uses the existing bytecode parser's CP-resolved instruction/BootstrapMethods
profiles; unsupported CP instructions fail closed.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .bytecode_profile import BytecodeProfileError, profile_class_field_accesses
from .classfile import parse_class, _descriptor_shape
from .descriptor_class_dependencies import build_descriptor_class_dependency_report
from .descriptor_class_private_jar_replay import _read_json_exact, write_research_report_no_clobber
from .indexer import sha256_file
from .lineage import validate_lineage


class V309CpMethodWitnessError(ValueError):
    pass


_CP_MEMBER = {"0xb2", "0xb3", "0xb4", "0xb5", "0xb6", "0xb7", "0xb8", "0xb9"}
_CP_TYPES = {"0xbb", "0xbd", "0xc0", "0xc1"}
_CP_CONSTANTS = {"0x12", "0x13", "0x14"}
_UNSUPPORTED = {
    "0xaa", "0xab",  # switch tables require full arms/padding proof
    "0xa9",          # ret: legacy subroutine control flow
    "0xbc",          # newarray atype not decoded by the existing profiler
    "0xc5",          # multianewarray CP + dimensions not decoded
    "0xca", "0xfe", "0xff", # debugger/reserved opcodes
}


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _rename(value: str, *, old_owner: str, new_owner: str) -> str:
    if value == old_owner:
        return new_owner
    return value.replace("L" + old_owner + ";", "L" + new_owner + ";")


def _handle_semantics(
    obj: dict[str, Any], *, old_owner: str, new_owner: str,
) -> tuple[Any, ...]:
    if (
        not isinstance(obj, dict)
        or type(obj.get("reference_kind")) is not int
        or not 1 <= obj["reference_kind"] <= 9
        or obj.get("target_kind") not in ("field", "method", "interface_method")
        or not all(isinstance(obj.get(k), str) for k in ("owner", "name", "descriptor"))
    ):
        raise V309CpMethodWitnessError("invalid bootstrap MethodHandle referent")
    return (
        obj["reference_kind"], obj["target_kind"],
        _rename(obj["owner"], old_owner=old_owner, new_owner=new_owner),
        obj["name"],
        _rename(obj["descriptor"], old_owner=old_owner, new_owner=new_owner),
    )


def _argument_semantics(
    arg: dict[str, Any], *, old_owner: str, new_owner: str,
) -> tuple[Any, ...]:
    if not isinstance(arg, dict):
        raise V309CpMethodWitnessError("invalid bootstrap argument")
    kind = arg.get("kind")
    if kind == "method_handle":
        return ("method_handle", _handle_semantics(
            arg.get("method_handle"), old_owner=old_owner, new_owner=new_owner,
        ))
    if kind in ("method_type", "class", "string"):
        key = {"method_type": "descriptor", "class": "name", "string": "value"}[kind]
        value = arg.get(key)
        if not isinstance(value, str):
            raise V309CpMethodWitnessError("invalid bootstrap argument value")
        return (kind, _rename(value, old_owner=old_owner, new_owner=new_owner)
                if kind != "string" else value)
    if kind == "constant":
        tag = arg.get("tag")
        value = arg.get("value")
        if tag not in (3, 4) or type(value) not in (int, float):
            raise V309CpMethodWitnessError("unsupported bootstrap primitive constant")
        return ("constant", tag, repr(value))
    # Includes dynamic/nested condy and any unsupported CP tag. Never silently
    # ignore unknown bootstrap semantics.
    raise V309CpMethodWitnessError("unresolved invokedynamic bootstrap argument")


def _indy_semantics(
    row: dict[str, Any], bootstraps: list[dict[str, Any]],
    *, old_owner: str, new_owner: str,
) -> tuple[Any, ...]:
    index = row.get("bootstrap_method_attr_index")
    if type(index) is not int or index < 0:
        raise V309CpMethodWitnessError("missing invokedynamic bootstrap index")
    hits = [b for b in bootstraps if isinstance(b, dict) and b.get("index") == index]
    if len(hits) != 1:
        raise V309CpMethodWitnessError("ambiguous or missing invokedynamic bootstrap")
    b = hits[0]
    if not all(isinstance(row.get(k), str) for k in ("name", "descriptor")):
        raise V309CpMethodWitnessError("malformed invokedynamic call site")
    args = b.get("arguments")
    if not isinstance(args, list):
        raise V309CpMethodWitnessError("missing invokedynamic bootstrap arguments")
    return (
        row["name"],
        _rename(row["descriptor"], old_owner=old_owner, new_owner=new_owner),
        _handle_semantics(b.get("bootstrap_method"), old_owner=old_owner, new_owner=new_owner),
        tuple(_argument_semantics(a, old_owner=old_owner, new_owner=new_owner) for a in args),
    )


def _instruction_semantics(
    row: dict[str, Any], bootstrap: list[dict[str, Any]],
    *, old_owner: str, new_owner: str,
) -> tuple[Any, ...]:
    if not isinstance(row, dict) or not isinstance(row.get("opcode"), str):
        raise V309CpMethodWitnessError("invalid decoded instruction")
    opcode = row["opcode"]
    length = row.get("length")
    if (
        len(opcode) != 4 or not opcode.startswith("0x")
        or type(length) is not int or length <= 0
        or opcode in _UNSUPPORTED
    ):
        raise V309CpMethodWitnessError("unsupported instruction semantics")
    base = [opcode, length]
    if opcode in _CP_MEMBER:
        if not all(isinstance(row.get(k), str) for k in ("owner", "name", "descriptor")):
            raise V309CpMethodWitnessError("unresolved field/method CP reference")
        base += [
            _rename(row["owner"], old_owner=old_owner, new_owner=new_owner),
            row["name"],
            _rename(row["descriptor"], old_owner=old_owner, new_owner=new_owner),
        ]
    elif opcode in _CP_TYPES:
        if not isinstance(row.get("type"), str):
            raise V309CpMethodWitnessError("unresolved class CP reference")
        base.append(_rename(row["type"], old_owner=old_owner, new_owner=new_owner))
    elif opcode in _CP_CONSTANTS:
        # The existing bytecode profiler resolves only numeric, String, and
        # Class LDC; MethodHandle, MethodType, condy are intentionally refused.
        value = row.get("constant")
        tag = row.get("constant_pool_tag")
        if (
            type(tag) is not int
            or tag not in (3, 4, 5, 6, 7, 8)
            or type(value) not in (int, float, str)
            or (tag in (3, 5) and type(value) is not int)
            or (tag in (4, 6) and type(value) is not float)
            or (tag in (7, 8) and type(value) is not str)
        ):
            raise V309CpMethodWitnessError("unsupported/unresolved LDC CP referent")
        # Only Class LDC values carry owner identities; String literals
        # must remain byte-for-byte exact, even when they look like names.
        if tag == 7:
            value = _rename(value, old_owner=old_owner, new_owner=new_owner)
        base += [tag, type(value).__name__, repr(value)]
    elif opcode == "0xba":
        base.append(_indy_semantics(row, bootstrap,
            old_owner=old_owner, new_owner=new_owner))
    else:
        # Decoder-supplied immediate operands are included instead of dropping
        # branch/local/primitive distinctions. Unknown multi-byte operands veto.
        if not isinstance(row.get("mnemonic"), str):
            raise V309CpMethodWitnessError("missing opcode mnemonic")
        if row["mnemonic"].startswith("opcode_") and length != 1:
            raise V309CpMethodWitnessError("unknown multi-byte instruction")
        for name in (
            "local_index", "int_constant", "increment", "branch_target_offset",
            "wide_opcode", "wide_mnemonic",
        ):
            if name in row:
                value = row[name]
                if type(value) not in (str, int):
                    raise V309CpMethodWitnessError("malformed instruction immediate")
                base.extend((name, value))
    return tuple(base)


def _method_semantics(
    method: dict[str, Any], bootstrap: list[dict[str, Any]],
    *, old_owner: str, new_owner: str,
) -> tuple[tuple, int]:
    if (
        not isinstance(method, dict) or method.get("name") in ("<init>", "<clinit>")
        or type(method.get("access")) is not int
        or not isinstance(method.get("descriptor"), str)
        or type(method.get("code_length")) is not int
        or method["code_length"] <= 0
    ):
        raise V309CpMethodWitnessError("not a code-bearing ordinary method")
    ins = method.get("instructions")
    handlers = method.get("exception_handlers")
    if not isinstance(ins, list) or not ins or not isinstance(handlers, list):
        raise V309CpMethodWitnessError("missing decoded Code/exception semantics")
    signature = []
    offset = 0
    cp_sites = 0
    for row in ins:
        if row.get("offset") != offset:
            raise V309CpMethodWitnessError("noncontiguous instruction byte offsets")
        signature.append(_instruction_semantics(row, bootstrap,
            old_owner=old_owner, new_owner=new_owner))
        offset += row["length"]
        if row["opcode"] in _CP_MEMBER | _CP_TYPES | _CP_CONSTANTS | {"0xba"}:
            cp_sites += 1
    if offset != method["code_length"]:
        raise V309CpMethodWitnessError("decoded Code length mismatch")
    normalized_handlers = []
    for row in handlers:
        if (
            not isinstance(row, dict)
            or not all(type(row.get(k)) is int for k in
                       ("start_pc", "end_pc", "handler_pc"))
            or row.get("catch_type") is not None and
               not isinstance(row["catch_type"], str)
        ):
            raise V309CpMethodWitnessError("invalid exception handler")
        normalized_handlers.append((
            row["start_pc"], row["end_pc"], row["handler_pc"],
            None if row["catch_type"] is None else _rename(
                row["catch_type"], old_owner=old_owner, new_owner=new_owner,
            ),
        ))
    return (
        method["access"],
        _descriptor_shape(method["descriptor"]),
        method["code_length"],
        tuple(signature),
        tuple(normalized_handlers),
    ), cp_sites


def compare_cp_method_profiles(
    old: dict[str, Any], new: dict[str, Any], *,
    old_owner: str, new_owner: str,
) -> dict[str, int]:
    """A pair-local exact *CP-referent* observation; never a class mapping."""
    if (
        old.get("internal_name") != old_owner
        or new.get("internal_name") != new_owner
    ):
        raise V309CpMethodWitnessError("proposed class profile owner mismatch")
    fingerprints: list[Counter] = []
    counts: list[dict[str, int]] = []
    for profile, src, dst in ((old, old_owner, new_owner), (new, new_owner, new_owner)):
        methods = profile.get("methods")
        bootstrap = profile.get("bootstrap_methods")
        if not isinstance(methods, list) or not isinstance(bootstrap, list):
            raise V309CpMethodWitnessError("malformed CP class profile")
        shapes: Counter = Counter()
        unsupported = 0
        zero_cp = 0
        for m in methods:
            if m.get("name") in ("<init>", "<clinit>") or m.get("code_length") is None:
                continue
            try:
                signature, refs = _method_semantics(
                    m, bootstrap, old_owner=src, new_owner=dst,
                )
            except V309CpMethodWitnessError:
                unsupported += 1
                continue
            if refs == 0:
                zero_cp += 1
                continue
            shapes[signature] += 1
        fingerprints.append(shapes)
        counts.append({
            "eligible_methods": sum(shapes.values()),
            "unsupported_methods": unsupported,
            "zero_cp_methods_excluded": zero_cp,
        })
    old_shapes, new_shapes = fingerprints
    overlap = old_shapes.keys() & new_shapes.keys()
    # Duplicate shapes on EITHER side cannot be identified as unique methods.
    ambiguous = sum(
        1 for shape in overlap if old_shapes[shape] != 1 or new_shapes[shape] != 1
    )
    unique = sum(1 for shape in overlap
                 if old_shapes[shape] == 1 and new_shapes[shape] == 1)
    return {
        "old_eligible": counts[0]["eligible_methods"],
        "new_eligible": counts[1]["eligible_methods"],
        "old_unsupported": counts[0]["unsupported_methods"],
        "new_unsupported": counts[1]["unsupported_methods"],
        "old_without_cp_references": counts[0]["zero_cp_methods_excluded"],
        "new_without_cp_references": counts[1]["zero_cp_methods_excluded"],
        "unique_cp_semantic_method_matches": unique,
        "ambiguous_duplicate_semantic_shapes": ambiguous,
        "accepted_class_identifications": 0,
        "accepted_member_identifications": 0,
    }


def build_v309_cp_method_research(
    frontier: dict[str, Any],
    global_report: dict[str, Any],
    lineage: dict[str, Any],
    old_jar: Path, new_jar: Path,
) -> dict[str, Any]:
    if (
        frontier.get("kind") != "v309_recovery_frontier"
        or frontier.get("state") != "ACCEPTED_INCOMPLETE"
        or frontier.get("frontier", {}).get("unresolved") != 143
        or global_report.get("kind") != "global_field_usage_identity_candidates"
        or global_report.get("canonical") is not False
        or global_report.get("summary", {}).get("descriptor_identity_guard_rejected") != 26
        or len(global_report.get("review_outcomes", [])) != 143
    ):
        raise V309CpMethodWitnessError("requires current pinned 143/26 incomplete v309 frontier")
    validate_lineage(lineage)
    expected = frontier["exact_clients"]
    old_sha, new_sha = sha256_file(old_jar), sha256_file(new_jar)
    if (
        old_sha.lower() != expected["v308_sha256"].lower()
        or new_sha.lower() != expected["v309_sha256"].lower()
        or old_sha.lower() != global_report["old_sha256"].lower()
        or new_sha.lower() != global_report["new_sha256"].lower()
    ):
        raise V309CpMethodWitnessError("exact client SHA drift")
    builds = {r["build_id"]: r["sha256"] for r in lineage["builds"]}
    if builds.get("v308") != old_sha or builds.get("v309") != new_sha:
        raise V309CpMethodWitnessError("lineage build SHA drift")
    deps = build_descriptor_class_dependency_report(global_report)
    if (
        deps["summary"]["blocked_fields"] != 26
        or deps["summary"]["blocking_old_class_identities"] != 8
    ):
        raise V309CpMethodWitnessError("blocked dependency accounting drift")
    classes = {row["logical_id"]: row for row in lineage["classes"]}
    new_owners = {
        x["internal_name"] for row in lineage["classes"]
        for x in row["lineage"] if x["build_id"] == "v309"
    }
    rows = []
    with zipfile.ZipFile(old_jar) as oldz, zipfile.ZipFile(new_jar) as newz:
        for dep in deps["class_dependencies"]:
            cid = dep["old_canonical_class_id"]
            old_rows = [x for x in classes[cid]["lineage"] if x["build_id"] == "v308"]
            new_rows = [x for x in classes[cid]["lineage"] if x["build_id"] == "v309"]
            if len(old_rows) != 1 or new_rows or dep["state"] != "UNPROVEN_NEW_CLASS_IDENTITY":
                raise V309CpMethodWitnessError(f"{cid}: class lineage proof drift")
            old = old_rows[0]
            if dep["old_raw_descriptors"] != ["L" + old["internal_name"] + ";"]:
                raise V309CpMethodWitnessError(f"{cid}: original descriptor proof drift")
            desc = dep["new_raw_descriptors"]
            if len(desc) != 1 or not desc[0].startswith("Lrs/") or not desc[0].endswith(";"):
                raise V309CpMethodWitnessError(f"{cid}: new descriptor ambiguous")
            proposed = desc[0][1:-1]
            if proposed in new_owners:
                raise V309CpMethodWitnessError(f"{cid}: new class already mapped")
            old_bytes = oldz.read(old["entry_path"])
            new_bytes = newz.read(proposed + ".class")
            if (
                hashlib.sha256(old_bytes).hexdigest() != old["entry_sha256"]
                or parse_class(old_bytes).structural_sha256() != old["structural_sha256"]
                or old_bytes == new_bytes
            ):
                raise V309CpMethodWitnessError(f"{cid}: exact old class/changed-byte proof drift")
            old_profile = profile_class_field_accesses(old_bytes)
            new_profile = profile_class_field_accesses(new_bytes)
            counts = compare_cp_method_profiles(
                old_profile, new_profile,
                old_owner=old["internal_name"], new_owner=proposed,
            )
            rows.append({
                "old_canonical_class_id": cid,
                "blocked_fields": dep["blocked_fields"],
                "research_state": "PAIRWISE_CP_REFERENCE_RESEARCH_ONLY",
                **counts,
            })
    rows.sort(key=lambda x: x["old_canonical_class_id"])
    body = {
        "schema_version": 1,
        "kind": "v309_cp_method_referent_pairwise_research",
        "canonical": False,
        "state": "CP_REFERENT_PAIRWISE_NO_CLASS_OR_MEMBER_IDENTITY_ACCEPTED",
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "frontier_id": frontier.get("report_id"),
        "global_report_id": global_report["report_id"],
        "summary": {
            "reviewed_descriptor_class_pairs": len(rows),
            "input_blocked_field_relationships": 26,
            "unique_cp_method_research_matches": sum(
                row["unique_cp_semantic_method_matches"] for row in rows),
            "class_identities_accepted": 0,
            "member_identities_accepted": 0,
            "accepted_frontier_unresolved": 143,
        },
        "rows": rows,
        "note": (
            "Pairwise CP-referent observation, NOT whole-archive uniqueness, "
            "method identity proof, or canonical class/member acceptance. "
            "Unsupported CP/control-flow constructs and duplicate fingerprints "
            "never count as unique. No private Code, constants, members or raw "
            "signatures are exported."
        ),
    }
    return {"report_id": "V309CPPAIR_" + _digest(body)[:20].upper(), **body}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-v309-cp-referent-pair-research")
    p.add_argument("--v308-jar", type=Path, required=True)
    p.add_argument("--v309-jar", type=Path, required=True)
    p.add_argument("--frontier", type=Path,
                   default=Path("research/v309-field-recovery/frontier.json"))
    p.add_argument("--class-lineage", type=Path,
                   default=Path("research/v309-field-recovery/class-lineage.json"))
    p.add_argument("--global-report", type=Path,
                   default=Path("research/v309-field-recovery/global-field-usage.json"))
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        for role, path in (
            ("class_lineage", args.class_lineage),
            ("global_field_usage", args.global_report),
        ):
            frontier = _read_json_exact(args.frontier)
            pinned = frontier.get("files", {}).get(role, {}).get("sha256")
            if not isinstance(pinned, str) or sha256_file(path) != pinned:
                raise V309CpMethodWitnessError(f"{role}: pinned tracked report SHA mismatch")
        report = build_v309_cp_method_research(
            _read_json_exact(args.frontier),
            _read_json_exact(args.global_report),
            _read_json_exact(args.class_lineage),
            args.v308_jar, args.v309_jar,
        )
        write_research_report_no_clobber(
            report, args.out, (
                args.v308_jar, args.v309_jar,
                args.frontier, args.global_report, args.class_lineage,
            ),
        )
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile) as exc:
        print(f"SPK_V309_CP_METHOD_RESEARCH_FAIL: {exc}")
        return 1
    print("SPK_V309_CP_METHOD_RESEARCH_PASS_RESEARCH_ONLY")
    print(f"report_id={report['report_id']}")
    for name, value in report["summary"].items():
        print(f"{name}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
