from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any
import zipfile

from .bytecode_profile import BytecodeProfileError, profile_class_field_accesses
from .classfile import ClassFormatError, parse_class
from .decompiler import sha256_file
from .source_digest import source_tree_digest


class SourceNormalizationError(ValueError):
    pass


_SYNTHETIC_CLASS_RE = re.compile(
    r"(?m)^(?P<indent>[ \t]*)synthetic class "
    r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)[ \t]*$"
)
_DISCARDED_STRING_RE = re.compile(
    r'^(?P<indent>[ \t]*)(?P<expr>"(?:\\.|[^"\\])*"\s*\+.+);[ \t]*$'
)
_METHOD_DECL_RE = re.compile(
    r"(?m)^(?P<indent>[ \t]*)"
    r"(?:(?:public|private|protected|static|final|synchronized|strictfp)\s+)*"
    r"(?P<return>[A-Za-z_$][A-Za-z0-9_$.<>?, \[\]]*)\s+"
    r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*"
    r"\((?P<params>[^()\n]*)\)\s*"
    r"(?:throws\s+[^\{\n]+\s*)?\{"
)
_FQ_PARAM_RE = re.compile(
    r"(?:^|,)\s*(?:final\s+)?"
    r"(?P<type>[A-Za-z_$][A-Za-z0-9_$]*"
    r"(?:\.[A-Za-z_$][A-Za-z0-9_$]*)+)\s+"
    r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*(?=,|$)"
)
_IDENTIFIER = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
_JAVA_RESERVED = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch",
    "char", "class", "const", "continue", "default", "do", "double",
    "else", "enum", "extends", "final", "finally", "float", "for",
    "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private",
    "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "_",
    "true", "false", "null",
}


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _source_tree_digest(root: Path) -> tuple[str, int, int]:
    digest, files, total_bytes = source_tree_digest(root)
    return digest, len(files), total_bytes


def _is_java_identifier(name: str) -> bool:
    return bool(_IDENTIFIER.fullmatch(name)) and name not in _JAVA_RESERVED


def _line_start_contexts(text: str) -> list[tuple[int, str]]:
    """Return (lexical brace depth, lexer state) at every source-line start."""
    contexts: list[tuple[int, str]] = [(0, "code")]
    depth = 0
    state = "code"
    escaped = False
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if state == "line_comment":
            if ch == "\n":
                state = "code"
                contexts.append((depth, state))
        elif state == "block_comment":
            if ch == "*" and nxt == "/":
                state = "code"
                i += 1
            elif ch == "\n":
                contexts.append((depth, state))
        elif state == "string":
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                state = "code"
            elif ch == "\n":
                contexts.append((depth, state))
        elif state == "char":
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                state = "code"
            elif ch == "\n":
                contexts.append((depth, state))
        elif state == "text_block":
            if text.startswith('"""', i):
                state = "code"
                i += 2
            elif ch == "\n":
                contexts.append((depth, state))
        else:
            if ch == "/" and nxt == "/":
                state = "line_comment"
                i += 1
            elif ch == "/" and nxt == "*":
                state = "block_comment"
                i += 1
            elif text.startswith('"""', i):
                state = "text_block"
                i += 2
            elif ch == '"':
                state = "string"
                escaped = False
            elif ch == "'":
                state = "char"
                escaped = False
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth = max(0, depth - 1)
            elif ch == "\n":
                contexts.append((depth, state))
        i += 1
    return contexts


