"""R54: exact original static-final String conditional concat source forms.

Only verify contiguous two-Enum-getstatic, if_acmpne, two String ldc
branches, StringConcatFactory.makeConcatWithConstants, putstatic.
A verified expression form is *not* original authorial source or runtime parity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from .boolean_join_witness import _edges
from .bytecode_profile import BytecodeProfileError, profile_jar_class
from .mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError, _clinit, _digest, _fields, _instructions,
)


class ConditionalConcatSourceError(ValueError):
    """Cannot establish exact supported original concat-expression evidence."""


_PIN = re.compile(r"[0-9a-fA-F]{64}\Z")
_ID = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")
_BOOTSTRAP_OWNER = "java/lang/invoke/StringConcatFactory"
_BOOTSTRAP_DESC = (
    "(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;"
    "Ljava/lang/invoke/MethodType;Ljava/lang/String;"
    "[Ljava/lang/Object;)Ljava/lang/invoke/CallSite;"
)


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise ConditionalConcatSourceError(message)


def _member(x: object) -> str:
    _need(type(x) is str and _ID.fullmatch(x) is not None,
          "UNREPRESENTABLE_JAVA_SOURCE_MEMBER")
    return x


def _readable_field(row: dict, owner: str) -> str:
    source_owner = row.get("owner")
    name = _member(row.get("name"))
    if source_owner == owner:
        return name
    _need(type(source_owner) is str and source_owner,
          "UNREPRESENTABLE_REFERENCED_OWNER")
    path = source_owner.replace("/", ".")
    _need(all(_ID.fullmatch(x) for x in path.split(".")),
          "UNREPRESENTABLE_REFERENCED_OWNER")
    return path + "." + name


def _string_literal(row: dict) -> str | None:
    if (row.get("opcode") not in ("0x12", "0x13")
            or row.get("constant_pool_tag") != 8
            or type(row.get("constant")) is not str):
        return None
    value = row["constant"]
    if not all(32 <= ord(c) <= 126 for c in value):
        return None
    return json.dumps(value, ensure_ascii=True)


def _concat_recipe(profile: dict, row: dict) -> tuple[str, str] | None:
    if (row.get("opcode") != "0xba"
            or row.get("name") != "makeConcatWithConstants"
            or row.get("descriptor") != "(Ljava/lang/String;)Ljava/lang/String;"
            or row.get("invokedynamic_reserved") != 0):
        return None
    index = row.get("bootstrap_method_attr_index")
    if type(index) is not int:
        return None
    matched = [x for x in profile.get("bootstrap_methods", [])
               if x.get("index") == index]
    if len(matched) != 1:
        return None
    call = matched[0].get("bootstrap_method", {})
    if (call.get("owner") != _BOOTSTRAP_OWNER
            or call.get("name") != "makeConcatWithConstants"
            or call.get("descriptor") != _BOOTSTRAP_DESC
            or call.get("reference_kind") != 6
            or call.get("target_kind") != "method"):
        return None
    args = matched[0].get("arguments")
    if (not isinstance(args, list) or len(args) != 1
            or args[0].get("kind") != "string"
            or type(args[0].get("value")) is not str):
        return None
    recipe = args[0]["value"]
    if recipe.count("\x01") != 1 or "\x02" in recipe:
        return None
    a, b = recipe.split("\x01")
    if not all(32 <= ord(c) <= 126 for c in a + b):
        return None
    return a, b


def plan_conditional_concat_strings(owner_class: dict, nested_classes: dict) -> dict:
    owner = owner_class.get("internal_name")
    _need(type(owner) is str and bool(owner), "INVALID_ORIGINAL_OWNER")
    fields = _fields(owner_class)
    final_strings = {
        k: value for k, value in fields.items()
        if (value["access"] & 0x0018) == 0x0018
        and k[1] == "Ljava/lang/String;"
        and value["constant_value"] is None
    }
    _need(bool(final_strings), "NO_NONCONSTANT_STRING_FINAL_DECLARATIONS")
    init = _clinit(owner_class, required=True)
    rows = _instructions(init)
    explicit = _edges(rows)
    handlers = init.get("exception_handlers")
    _need(isinstance(handlers, list), "EXCEPTION_TABLE_MISSING")
    writes = {key: [] for key in final_strings}
    for i, row in enumerate(rows):
        key = row.get("name"), row.get("descriptor")
        if row.get("opcode") == "0xb3" and row.get("owner") == owner and key in writes:
            writes[key].append((i, row))
    _need(all(len(v) == 1 for v in writes.values()),
          "STRING_FINAL_ORIGINAL_STORE_MISSING_OR_DUPLICATE")
    expressions = []
    for key, ((index, store),) in writes.items():
        if index < 7:
            continue
        a, b, cond, t, jump, f, concat = rows[index - 7:index]
        seq = [a, b, cond, t, jump, f, concat, store]
        if any(x["offset"] + x["length"] != y["offset"]
               for x, y in zip(seq, seq[1:])):
            continue
        if (a.get("opcode") != "0xb2" or b.get("opcode") != "0xb2"
                or cond.get("opcode") != "0xa6"
                or cond.get("branch_target_offset") != f["offset"]
                or jump.get("opcode") not in ("0xa7", "0xc8")
                or jump.get("branch_target_offset") != concat["offset"]):
            continue
        first, second = _string_literal(t), _string_literal(f)
        recipe = _concat_recipe(owner_class, concat)
        if first is None or second is None or recipe is None:
            continue
        if a.get("owner") != owner:
            continue
        original_enum_field = fields.get((a.get("name"), a.get("descriptor")))
        nested_desc = a.get("descriptor")
        if (original_enum_field is None
                or (original_enum_field["access"] & 0x0008) == 0
                or type(nested_desc) is not str
                or not nested_desc.startswith("L" + owner + "$")
                or not nested_desc.endswith(";")
                or b.get("descriptor") != nested_desc
                or b.get("owner") != nested_desc[1:-1]):
            continue
        enum = nested_classes.get(nested_desc[1:-1])
        if (not isinstance(enum, dict)
                or enum.get("super_name") != "java/lang/Enum"
                or (enum.get("class_access", 0) & 0x4000) == 0):
            continue
        enum_const = _fields(enum).get((b.get("name"), b.get("descriptor")))
        if (enum_const is None
                or (enum_const["access"] & 0x4018) != 0x4018):
            continue
        allowed = {(cond["offset"], f["offset"]),
                   (jump["offset"], concat["offset"])}
        inside = {x["offset"] for x in seq}
        if any(dst in inside and (src, dst) not in allowed
               for src, dst in explicit):
            continue
        overlaps = False
        for h in handlers:
            _need(isinstance(h, dict)
                  and all(type(h.get(k)) is int
                          for k in ("start_pc", "end_pc", "handler_pc")),
                  "INVALID_EXCEPTION_HANDLER")
            if (h["handler_pc"] in inside
                    or any(h["start_pc"] <= pc < h["end_pc"]
                           for pc in inside)):
                overlaps = True
        if overlaps:
            continue
        prefix, suffix = recipe
        source_a = _readable_field(a, owner)
        source_b = _readable_field(b, owner)
        target = _member(key[0])
        expression = (
            json.dumps(prefix, ensure_ascii=True)
            + f" + ({source_a} == {source_b} ? {first} : {second}) + "
            + json.dumps(suffix, ensure_ascii=True)
        )
        expressions.append((store["offset"], f"    {target} = {expression};\n"))
    expressions.sort()
    snippet = (
        "// PRIVATE: exact JVM conditional-StringConcatFactory expression forms.\n"
        "// Does not reconstruct full initializer or original authorial source.\n"
        "static {\n" + "".join(t for _, t in expressions) + "}\n"
    )
    return {
        "private_source_fragment": snippet,
        "original_dynamic_final_string_count": len(final_strings),
        "exact_conditional_concat_expression_forms": len(expressions),
        "other_string_final_expression_forms_not_handled":
            len(final_strings) - len(expressions),
        "nested_enum_binary_source_equivalence_certified": False,
        "complete_jvm_clinit_order_certified": False,
        "compiled_private_expression_parity_certified": False,
        "runtime_equivalence_certified": False,
        "canonical_owner_or_field_identity_accepted": False,
    }


def build_private_conditional_concat_source(
    original_jar: Path, class_entry: str, out_dir: Path, *, original_sha256: str
) -> dict:
    jar, out = Path(original_jar), Path(out_dir)
    _need(not out.exists() and not out.is_symlink(), "OUTPUT_ALREADY_EXISTS")
    _need(type(original_sha256) is str and _PIN.fullmatch(original_sha256)
          is not None, "INVALID_COMPLETE_JAR_PIN")
    _need(jar.is_file() and not jar.is_symlink(),
          "ORIGINAL_JAR_MISSING_OR_SYMLINK")
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_JAR_SHA256_MISMATCH")
    _need(type(class_entry) is str and class_entry.endswith(".class")
          and not class_entry.startswith("/") and "\\" not in class_entry
          and all(p not in ("", ".", "..") and ":" not in p
                  for p in class_entry.split("/")),
          "INVALID_PRIVATE_CLASS_ENTRY")
    try:
        with ZipFile(jar) as z:
            _need(z.namelist().count(class_entry) == 1,
                  "ORIGINAL_OWNER_MISSING_OR_DUPLICATED")
            owner = profile_jar_class(jar, class_entry)
            class_name = owner["internal_name"]
            refs = {
                d[1:-1] for (_, d), f in _fields(owner).items()
                if (f["access"] & 0x8) and d.startswith("L" + class_name + "$")
                and d.endswith(";")
            }
            for ref in refs:
                _need(z.namelist().count(ref + ".class") == 1,
                      "ORIGINAL_ENUM_CLASS_MISSING_OR_DUPLICATED")
            enum_profiles = {
                ref: profile_jar_class(jar, ref + ".class")
                for ref in refs
            }
        proof = plan_conditional_concat_strings(owner, enum_profiles)
    except (BadZipFile, BytecodeProfileError, ScalarInitializerRecoveryError,
            KeyError, IndexError, OSError):
        raise ConditionalConcatSourceError(
            "ORIGINAL_CONCAT_JVM_EVIDENCE_UNEVALUABLE"
        ) from None
    _need(_digest(jar) == original_sha256.lower(),
          "ORIGINAL_JAR_CHANGED_DURING_PROOF")
    fragment = proof.pop("private_source_fragment")
    result = {
        "schema_version": 1,
        "kind": "original_private_conditional_string_concat_source_forms",
        "research_only": True,
        "original_complete_jar_sha256": original_sha256.lower(),
        "private_fragment_sha256":
            hashlib.sha256(fragment.encode("utf-8")).hexdigest(),
        **proof,
    }
    out.mkdir(parents=True, exist_ok=False)
    with (out / "conditional-concat-source.private.txt").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        f.write(fragment)
    with (out / "conditional-concat-aggregate.json").open(
        "x", encoding="utf-8", newline="\n"
    ) as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_jar", type=Path)
    p.add_argument("class_entry")
    p.add_argument("output_root", type=Path)
    p.add_argument("--original-sha256", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(build_private_conditional_concat_source(
            a.original_jar, a.class_entry, a.output_root,
            original_sha256=a.original_sha256,
        ), sort_keys=True))
    except ConditionalConcatSourceError as exc:
        p.error(str(exc))
    except (OSError, ValueError):
        p.error("CONDITIONAL_CONCAT_SOURCE_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
