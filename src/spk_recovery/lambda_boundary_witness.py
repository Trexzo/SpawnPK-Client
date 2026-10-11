"""R61: original JVM LambdaMetafactory four-op method boundary witness.

Proves a literal String -> invokedynamic functional-interface factory ->
invokestatic declared consumer -> return chain. DOES NOT reconstruct the
captured lambda implementation, invokedynamic bootstrap execution or consumer
side effects. Never emit original literals, member names or class coordinates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _digest, _instructions,
)


class LambdaBoundaryWitnessError(ValueError):
    """Four-op original LambdaMetafactory boundary is not proved."""


_SHA = re.compile(r"[a-fA-F0-9]{64}\Z")
_FACTORY = "java/lang/invoke/LambdaMetafactory"
_SIG = (
    "(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;"
    "Ljava/lang/invoke/MethodType;Ljava/lang/invoke/MethodType;"
    "Ljava/lang/invoke/MethodHandle;Ljava/lang/invoke/MethodType;)"
    "Ljava/lang/invoke/CallSite;"
)


def _need(ok: bool, why: str) -> None:
    if not ok:
        raise LambdaBoundaryWitnessError(why)


def _method(original: dict, method: dict, dependencies: dict) -> dict | None:
    if (method.get("name") in ("<clinit>", "<init>")
            or method.get("descriptor") != "()V"
            or method.get("access") != 0x0009):
        return None
    handlers = method.get("exception_handlers")
    _need(isinstance(handlers, list), "EXCEPTION_TABLE_MISSING")
    if handlers:
        return None
    rows = _instructions(method)
    if len(rows) != 4 or [r.get("opcode") for r in rows] != [
        "0x12", "0xba", "0xb8", "0xb1"
    ]:
        return None
    _need(all(a["offset"] + a["length"] == b["offset"]
              for a, b in zip(rows, rows[1:])),
          "LAMBDA_METHOD_HAS_NONCONTIGUOUS_JVM_INSTRUCTIONS")
    if any("branch_target_offset" in row for row in rows):
        return None
    literal, factory, consumer, ret = rows
    if (literal.get("constant_pool_tag") != 8
            or type(literal.get("constant")) is not str):
        return None
    desc = factory.get("descriptor")
    if (type(desc) is not str
            or not desc.startswith("()L")
            or not desc.endswith(";")
            or factory.get("invokedynamic_reserved") != 0):
        return None
    sam_desc = desc[2:]
    _need(
        consumer.get("descriptor") == "(Ljava/lang/String;" + sam_desc + ")V",
        "FUNCTIONAL_INTERFACE_NOT_SAME_CONSUMER_DESCRIPTOR"
    )
    idx = factory.get("bootstrap_method_attr_index")
    if type(idx) is not int:
        return None
    bs = [
        row for row in original.get("bootstrap_methods", [])
        if row.get("index") == idx
    ]
    _need(len(bs) == 1, "LAMBDA_BOOTSTRAP_NOT_UNIQUE")
    b = bs[0]
    handle = b.get("bootstrap_method", {})
    if (handle.get("reference_kind") != 6
            or handle.get("target_kind") != "method"
            or handle.get("owner") != _FACTORY
            or handle.get("name") != "metafactory"
            or handle.get("descriptor") != _SIG):
        return None
    arguments = b.get("arguments")
    if (not isinstance(arguments, list)
            or [a.get("kind") for a in arguments]
            != ["method_type", "method_handle", "method_type"]):
        return None
    impl = arguments[1]["method_handle"]
    if (not isinstance(impl, dict)
            or type(impl.get("owner")) is not str
            or type(impl.get("name")) is not str
            or type(impl.get("descriptor")) is not str):
        return None
    consumer_owner = consumer.get("owner")
    if type(consumer_owner) is not str:
        return None
    owner_profile = (original if consumer_owner == original.get("internal_name")
                     else dependencies.get(consumer_owner))
    if not isinstance(owner_profile, dict):
        return None
    methods = owner_profile.get("methods")
    if not isinstance(methods, list):
        return None
    declared = [
        m for m in methods if
        m.get("name") == consumer.get("name")
        and m.get("descriptor") == consumer.get("descriptor")
        and (m.get("access", 0) & 0x0008)
    ]
    if len(declared) != 1:
        return None
    # Do not resolve/create a fictional Java source for the lambda body:
    # the method handle is recorded as private evidence, NOT as source.
    private = {
        "method_name": method.get("name"),
        "original_string_literal": literal["constant"],
        "sam_descriptor": sam_desc,
        "bootstrap_implementation_handle": impl,
        "consumer_owner": consumer_owner,
        "consumer_method_name": consumer.get("name"),
        "consumer_method_descriptor": consumer.get("descriptor"),
    }
    return private


def plan_original_lambda_boundary(
    original: dict, dependencies: dict,
) -> dict:
    _need(isinstance(original.get("methods"), list),
          "ORIGINAL_METHOD_INVENTORY_MISSING")
    found = []
    for method in original["methods"]:
        detail = _method(original, method, dependencies)
        if detail is not None:
            found.append(detail)
    _need(len(found) == 1, "EXACTLY_ONE_ORIGINAL_FOUR_OP_LAMBDA_BOUNDARY_REQUIRED")
    private_bytes = json.dumps(found, sort_keys=True,
                               ensure_ascii=True).encode("utf-8")
    return {
        "original_four_op_private_witness_sha256":
            hashlib.sha256(private_bytes).hexdigest(),
        "exact_four_instruction_methods": len(found),
        "bootstrap_factory": "java/lang/invoke/LambdaMetafactory",
        "bootstrap_method": "metafactory",
        "literal_ldc_string_exactly_proven": True,
        "functional_interface_same_descriptor_passed_to_consumer": True,
        "consumer_method_declared_static": True,
        "lambda_implementation_body_reconstructed": False,
        "consumer_method_body_reconstructed": False,
        "java_lambda_expression_source_recovered": False,
        "bootstrap_execution_parity_verified": False,
        "runtime_equivalence_certified": False,
        "canonical_original_class_method_aliases_accepted": False,
    }


def replay_private_lambda_boundary(
    original_jar: Path, class_entry: str, output_root: Path, *, sha256: str,
) -> dict:
    jar, out = Path(original_jar), Path(output_root)
    _need(not out.exists() and not out.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    _need(type(sha256) is str and _SHA.fullmatch(sha256) is not None,
          "INVALID_WHOLE_ORIGINAL_SHA256")
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
            names = archive.namelist()
            _need(names.count(class_entry) == 1,
                  "PRIVATE_ORIGINAL_OWNER_CLASS_ENTRY_NOT_UNIQUE")
            original = profile_jar_class(jar, class_entry)
            consumer_owners = set()
            for m in original.get("methods", []):
                rows = m.get("instructions", [])
                if len(rows) == 4 and any(
                    r.get("opcode") == "0xba" for r in rows
                ):
                    for row in rows:
                        if (row.get("opcode") == "0xb8"
                                and row.get("owner")
                                != original.get("internal_name")):
                            consumer_owners.add(row.get("owner"))
            _need(all(type(x) is str and names.count(x + ".class") == 1
                      for x in consumer_owners),
                  "PRIVATE_CONSUMER_CLASSFILE_NOT_UNIQUE")
            profiles = {
                x: profile_jar_class(jar, x + ".class")
                for x in consumer_owners
            }
        proof = plan_original_lambda_boundary(original, profiles)
    except (OSError, BadZipFile, BytecodeProfileError,
            ScalarInitializerRecoveryError, KeyError, TypeError, IndexError):
        raise LambdaBoundaryWitnessError(
            "ORIGINAL_LAMBDA_BOUNDARY_INPUT_UNVERIFIABLE"
        ) from None
    _need(_digest(jar) == sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_PROOF")
    aggregate = {
        "schema_version": 1,
        "kind": "private_original_lambda_metafactory_four_op_boundary",
        "research_only": True,
        "original_complete_jar_sha256": sha256.lower(),
        **proof,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "lambda-boundary.aggregate.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as fd:
        json.dump(aggregate, fd, indent=2, sort_keys=True)
        fd.write("\n")
    return aggregate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("original_class_entry")
    parser.add_argument("new_private_output_directory", type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(replay_private_lambda_boundary(
            args.original_jar, args.original_class_entry,
            args.new_private_output_directory, sha256=args.sha256,
        ), sort_keys=True))
    except LambdaBoundaryWitnessError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