def _normalize_synthetic_class(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8")
    matches = list(_SYNTHETIC_CLASS_RE.finditer(text))
    if not matches:
        return None
    if len(matches) != 1:
        raise SourceNormalizationError(
            f"{path}: expected one Procyon synthetic class declaration, "
            f"found {len(matches)}"
        )

    rel = path.relative_to(source_root).as_posix()
    match = matches[0]
    name = match.group("name")
    if Path(rel).stem != name:
        raise SourceNormalizationError(
            f"{rel}: synthetic class name {name!r} does not match file stem"
        )

    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError as exc:
        raise SourceNormalizationError(
            f"{rel}: exact readable class entry {class_entry!r} is absent"
        ) from exc

    try:
        parsed = parse_class(class_bytes)
    except ClassFormatError as exc:
        raise SourceNormalizationError(
            f"{rel}: exact readable class could not be parsed: {exc}"
        ) from exc

    if parsed.name != class_entry[:-6]:
        raise SourceNormalizationError(
            f"{rel}: readable class identity disagrees with source path"
        )

    # Exact proven Procyon/Javac switch-map helper shape:
    # package-private ACC_SUPER | ACC_SYNTHETIC, Object superclass, no
    # interfaces, zero or more synthetic static-final int[] fields, and
    # either no methods or one ordinary static <clinit>.
    if parsed.access != 0x1020:
        raise SourceNormalizationError(
            f"{rel}: unsupported synthetic class access {parsed.access:#x}"
        )
    if parsed.super_name != "java/lang/Object" or parsed.interfaces:
        raise SourceNormalizationError(
            f"{rel}: unsupported synthetic class hierarchy"
        )
    for field in parsed.fields:
        if (
            field.get("access") != 0x1018
            or field.get("descriptor") != "[I"
            or not _is_java_identifier(str(field.get("name", "")))
        ):
            raise SourceNormalizationError(
                f"{rel}: unsupported synthetic field shape {field!r}"
            )
    if parsed.methods:
        if len(parsed.methods) != 1:
            raise SourceNormalizationError(
                f"{rel}: unsupported synthetic method count "
                f"{len(parsed.methods)}"
            )
        method = parsed.methods[0]
        if (
            method.get("name") != "<clinit>"
            or method.get("descriptor") != "()V"
            or method.get("access") != 0x0008
        ):
            raise SourceNormalizationError(
                f"{rel}: unsupported synthetic method shape {method!r}"
            )

    declared_fields: list[str] = []
    for field in parsed.fields:
        field_name = str(field["name"])
        declaration_re = re.compile(
            r"(?m)^[ \t]*(?:static\s+final|final\s+static)\s+"
            r"int\[\]\s+" + re.escape(field_name) + r"\s*;"
        )
        if declaration_re.search(text):
            declared_fields.append(field_name)
    if declared_fields and len(declared_fields) != len(parsed.fields):
        raise SourceNormalizationError(
            f"{rel}: Procyon emitted only a subset of exact synthetic fields"
        )

    replacement = match.group("indent") + "class " + name
    text = text[: match.start()] + replacement + text[match.end() :]

    inserted_fields: list[str] = []
    if parsed.fields and not declared_fields:
        declaration = re.search(
            r"(?m)^[ \t]*class\s+"
            + re.escape(name)
            + r"[ \t]*\n(?P<brace>[ \t]*\{[ \t]*)$",
            text,
        )
        if declaration is None:
            raise SourceNormalizationError(
                f"{rel}: normalized synthetic class opening brace is unsupported"
            )
        insert_at = declaration.end()
        block = "".join(
            "\n    static final int[] " + str(field["name"]) + ";"
            for field in parsed.fields
        )
        text = text[:insert_at] + block + text[insert_at:]
        inserted_fields = [str(field["name"]) for field in parsed.fields]

    path.write_text(text, encoding="utf-8")
    return {
        "kind": "synthetic_class_reconstruction",
        "source_path": rel,
        "class_entry": class_entry,
        "class_entry_sha256": hashlib.sha256(class_bytes).hexdigest(),
        "source_class_name": name,
        "inserted_fields": inserted_fields,
        "exact_field_count": len(parsed.fields),
        "exact_method_count": len(parsed.methods),
        "provenance": {
            "kind": "source_safety",
            "reason": "procyon_synthetic_class_pseudo_syntax",
            "strategy": "exact_readable_class_shape_reconstruction",
        },
    }


def _normalize_discarded_strings(
    *,
    source_root: Path,
    path: Path,
) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    contexts = _line_start_contexts(text)
    changed = False
    actions: list[dict[str, Any]] = []

    for index, line in enumerate(lines):
        raw = line[:-1] if line.endswith("\n") else line
        match = _DISCARDED_STRING_RE.fullmatch(raw)
        if match is None:
            continue
        if index >= len(contexts):
            raise SourceNormalizationError(
                f"{path}: missing lexical context for source line {index + 1}"
            )
        depth, state = contexts[index]
        if state != "code" or depth < 2:
            raise SourceNormalizationError(
                f"{path}: discarded string expression at line {index + 1} "
                "is not proven to be inside executable Java code"
            )

        rel = path.relative_to(source_root).as_posix()
        expression = match.group("expr")
        original = raw.strip()
        suffix = hashlib.sha256(
            (rel + "\0" + original).encode("utf-8")
        ).hexdigest()[:12]
        local_name = "recoveredDiscardedExpression_" + suffix
        if re.search(r"\b" + re.escape(local_name) + r"\b", text):
            raise SourceNormalizationError(
                f"{rel}: deterministic discarded-expression local collides"
            )

        newline = "\n" if line.endswith("\n") else ""
        replacement = (
            match.group("indent")
            + "final String "
            + local_name
            + " = "
            + expression
            + ";"
            + newline
        )
        lines[index] = replacement
        changed = True
        actions.append(
            {
                "kind": "discarded_string_expression_capture",
                "source_path": rel,
                "source_line": index + 1,
                "original_sha256": hashlib.sha256(
                    original.encode("utf-8")
                ).hexdigest(),
                "replacement_local": local_name,
                "provenance": {
                    "kind": "source_safety",
                    "reason": "java_illegal_discarded_string_expression",
                    "strategy": "preserve_evaluation_via_unused_string_local",
                },
            }
        )

    if changed:
        path.write_text("".join(lines), encoding="utf-8")
    return actions



def _matching_brace_end(text: str, brace_start: int) -> int:
    depth = 0
    state = "code"
    escaped = False
    i = brace_start
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if state == "line_comment":
            if ch == "\n":
                state = "code"
        elif state == "block_comment":
            if ch == "*" and nxt == "/":
                state = "code"
                i += 1
        elif state == "string":
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                state = "code"
        elif state == "char":
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                state = "code"
        elif state == "text_block":
            if text.startswith('"""', i):
                state = "code"
                i += 2
        else:
            if ch == "/" and nxt == "/":
                state = "line_comment"
                i += 1
            elif ch == "/" and nxt == "*":
                state = "block_comment"
                i += 1
            elif text.startswith('"""', i):
                state = "text_block"
                i += 2
            elif ch == '"':
                state = "string"
                escaped = False
            elif ch == "'":
                state = "char"
                escaped = False
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i + 1
                if depth < 0:
                    break
        i += 1
    raise SourceNormalizationError(
        f"unbalanced Java method body starting at offset {brace_start}"
    )


def _java_code_mask(text: str) -> str:
    """Mask comments and literals while preserving source offsets."""
    chars = list(text)
    state = "code"
    escaped = False
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if state == "line_comment":
            if ch == "\n":
                state = "code"
            else:
                chars[i] = " "
        elif state == "block_comment":
            chars[i] = " " if ch != "\n" else "\n"
            if ch == "*" and nxt == "/":
                chars[i + 1] = " "
                state = "code"
                i += 1
        elif state == "string":
            chars[i] = " " if ch != "\n" else "\n"
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                state = "code"
        elif state == "char":
            chars[i] = " " if ch != "\n" else "\n"
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                state = "code"
        elif state == "text_block":
            chars[i] = " " if ch != "\n" else "\n"
            if text.startswith('"""', i):
                if i + 1 < len(chars):
                    chars[i + 1] = " "
                if i + 2 < len(chars):
                    chars[i + 2] = " "
                state = "code"
                i += 2
        else:
            if ch == "/" and nxt == "/":
                chars[i] = chars[i + 1] = " "
                state = "line_comment"
                i += 1
            elif ch == "/" and nxt == "*":
                chars[i] = chars[i + 1] = " "
                state = "block_comment"
                i += 1
            elif text.startswith('"""', i):
                chars[i] = " "
                if i + 1 < len(chars):
                    chars[i + 1] = " "
                if i + 2 < len(chars):
                    chars[i + 2] = " "
                state = "text_block"
                i += 2
            elif ch == '"':
                chars[i] = " "
                state = "string"
                escaped = False
            elif ch == "'":
                chars[i] = " "
                state = "char"
                escaped = False
        i += 1
    return "".join(chars)


def _field_access_counter(
    method: dict[str, Any],
    *,
    owner: str,
    field_names: set[str],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for access in method.get("field_accesses", []):
        if access.get("owner") != owner:
            continue
        name = str(access.get("name", ""))
        if name not in field_names:
            continue
        if access.get("operation") not in {"getstatic", "putstatic"}:
            continue
        counts[name] = counts.get(name, 0) + 1
    return counts


def _normalize_shadowed_self_static_field_owners(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Qualify exact self static-field owners hidden by a same-name parameter.

    Procyon can print a.a for a self static field in a method whose parameter
    is also named a. Java then resolves the qualifier as the parameter
    expression. Rewriting is allowed only when the source field-use multiset
    exactly equals the current-owner getstatic/putstatic multiset for one
    exact method and the bytecode has no corresponding field access through
    the shadow parameter owner.
    """
    rel = path.relative_to(source_root).as_posix()
    simple_name_from_path = Path(rel).stem
    text = path.read_text(encoding="utf-8")
    potential_shadow = False
    for method_match in _METHOD_DECL_RE.finditer(text):
        if any(
            param.group("name") == simple_name_from_path
            for param in _FQ_PARAM_RE.finditer(method_match.group("params"))
        ):
            potential_shadow = True
            break
    if not potential_shadow:
        return []

    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError:
        return []

    try:
        profile = profile_class_field_accesses(class_bytes)
    except BytecodeProfileError as exc:
        raise SourceNormalizationError(
            f"{rel}: exact readable class field profile failed: {exc}"
        ) from exc

    internal_name = str(profile["internal_name"])
    simple_name = internal_name.rsplit("/", 1)[-1]
    if Path(rel).stem != simple_name:
        return []

    static_fields = {
        str(field["name"])
        for field in profile.get("fields", [])
        if int(field.get("access", 0)) & 0x0008
        and _is_java_identifier(str(field.get("name", "")))
    }
    if not static_fields:
        return []

    edits: list[tuple[int, int, str]] = []
    actions: list[dict[str, Any]] = []
    qualified_owner = internal_name.replace("/", ".")

    for match in _METHOD_DECL_RE.finditer(text):
        shadow_params = [
            param
            for param in _FQ_PARAM_RE.finditer(match.group("params"))
            if param.group("name") == simple_name
        ]
        if len(shadow_params) != 1:
            continue
        shadow_type = shadow_params[0].group("type")
        shadow_internal = shadow_type.replace(".", "/")
        if shadow_internal == internal_name:
            continue

        shadow_entry = shadow_internal + ".class"
        try:
            shadow_bytes = readable_zip.read(shadow_entry)
        except KeyError:
            continue
        try:
            shadow_profile = profile_class_field_accesses(shadow_bytes)
        except BytecodeProfileError as exc:
            raise SourceNormalizationError(
                f"{rel}: shadow class field profile failed for "
                f"{shadow_internal}: {exc}"
            ) from exc

        shadow_private_fields = {
            str(field["name"])
            for field in shadow_profile.get("fields", [])
            if int(field.get("access", 0)) & 0x0002
        }

        brace_start = text.find("{", match.start(), match.end())
        if brace_start < 0:
            continue
        body_end = _matching_brace_end(text, brace_start)
        method_text = text[match.start():body_end]
        method_code = _java_code_mask(method_text)

        source_counts: dict[str, int] = {}
        occurrences: list[tuple[int, int, str]] = []
        for field_name in sorted(static_fields):
            token = re.compile(
                r"(?<![A-Za-z0-9_$.])"
                + re.escape(simple_name)
                + r"\."
                + re.escape(field_name)
                + r"\b(?!\s*\()"
            )
            hits = list(token.finditer(method_code))
            if not hits:
                continue
            source_counts[field_name] = len(hits)
            for hit in hits:
                occurrences.append(
                    (
                        match.start() + hit.start(),
                        match.start() + hit.end(),
                        qualified_owner + "." + field_name,
                    )
                )
        if not source_counts:
            continue
        if not set(source_counts).issubset(shadow_private_fields):
            continue

        candidates = []
        for method in profile.get("methods", []):
            if method.get("name") != match.group("name"):
                continue
            descriptor = str(method.get("descriptor", ""))
            if ("L" + shadow_internal + ";") not in descriptor:
                continue
            self_counts = _field_access_counter(
                method,
                owner=internal_name,
                field_names=static_fields,
            )
            if self_counts != source_counts:
                continue
            shadow_counts = _field_access_counter(
                method,
                owner=shadow_internal,
                field_names=set(source_counts),
            )
            if shadow_counts:
                continue
            candidates.append(method)

        if len(candidates) != 1:
            continue
        exact_method = candidates[0]

        edits.extend(occurrences)
        actions.append(
            {
                "kind": "shadowed_self_static_field_owner_qualification",
                "source_path": rel,
                "method_name": match.group("name"),
                "method_descriptor": exact_method["descriptor"],
                "shadow_parameter_name": simple_name,
                "shadow_parameter_type": shadow_internal,
                "qualified_owner": internal_name,
                "field_access_counts": dict(sorted(source_counts.items())),
                "replacement_count": sum(source_counts.values()),
                "provenance": {
                    "kind": "source_safety",
                    "reason": "procyon_shadowed_self_static_field_owner",
                    "strategy": (
                        "exact_method_field_access_multiset_qualification"
                    ),
                },
            }
        )

    if not edits:
        return []

    edits.sort(key=lambda row: row[0])
    for left, right in zip(edits, edits[1:]):
        if left[1] > right[0]:
            raise SourceNormalizationError(
                f"{rel}: overlapping owner-qualification edits"
            )
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return actions



_PRIMITIVE_FIELD_DESCRIPTORS = {
    "Z", "B", "C", "S", "I", "J", "F", "D",
}


def _is_primitive_value_shadow_descriptor(descriptor: str) -> bool:
    """Return true for primitive scalars or arrays of primitive values."""
    if descriptor in _PRIMITIVE_FIELD_DESCRIPTORS:
        return True
    value = descriptor
    while value.startswith("["):
        value = value[1:]
    return (
        value in _PRIMITIVE_FIELD_DESCRIPTORS
        and value != descriptor
    )


def _is_reference_value_shadow_descriptor(descriptor: str) -> bool:
    """Return true for reference scalars or arrays of references."""
    value = descriptor
    while value.startswith("["):
        value = value[1:]
    return value.startswith("L") and value.endswith(";")


def _read_readable_hierarchy(
    *,
    readable_zip: zipfile.ZipFile,
    internal_name: str,
) -> list[tuple[str, Any]]:
    hierarchy: list[tuple[str, Any]] = []
    seen: set[str] = set()
    current: str | None = internal_name
    while current and current not in seen:
        seen.add(current)
        try:
            data = readable_zip.read(current + ".class")
        except KeyError:
            break
        try:
            parsed = parse_class(data)
        except ClassFormatError as exc:
            raise SourceNormalizationError(
                f"{internal_name}: hierarchy class {current} could not be "
                f"parsed: {exc}"
            ) from exc
        if parsed.name != current:
            raise SourceNormalizationError(
                f"{internal_name}: hierarchy identity mismatch for {current}"
            )
        hierarchy.append((current, parsed))
        current = parsed.super_name
    return hierarchy


def _field_visible_from(
    *,
    declaring_owner: str,
    current_owner: str,
    access: int,
) -> bool:
    if declaring_owner == current_owner:
        return True
    if access & 0x0002:  # private
        return False
    if access & (0x0001 | 0x0004):  # public or protected
        return True
    declaring_package = declaring_owner.rpartition("/")[0]
    current_package = current_owner.rpartition("/")[0]
    return declaring_package == current_package


def _same_name_value_shadow_spans(
    *,
    method_match: re.Match[str],
    method_code: str,
    simple_name: str,
) -> tuple[bool, list[tuple[int, int]]]:
    """Return whole-method parameter shadow plus conservative local scopes."""
    params = method_match.group("params")
    primitive_source_types = {
        "boolean", "byte", "char", "short", "int", "long", "float",
        "double",
    }
    param_name = re.compile(
        r"(?:^|,)\s*(?:final\s+)?"
        r"(?P<type>[A-Za-z_$][A-Za-z0-9_$.\[\]<>?, ]*?)\s+"
        + re.escape(simple_name)
        + r"\s*(?=,|$)"
    )
    for param in param_name.finditer(params):
        param_type = param.group("type").strip()
        if param_type not in primitive_source_types:
            return True, []

    brace = method_code.find("{")
    if brace < 0:
        return True, []
    body_start = brace + 1
    body = method_code[body_start:]
    local_name = re.compile(
        r"(?:^|[;{}]\s*|\(\s*|,\s*)\s*"
        r"(?:final\s+)?"
        r"(?P<type>[A-Za-z_$][A-Za-z0-9_$.\[\]<>?]*"
        r"(?:\s*<[^;{}()]*>)?)"
        r"\s+(?P<name>"
        + re.escape(simple_name)
        + r")\s*(?==|;|,|:|\))",
        re.MULTILINE,
    )
    spans: list[tuple[int, int]] = []
    for local in local_name.finditer(body):
        local_type = local.group("type").strip()
        if local_type in primitive_source_types:
            # A scalar primitive cannot be the receiver of `.field`; exact
            # bytecode proof can therefore establish class qualification
            # even while the primitive local shadows the class simple name.
            continue
        declaration = body_start + local.start("name")
        stack: list[int] = []
        for index, ch in enumerate(method_code[:declaration]):
            if ch == "{":
                stack.append(index)
            elif ch == "}" and stack:
                stack.pop()
        if not stack:
            spans.append((declaration, len(method_code)))
            continue
        spans.append(
            (declaration, _matching_brace_end(method_code, stack[-1]))
        )
    return False, spans


def _primitive_same_name_value_shadow_spans(
    *,
    method_match: re.Match[str],
    method_code: str,
    simple_name: str,
) -> tuple[bool, list[tuple[int, int]]]:
    """Return scalar-primitive parameter shadow plus primitive local scopes."""
    primitive_source_types = {
        "boolean", "byte", "char", "short", "int", "long", "float",
        "double",
    }
    params = method_match.group("params")
    param_name = re.compile(
        r"(?:^|,)\s*(?:final\s+)?"
        r"(?P<type>[A-Za-z_$][A-Za-z0-9_$.\[\]<>?, ]*?)\s+"
        + re.escape(simple_name)
        + r"\s*(?=,|$)"
    )
    primitive_parameter = any(
        param.group("type").strip() in primitive_source_types
        for param in param_name.finditer(params)
    )

    brace = method_code.find("{")
    if brace < 0:
        return primitive_parameter, []
    body_start = brace + 1
    body = method_code[body_start:]
    local_name = re.compile(
        r"(?:^|[;{}]\s*|\(\s*|,\s*)\s*"
        r"(?:final\s+)?"
        r"(?P<type>[A-Za-z_$][A-Za-z0-9_$.\[\]<>?]*"
        r"(?:\s*<[^;{}()]*>)?)"
        r"\s+(?P<name>"
        + re.escape(simple_name)
        + r")\s*(?==|;|,|:|\))",
        re.MULTILINE,
    )
    spans: list[tuple[int, int]] = []
    for local in local_name.finditer(body):
        if local.group("type").strip() not in primitive_source_types:
            continue
        declaration = body_start + local.start("name")
        stack: list[int] = []
        for index, ch in enumerate(method_code[:declaration]):
            if ch == "{":
                stack.append(index)
            elif ch == "}" and stack:
                stack.pop()
        if not stack:
            spans.append((declaration, len(method_code)))
            continue
        spans.append(
            (declaration, _matching_brace_end(method_code, stack[-1]))
        )
    return primitive_parameter, spans


def _method_has_same_name_value_binding(
    *,
    method_match: re.Match[str],
    method_code: str,
    simple_name: str,
) -> bool:
    parameter_shadow, local_spans = _same_name_value_shadow_spans(
        method_match=method_match,
        method_code=method_code,
        simple_name=simple_name,
    )
    return parameter_shadow or bool(local_spans)


def _source_parameter_count(params: str) -> int:
    text = params.strip()
    if not text:
        return 0
    depth = 0
    count = 1
    for ch in text:
        if ch == "<":
            depth += 1
        elif ch == ">" and depth:
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1
    return count


def _descriptor_parameter_count(descriptor: str) -> int | None:
    if not descriptor.startswith("("):
        return None
    i = 1
    count = 0
    while i < len(descriptor) and descriptor[i] != ")":
        while i < len(descriptor) and descriptor[i] == "[":
            i += 1
        if i >= len(descriptor):
            return None
        if descriptor[i] == "L":
            end = descriptor.find(";", i + 1)
            if end < 0:
                return None
            i = end + 1
        elif descriptor[i] in "ZBCSIJFD":
            i += 1
        else:
            return None
        count += 1
    if i >= len(descriptor) or descriptor[i] != ")":
        return None
    return count


def _source_parameter_shapes(
    params: str,
) -> list[tuple[int, str, str]] | None:
    text = params.strip()
    if not text:
        return []
    parts: list[str] = []
    start = 0
    depth = 0
    for index, ch in enumerate(text):
        if ch == "<":
            depth += 1
        elif ch == ">" and depth:
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())

    primitive = {
        "boolean": "Z", "byte": "B", "char": "C", "short": "S",
        "int": "I", "long": "J", "float": "F", "double": "D",
    }
    out: list[tuple[int, str, str]] = []
    for part in parts:
        value = re.sub(r"^(?:final\s+)+", "", part.strip())
        match = re.fullmatch(
            r"(?P<type>.+?)\s+"
            r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)"
            r"(?P<var_arrays>(?:\[\])*)",
            value,
        )
        if match is None:
            return None
        type_text = match.group("type").strip()
        # Erase generic arguments conservatively while preserving the raw
        # reference name around them.
        erased: list[str] = []
        generic_depth = 0
        for ch in type_text:
            if ch == "<":
                generic_depth += 1
            elif ch == ">" and generic_depth:
                generic_depth -= 1
            elif generic_depth == 0:
                erased.append(ch)
        type_text = "".join(erased).strip()
        arrays = 0
        while type_text.endswith("[]"):
            arrays += 1
            type_text = type_text[:-2].strip()
        arrays += len(match.group("var_arrays")) // 2
        if type_text in primitive:
            out.append((arrays, "primitive", primitive[type_text]))
            continue
        if not re.fullmatch(
            r"[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)*",
            type_text,
        ):
            return None
        kind = "qualified_ref" if "." in type_text else "simple_ref"
        out.append((arrays, kind, type_text))
    return out


def _descriptor_parameter_shapes(
    descriptor: str,
) -> list[tuple[int, str, str]] | None:
    if not descriptor.startswith("("):
        return None
    i = 1
    out: list[tuple[int, str, str]] = []
    while i < len(descriptor) and descriptor[i] != ")":
        arrays = 0
        while i < len(descriptor) and descriptor[i] == "[":
            arrays += 1
            i += 1
        if i >= len(descriptor):
            return None
        ch = descriptor[i]
        if ch == "L":
            end = descriptor.find(";", i + 1)
            if end < 0:
                return None
            out.append((arrays, "ref", descriptor[i + 1:end]))
            i = end + 1
        elif ch in "ZBCSIJFD":
            out.append((arrays, "primitive", ch))
            i += 1
        else:
            return None
    if i >= len(descriptor) or descriptor[i] != ")":
        return None
    return out


def _source_parameters_match_descriptor(
    params: str,
    descriptor: str,
    *,
    current_package: str | None = None,
) -> bool | None:
    source = _source_parameter_shapes(params)
    target = _descriptor_parameter_shapes(descriptor)
    if source is None or target is None:
        return None
    if len(source) != len(target):
        return False
    for (s_arrays, s_kind, s_name), (t_arrays, t_kind, t_name) in zip(
        source, target
    ):
        if s_arrays != t_arrays:
            return False
        if s_kind == "primitive":
            if t_kind != "primitive" or s_name != t_name:
                return False
            continue
        if t_kind != "ref":
            return False
        if s_kind == "qualified_ref":
            parts = s_name.split(".")
            candidates: set[str] = set()
            # A dotted Java source type can represent package separators,
            # nested-class separators, or (for a relative spelling such as
            # h.a) a type in the current package. Enumerate those exact JVM
            # spellings and require the descriptor owner to equal one.
            for split in range(1, len(parts) + 1):
                package = "/".join(parts[:split])
                nested = "$".join(parts[split:])
                candidates.add(package + (("$" + nested) if nested else ""))
            if current_package:
                relative = set()
                for candidate in candidates:
                    relative.add(current_package + "/" + candidate)
                candidates.update(relative)
            if t_name not in candidates:
                return False
        else:
            target_simple = t_name.rsplit("/", 1)[-1].rsplit("$", 1)[-1]
            if target_simple != s_name:
                return False
    return True


def _brace_depth_before(code: str, offset: int) -> int:
    depth = 0
    for ch in code[:offset]:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
    return depth


def _block_has_same_name_local_declaration(
    code: str,
    *,
    simple_name: str,
) -> bool:
    local_name = re.compile(
        r"(?:^|[;{}]\s*|\(\s*|,\s*)\s*"
        r"(?:final\s+)?"
        r"[A-Za-z_$][A-Za-z0-9_$.\[\]<>?]*"
        r"(?:\s*<[^;{}()]*>)?\s+"
        + re.escape(simple_name)
        + r"\s*(?==|;|,|:|\))",
        re.MULTILINE,
    )
    return bool(local_name.search(code))

def _hierarchy_static_field_access_counts(
    method: dict[str, Any],
    *,
    hierarchy: list[tuple[str, Any]],
    targets: dict[str, str],
) -> dict[tuple[str, str], int]:
    hierarchy_index = {
        owner: index for index, (owner, _parsed) in enumerate(hierarchy)
    }
    counts: dict[tuple[str, str], int] = {}

    for access in method.get("field_accesses", []):
        if access.get("operation") not in {"getstatic", "putstatic"}:
            continue
        field_name = str(access.get("name", ""))
        expected_declaring = targets.get(field_name)
        if expected_declaring is None:
            continue
        symbolic_owner = str(access.get("owner", ""))
        start = hierarchy_index.get(symbolic_owner)
        if start is None:
            continue

        resolved_owner: str | None = None
        for owner, parsed in hierarchy[start:]:
            declarations = [
                field
                for field in parsed.fields
                if (
                    str(field.get("name", "")) == field_name
                    and int(field.get("access", 0)) & 0x0008
                )
            ]
            if declarations:
                if len(declarations) != 1:
                    resolved_owner = None
                else:
                    resolved_owner = owner
                break

        if resolved_owner != expected_declaring:
            continue
        key = (expected_declaring, field_name)
        counts[key] = counts.get(key, 0) + 1

    return counts


def _nearest_visible_instance_reference_field(
    *,
    hierarchy: list[tuple[str, Any]],
    current_owner: str,
    field_name: str,
) -> tuple[str, str] | None:
    """Resolve the nearest visible instance reference field by Java name."""
    for owner, parsed in hierarchy:
        declarations = [
            field
            for field in parsed.fields
            if (
                str(field.get("name", "")) == field_name
                and _field_visible_from(
                    declaring_owner=owner,
                    current_owner=current_owner,
                    access=int(field.get("access", 0)),
                )
            )
        ]
        if not declarations:
            continue
        if len(declarations) != 1:
            return None
        field = declarations[0]
        if int(field.get("access", 0)) & 0x0008:
            return None
        descriptor = str(field.get("descriptor", ""))
        if not (
            descriptor.startswith("L")
            and descriptor.endswith(";")
        ):
            return None
        return owner, descriptor[1:-1]
    return None


def _hierarchy_instance_field_get_count(
    method: dict[str, Any],
    *,
    hierarchy: list[tuple[str, Any]],
    field_name: str,
    declaring_owner: str,
    descriptor: str,
) -> int:
    hierarchy_index = {
        owner: index for index, (owner, _parsed) in enumerate(hierarchy)
    }
    count = 0
    for access in method.get("field_accesses", []):
        if access.get("operation") != "getfield":
            continue
        if str(access.get("name", "")) != field_name:
            continue
        if str(access.get("descriptor", "")) != descriptor:
            continue
        symbolic_owner = str(access.get("owner", ""))
        start = hierarchy_index.get(symbolic_owner)
        if start is None:
            continue

        resolved_owner: str | None = None
        for owner, parsed in hierarchy[start:]:
            declarations = [
                field
                for field in parsed.fields
                if (
                    str(field.get("name", "")) == field_name
                    and not (int(field.get("access", 0)) & 0x0008)
                    and str(field.get("descriptor", "")) == descriptor
                )
            ]
            if declarations:
                resolved_owner = owner if len(declarations) == 1 else None
                break

        if resolved_owner == declaring_owner:
            count += 1
    return count


def _normalize_hierarchy_shadowed_self_static_field_owners(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Qualify class-static fields hidden by primitive-value shadows.

    Procyon can emit h.ae inside class h while h (or a superclass) also
    declares a primitive scalar/array field named h. javac resolves h as a value
    expression and reports "int cannot be dereferenced". Rewriting is
    allowed only when hierarchy shape, source occurrence counts and one
    exact bytecode method agree.
    """
    rel = path.relative_to(source_root).as_posix()
    simple_name_from_path = Path(rel).stem
    text = path.read_text(encoding="utf-8")
    code = _java_code_mask(text)
    candidate = re.compile(
        r"(?<![A-Za-z0-9_$.])"
        + re.escape(simple_name_from_path)
        + r"\.[A-Za-z_$][A-Za-z0-9_$]*\b"
    )
    if candidate.search(code) is None:
        return []

    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError:
        return []

    try:
        profile = profile_class_field_accesses(class_bytes)
    except BytecodeProfileError as exc:
        raise SourceNormalizationError(
            f"{rel}: exact readable class field profile failed: {exc}"
        ) from exc

    internal_name = str(profile["internal_name"])
    simple_name = internal_name.rsplit("/", 1)[-1]
    if Path(rel).stem != simple_name:
        return []

    hierarchy = _read_readable_hierarchy(
        readable_zip=readable_zip,
        internal_name=internal_name,
    )
    if not hierarchy:
        return []

    primitive_shadow_owners = [
        owner
        for owner, parsed in hierarchy
        for field in parsed.fields
        if (
            str(field.get("name", "")) == simple_name
            and _is_primitive_value_shadow_descriptor(
                str(field.get("descriptor", ""))
            )
            and _field_visible_from(
                declaring_owner=owner,
                current_owner=internal_name,
                access=int(field.get("access", 0)),
            )
        )
    ]
    if not primitive_shadow_owners:
        return []

    static_by_name: dict[str, list[str]] = {}
    for owner, parsed in hierarchy:
        for field in parsed.fields:
            name = str(field.get("name", ""))
            if (
                int(field.get("access", 0)) & 0x0008
                and _is_java_identifier(name)
                and _field_visible_from(
                    declaring_owner=owner,
                    current_owner=internal_name,
                    access=int(field.get("access", 0)),
                )
            ):
                static_by_name.setdefault(name, []).append(owner)
    static_targets = {
        name: owners[0]
        for name, owners in static_by_name.items()
        if len(owners) == 1
    }
    if not static_targets:
        return []

    qualified_owner = internal_name.replace("/", ".")
    edits: list[tuple[int, int, str]] = []
    actions: list[dict[str, Any]] = []

    for match in _METHOD_DECL_RE.finditer(text):
        brace_start = text.find("{", match.start(), match.end())
        if brace_start < 0:
            continue
        body_end = _matching_brace_end(text, brace_start)
        method_text = text[match.start():body_end]
        method_code = _java_code_mask(method_text)

        parameter_shadow, local_shadow_spans = (
            _same_name_value_shadow_spans(
                method_match=match,
                method_code=method_code,
                simple_name=simple_name,
            )
        )
        if parameter_shadow:
            continue

        source_counts: dict[tuple[str, str], int] = {}
        occurrences: list[tuple[int, int, str]] = []
        for field_name, declaring_owner in sorted(static_targets.items()):
            token = re.compile(
                r"(?<![A-Za-z0-9_$.])"
                + re.escape(simple_name)
                + r"\."
                + re.escape(field_name)
                + r"\b(?!\s*\()"
            )
            hits = [
                hit
                for hit in token.finditer(method_code)
                if not any(
                    start <= hit.start() < end
                    for start, end in local_shadow_spans
                )
            ]
            if not hits:
                continue
            source_counts[(declaring_owner, field_name)] = len(hits)
            for hit in hits:
                occurrences.append(
                    (
                        match.start() + hit.start(),
                        match.start() + hit.end(),
                        qualified_owner + "." + field_name,
                    )
                )
        if not source_counts:
            continue

        candidates: list[dict[str, Any]] = []
        source_arity = _source_parameter_count(match.group("params"))
        for method in profile.get("methods", []):
            if method.get("name") != match.group("name"):
                continue
            descriptor = str(method.get("descriptor", ""))
            if _descriptor_parameter_count(descriptor) != source_arity:
                continue
            parameter_match = _source_parameters_match_descriptor(
                match.group("params"),
                descriptor,
                current_package=internal_name.rpartition("/")[0],
            )
            if parameter_match is False:
                continue
            exact_counts = _hierarchy_static_field_access_counts(
                method,
                hierarchy=hierarchy,
                targets=static_targets,
            )
            if all(
                exact_counts.get(key, 0) >= count
                for key, count in source_counts.items()
            ):
                candidates.append(method)

        if len(candidates) != 1:
            continue

        exact_method = candidates[0]
        edits.extend(occurrences)
        actions.append(
            {
                "kind": (
                    "hierarchy_shadowed_self_static_field_owner_qualification"
                ),
                "source_path": rel,
                "method_name": match.group("name"),
                "method_descriptor": exact_method["descriptor"],
                "qualified_owner": internal_name,
                "primitive_shadow_owners": sorted(
                    set(primitive_shadow_owners)
                ),
                "field_access_counts": {
                    owner + "." + name: count
                    for (owner, name), count in sorted(
                        source_counts.items()
                    )
                },
                "replacement_count": sum(source_counts.values()),
                "provenance": {
                    "kind": "source_safety",
                    "reason": (
                        "procyon_hierarchy_primitive_value_shadowed_class_owner"
                    ),
                    "strategy": (
                        "exact_hierarchy_static_field_access_sufficiency_qualification"
                    ),
                },
            }
        )

    whole_code = _java_code_mask(text)
    static_block_re = re.compile(r"(?m)^[ \t]*static[ \t]*\{")
    exact_clinits = [
        method
        for method in profile.get("methods", [])
        if method.get("name") == "<clinit>"
        and method.get("descriptor") == "()V"
    ]
    if len(exact_clinits) == 1:
        for block_match in static_block_re.finditer(whole_code):
            brace_start = whole_code.find(
                "{", block_match.start(), block_match.end()
            )
            if (
                brace_start < 0
                or _brace_depth_before(whole_code, brace_start) != 1
            ):
                continue
            block_end = _matching_brace_end(whole_code, brace_start)
            block_code = whole_code[block_match.start():block_end]
            if _block_has_same_name_local_declaration(
                block_code, simple_name=simple_name
            ):
                continue

            block_counts: dict[tuple[str, str], int] = {}
            block_occurrences: list[tuple[int, int, str]] = []
            for field_name, declaring_owner in sorted(
                static_targets.items()
            ):
                token = re.compile(
                    r"(?<![A-Za-z0-9_$.])"
                    + re.escape(simple_name)
                    + r"\."
                    + re.escape(field_name)
                    + r"\b(?!\s*\()"
                )
                hits = list(token.finditer(block_code))
                if not hits:
                    continue
                block_counts[(declaring_owner, field_name)] = len(hits)
                for hit in hits:
                    block_occurrences.append(
                        (
                            block_match.start() + hit.start(),
                            block_match.start() + hit.end(),
                            qualified_owner + "." + field_name,
                        )
                    )
            if not block_counts:
                continue
            exact_counts = _hierarchy_static_field_access_counts(
                exact_clinits[0],
                hierarchy=hierarchy,
                targets=static_targets,
            )
            if not all(
                exact_counts.get(key, 0) >= count
                for key, count in block_counts.items()
            ):
                continue
            edits.extend(block_occurrences)
            actions.append(
                {
                    "kind": (
                        "hierarchy_shadowed_self_static_field_owner_qualification"
                    ),
                    "source_path": rel,
                    "method_name": "<clinit>",
                    "method_descriptor": "()V",
                    "qualified_owner": internal_name,
                    "primitive_shadow_owners": sorted(
                        set(primitive_shadow_owners)
                    ),
                    "field_access_counts": {
                        owner + "." + name: count
                        for (owner, name), count in sorted(
                            block_counts.items()
                        )
                    },
                    "replacement_count": sum(block_counts.values()),
                    "provenance": {
                        "kind": "source_safety",
                        "reason": (
                            "procyon_hierarchy_primitive_shadowed_class_owner"
                        ),
                        "strategy": (
                            "exact_hierarchy_static_field_access_sufficiency_qualification"
                        ),
                    },
                }
            )

    if not edits:
        return []

    edits.sort(key=lambda row: row[0])
    for left, right in zip(edits, edits[1:]):
        if left[1] > right[0]:
            raise SourceNormalizationError(
                f"{rel}: overlapping hierarchy owner-qualification edits"
            )
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return actions


def _normalize_primitive_scope_shadowed_self_static_field_owners(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Qualify self static fields hidden by primitive parameters or locals.

    Procyon can print i.c inside class i while a scalar primitive parameter
    or local named i is in scope. javac then treats i as the primitive value
    and reports that it cannot be dereferenced. Only occurrences proven by
    one exact readable bytecode method's complete static-field access
    multiset are rewritten.
    """
    rel = path.relative_to(source_root).as_posix()
    simple_name_from_path = Path(rel).stem
    text = path.read_text(encoding="utf-8")
    code = _java_code_mask(text)
    candidate = re.compile(
        r"(?<![A-Za-z0-9_$.])"
        + re.escape(simple_name_from_path)
        + r"\.[A-Za-z_$][A-Za-z0-9_$]*\b"
    )
    if candidate.search(code) is None:
        return []

    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError:
        return []

    try:
        profile = profile_class_field_accesses(class_bytes)
    except BytecodeProfileError as exc:
        raise SourceNormalizationError(
            f"{rel}: exact readable class field profile failed: {exc}"
        ) from exc

    internal_name = str(profile["internal_name"])
    simple_name = internal_name.rsplit("/", 1)[-1]
    if Path(rel).stem != simple_name:
        return []

    hierarchy = _read_readable_hierarchy(
        readable_zip=readable_zip,
        internal_name=internal_name,
    )
    if not hierarchy:
        return []

    static_by_name: dict[str, list[str]] = {}
    for owner, parsed in hierarchy:
        for field in parsed.fields:
            name = str(field.get("name", ""))
            if (
                int(field.get("access", 0)) & 0x0008
                and _is_java_identifier(name)
                and _field_visible_from(
                    declaring_owner=owner,
                    current_owner=internal_name,
                    access=int(field.get("access", 0)),
                )
            ):
                static_by_name.setdefault(name, []).append(owner)
    static_targets = {
        name: owners[0]
        for name, owners in static_by_name.items()
        if len(owners) == 1
    }
    if not static_targets:
        return []

    qualified_owner = internal_name.replace("/", ".")
    edits: list[tuple[int, int, str]] = []
    actions: list[dict[str, Any]] = []

    for match in _METHOD_DECL_RE.finditer(text):
        brace_start = text.find("{", match.start(), match.end())
        if brace_start < 0:
            continue
        body_end = _matching_brace_end(text, brace_start)
        method_text = text[match.start():body_end]
        method_code = _java_code_mask(method_text)

        reference_parameter, reference_local_spans = (
            _same_name_value_shadow_spans(
                method_match=match,
                method_code=method_code,
                simple_name=simple_name,
            )
        )
        if reference_parameter:
            continue

        primitive_parameter, primitive_local_spans = (
            _primitive_same_name_value_shadow_spans(
                method_match=match,
                method_code=method_code,
                simple_name=simple_name,
            )
        )
        if not primitive_parameter and not primitive_local_spans:
            continue

        affected_counts: dict[tuple[str, str], int] = {}
        total_source_counts: dict[tuple[str, str], int] = {}
        occurrences: list[tuple[int, int, str]] = []

        for field_name, declaring_owner in sorted(static_targets.items()):
            simple_token = re.compile(
                r"(?<![A-Za-z0-9_$.])"
                + re.escape(simple_name)
                + r"\."
                + re.escape(field_name)
                + r"\b(?!\s*\()"
            )
            simple_hits = [
                hit
                for hit in simple_token.finditer(method_code)
                if not any(
                    start <= hit.start() < end
                    for start, end in reference_local_spans
                )
            ]
            qualified_token = re.compile(
                r"(?<![A-Za-z0-9_$.])"
                + re.escape(qualified_owner)
                + r"\."
                + re.escape(field_name)
                + r"\b(?!\s*\()"
            )
            qualified_hits = list(qualified_token.finditer(method_code))

            affected_hits = [
                hit
                for hit in simple_hits
                if (
                    primitive_parameter
                    or any(
                        start <= hit.start() < end
                        for start, end in primitive_local_spans
                    )
                )
            ]
            if not affected_hits:
                continue

            key = (declaring_owner, field_name)
            affected_counts[key] = len(affected_hits)
            total_source_counts[key] = len(simple_hits) + len(qualified_hits)
            for hit in affected_hits:
                occurrences.append(
                    (
                        match.start() + hit.start(),
                        match.start() + hit.end(),
                        qualified_owner + "." + field_name,
                    )
                )

        if not affected_counts:
            continue

        candidates: list[dict[str, Any]] = []
        source_arity = _source_parameter_count(match.group("params"))
        for method in profile.get("methods", []):
            if method.get("name") != match.group("name"):
                continue
            descriptor = str(method.get("descriptor", ""))
            if _descriptor_parameter_count(descriptor) != source_arity:
                continue
            parameter_match = _source_parameters_match_descriptor(
                match.group("params"),
                descriptor,
                current_package=internal_name.rpartition("/")[0],
            )
            if parameter_match is False:
                continue

            exact_counts = _hierarchy_static_field_access_counts(
                method,
                hierarchy=hierarchy,
                targets=static_targets,
            )
            if all(
                exact_counts.get(key, 0) == count
                for key, count in total_source_counts.items()
            ):
                candidates.append(method)

        if len(candidates) != 1:
            continue

        exact_method = candidates[0]
        edits.extend(occurrences)
        actions.append(
            {
                "kind": (
                    "primitive_scope_shadowed_self_static_field_owner_qualification"
                ),
                "source_path": rel,
                "method_name": match.group("name"),
                "method_descriptor": exact_method["descriptor"],
                "qualified_owner": internal_name,
                "primitive_parameter_shadow": primitive_parameter,
                "primitive_local_shadow_scope_count": len(
                    primitive_local_spans
                ),
                "field_access_counts": {
                    owner + "." + name: count
                    for (owner, name), count in sorted(
                        affected_counts.items()
                    )
                },
                "total_field_access_counts": {
                    owner + "." + name: count
                    for (owner, name), count in sorted(
                        total_source_counts.items()
                    )
                },
                "replacement_count": sum(affected_counts.values()),
                "provenance": {
                    "kind": "source_safety",
                    "reason": (
                        "procyon_primitive_scope_shadowed_self_class_owner"
                    ),
                    "strategy": (
                        "exact_method_complete_static_field_access_qualification"
                    ),
                },
            }
        )

    if not edits:
        return []

    edits.sort(key=lambda row: row[0])
    for left, right in zip(edits, edits[1:]):
        if left[1] > right[0]:
            raise SourceNormalizationError(
                f"{rel}: overlapping primitive-scope self-owner edits"
            )
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return actions


def _normalize_primitive_shadowed_instance_field_receivers(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Restore instance-field receivers hidden by scalar primitive values.

    Procyon can emit h.a(...) while a primitive parameter/local named h
    shadows the current object's reference field h. Rewriting to this.h is
    permitted only when one exact readable method proves both the complete
    getfield count for h and the matching invokevirtual/invokeinterface
    owner/name multiset.
    """
    rel = path.relative_to(source_root).as_posix()
    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError:
        return []
    try:
        profile = profile_class_field_accesses(class_bytes)
    except BytecodeProfileError:
        return []

    current_owner = str(profile.get("internal_name", ""))
    if current_owner != class_entry[:-6]:
        return []

    hierarchy = _read_readable_hierarchy(
        readable_zip=readable_zip,
        internal_name=current_owner,
    )
    if not hierarchy:
        return []

    visible_names = sorted(
        {
            str(field.get("name", ""))
            for owner, parsed in hierarchy
            for field in parsed.fields
            if (
                _is_java_identifier(str(field.get("name", "")))
                and _field_visible_from(
                    declaring_owner=owner,
                    current_owner=current_owner,
                    access=int(field.get("access", 0)),
                )
            )
        }
    )
    receivers: dict[str, tuple[str, str]] = {}
    for simple in visible_names:
        resolved = _nearest_visible_instance_reference_field(
            hierarchy=hierarchy,
            current_owner=current_owner,
            field_name=simple,
        )
        if resolved is not None:
            receivers[simple] = resolved
    if not receivers:
        return []

    text = path.read_text(encoding="utf-8")
    whole_code = _java_code_mask(text)
    edits: list[tuple[int, int, str]] = []
    actions: list[dict[str, Any]] = []

    for match in _METHOD_DECL_RE.finditer(text):
        brace_start = text.find("{", match.start(), match.end())
        if brace_start < 0:
            continue
        header_code = whole_code[match.start():brace_start]
        if re.search(r"\bstatic\b", header_code) is not None:
            continue

        body_end = _matching_brace_end(text, brace_start)
        method_text = text[match.start():body_end]
        method_code = _java_code_mask(method_text)

        for simple, (declaring_owner, receiver_owner) in sorted(
            receivers.items()
        ):
            reference_parameter, reference_local_spans = (
                _same_name_value_shadow_spans(
                    method_match=match,
                    method_code=method_code,
                    simple_name=simple,
                )
            )
            if reference_parameter:
                continue
            primitive_parameter, primitive_local_spans = (
                _primitive_same_name_value_shadow_spans(
                    method_match=match,
                    method_code=method_code,
                    simple_name=simple,
                )
            )
            if not primitive_parameter and not primitive_local_spans:
                continue

            simple_call = re.compile(
                r"(?<![A-Za-z0-9_$.])"
                + re.escape(simple)
                + r"\.(?P<method>[A-Za-z_$][A-Za-z0-9_$]*)\s*\("
            )
            simple_hits = [
                hit
                for hit in simple_call.finditer(method_code)
                if not any(
                    start <= hit.start() < end
                    for start, end in reference_local_spans
                )
            ]
            affected_hits = [
                hit
                for hit in simple_hits
                if (
                    primitive_parameter
                    or any(
                        start <= hit.start() < end
                        for start, end in primitive_local_spans
                    )
                )
            ]
            if not affected_hits:
                continue

            qualified_call = re.compile(
                r"(?<![A-Za-z0-9_$.])this\."
                + re.escape(simple)
                + r"\.(?P<method>[A-Za-z_$][A-Za-z0-9_$]*)\s*\("
            )
            qualified_hits = list(qualified_call.finditer(method_code))

            affected_counts: dict[str, int] = {}
            total_counts: dict[str, int] = {}
            for hit in affected_hits:
                name = hit.group("method")
                affected_counts[name] = affected_counts.get(name, 0) + 1
            for hit in simple_hits + qualified_hits:
                name = hit.group("method")
                total_counts[name] = total_counts.get(name, 0) + 1

            source_arity = _source_parameter_count(match.group("params"))
            candidates: list[dict[str, Any]] = []
            field_descriptor = "L" + receiver_owner + ";"
            for method in profile.get("methods", []):
                if method.get("name") != match.group("name"):
                    continue
                descriptor = str(method.get("descriptor", ""))
                if _descriptor_parameter_count(descriptor) != source_arity:
                    continue
                parameter_match = _source_parameters_match_descriptor(
                    match.group("params"),
                    descriptor,
                    current_package=current_owner.rpartition("/")[0],
                )
                if parameter_match is False:
                    continue

                field_get_count = _hierarchy_instance_field_get_count(
                    method,
                    hierarchy=hierarchy,
                    field_name=simple,
                    declaring_owner=declaring_owner,
                    descriptor=field_descriptor,
                )
                if field_get_count != sum(total_counts.values()):
                    continue

                invocation_counts: dict[str, int] = {}
                for invocation in method.get("method_invocations", []):
                    if invocation.get("operation") not in {
                        "invokevirtual",
                        "invokeinterface",
                    }:
                        continue
                    if str(invocation.get("owner", "")) != receiver_owner:
                        continue
                    name = str(invocation.get("name", ""))
                    if name not in total_counts:
                        continue
                    invocation_counts[name] = (
                        invocation_counts.get(name, 0) + 1
                    )

                if all(
                    invocation_counts.get(name, 0) == count
                    for name, count in total_counts.items()
                ):
                    candidates.append(method)

            if len(candidates) != 1:
                continue

            exact_method = candidates[0]
            for hit in affected_hits:
                edits.append(
                    (
                        match.start() + hit.start(),
                        match.start() + hit.start() + len(simple),
                        "this." + simple,
                    )
                )
            actions.append(
                {
                    "kind": (
                        "primitive_shadowed_instance_field_receiver_qualification"
                    ),
                    "source_path": rel,
                    "method_name": match.group("name"),
                    "method_descriptor": exact_method["descriptor"],
                    "receiver_field_name": simple,
                    "receiver_declaring_owner": declaring_owner,
                    "receiver_type_owner": receiver_owner,
                    "primitive_parameter_shadow": primitive_parameter,
                    "primitive_local_shadow_scope_count": len(
                        primitive_local_spans
                    ),
                    "call_counts": dict(sorted(affected_counts.items())),
                    "total_call_counts": dict(sorted(total_counts.items())),
                    "replacement_count": len(affected_hits),
                    "provenance": {
                        "kind": "source_safety",
                        "reason": (
                            "procyon_primitive_scope_shadowed_instance_field_receiver"
                        ),
                        "strategy": (
                            "exact_getfield_and_virtual_invocation_multiset_qualification"
                        ),
                    },
                }
            )

    if not edits:
        return []

    edits.sort(key=lambda row: row[0])
    for left, right in zip(edits, edits[1:]):
        if left[1] > right[0]:
            raise SourceNormalizationError(
                f"{rel}: overlapping instance-receiver qualification edits"
            )
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return actions


def _normalize_reference_shadowed_self_static_field_owners(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Qualify self static fields hidden by a same-name reference field.

    This is the reference-valued counterpart to the primitive hierarchy rule,
    but intentionally narrower: only static source methods are considered,
    parameter/local value shadows remain excluded, and the exact readable
    bytecode must account for the complete source field-access multiset.
    """
    rel = path.relative_to(source_root).as_posix()
    simple_name_from_path = Path(rel).stem
    text = path.read_text(encoding="utf-8")
    code = _java_code_mask(text)
    candidate = re.compile(
        r"(?<![A-Za-z0-9_$.])"
        + re.escape(simple_name_from_path)
        + r"\.[A-Za-z_$][A-Za-z0-9_$]*\b"
    )
    if candidate.search(code) is None:
        return []

    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError:
        return []

    try:
        profile = profile_class_field_accesses(class_bytes)
    except BytecodeProfileError as exc:
        raise SourceNormalizationError(
            f"{rel}: exact readable class field profile failed: {exc}"
        ) from exc

    internal_name = str(profile["internal_name"])
    simple_name = internal_name.rsplit("/", 1)[-1]
    if Path(rel).stem != simple_name:
        return []

    hierarchy = _read_readable_hierarchy(
        readable_zip=readable_zip,
        internal_name=internal_name,
    )
    if not hierarchy:
        return []

    reference_shadow_owners = [
        owner
        for owner, parsed in hierarchy
        for field in parsed.fields
        if (
            str(field.get("name", "")) == simple_name
            and not (int(field.get("access", 0)) & 0x0008)
            and _is_reference_value_shadow_descriptor(
                str(field.get("descriptor", ""))
            )
            and _field_visible_from(
                declaring_owner=owner,
                current_owner=internal_name,
                access=int(field.get("access", 0)),
            )
        )
    ]
    if not reference_shadow_owners:
        return []

    static_by_name: dict[str, list[str]] = {}
    for owner, parsed in hierarchy:
        for field in parsed.fields:
            name = str(field.get("name", ""))
            if (
                int(field.get("access", 0)) & 0x0008
                and _is_java_identifier(name)
                and _field_visible_from(
                    declaring_owner=owner,
                    current_owner=internal_name,
                    access=int(field.get("access", 0)),
                )
            ):
                static_by_name.setdefault(name, []).append(owner)
    static_targets = {
        name: owners[0]
        for name, owners in static_by_name.items()
        if len(owners) == 1
    }
    if not static_targets:
        return []

    qualified_owner = internal_name.replace("/", ".")
    edits: list[tuple[int, int, str]] = []
    actions: list[dict[str, Any]] = []

    for match in _METHOD_DECL_RE.finditer(text):
        brace_start = text.find("{", match.start(), match.end())
        if brace_start < 0:
            continue
        header_code = code[match.start():brace_start]
        if re.search(r"\bstatic\b", header_code) is None:
            continue

        body_end = _matching_brace_end(text, brace_start)
        method_text = text[match.start():body_end]
        method_code = _java_code_mask(method_text)

        parameter_shadow, local_shadow_spans = (
            _same_name_value_shadow_spans(
                method_match=match,
                method_code=method_code,
                simple_name=simple_name,
            )
        )
        if parameter_shadow:
            continue

        source_counts: dict[tuple[str, str], int] = {}
        total_source_counts: dict[tuple[str, str], int] = {}
        occurrences: list[tuple[int, int, str]] = []

        for field_name, declaring_owner in sorted(static_targets.items()):
            simple_token = re.compile(
                r"(?<![A-Za-z0-9_$.])"
                + re.escape(simple_name)
                + r"\."
                + re.escape(field_name)
                + r"\b(?!\s*\()"
            )
            simple_hits = [
                hit
                for hit in simple_token.finditer(method_code)
                if not any(
                    start <= hit.start() < end
                    for start, end in local_shadow_spans
                )
            ]
            if not simple_hits:
                continue

            qualified_token = re.compile(
                r"(?<![A-Za-z0-9_$.])"
                + re.escape(qualified_owner)
                + r"\."
                + re.escape(field_name)
                + r"\b(?!\s*\()"
            )
            qualified_hits = list(qualified_token.finditer(method_code))

            key = (declaring_owner, field_name)
            source_counts[key] = len(simple_hits)
            total_source_counts[key] = len(simple_hits) + len(qualified_hits)
            for hit in simple_hits:
                occurrences.append(
                    (
                        match.start() + hit.start(),
                        match.start() + hit.end(),
                        qualified_owner + "." + field_name,
                    )
                )

        if not source_counts:
            continue

        candidates: list[dict[str, Any]] = []
        source_arity = _source_parameter_count(match.group("params"))
        for method in profile.get("methods", []):
            if method.get("name") != match.group("name"):
                continue
            if not (int(method.get("access", 0)) & 0x0008):
                continue
            descriptor = str(method.get("descriptor", ""))
            if _descriptor_parameter_count(descriptor) != source_arity:
                continue
            parameter_match = _source_parameters_match_descriptor(
                match.group("params"),
                descriptor,
                current_package=internal_name.rpartition("/")[0],
            )
            if parameter_match is False:
                continue

            exact_counts = _hierarchy_static_field_access_counts(
                method,
                hierarchy=hierarchy,
                targets=static_targets,
            )
            if all(
                exact_counts.get(key, 0) == count
                for key, count in total_source_counts.items()
            ):
                candidates.append(method)

        if len(candidates) != 1:
            continue

        exact_method = candidates[0]
        edits.extend(occurrences)
        actions.append(
            {
                "kind": (
                    "reference_shadowed_self_static_field_owner_qualification"
                ),
                "source_path": rel,
                "method_name": match.group("name"),
                "method_descriptor": exact_method["descriptor"],
                "qualified_owner": internal_name,
                "reference_shadow_owners": sorted(
                    set(reference_shadow_owners)
                ),
                "field_access_counts": {
                    owner + "." + name: count
                    for (owner, name), count in sorted(source_counts.items())
                },
                "total_field_access_counts": {
                    owner + "." + name: count
                    for (owner, name), count in sorted(
                        total_source_counts.items()
                    )
                },
                "replacement_count": sum(source_counts.values()),
                "provenance": {
                    "kind": "source_safety",
                    "reason": (
                        "procyon_reference_value_shadowed_self_class_owner"
                    ),
                    "strategy": (
                        "exact_static_method_complete_field_access_qualification"
                    ),
                },
            }
        )

    if not edits:
        return []

    edits.sort(key=lambda row: row[0])
    for left, right in zip(edits, edits[1:]):
        if left[1] > right[0]:
            raise SourceNormalizationError(
                f"{rel}: overlapping reference self-owner edits"
            )
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return actions


_DOTTED_STATIC_FIELD_RE = re.compile(
    r"(?<![A-Za-z0-9_$])"
    r"(?P<owner>[A-Za-z_$][A-Za-z0-9_$]*"
    r"(?:\.[A-Za-z_$][A-Za-z0-9_$]*){2,})"
    r"\.(?P<field>[A-Za-z_$][A-Za-z0-9_$]*)\b"
    r"(?!\s*\()"
)


def _java_owner_binary_candidates(owner: str) -> list[str]:
    parts = owner.split(".")
    candidates: list[str] = []
    for split in range(1, len(parts) + 1):
        package = "/".join(parts[:split])
        nested = "$".join(parts[split:])
        candidate = package + (("$" + nested) if nested else "")
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _nested_owner_has_visible_name_shadow(
    *,
    nested_internal: str,
    current_owner: str,
    readable_zip: zipfile.ZipFile,
) -> tuple[bool, list[str]]:
    if "$" not in nested_internal.rsplit("/", 1)[-1]:
        return False, []

    outer_internal, nested_simple = nested_internal.rsplit("$", 1)
    if not _is_java_identifier(nested_simple):
        return False, []

    hierarchy = _read_readable_hierarchy(
        readable_zip=readable_zip,
        internal_name=outer_internal,
    )
    if not hierarchy:
        return False, []

    shadow_owners: list[str] = []
    for declaring_owner, parsed in hierarchy:
        for field in parsed.fields:
            if str(field.get("name", "")) != nested_simple:
                continue
            if not _field_visible_from(
                declaring_owner=declaring_owner,
                current_owner=current_owner,
                access=int(field.get("access", 0)),
            ):
                continue
            shadow_owners.append(declaring_owner)

    return bool(shadow_owners), sorted(set(shadow_owners))


def _resolve_shadowed_nested_static_field(
    *,
    owner: str,
    field_name: str,
    current_owner: str,
    readable_zip: zipfile.ZipFile,
    entries: set[str],
    class_cache: dict[str, Any],
) -> tuple[str, list[str]] | None:
    matches: list[tuple[str, list[str]]] = []

    for candidate in _java_owner_binary_candidates(owner):
        entry = candidate + ".class"
        if entry not in entries:
            continue
        if "$" not in candidate.rsplit("/", 1)[-1]:
            continue

        parsed = class_cache.get(candidate)
        if parsed is None:
            try:
                parsed = parse_class(readable_zip.read(entry))
            except (KeyError, ClassFormatError):
                continue
            class_cache[candidate] = parsed

        declarations = [
            field
            for field in parsed.fields
            if (
                str(field.get("name", "")) == field_name
                and int(field.get("access", 0)) & 0x0008
            )
        ]
        if len(declarations) != 1:
            continue

        shadowed, shadow_owners = _nested_owner_has_visible_name_shadow(
            nested_internal=candidate,
            current_owner=current_owner,
            readable_zip=readable_zip,
        )
        if not shadowed:
            continue

        matches.append((candidate, shadow_owners))

    if len(matches) != 1:
        return None
    return matches[0]


def _normalize_shadowed_nested_static_field_owners(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Force shadowed nested static-field owners into Java type context.

    Procyon can emit pkg.Outer.Inner.FIELD for a JVM getstatic/putstatic
    owned by pkg/Outer$Inner. If Outer or one of its superclasses also
    exposes a field named Inner, javac resolves Inner as that value in
    expression context and the otherwise exact source becomes illegal.

    A null cast to pkg.Outer.Inner forces the owner through a type context
    while preserving Java static-field semantics. Rewrites are made only
    when one source method and one exact readable bytecode method agree on
    every affected nested-owner static-field access.
    """
    rel = path.relative_to(source_root).as_posix()
    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError:
        return []

    try:
        profile = profile_class_field_accesses(class_bytes)
    except BytecodeProfileError:
        # Some synthetic/unit-test workspaces intentionally use placeholder
        # class bytes. This optional normalization has no exact bytecode
        # authority in that case, so fail closed by making no source edit.
        return []

    current_owner = str(profile["internal_name"])
    text = path.read_text(encoding="utf-8")
    if "." not in text:
        return []

    entries = {
        info.filename
        for info in readable_zip.infolist()
        if not info.is_dir() and info.filename.endswith(".class")
    }
    class_cache: dict[str, Any] = {}

    edits: list[tuple[int, int, str]] = []
    actions: list[dict[str, Any]] = []

    for match in _METHOD_DECL_RE.finditer(text):
        brace_start = text.find("{", match.start(), match.end())
        if brace_start < 0:
            continue
        body_end = _matching_brace_end(text, brace_start)
        method_text = text[match.start():body_end]
        method_code = _java_code_mask(method_text)

        source_counts: dict[tuple[str, str, str], int] = {}
        source_occurrences: dict[
            tuple[str, str, str],
            list[tuple[int, int, str]],
        ] = {}
        shadow_owners_by_key: dict[
            tuple[str, str, str],
            list[str],
        ] = {}

        for token in _DOTTED_STATIC_FIELD_RE.finditer(method_code):
            owner = token.group("owner")
            field_name = token.group("field")
            resolved = _resolve_shadowed_nested_static_field(
                owner=owner,
                field_name=field_name,
                current_owner=current_owner,
                readable_zip=readable_zip,
                entries=entries,
                class_cache=class_cache,
            )
            if resolved is None:
                continue

            nested_internal, shadow_owners = resolved
            key = (nested_internal, field_name, owner)
            source_counts[key] = source_counts.get(key, 0) + 1
            shadow_owners_by_key[key] = shadow_owners
            source_occurrences.setdefault(key, []).append(
                (
                    match.start() + token.start(),
                    match.start() + token.end(),
                    "((" + owner + ")null)." + field_name,
                )
            )

        if not source_counts:
            continue

        candidates: list[dict[str, Any]] = []
        source_arity = _source_parameter_count(match.group("params"))
        for method in profile.get("methods", []):
            if method.get("name") != match.group("name"):
                continue
            descriptor = str(method.get("descriptor", ""))
            if _descriptor_parameter_count(descriptor) != source_arity:
                continue
            parameter_match = _source_parameters_match_descriptor(
                match.group("params"),
                descriptor,
                current_package=current_owner.rpartition("/")[0],
            )
            if parameter_match is False:
                continue

            byte_counts: dict[tuple[str, str, str], int] = {}
            for access in method.get("field_accesses", []):
                if access.get("operation") not in {"getstatic", "putstatic"}:
                    continue
                for key in source_counts:
                    nested_internal, field_name, _owner = key
                    if (
                        str(access.get("owner", "")) == nested_internal
                        and str(access.get("name", "")) == field_name
                    ):
                        byte_counts[key] = byte_counts.get(key, 0) + 1

            if all(
                byte_counts.get(key, 0) == count
                for key, count in source_counts.items()
            ):
                candidates.append(method)

        if len(candidates) != 1:
            continue

        exact_method = candidates[0]
        method_edits = [
            edit
            for key in source_counts
            for edit in source_occurrences[key]
        ]
        edits.extend(method_edits)

        actions.append(
            {
                "kind": (
                    "shadowed_nested_static_field_owner_type_context"
                ),
                "source_path": rel,
                "method_name": match.group("name"),
                "method_descriptor": exact_method["descriptor"],
                "nested_owners": sorted(
                    {key[0] for key in source_counts}
                ),
                "shadow_declaring_owners": sorted(
                    {
                        shadow_owner
                        for key in source_counts
                        for shadow_owner in shadow_owners_by_key[key]
                    }
                ),
                "field_access_counts": {
                    nested + "." + field: count
                    for (nested, field, _owner), count in sorted(
                        source_counts.items()
                    )
                },
                "replacement_count": sum(source_counts.values()),
                "provenance": {
                    "kind": "source_safety",
                    "reason": (
                        "procyon_nested_type_hidden_by_enclosing_hierarchy_field"
                    ),
                    "strategy": (
                        "exact_bytecode_static_field_type_context_qualification"
                    ),
                },
            }
        )


    simple_name = current_owner.rsplit("/", 1)[-1]
    constructor_re = re.compile(
        r"(?m)^(?P<indent>[ \t]*)"
        r"(?:(?:public|private|protected)\s+)*"
        + re.escape(simple_name)
        + r"\s*\((?P<params>[^()\n]*)\)\s*"
        r"(?:throws\s+[^\{\n]+\s*)?\{"
    )
    for match in constructor_re.finditer(text):
        brace_start = text.find("{", match.start(), match.end())
        if brace_start < 0:
            continue
        body_end = _matching_brace_end(text, brace_start)
        constructor_text = text[match.start():body_end]
        constructor_code = _java_code_mask(constructor_text)

        source_counts: dict[tuple[str, str, str], int] = {}
        source_occurrences: dict[
            tuple[str, str, str],
            list[tuple[int, int, str]],
        ] = {}
        shadow_owners_by_key: dict[
            tuple[str, str, str],
            list[str],
        ] = {}

        for token in _DOTTED_STATIC_FIELD_RE.finditer(constructor_code):
            owner = token.group("owner")
            field_name = token.group("field")
            resolved = _resolve_shadowed_nested_static_field(
                owner=owner,
                field_name=field_name,
                current_owner=current_owner,
                readable_zip=readable_zip,
                entries=entries,
                class_cache=class_cache,
            )
            if resolved is None:
                continue

            nested_internal, shadow_owners = resolved
            key = (nested_internal, field_name, owner)
            source_counts[key] = source_counts.get(key, 0) + 1
            shadow_owners_by_key[key] = shadow_owners
            source_occurrences.setdefault(key, []).append(
                (
                    match.start() + token.start(),
                    match.start() + token.end(),
                    "((" + owner + ")null)." + field_name,
                )
            )

        if not source_counts:
            continue

        candidates: list[dict[str, Any]] = []
        source_arity = _source_parameter_count(match.group("params"))
        for method in profile.get("methods", []):
            if method.get("name") != "<init>":
                continue
            descriptor = str(method.get("descriptor", ""))
            if _descriptor_parameter_count(descriptor) != source_arity:
                continue
            parameter_match = _source_parameters_match_descriptor(
                match.group("params"),
                descriptor,
                current_package=current_owner.rpartition("/")[0],
            )
            if parameter_match is False:
                continue

            byte_counts: dict[tuple[str, str, str], int] = {}
            for access in method.get("field_accesses", []):
                if access.get("operation") not in {"getstatic", "putstatic"}:
                    continue
                for key in source_counts:
                    nested_internal, field_name, _owner = key
                    if (
                        str(access.get("owner", "")) == nested_internal
                        and str(access.get("name", "")) == field_name
                    ):
                        byte_counts[key] = byte_counts.get(key, 0) + 1

            if all(
                byte_counts.get(key, 0) == count
                for key, count in source_counts.items()
            ):
                candidates.append(method)

        if len(candidates) != 1:
            continue

        exact_method = candidates[0]
        constructor_edits = [
            edit
            for key in source_counts
            for edit in source_occurrences[key]
        ]
        edits.extend(constructor_edits)

        actions.append(
            {
                "kind": (
                    "shadowed_nested_static_field_owner_type_context"
                ),
                "source_path": rel,
                "method_name": "<init>",
                "method_descriptor": exact_method["descriptor"],
                "nested_owners": sorted(
                    {key[0] for key in source_counts}
                ),
                "shadow_declaring_owners": sorted(
                    {
                        shadow_owner
                        for key in source_counts
                        for shadow_owner in shadow_owners_by_key[key]
                    }
                ),
                "field_access_counts": {
                    nested + "." + field: count
                    for (nested, field, _owner), count in sorted(
                        source_counts.items()
                    )
                },
                "replacement_count": sum(source_counts.values()),
                "provenance": {
                    "kind": "source_safety",
                    "reason": (
                        "procyon_nested_type_hidden_by_enclosing_hierarchy_field"
                    ),
                    "strategy": (
                        "exact_constructor_descriptor_static_field_type_context_qualification"
                    ),
                },
            }
        )

    if not edits:
        return []

    edits.sort(key=lambda row: row[0])
    for left, right in zip(edits, edits[1:]):
        if left[1] > right[0]:
            raise SourceNormalizationError(
                f"{rel}: overlapping nested-owner type-context edits"
            )
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return actions

_PACKAGE_DECL_RE = re.compile(
    r"(?m)^\s*package\s+"
    r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)*)"
    r"\s*;"
)
_SINGLE_TYPE_IMPORT_RE = re.compile(
    r"(?m)^\s*import\s+(?!static\s+)"
    r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)+)"
    r"\s*;"
)


def _parameter_type_spans(
    params: str,
) -> list[tuple[int, int, str]] | None:
    if not params.strip():
        return []

    bounds: list[tuple[int, int]] = []
    start = 0
    depth = 0
    for index, ch in enumerate(params):
        if ch == "<":
            depth += 1
        elif ch == ">" and depth:
            depth -= 1
        elif ch == "," and depth == 0:
            bounds.append((start, index))
            start = index + 1
    bounds.append((start, len(params)))

    out: list[tuple[int, int, str]] = []
    for left, right in bounds:
        raw = params[left:right]
        match = re.fullmatch(
            r"(?P<prefix>\s*(?:(?:final)\s+)*)"
            r"(?P<type>.+?)"
            r"(?P<gap>\s+)"
            r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)"
            r"(?P<var_arrays>(?:\[\])*)"
            r"\s*",
            raw,
        )
        if match is None:
            return None
        type_text = match.group("type").strip()
        type_left = left + match.start("type")
        type_right = left + match.end("type")
        # Exclude surrounding whitespace captured by the lazy type group.
        while type_left < type_right and params[type_left].isspace():
            type_left += 1
        while type_right > type_left and params[type_right - 1].isspace():
            type_right -= 1
        out.append((type_left, type_right, type_text))
    return out


