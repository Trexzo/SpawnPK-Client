"""R64: original conditional-null boolean store source micro-forms.

For exact JVM windows: aload_1; ldc String; invokevirtual(String)->ref;
ifnonnull after_store; iconst_0/1; putstatic original boolean field.
Only the local source *shape* is recovered; the real Java local variable type,
exception-region nesting, surrounding jumps and runtime side effects are not.
Never publish the original private string keys or member identities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from .boolean_join_witness import BooleanJoinWitnessError, _edges
from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _fields, _instructions,
)


class NullGuardBooleanSourceError(ValueError):
    """Original nullable boolean store form cannot be proven."""


_PIN = re.compile(r"[a-fA-F0-9]{64}\Z")
_ID = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")
_REF = re.compile(r"L[^;]+;\Z")
_BASE = ("0x2b", "0x12", "0xb6", "0xc7")
_LITERALS = {"0x03": "false", "0x04": "true"}


def _need(ok: bool, why: str) -> None:
    if not ok:
        raise NullGuardBooleanSourceError(why)


def plan_original_null_guard_boolean_source(
    original: dict, private_method_name: str, method_descriptor: str
) -> dict:
    owner = original.get("internal_name")
    _need(type(owner) is str and owner, "INVALID_ORIGINAL_OWNER")
    methods = original.get("methods")
    _need(isinstance(methods, list), "ORIGINAL_METHOD_INVENTORY_MISSING")
    selected = [m for m in methods
                if m.get("name") == private_method_name
                and m.get("descriptor") == method_descriptor]
    _need(len(selected) == 1, "ORIGINAL_PRIVATE_METHOD_IDENTITY_NOT_UNIQUE")
    method = selected[0]
    rows = _instructions(method)
    _need(rows and rows[0]["offset"] == 0
          and all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(rows, rows[1:])),
          "ORIGINAL_METHOD_CONTAINS_UNACCOUNTED_BYTECODE_GAP")
    try:
        edges = _edges(rows)
    except BooleanJoinWitnessError:
        raise NullGuardBooleanSourceError("INVALID_JVM_BRANCH_TARGET") from None
    incoming = {target for _, target in edges}
    handlers = method.get("exception_handlers")
    _need(isinstance(handlers, list), "EXCEPTION_TABLE_UNAVAILABLE")
    declared = _fields(original)
    raw = 0
    accepted = []
    vetoed = 0
    for i, row in enumerate(rows):
        if row.get("opcode") != "0xb3" or i < 5:
            continue
        win = rows[i-5:i+1]
        if (tuple(x.get("opcode") for x in win[:4]) != _BASE
                or win[4].get("opcode") not in _LITERALS):
            continue
        raw += 1
        local, literal, lookup, condition, assigned, store = win
        field = (store.get("name"), store.get("descriptor"))
        if (store.get("owner") != owner
                or store.get("descriptor") != "Z"
                or field not in declared
                or not (declared[field]["access"] & 0x0008)
                or literal.get("constant_pool_tag") != 8
                or type(literal.get("constant")) is not str):
            vetoed += 1
            continue
        descriptor = lookup.get("descriptor")
        if (type(descriptor) is not str
                or not descriptor.startswith("(Ljava/lang/String;)")
                or _REF.fullmatch(descriptor.split(")", 1)[1]) is None
                or type(lookup.get("owner")) is not str
                or type(lookup.get("name")) is not str):
            vetoed += 1
            continue
        branch_dest = condition.get("branch_target_offset")
        if (type(branch_dest) is not int
                or branch_dest <= store["offset"]
                or (condition["offset"], branch_dest) not in edges):
            vetoed += 1
            continue
        interior = {r["offset"] for r in win[1:]}
        if (incoming & interior
                or any(h.get("handler_pc") in interior for h in handlers)):
            vetoed += 1
            continue
        _need(all(a["offset"] + a["length"] == b["offset"]
                  for a, b in zip(win, win[1:])),
              "NULL_GUARD_BYTECODE_NOT_CONTIGUOUS")
        name = store.get("name")
        _need(type(name) is str and _ID.fullmatch(name) is not None
              and _ID.fullmatch(lookup["name"]) is not None,
              "ORIGINAL_PRIVATE_JAVA_MEMBER_NOT_REPRESENTABLE")
        local_expr = "originalLocalSlot1"
        snippet = (
            "    if (" + local_expr + "." + lookup["name"] + "("
            + json.dumps(literal["constant"], ensure_ascii=True)
            + ") == null) { " + name + " = "
            + _LITERALS[assigned["opcode"]] + "; }\n"
        )
        accepted.append({
            "method_private_original_field": name,
            "original_private_lookup_owner": lookup["owner"],
            "original_lookup_descriptor": descriptor,
            "private_key_literal": literal["constant"],
            "store_offset": store["offset"],
            "conditional_branch_destination": branch_dest,
            "boolean_literal": _LITERALS[assigned["opcode"]],
            "private_source_shape": snippet,
            "real_JVM_local_slot_one_type_proven": False,
        })
    fragment = (
        "// PRIVATE JVM-local nullable boolean store source shapes.\n"
        "// originalLocalSlot1 is an UNRESOLVED source variable placeholder.\n"
        "// Exception regions and surrounding method control flow are missing.\n"
        + "".join(x["private_source_shape"] for x in accepted)
    )
    return {
        "private_original_null_guard_sites": accepted,
        "private_null_guard_source_shapes": fragment,
        "original_six_instruction_null_guard_windows": raw,
        "exact_local_null_guard_source_shapes": len(accepted),
        "rejected_due_to_branch_or_field_metadata": vetoed,
        "boolean_true_on_null_stores": sum(
            x["boolean_literal"] == "true" for x in accepted
        ),
        "boolean_false_on_null_stores": sum(
            x["boolean_literal"] == "false" for x in accepted
        ),
        "original_local_one_java_variable_type_recovered": False,
        "complete_java_branch_and_exception_nesting_recovered": False,
        "complete_original_method_recompiled_and_verified": False,
        "helper_method_runtime_behavior_certified": False,
        "original_class_runtime_equivalence_certified": False,
        "canonical_private_member_identity_accepted": False,
    }


def build_private_null_guard_source(original_jar: Path, class_entry: str,
                                    private_method_name: str,
                                    method_descriptor: str,
                                    output_root: Path, *, sha256: str) -> dict:
    jar, out = Path(original_jar), Path(output_root)
    _need(not out.exists() and not out.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    _need(type(sha256) is str and _PIN.fullmatch(sha256) is not None,
          "INVALID_ORIGINAL_WHOLE_JAR_PIN")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar) == sha256.lower(), "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/") and "\\" not in class_entry
          and all(x not in ("", ".", "..") and ":" not in x
                  for x in class_entry.split("/")),
          "INVALID_PRIVATE_CLASS_ENTRY")
    try:
        with ZipFile(jar) as archive:
            _need(archive.namelist().count(class_entry) == 1,
                  "ORIGINAL_OWNER_CLASSFILE_NOT_UNIQUE")
            profile = profile_jar_class(jar, class_entry)
        plan = plan_original_null_guard_boolean_source(
            profile, private_method_name, method_descriptor
        )
    except (BadZipFile, BytecodeProfileError, ScalarInitializerRecoveryError,
            KeyError, OSError, IndexError):
        raise NullGuardBooleanSourceError(
            "ORIGINAL_NULL_BOOLEAN_SOURCE_EVIDENCE_UNVERIFIABLE"
        ) from None
    _need(_digest(jar) == sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_REPLAY")
    private_sites = plan.pop("private_original_null_guard_sites")
    source = plan.pop("private_null_guard_source_shapes")
    _need(bool(private_sites), "NO_EXACT_NULL_GUARDED_BOOLEAN_SOURCES")
    raw = json.dumps(private_sites, indent=2, sort_keys=True) + "\n"
    public = {
        "schema_version": 1,
        "kind": "private_exact_jvm_null_guard_boolean_source_forms",
        "research_only": True,
        "original_complete_jar_sha256": sha256.lower(),
        "private_site_graph_sha256": hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest(),
        "private_java_shape_sha256": hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest(),
        **plan,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "null-boolean-sites.private.json").open(
            "x", encoding="utf-8", newline="\n") as fd:
        fd.write(raw)
    with (out / "null-boolean-source.private.java.txt").open(
            "x", encoding="utf-8", newline="\n") as fd:
        fd.write(source)
    with (out / "null-boolean-source.aggregate.json").open(
            "x", encoding="utf-8", newline="\n") as fd:
        json.dump(public, fd, indent=2, sort_keys=True)
        fd.write("\n")
    return public


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("private_owner_class_entry")
    p.add_argument("private_method_name")
    p.add_argument("private_method_descriptor")
    p.add_argument("new_private_output_directory", type=Path)
    p.add_argument("--sha256", required=True)
    args = p.parse_args(argv)
    try:
        print(json.dumps(build_private_null_guard_source(
            args.original_jar, args.private_owner_class_entry,
            args.private_method_name, args.private_method_descriptor,
            args.new_private_output_directory, sha256=args.sha256,
        ), sort_keys=True))
    except NullGuardBooleanSourceError as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