def _normalize_imported_parameter_types_shadowed_by_same_package(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Qualify imported parameter types hidden by a same-package source type.

    Java gives a same-package type precedence during a multi-source compile.
    Procyon can still emit a single-type import and a simple parameter type
    matching an exact descriptor from the imported package. When another
    recovered source unit declares the same simple name in the current
    package, javac silently rebinds the parameter to that local package type.

    Rewrite only the parameter type token whose exact bytecode descriptor
    resolves to the imported owner. Method bodies are left untouched.
    """
    rel = path.relative_to(source_root).as_posix()
    text = path.read_text(encoding="utf-8")

    package_match = _PACKAGE_DECL_RE.search(text)
    if package_match is None:
        return []
    package_name = package_match.group("name")
    package_internal = package_name.replace(".", "/")

    imports: dict[str, str] = {}
    duplicate_imports: set[str] = set()
    for import_match in _SINGLE_TYPE_IMPORT_RE.finditer(text):
        dotted = import_match.group("name")
        simple = dotted.rsplit(".", 1)[-1]
        internal = dotted.replace(".", "/")
        previous = imports.get(simple)
        if previous is not None and previous != internal:
            duplicate_imports.add(simple)
        else:
            imports[simple] = internal
    for simple in duplicate_imports:
        imports.pop(simple, None)
    if not imports:
        return []

    shadowed: dict[str, tuple[str, str]] = {}
    for simple, imported_internal in imports.items():
        same_package_internal = package_internal + "/" + simple
        if same_package_internal == imported_internal:
            continue
        if not (source_root / package_internal / (simple + ".java")).is_file():
            continue
        try:
            readable_zip.getinfo(imported_internal + ".class")
            readable_zip.getinfo(same_package_internal + ".class")
        except KeyError:
            continue
        shadowed[simple] = (imported_internal, same_package_internal)
    if not shadowed:
        return []

    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError:
        return []
    try:
        profile = profile_class_field_accesses(class_bytes)
    except BytecodeProfileError:
        return []

    current_owner = str(profile.get("internal_name", ""))
    if current_owner != class_entry[:-6]:
        return []

    edits: list[tuple[int, int, str]] = []
    actions: list[dict[str, Any]] = []

    for match in _METHOD_DECL_RE.finditer(text):
        params = match.group("params")
        spans = _parameter_type_spans(params)
        shapes = _source_parameter_shapes(params)
        if spans is None or shapes is None or len(spans) != len(shapes):
            continue

        shadow_positions: dict[int, tuple[str, str, str]] = {}
        for index, ((_, _, type_text), shape) in enumerate(zip(spans, shapes)):
            arrays, kind, source_name = shape
            if kind != "simple_ref":
                continue
            details = shadowed.get(source_name)
            if details is None:
                continue
            imported_internal, same_package_internal = details
            # Parameter arrays do not affect the owner identity; the exact
            # descriptor shape check below still requires matching dimensions.
            shadow_positions[index] = (
                source_name,
                imported_internal,
                same_package_internal,
            )
        if not shadow_positions:
            continue

        candidates: list[tuple[dict[str, Any], list[tuple[int, str, str]]]] = []
        for method in profile.get("methods", []):
            if method.get("name") != match.group("name"):
                continue
            descriptor = str(method.get("descriptor", ""))
            if _source_parameters_match_descriptor(
                params,
                descriptor,
                current_package=package_internal,
            ) is False:
                continue
            descriptor_shapes = _descriptor_parameter_shapes(descriptor)
            if descriptor_shapes is None or len(descriptor_shapes) != len(shapes):
                continue
            candidates.append((method, descriptor_shapes))

        if len(candidates) != 1:
            continue

        exact_method, descriptor_shapes = candidates[0]
        replacements: list[dict[str, Any]] = []

        for index, (simple, imported_internal, same_package_internal) in sorted(
            shadow_positions.items()
        ):
            s_arrays, _s_kind, _s_name = shapes[index]
            t_arrays, t_kind, t_name = descriptor_shapes[index]
            if s_arrays != t_arrays or t_kind != "ref":
                continue
            if t_name == same_package_internal:
                continue
            if t_name != imported_internal:
                continue

            type_left, type_right, type_text = spans[index]
            if type_text != simple:
                continue
            absolute_left = match.start("params") + type_left
            absolute_right = match.start("params") + type_right
            replacement = imported_internal.replace("/", ".")
            edits.append((absolute_left, absolute_right, replacement))
            replacements.append(
                {
                    "parameter_index": index,
                    "simple_name": simple,
                    "imported_owner": imported_internal,
                    "same_package_owner": same_package_internal,
                    "qualified_type": replacement,
                }
            )

        if replacements:
            actions.append(
                {
                    "kind": (
                        "imported_parameter_type_shadowed_by_same_package"
                    ),
                    "source_path": rel,
                    "method_name": match.group("name"),
                    "method_descriptor": exact_method["descriptor"],
                    "replacements": replacements,
                    "replacement_count": len(replacements),
                    "provenance": {
                        "kind": "source_safety",
                        "reason": (
                            "procyon_imported_simple_type_hidden_by_same_package_source"
                        ),
                        "strategy": (
                            "exact_method_descriptor_parameter_qualification"
                        ),
                    },
                }
            )

    if not edits:
        return []

    edits.sort(key=lambda row: row[0])
    for left, right in zip(edits, edits[1:]):
        if left[1] > right[0]:
            raise SourceNormalizationError(
                f"{rel}: overlapping imported-parameter qualification edits"
            )
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return actions


def _normalize_imported_static_field_owners_shadowed_by_values(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Force shadowed imported static-field owners through type context.

    Procyon may emit ImportedType.FIELD inside static methods or a class-level
    static initializer even when the current hierarchy exposes a non-static
    field named ImportedType. javac then binds the simple owner to that value.

    Rewrite only explicit single-type imports whose owner/field accesses are
    proven one-for-one by the exact readable method bytecode.
    """
    rel = path.relative_to(source_root).as_posix()
    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError:
        return []

    try:
        profile = profile_class_field_accesses(class_bytes)
    except BytecodeProfileError:
        return []

    current_owner = str(profile.get("internal_name", ""))
    if current_owner != class_entry[:-6]:
        return []

    text = path.read_text(encoding="utf-8")
    imports: dict[str, str] = {}
    duplicates: set[str] = set()
    for import_match in _SINGLE_TYPE_IMPORT_RE.finditer(text):
        dotted = import_match.group("name")
        simple = dotted.rsplit(".", 1)[-1]
        internal = dotted.replace(".", "/")
        previous = imports.get(simple)
        if previous is not None and previous != internal:
            duplicates.add(simple)
        else:
            imports[simple] = internal
    for simple in duplicates:
        imports.pop(simple, None)
    if not imports:
        return []

    hierarchy = _read_readable_hierarchy(
        readable_zip=readable_zip,
        internal_name=current_owner,
    )

    shadowed: dict[str, tuple[str, list[str], Any]] = {}
    for simple, imported_internal in sorted(imports.items()):
        shadow_owners: list[str] = []
        for owner, parsed in hierarchy:
            for field in parsed.fields:
                if (
                    str(field.get("name", "")) == simple
                    and not (int(field.get("access", 0)) & 0x0008)
                    and _field_visible_from(
                        declaring_owner=owner,
                        current_owner=current_owner,
                        access=int(field.get("access", 0)),
                    )
                ):
                    shadow_owners.append(owner)

        if not shadow_owners:
            continue

        try:
            imported = parse_class(
                readable_zip.read(imported_internal + ".class")
            )
        except (KeyError, ClassFormatError):
            continue
        if imported.name != imported_internal:
            continue

        shadowed[simple] = (
            imported_internal,
            sorted(set(shadow_owners)),
            imported,
        )

    if not shadowed:
        return []

    whole_code = _java_code_mask(text)
    edits: list[tuple[int, int, str]] = []
    actions: list[dict[str, Any]] = []

    for method_match in _METHOD_DECL_RE.finditer(text):
        brace_start = text.find(
            "{", method_match.start(), method_match.end()
        )
        if brace_start < 0:
            continue

        header_code = whole_code[method_match.start():brace_start]
        if re.search(r"\bstatic\b", header_code) is None:
            continue

        body_end = _matching_brace_end(text, brace_start)
        method_text = text[method_match.start():body_end]
        method_code = _java_code_mask(method_text)

        source_counts: dict[tuple[str, str, str], int] = {}
        occurrences: list[tuple[int, int, str]] = []
        shadow_owners_by_simple: dict[str, list[str]] = {}

        for simple, (
            imported_internal,
            shadow_owners,
            imported,
        ) in sorted(shadowed.items()):
            parameter_shadow, local_shadow_spans = (
                _same_name_value_shadow_spans(
                    method_match=method_match,
                    method_code=method_code,
                    simple_name=simple,
                )
            )
            if parameter_shadow:
                continue

            shadow_owners_by_simple[simple] = shadow_owners

            for field in imported.fields:
                field_name = str(field.get("name", ""))
                access = int(field.get("access", 0))
                if (
                    not (access & 0x0008)
                    or not _is_java_identifier(field_name)
                    or not _field_visible_from(
                        declaring_owner=imported_internal,
                        current_owner=current_owner,
                        access=access,
                    )
                ):
                    continue

                token = re.compile(
                    r"(?<![A-Za-z0-9_$.])"
                    + re.escape(simple)
                    + r"\."
                    + re.escape(field_name)
                    + r"\b(?!\s*\()"
                )
                hits = [
                    hit
                    for hit in token.finditer(method_code)
                    if not any(
                        start <= hit.start() < end
                        for start, end in local_shadow_spans
                    )
                ]
                if not hits:
                    continue

                key = (imported_internal, field_name, simple)
                source_counts[key] = len(hits)
                qualified = imported_internal.replace("/", ".")
                for hit in hits:
                    occurrences.append(
                        (
                            method_match.start() + hit.start(),
                            method_match.start() + hit.end(),
                            "((" + qualified + ")null)." + field_name,
                        )
                    )

        if not source_counts:
            continue

        candidates: list[dict[str, Any]] = []
        source_arity = _source_parameter_count(
            method_match.group("params")
        )

        for method in profile.get("methods", []):
            if method.get("name") != method_match.group("name"):
                continue
            if not (int(method.get("access", 0)) & 0x0008):
                continue

            descriptor = str(method.get("descriptor", ""))
            if _descriptor_parameter_count(descriptor) != source_arity:
                continue

            parameter_match = _source_parameters_match_descriptor(
                method_match.group("params"),
                descriptor,
                current_package=current_owner.rpartition("/")[0],
            )
            if parameter_match is False:
                continue

            byte_counts: dict[tuple[str, str, str], int] = {}
            for access in method.get("field_accesses", []):
                if access.get("operation") not in {"getstatic", "putstatic"}:
                    continue
                for key in source_counts:
                    imported_internal, field_name, _simple = key
                    if (
                        str(access.get("owner", ""))
                        == imported_internal
                        and str(access.get("name", "")) == field_name
                    ):
                        byte_counts[key] = byte_counts.get(key, 0) + 1

            if all(
                byte_counts.get(key, 0) == count
                for key, count in source_counts.items()
            ):
                candidates.append(method)

        if len(candidates) != 1:
            continue

        exact_method = candidates[0]
        edits.extend(occurrences)
        actions.append(
            {
                "kind": (
                    "shadowed_imported_static_field_owner_type_context"
                ),
                "source_path": rel,
                "method_name": method_match.group("name"),
                "method_descriptor": exact_method["descriptor"],
                "imported_owners": sorted(
                    {key[0] for key in source_counts}
                ),
                "shadow_declaring_owners": sorted(
                    {
                        owner
                        for _imported, _field, simple in source_counts
                        for owner in shadow_owners_by_simple[simple]
                    }
                ),
                "field_access_counts": {
                    imported + "." + field: count
                    for (imported, field, _simple), count in sorted(
                        source_counts.items()
                    )
                },
                "replacement_count": sum(source_counts.values()),
                "provenance": {
                    "kind": "source_safety",
                    "reason": (
                        "procyon_imported_type_hidden_by_visible_value_in_static_method"
                    ),
                    "strategy": (
                        "exact_static_method_field_type_context_qualification"
                    ),
                },
            }
        )


    exact_clinits = [
        method
        for method in profile.get("methods", [])
        if method.get("name") == "<clinit>"
        and method.get("descriptor") == "()V"
    ]
    if len(exact_clinits) != 1:
        if not edits:
            return []
        edits.sort(key=lambda row: row[0])
        for left, right in zip(edits, edits[1:]):
            if left[1] > right[0]:
                raise SourceNormalizationError(
                    f"{rel}: overlapping imported-owner type-context edits"
                )
        for start, end, replacement in reversed(edits):
            text = text[:start] + replacement + text[end:]
        path.write_text(text, encoding="utf-8")
        return actions

    exact_clinit = exact_clinits[0]
    static_block_re = re.compile(r"(?m)^[ \t]*static[ \t]*\{")

    for block_match in static_block_re.finditer(whole_code):
        brace_start = whole_code.find(
            "{", block_match.start(), block_match.end()
        )
        if (
            brace_start < 0
            or _brace_depth_before(whole_code, brace_start) != 1
        ):
            continue
        block_end = _matching_brace_end(whole_code, brace_start)
        block_code = whole_code[block_match.start():block_end]

        source_counts: dict[tuple[str, str, str], int] = {}
        occurrences: list[tuple[int, int, str]] = []
        shadow_owners_by_simple: dict[str, list[str]] = {}

        for simple, (
            imported_internal,
            shadow_owners,
            imported,
        ) in sorted(shadowed.items()):
            shadow_owners_by_simple[simple] = shadow_owners
            for field in imported.fields:
                field_name = str(field.get("name", ""))
                access = int(field.get("access", 0))
                if (
                    not (access & 0x0008)
                    or not _is_java_identifier(field_name)
                    or not _field_visible_from(
                        declaring_owner=imported_internal,
                        current_owner=current_owner,
                        access=access,
                    )
                ):
                    continue

                token = re.compile(
                    r"(?<![A-Za-z0-9_$.])"
                    + re.escape(simple)
                    + r"\."
                    + re.escape(field_name)
                    + r"\b(?!\s*\()"
                )
                hits = list(token.finditer(block_code))
                if not hits:
                    continue

                key = (imported_internal, field_name, simple)
                source_counts[key] = len(hits)
                qualified = imported_internal.replace("/", ".")
                for hit in hits:
                    occurrences.append(
                        (
                            block_match.start() + hit.start(),
                            block_match.start() + hit.end(),
                            "((" + qualified + ")null)." + field_name,
                        )
                    )

        if not source_counts:
            continue

        byte_counts: dict[tuple[str, str, str], int] = {}
        for access in exact_clinit.get("field_accesses", []):
            if access.get("operation") not in {"getstatic", "putstatic"}:
                continue
            for key in source_counts:
                imported_internal, field_name, _simple = key
                if (
                    str(access.get("owner", "")) == imported_internal
                    and str(access.get("name", "")) == field_name
                ):
                    byte_counts[key] = byte_counts.get(key, 0) + 1

        if not all(
            byte_counts.get(key, 0) == count
            for key, count in source_counts.items()
        ):
            continue

        edits.extend(occurrences)
        actions.append(
            {
                "kind": (
                    "shadowed_imported_static_field_owner_type_context"
                ),
                "source_path": rel,
                "method_name": "<clinit>",
                "method_descriptor": "()V",
                "imported_owners": sorted(
                    {key[0] for key in source_counts}
                ),
                "shadow_declaring_owners": sorted(
                    {
                        owner
                        for _imported, _field, simple in source_counts
                        for owner in shadow_owners_by_simple[simple]
                    }
                ),
                "field_access_counts": {
                    imported + "." + field: count
                    for (imported, field, _simple), count in sorted(
                        source_counts.items()
                    )
                },
                "replacement_count": sum(source_counts.values()),
                "provenance": {
                    "kind": "source_safety",
                    "reason": (
                        "procyon_imported_type_hidden_by_visible_value_in_static_initializer"
                    ),
                    "strategy": (
                        "exact_clinit_static_field_type_context_qualification"
                    ),
                },
            }
        )

    if not edits:
        return []

    edits.sort(key=lambda row: row[0])
    for left, right in zip(edits, edits[1:]):
        if left[1] > right[0]:
            raise SourceNormalizationError(
                f"{rel}: overlapping imported-owner type-context edits"
            )
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return actions


def _normalize_imported_static_method_owners_shadowed_by_values(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Qualify imported static-call owners hidden by primitive values.

    An explicit imported type such as b can be hidden in expression context
    by a primitive field, parameter or local also named b. Source calls like
    b.a(...) are rewritten to the fully-qualified imported type only when one
    exact readable method proves the complete invokestatic owner/name
    multiset.
    """
    rel = path.relative_to(source_root).as_posix()
    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError:
        return []
    try:
        profile = profile_class_field_accesses(class_bytes)
    except BytecodeProfileError:
        return []

    current_owner = str(profile.get("internal_name", ""))
    if current_owner != class_entry[:-6]:
        return []

    text = path.read_text(encoding="utf-8")
    imports: dict[str, str] = {}
    duplicates: set[str] = set()
    for import_match in _SINGLE_TYPE_IMPORT_RE.finditer(text):
        dotted = import_match.group("name")
        simple = dotted.rsplit(".", 1)[-1]
        internal = dotted.replace(".", "/")
        previous = imports.get(simple)
        if previous is not None and previous != internal:
            duplicates.add(simple)
        else:
            imports[simple] = internal
    for simple in duplicates:
        imports.pop(simple, None)
    if not imports:
        return []

    imported_methods: dict[str, tuple[str, set[str]]] = {}
    for simple, imported_owner in sorted(imports.items()):
        try:
            imported = parse_class(
                readable_zip.read(imported_owner + ".class")
            )
        except (KeyError, ClassFormatError):
            continue
        if imported.name != imported_owner:
            continue

        names = {
            str(method.get("name", ""))
            for method in imported.methods
            if (
                int(method.get("access", 0)) & 0x0008
                and _is_java_identifier(str(method.get("name", "")))
                and _field_visible_from(
                    declaring_owner=imported_owner,
                    current_owner=current_owner,
                    access=int(method.get("access", 0)),
                )
            )
        }
        if names:
            imported_methods[simple] = (imported_owner, names)
    if not imported_methods:
        return []

    hierarchy = _read_readable_hierarchy(
        readable_zip=readable_zip,
        internal_name=current_owner,
    )
    whole_code = _java_code_mask(text)
    edits: list[tuple[int, int, str]] = []
    actions: list[dict[str, Any]] = []

    for match in _METHOD_DECL_RE.finditer(text):
        brace_start = text.find("{", match.start(), match.end())
        if brace_start < 0:
            continue
        body_end = _matching_brace_end(text, brace_start)
        method_text = text[match.start():body_end]
        method_code = _java_code_mask(method_text)

        for simple, (imported_owner, method_names) in sorted(
            imported_methods.items()
        ):
            reference_parameter, reference_local_spans = (
                _same_name_value_shadow_spans(
                    method_match=match,
                    method_code=method_code,
                    simple_name=simple,
                )
            )
            if reference_parameter:
                continue

            primitive_parameter, primitive_local_spans = (
                _primitive_same_name_value_shadow_spans(
                    method_match=match,
                    method_code=method_code,
                    simple_name=simple,
                )
            )

            hierarchy_primitive_shadow = False
            hierarchy_shadow_owner: str | None = None
            for owner, parsed in hierarchy:
                declarations = [
                    field
                    for field in parsed.fields
                    if (
                        str(field.get("name", "")) == simple
                        and _field_visible_from(
                            declaring_owner=owner,
                            current_owner=current_owner,
                            access=int(field.get("access", 0)),
                        )
                    )
                ]
                if not declarations:
                    continue
                if len(declarations) == 1:
                    descriptor = str(
                        declarations[0].get("descriptor", "")
                    )
                    if descriptor in _PRIMITIVE_FIELD_DESCRIPTORS:
                        hierarchy_primitive_shadow = True
                        hierarchy_shadow_owner = owner
                break

            if (
                not hierarchy_primitive_shadow
                and not primitive_parameter
                and not primitive_local_spans
            ):
                continue

            affected_counts: dict[str, int] = {}
            total_counts: dict[str, int] = {}
            affected_hits: list[re.Match[str]] = []

            qualified_owner = imported_owner.replace("/", ".")
            for method_name in sorted(method_names):
                simple_call = re.compile(
                    r"(?<![A-Za-z0-9_$.])"
                    + re.escape(simple)
                    + r"\."
                    + re.escape(method_name)
                    + r"\s*\("
                )
                simple_hits = [
                    hit
                    for hit in simple_call.finditer(method_code)
                    if not any(
                        start <= hit.start() < end
                        for start, end in reference_local_spans
                    )
                ]
                qualified_call = re.compile(
                    r"(?<![A-Za-z0-9_$.])"
                    + re.escape(qualified_owner)
                    + r"\."
                    + re.escape(method_name)
                    + r"\s*\("
                )
                qualified_hits = list(
                    qualified_call.finditer(method_code)
                )

                selected = [
                    hit
                    for hit in simple_hits
                    if (
                        hierarchy_primitive_shadow
                        or primitive_parameter
                        or any(
                            start <= hit.start() < end
                            for start, end in primitive_local_spans
                        )
                    )
                ]
                if not selected:
                    continue

                affected_counts[method_name] = len(selected)
                total_counts[method_name] = (
                    len(simple_hits) + len(qualified_hits)
                )
                affected_hits.extend(selected)

            if not affected_counts:
                continue

            source_arity = _source_parameter_count(match.group("params"))
            candidates: list[dict[str, Any]] = []
            for method in profile.get("methods", []):
                if method.get("name") != match.group("name"):
                    continue
                descriptor = str(method.get("descriptor", ""))
                if _descriptor_parameter_count(descriptor) != source_arity:
                    continue
                parameter_match = _source_parameters_match_descriptor(
                    match.group("params"),
                    descriptor,
                    current_package=current_owner.rpartition("/")[0],
                )
                if parameter_match is False:
                    continue

                invocation_counts: dict[str, int] = {}
                for invocation in method.get("method_invocations", []):
                    if invocation.get("operation") != "invokestatic":
                        continue
                    if str(invocation.get("owner", "")) != imported_owner:
                        continue
                    name = str(invocation.get("name", ""))
                    if name not in total_counts:
                        continue
                    invocation_counts[name] = (
                        invocation_counts.get(name, 0) + 1
                    )

                if all(
                    invocation_counts.get(name, 0) == count
                    for name, count in total_counts.items()
                ):
                    candidates.append(method)

            if len(candidates) != 1:
                continue

            exact_method = candidates[0]
            for hit in affected_hits:
                edits.append(
                    (
                        match.start() + hit.start(),
                        match.start() + hit.start() + len(simple),
                        qualified_owner,
                    )
                )
            actions.append(
                {
                    "kind": (
                        "shadowed_imported_static_method_owner_qualification"
                    ),
                    "source_path": rel,
                    "method_name": match.group("name"),
                    "method_descriptor": exact_method["descriptor"],
                    "simple_owner": simple,
                    "imported_owner": imported_owner,
                    "hierarchy_primitive_shadow_owner": (
                        hierarchy_shadow_owner
                    ),
                    "primitive_parameter_shadow": primitive_parameter,
                    "primitive_local_shadow_scope_count": len(
                        primitive_local_spans
                    ),
                    "call_counts": dict(sorted(affected_counts.items())),
                    "total_call_counts": dict(sorted(total_counts.items())),
                    "replacement_count": len(affected_hits),
                    "provenance": {
                        "kind": "source_safety",
                        "reason": (
                            "procyon_imported_static_method_owner_hidden_by_primitive_value"
                        ),
                        "strategy": (
                            "exact_invokestatic_owner_name_multiset_qualification"
                        ),
                    },
                }
            )

    if not edits:
        return []

    edits.sort(key=lambda row: row[0])
    for left, right in zip(edits, edits[1:]):
        if left[1] > right[0]:
            raise SourceNormalizationError(
                f"{rel}: overlapping imported static-call owner edits"
            )
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return actions


def _normalize_same_package_static_method_owners_shadowed_by_values(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Qualify same-package static-call owners hidden by source values.

    This handles the method-call counterpart to the existing same-package
    static-field owner repair. A simple owner token is rewritten only when:
    the exact same-package class exists, that class declares the referenced
    visible static method name, source scope proves a same-name value shadow,
    and one exact current method contains the complete matching invokestatic
    owner/name multiset.
    """
    rel = path.relative_to(source_root).as_posix()
    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError:
        return []
    try:
        profile = profile_class_field_accesses(class_bytes)
    except BytecodeProfileError:
        return []

    current_owner = str(profile.get("internal_name", ""))
    if current_owner != class_entry[:-6]:
        return []
    current_package = current_owner.rpartition("/")[0]
    if not current_package:
        return []

    text = path.read_text(encoding="utf-8")
    whole_code = _java_code_mask(text)
    owner_token = re.compile(
        r"(?<![A-Za-z0-9_$.])"
        r"(?P<owner>[A-Za-z_$][A-Za-z0-9_$]*)"
        r"\.(?P<method>[A-Za-z_$][A-Za-z0-9_$]*)\s*\("
    )
    candidate_simples = sorted(
        {
            match.group("owner")
            for match in owner_token.finditer(whole_code)
        }
    )
    if not candidate_simples:
        return []

    siblings: dict[str, tuple[str, set[str]]] = {}
    for simple in candidate_simples:
        sibling_owner = current_package + "/" + simple
        if sibling_owner == current_owner:
            continue
        try:
            sibling = parse_class(
                readable_zip.read(sibling_owner + ".class")
            )
        except (KeyError, ClassFormatError):
            continue
        if sibling.name != sibling_owner:
            continue

        static_names = {
            str(method.get("name", ""))
            for method in sibling.methods
            if (
                int(method.get("access", 0)) & 0x0008
                and _is_java_identifier(str(method.get("name", "")))
                and _field_visible_from(
                    declaring_owner=sibling_owner,
                    current_owner=current_owner,
                    access=int(method.get("access", 0)),
                )
            )
        }
        if static_names:
            siblings[simple] = (sibling_owner, static_names)
    if not siblings:
        return []

    hierarchy = _read_readable_hierarchy(
        readable_zip=readable_zip,
        internal_name=current_owner,
    )
    edits: list[tuple[int, int, str]] = []
    actions: list[dict[str, Any]] = []

    for method_match in _METHOD_DECL_RE.finditer(text):
        brace_start = text.find(
            "{", method_match.start(), method_match.end()
        )
        if brace_start < 0:
            continue
        body_end = _matching_brace_end(text, brace_start)
        method_text = text[method_match.start():body_end]
        method_code = _java_code_mask(method_text)

        for simple, (sibling_owner, static_names) in sorted(
            siblings.items()
        ):
            reference_parameter, reference_local_spans = (
                _same_name_value_shadow_spans(
                    method_match=method_match,
                    method_code=method_code,
                    simple_name=simple,
                )
            )
            primitive_parameter, primitive_local_spans = (
                _primitive_same_name_value_shadow_spans(
                    method_match=method_match,
                    method_code=method_code,
                    simple_name=simple,
                )
            )

            hierarchy_shadow_owner: str | None = None
            for owner, parsed in hierarchy:
                declarations = [
                    field
                    for field in parsed.fields
                    if (
                        str(field.get("name", "")) == simple
                        and _field_visible_from(
                            declaring_owner=owner,
                            current_owner=current_owner,
                            access=int(field.get("access", 0)),
                        )
                    )
                ]
                if not declarations:
                    continue
                if len(declarations) == 1:
                    hierarchy_shadow_owner = owner
                break

            whole_method_shadow = bool(
                hierarchy_shadow_owner
                or reference_parameter
                or primitive_parameter
            )
            local_shadow_spans = sorted(
                set(reference_local_spans + primitive_local_spans)
            )
            if not whole_method_shadow and not local_shadow_spans:
                continue

            affected_counts: dict[str, int] = {}
            total_counts: dict[str, int] = {}
            affected_hits: list[re.Match[str]] = []
            qualified_owner = sibling_owner.replace("/", ".")

            for static_name in sorted(static_names):
                simple_call = re.compile(
                    r"(?<![A-Za-z0-9_$.])"
                    + re.escape(simple)
                    + r"\."
                    + re.escape(static_name)
                    + r"\s*\("
                )
                simple_hits = list(simple_call.finditer(method_code))
                qualified_call = re.compile(
                    r"(?<![A-Za-z0-9_$.])"
                    + re.escape(qualified_owner)
                    + r"\."
                    + re.escape(static_name)
                    + r"\s*\("
                )
                qualified_hits = list(
                    qualified_call.finditer(method_code)
                )

                selected = [
                    hit
                    for hit in simple_hits
                    if (
                        whole_method_shadow
                        or any(
                            start <= hit.start() < end
                            for start, end in local_shadow_spans
                        )
                    )
                ]
                if not selected:
                    continue

                affected_counts[static_name] = len(selected)
                total_counts[static_name] = (
                    len(simple_hits) + len(qualified_hits)
                )
                affected_hits.extend(selected)

            if not affected_counts:
                continue

            source_arity = _source_parameter_count(
                method_match.group("params")
            )
            candidates: list[dict[str, Any]] = []
            for method in profile.get("methods", []):
                if method.get("name") != method_match.group("name"):
                    continue
                descriptor = str(method.get("descriptor", ""))
                if _descriptor_parameter_count(descriptor) != source_arity:
                    continue
                parameter_match = _source_parameters_match_descriptor(
                    method_match.group("params"),
                    descriptor,
                    current_package=current_package,
                )
                if parameter_match is False:
                    continue

                invocation_counts: dict[str, int] = {}
                for invocation in method.get("method_invocations", []):
                    if invocation.get("operation") != "invokestatic":
                        continue
                    if str(invocation.get("owner", "")) != sibling_owner:
                        continue
                    name = str(invocation.get("name", ""))
                    if name not in total_counts:
                        continue
                    invocation_counts[name] = (
                        invocation_counts.get(name, 0) + 1
                    )

                if all(
                    invocation_counts.get(name, 0) == count
                    for name, count in total_counts.items()
                ):
                    candidates.append(method)

            if len(candidates) != 1:
                continue

            exact_method = candidates[0]
            for hit in affected_hits:
                edits.append(
                    (
                        method_match.start() + hit.start(),
                        method_match.start() + hit.start() + len(simple),
                        qualified_owner,
                    )
                )
            actions.append(
                {
                    "kind": (
                        "shadowed_same_package_static_method_owner_qualification"
                    ),
                    "source_path": rel,
                    "method_name": method_match.group("name"),
                    "method_descriptor": exact_method["descriptor"],
                    "simple_owner": simple,
                    "same_package_owner": sibling_owner,
                    "hierarchy_shadow_owner": hierarchy_shadow_owner,
                    "reference_parameter_shadow": reference_parameter,
                    "primitive_parameter_shadow": primitive_parameter,
                    "local_shadow_scope_count": len(local_shadow_spans),
                    "call_counts": dict(sorted(affected_counts.items())),
                    "total_call_counts": dict(sorted(total_counts.items())),
                    "replacement_count": len(affected_hits),
                    "provenance": {
                        "kind": "source_safety",
                        "reason": (
                            "procyon_same_package_static_method_owner_hidden_by_value"
                        ),
                        "strategy": (
                            "exact_invokestatic_owner_name_multiset_qualification"
                        ),
                    },
                }
            )

    if not edits:
        return []

    edits.sort(key=lambda row: row[0])
    for left, right in zip(edits, edits[1:]):
        if left[1] > right[0]:
            raise SourceNormalizationError(
                f"{rel}: overlapping same-package static-call owner edits"
            )
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return actions


def _normalize_same_package_static_field_owners_shadowed_by_scoped_values(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Qualify same-package static fields hidden by parameter/local values.

    This rule intentionally excludes hierarchy-field-only shadows, which are
    owned by the older same-package static-field normalizer. It targets
    reference or primitive parameters/locals and requires the complete exact
    getstatic/putstatic owner/name multiset to agree with source before any
    edit is made.
    """
    rel = path.relative_to(source_root).as_posix()
    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError:
        return []
    try:
        profile = profile_class_field_accesses(class_bytes)
    except BytecodeProfileError:
        return []

    current_owner = str(profile.get("internal_name", ""))
    if current_owner != class_entry[:-6]:
        return []
    current_package = current_owner.rpartition("/")[0]
    if not current_package:
        return []

    text = path.read_text(encoding="utf-8")
    whole_code = _java_code_mask(text)
    field_token = re.compile(
        r"(?<![A-Za-z0-9_$.])"
        r"(?P<owner>[A-Za-z_$][A-Za-z0-9_$]*)"
        r"\.(?P<field>[A-Za-z_$][A-Za-z0-9_$]*)"
        r"\b(?!\s*\()"
    )
    candidate_simples = sorted(
        {
            match.group("owner")
            for match in field_token.finditer(whole_code)
        }
    )
    if not candidate_simples:
        return []

    hierarchy = _read_readable_hierarchy(
        readable_zip=readable_zip,
        internal_name=current_owner,
    )
    hierarchy_value_names = {
        str(field.get("name", ""))
        for owner, parsed in hierarchy
        for field in parsed.fields
        if (
            _is_java_identifier(str(field.get("name", "")))
            and _field_visible_from(
                declaring_owner=owner,
                current_owner=current_owner,
                access=int(field.get("access", 0)),
            )
        )
    }

    siblings: dict[str, tuple[str, set[str]]] = {}
    for simple in candidate_simples:
        if simple in hierarchy_value_names:
            # Leave hierarchy-shadow cases to the established normalizer and
            # avoid overlapping edits between the two exact rules.
            continue
        sibling_owner = current_package + "/" + simple
        if sibling_owner == current_owner:
            continue
        try:
            sibling = parse_class(
                readable_zip.read(sibling_owner + ".class")
            )
        except (KeyError, ClassFormatError):
            continue
        if sibling.name != sibling_owner:
            continue

        static_names = {
            str(field.get("name", ""))
            for field in sibling.fields
            if (
                int(field.get("access", 0)) & 0x0008
                and _is_java_identifier(str(field.get("name", "")))
                and _field_visible_from(
                    declaring_owner=sibling_owner,
                    current_owner=current_owner,
                    access=int(field.get("access", 0)),
                )
            )
        }
        if static_names:
            siblings[simple] = (sibling_owner, static_names)
    if not siblings:
        return []

    edits: list[tuple[int, int, str]] = []
    actions: list[dict[str, Any]] = []

    for method_match in _METHOD_DECL_RE.finditer(text):
        brace_start = text.find(
            "{", method_match.start(), method_match.end()
        )
        if brace_start < 0:
            continue
        body_end = _matching_brace_end(text, brace_start)
        method_text = text[method_match.start():body_end]
        method_code = _java_code_mask(method_text)

        for simple, (sibling_owner, static_names) in sorted(
            siblings.items()
        ):
            reference_parameter, reference_local_spans = (
                _same_name_value_shadow_spans(
                    method_match=method_match,
                    method_code=method_code,
                    simple_name=simple,
                )
            )
            primitive_parameter, primitive_local_spans = (
                _primitive_same_name_value_shadow_spans(
                    method_match=method_match,
                    method_code=method_code,
                    simple_name=simple,
                )
            )
            whole_method_shadow = bool(
                reference_parameter or primitive_parameter
            )
            local_shadow_spans = sorted(
                set(reference_local_spans + primitive_local_spans)
            )
            if not whole_method_shadow and not local_shadow_spans:
                continue

            affected_counts: dict[str, int] = {}
            total_counts: dict[str, int] = {}
            affected_hits: list[re.Match[str]] = []
            qualified_owner = sibling_owner.replace("/", ".")

            for static_name in sorted(static_names):
                simple_field = re.compile(
                    r"(?<![A-Za-z0-9_$.])"
                    + re.escape(simple)
                    + r"\."
                    + re.escape(static_name)
                    + r"\b(?!\s*\()"
                )
                simple_hits = list(simple_field.finditer(method_code))
                qualified_field = re.compile(
                    r"(?<![A-Za-z0-9_$.])"
                    + re.escape(qualified_owner)
                    + r"\."
                    + re.escape(static_name)
                    + r"\b(?!\s*\()"
                )
                qualified_hits = list(
                    qualified_field.finditer(method_code)
                )

                selected = [
                    hit
                    for hit in simple_hits
                    if (
                        whole_method_shadow
                        or any(
                            start <= hit.start() < end
                            for start, end in local_shadow_spans
                        )
                    )
                ]
                if not selected:
                    continue

                affected_counts[static_name] = len(selected)
                total_counts[static_name] = (
                    len(simple_hits) + len(qualified_hits)
                )
                affected_hits.extend(selected)

            if not affected_counts:
                continue

            source_arity = _source_parameter_count(
                method_match.group("params")
            )
            candidates: list[dict[str, Any]] = []
            for method in profile.get("methods", []):
                if method.get("name") != method_match.group("name"):
                    continue
                descriptor = str(method.get("descriptor", ""))
                if _descriptor_parameter_count(descriptor) != source_arity:
                    continue
                parameter_match = _source_parameters_match_descriptor(
                    method_match.group("params"),
                    descriptor,
                    current_package=current_package,
                )
                if parameter_match is False:
                    continue

                byte_counts: dict[str, int] = {}
                for access in method.get("field_accesses", []):
                    if access.get("operation") not in {
                        "getstatic", "putstatic"
                    }:
                        continue
                    if str(access.get("owner", "")) != sibling_owner:
                        continue
                    name = str(access.get("name", ""))
                    if name not in total_counts:
                        continue
                    byte_counts[name] = byte_counts.get(name, 0) + 1

                if all(
                    byte_counts.get(name, 0) == count
                    for name, count in total_counts.items()
                ):
                    candidates.append(method)

            if len(candidates) != 1:
                continue

            exact_method = candidates[0]
            for hit in affected_hits:
                field_name = hit.group(0).split(".", 1)[1]
                replacement = (
                    "((" + qualified_owner + ")null)." + field_name
                )
                edits.append(
                    (
                        method_match.start() + hit.start(),
                        method_match.start() + hit.end(),
                        replacement,
                    )
                )
            actions.append(
                {
                    "kind": (
                        "scoped_same_package_static_field_owner_qualification"
                    ),
                    "source_path": rel,
                    "method_name": method_match.group("name"),
                    "method_descriptor": exact_method["descriptor"],
                    "simple_owner": simple,
                    "same_package_owner": sibling_owner,
                    "reference_parameter_shadow": reference_parameter,
                    "primitive_parameter_shadow": primitive_parameter,
                    "local_shadow_scope_count": len(local_shadow_spans),
                    "field_access_counts": dict(
                        sorted(affected_counts.items())
                    ),
                    "total_field_access_counts": dict(
                        sorted(total_counts.items())
                    ),
                    "replacement_count": len(affected_hits),
                    "provenance": {
                        "kind": "source_safety",
                        "reason": (
                            "procyon_same_package_static_field_owner_hidden_by_scoped_value"
                        ),
                        "strategy": (
                            "exact_static_field_owner_name_multiset_qualification"
                        ),
                    },
                }
            )

    if not edits:
        return []

    edits.sort(key=lambda row: row[0])
    for left, right in zip(edits, edits[1:]):
        if left[1] > right[0]:
            raise SourceNormalizationError(
                f"{rel}: overlapping scoped same-package static-field edits"
            )
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return actions


def _normalize_same_package_static_field_owners_shadowed_by_values(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Force shadowed same-package static-field owners through type context.

    Procyon may emit SiblingType.FIELD inside a static method even when the
    current class hierarchy exposes a visible non-static field named
    SiblingType. javac then resolves the simple owner as that value instead
    of the same-package class.

    Rewriting is source-driven and fail-closed: the sibling class and static
    field must exist in the exact readable JAR, the shadowing value must be
    visible in the current hierarchy, and one unique exact static method must
    contain the same owner/field access multiset.
    """
    rel = path.relative_to(source_root).as_posix()
    class_entry = Path(rel).with_suffix(".class").as_posix()
    try:
        class_bytes = readable_zip.read(class_entry)
    except KeyError:
        return []

    try:
        profile = profile_class_field_accesses(class_bytes)
    except BytecodeProfileError:
        return []

    current_owner = str(profile.get("internal_name", ""))
    if current_owner != class_entry[:-6]:
        return []

    current_package = current_owner.rpartition("/")[0]
    if not current_package:
        return []

    hierarchy = _read_readable_hierarchy(
        readable_zip=readable_zip,
        internal_name=current_owner,
    )

    shadow_owners_by_simple: dict[str, list[str]] = {}
    for owner, parsed in hierarchy:
        for field in parsed.fields:
            simple = str(field.get("name", ""))
            access = int(field.get("access", 0))
            if (
                not _is_java_identifier(simple)
                or (access & 0x0008)
                or not _field_visible_from(
                    declaring_owner=owner,
                    current_owner=current_owner,
                    access=access,
                )
            ):
                continue
            shadow_owners_by_simple.setdefault(simple, []).append(owner)

    if not shadow_owners_by_simple:
        return []

    siblings: dict[str, tuple[str, Any]] = {}
    for simple in sorted(shadow_owners_by_simple):
        sibling_owner = current_package + "/" + simple
        if sibling_owner == current_owner:
            continue
        try:
            sibling = parse_class(
                readable_zip.read(sibling_owner + ".class")
            )
        except (KeyError, ClassFormatError):
            continue
        if sibling.name != sibling_owner:
            continue
        siblings[simple] = (sibling_owner, sibling)

    if not siblings:
        return []

    text = path.read_text(encoding="utf-8")
    whole_code = _java_code_mask(text)
    edits: list[tuple[int, int, str]] = []
    actions: list[dict[str, Any]] = []

    for method_match in _METHOD_DECL_RE.finditer(text):
        brace_start = text.find(
            "{", method_match.start(), method_match.end()
        )
        if brace_start < 0:
            continue

        header_code = whole_code[method_match.start():brace_start]
        if re.search(r"\bstatic\b", header_code) is None:
            continue

        body_end = _matching_brace_end(text, brace_start)
        method_text = text[method_match.start():body_end]
        method_code = _java_code_mask(method_text)

        source_counts: dict[tuple[str, str, str], int] = {}
        occurrences: list[tuple[int, int, str]] = []
        used_shadow_owners: dict[str, list[str]] = {}

        for simple, (sibling_owner, sibling) in sorted(siblings.items()):
            parameter_shadow, local_shadow_spans = (
                _same_name_value_shadow_spans(
                    method_match=method_match,
                    method_code=method_code,
                    simple_name=simple,
                )
            )
            if parameter_shadow:
                continue

            for field in sibling.fields:
                field_name = str(field.get("name", ""))
                access = int(field.get("access", 0))
                if (
                    not (access & 0x0008)
                    or not _is_java_identifier(field_name)
                    or not _field_visible_from(
                        declaring_owner=sibling_owner,
                        current_owner=current_owner,
                        access=access,
                    )
                ):
                    continue

                token = re.compile(
                    r"(?<![A-Za-z0-9_$.])"
                    + re.escape(simple)
                    + r"\."
                    + re.escape(field_name)
                    + r"\b(?!\s*\()"
                )
                hits = [
                    hit
                    for hit in token.finditer(method_code)
                    if not any(
                        start <= hit.start() < end
                        for start, end in local_shadow_spans
                    )
                ]
                if not hits:
                    continue

                key = (sibling_owner, field_name, simple)
                source_counts[key] = len(hits)
                used_shadow_owners[simple] = sorted(
                    set(shadow_owners_by_simple[simple])
                )
                qualified = sibling_owner.replace("/", ".")
                for hit in hits:
                    occurrences.append(
                        (
                            method_match.start() + hit.start(),
                            method_match.start() + hit.end(),
                            "((" + qualified + ")null)." + field_name,
                        )
                    )

        if not source_counts:
            continue

        source_arity = _source_parameter_count(
            method_match.group("params")
        )
        candidates: list[dict[str, Any]] = []

        for method in profile.get("methods", []):
            if method.get("name") != method_match.group("name"):
                continue
            if not (int(method.get("access", 0)) & 0x0008):
                continue

            descriptor = str(method.get("descriptor", ""))
            if _descriptor_parameter_count(descriptor) != source_arity:
                continue

            parameter_match = _source_parameters_match_descriptor(
                method_match.group("params"),
                descriptor,
                current_package=current_package,
            )
            if parameter_match is False:
                continue

            byte_counts: dict[tuple[str, str, str], int] = {}
            for access in method.get("field_accesses", []):
                if access.get("operation") not in {"getstatic", "putstatic"}:
                    continue
                for key in source_counts:
                    sibling_owner, field_name, _simple = key
                    if (
                        str(access.get("owner", "")) == sibling_owner
                        and str(access.get("name", "")) == field_name
                    ):
                        byte_counts[key] = byte_counts.get(key, 0) + 1

            if all(
                byte_counts.get(key, 0) == count
                for key, count in source_counts.items()
            ):
                candidates.append(method)

        if len(candidates) != 1:
            continue

        exact_method = candidates[0]
        edits.extend(occurrences)
        actions.append(
            {
                "kind": (
                    "shadowed_same_package_static_field_owner_type_context"
                ),
                "source_path": rel,
                "method_name": method_match.group("name"),
                "method_descriptor": exact_method["descriptor"],
                "same_package_owners": sorted(
                    {key[0] for key in source_counts}
                ),
                "shadow_declaring_owners": sorted(
                    {
                        owner
                        for _sibling, _field, simple in source_counts
                        for owner in used_shadow_owners[simple]
                    }
                ),
                "field_access_counts": {
                    owner + "." + field: count
                    for (owner, field, _simple), count in sorted(
                        source_counts.items()
                    )
                },
                "replacement_count": sum(source_counts.values()),
                "provenance": {
                    "kind": "source_safety",
                    "reason": (
                        "procyon_same_package_type_hidden_by_visible_value_in_static_method"
                    ),
                    "strategy": (
                        "exact_static_method_field_type_context_qualification"
                    ),
                },
            }
        )

    if not edits:
        return []

    edits.sort(key=lambda row: row[0])
    for left, right in zip(edits, edits[1:]):
        if left[1] > right[0]:
            raise SourceNormalizationError(
                f"{rel}: overlapping same-package owner type-context edits"
            )

    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return actions


def normalize_procyon_source(
    source_root: Path,
    readable_jar: Path,
) -> dict[str, Any]:
    """Normalize only exact, proven Procyon output defects into legal Java.

    This stage does not infer semantic names. Every synthetic-class rewrite is
    bound to the exact readable classfile shape, and discarded string
    concatenations preserve evaluation by assigning the result to a
    deterministic unused local.
    """
    source_root = source_root.resolve()
    readable_jar = readable_jar.resolve()
    if not source_root.is_dir():
        raise SourceNormalizationError(
            f"source root does not exist: {source_root}"
        )
    if not readable_jar.is_file():
        raise SourceNormalizationError(
            f"readable JAR does not exist: {readable_jar}"
        )

    before_sha, before_count, before_bytes = _source_tree_digest(source_root)
    actions: list[dict[str, Any]] = []

    try:
        with zipfile.ZipFile(readable_jar) as z:
            for path in sorted(
                source_root.rglob("*.java"),
                key=lambda path: path.relative_to(source_root).as_posix(),
            ):
                action = _normalize_synthetic_class(
                    source_root=source_root,
                    path=path,
                    readable_zip=z,
                )
                if action is not None:
                    actions.append(action)
                actions.extend(
                    _normalize_shadowed_self_static_field_owners(
                        source_root=source_root,
                        path=path,
                        readable_zip=z,
                    )
                )
                actions.extend(
                    _normalize_hierarchy_shadowed_self_static_field_owners(
                        source_root=source_root,
                        path=path,
                        readable_zip=z,
                    )
                )
                actions.extend(
                    _normalize_primitive_scope_shadowed_self_static_field_owners(
                        source_root=source_root,
                        path=path,
                        readable_zip=z,
                    )
                )
                actions.extend(
                    _normalize_primitive_shadowed_instance_field_receivers(
                        source_root=source_root,
                        path=path,
                        readable_zip=z,
                    )
                )
                actions.extend(
                    _normalize_reference_shadowed_self_static_field_owners(
                        source_root=source_root,
                        path=path,
                        readable_zip=z,
                    )
                )
                actions.extend(
                    _normalize_shadowed_nested_static_field_owners(
                        source_root=source_root,
                        path=path,
                        readable_zip=z,
                    )
                )
                actions.extend(
                    _normalize_imported_parameter_types_shadowed_by_same_package(
                        source_root=source_root,
                        path=path,
                        readable_zip=z,
                    )
                )
                actions.extend(
                    _normalize_imported_static_field_owners_shadowed_by_values(
                        source_root=source_root,
                        path=path,
                        readable_zip=z,
                    )
                )
                actions.extend(
                    _normalize_imported_static_method_owners_shadowed_by_values(
                        source_root=source_root,
                        path=path,
                        readable_zip=z,
                    )
                )
                actions.extend(
                    _normalize_same_package_static_method_owners_shadowed_by_values(
                        source_root=source_root,
                        path=path,
                        readable_zip=z,
                    )
                )
                actions.extend(
                    _normalize_same_package_static_field_owners_shadowed_by_scoped_values(
                        source_root=source_root,
                        path=path,
                        readable_zip=z,
                    )
                )
                actions.extend(
                    _normalize_same_package_static_field_owners_shadowed_by_values(
                        source_root=source_root,
                        path=path,
                        readable_zip=z,
                    )
                )
    except zipfile.BadZipFile as exc:
        raise SourceNormalizationError(
            f"readable JAR is invalid: {readable_jar}"
        ) from exc

    for path in sorted(
        source_root.rglob("*.java"),
        key=lambda path: path.relative_to(source_root).as_posix(),
    ):
        actions.extend(
            _normalize_discarded_strings(
                source_root=source_root,
                path=path,
            )
        )

    after_sha, after_count, after_bytes = _source_tree_digest(source_root)
    if after_count != before_count:
        raise SourceNormalizationError(
            "source normalization changed the Java file count"
        )

    summary = {
        "action_count": len(actions),
        "synthetic_class_count": sum(
            action["kind"] == "synthetic_class_reconstruction"
            for action in actions
        ),
        "synthetic_field_count": sum(
            len(action.get("inserted_fields", []))
            for action in actions
            if action["kind"] == "synthetic_class_reconstruction"
        ),
        "discarded_string_expression_count": sum(
            action["kind"] == "discarded_string_expression_capture"
            for action in actions
        ),
        "shadowed_self_static_field_method_count": sum(
            action["kind"]
            == "shadowed_self_static_field_owner_qualification"
            for action in actions
        ),
        "shadowed_self_static_field_reference_count": sum(
            int(action.get("replacement_count", 0))
            for action in actions
            if action["kind"]
            == "shadowed_self_static_field_owner_qualification"
        ),
        "hierarchy_shadowed_self_static_field_method_count": sum(
            action["kind"]
            == "hierarchy_shadowed_self_static_field_owner_qualification"
            for action in actions
        ),
        "hierarchy_shadowed_self_static_field_reference_count": sum(
            int(action.get("replacement_count", 0))
            for action in actions
            if action["kind"]
            == "hierarchy_shadowed_self_static_field_owner_qualification"
        ),
        "primitive_scope_shadowed_self_static_field_method_count": sum(
            action["kind"]
            == "primitive_scope_shadowed_self_static_field_owner_qualification"
            for action in actions
        ),
        "primitive_scope_shadowed_self_static_field_reference_count": sum(
            int(action.get("replacement_count", 0))
            for action in actions
            if action["kind"]
            == "primitive_scope_shadowed_self_static_field_owner_qualification"
        ),
        "primitive_shadowed_instance_receiver_method_count": sum(
            action["kind"]
            == "primitive_shadowed_instance_field_receiver_qualification"
            for action in actions
        ),
        "primitive_shadowed_instance_receiver_reference_count": sum(
            int(action.get("replacement_count", 0))
            for action in actions
            if action["kind"]
            == "primitive_shadowed_instance_field_receiver_qualification"
        ),
        "reference_shadowed_self_static_field_method_count": sum(
            action["kind"]
            == "reference_shadowed_self_static_field_owner_qualification"
            for action in actions
        ),
        "reference_shadowed_self_static_field_reference_count": sum(
            int(action.get("replacement_count", 0))
            for action in actions
            if action["kind"]
            == "reference_shadowed_self_static_field_owner_qualification"
        ),
        "shadowed_nested_static_field_method_count": sum(
            action["kind"]
            == "shadowed_nested_static_field_owner_type_context"
            for action in actions
        ),
        "shadowed_nested_static_field_reference_count": sum(
            int(action.get("replacement_count", 0))
            for action in actions
            if action["kind"]
            == "shadowed_nested_static_field_owner_type_context"
        ),
        "imported_parameter_shadow_method_count": sum(
            action["kind"]
            == "imported_parameter_type_shadowed_by_same_package"
            for action in actions
        ),
        "imported_parameter_shadow_reference_count": sum(
            int(action.get("replacement_count", 0))
            for action in actions
            if action["kind"]
            == "imported_parameter_type_shadowed_by_same_package"
        ),
        "shadowed_imported_static_field_action_count": sum(
            action["kind"]
            == "shadowed_imported_static_field_owner_type_context"
            for action in actions
        ),
        "shadowed_imported_static_field_method_count": sum(
            action["kind"]
            == "shadowed_imported_static_field_owner_type_context"
            and action.get("method_name") != "<clinit>"
            for action in actions
        ),
        "shadowed_imported_static_field_block_count": sum(
            action["kind"]
            == "shadowed_imported_static_field_owner_type_context"
            and action.get("method_name") == "<clinit>"
            for action in actions
        ),
        "shadowed_imported_static_field_reference_count": sum(
            int(action.get("replacement_count", 0))
            for action in actions
            if action["kind"]
            == "shadowed_imported_static_field_owner_type_context"
        ),
        "shadowed_imported_static_method_method_count": sum(
            action["kind"]
            == "shadowed_imported_static_method_owner_qualification"
            for action in actions
        ),
        "shadowed_imported_static_method_reference_count": sum(
            int(action.get("replacement_count", 0))
            for action in actions
            if action["kind"]
            == "shadowed_imported_static_method_owner_qualification"
        ),
        "shadowed_same_package_static_method_method_count": sum(
            action["kind"]
            == "shadowed_same_package_static_method_owner_qualification"
            for action in actions
        ),
        "shadowed_same_package_static_method_reference_count": sum(
            int(action.get("replacement_count", 0))
            for action in actions
            if action["kind"]
            == "shadowed_same_package_static_method_owner_qualification"
        ),
        "scoped_same_package_static_field_method_count": sum(
            action["kind"]
            == "scoped_same_package_static_field_owner_qualification"
            for action in actions
        ),
        "scoped_same_package_static_field_reference_count": sum(
            int(action.get("replacement_count", 0))
            for action in actions
            if action["kind"]
            == "scoped_same_package_static_field_owner_qualification"
        ),
        "shadowed_same_package_static_field_method_count": sum(
            action["kind"]
            == "shadowed_same_package_static_field_owner_type_context"
            for action in actions
        ),
        "shadowed_same_package_static_field_reference_count": sum(
            int(action.get("replacement_count", 0))
            for action in actions
            if action["kind"]
            == "shadowed_same_package_static_field_owner_type_context"
        ),
        "java_file_count": after_count,
        "source_bytes_before": before_bytes,
        "source_bytes_after": after_bytes,
    }
    material = {
        "readable_jar_sha256": sha256_file(readable_jar),
        "source_tree_before_sha256": before_sha,
        "source_tree_after_sha256": after_sha,
        "actions": actions,
    }
    return {
        "schema_version": 1,
        "kind": "procyon_source_normalization_report",
        "normalization_id": (
            "SRCNORM_" + _stable_digest(material)[:20].upper()
        ),
        "readable_jar_sha256": material["readable_jar_sha256"],
        "source_tree_before_sha256": before_sha,
        "source_tree_after_sha256": after_sha,
        "summary": summary,
        "actions": actions,
    }
