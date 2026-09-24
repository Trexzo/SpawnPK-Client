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
    files = sorted(\n        root.rglob("*.java"),\n        key=lambda path: path.relative_to(root).as_posix(),\n    )
    h = hashlib.sha256()
    total_bytes = 0
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
        total_bytes += len(data)
    return h.hexdigest(), len(files), total_bytes


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


def _normalize_hierarchy_shadowed_self_static_field_owners(
    *,
    source_root: Path,
    path: Path,
    readable_zip: zipfile.ZipFile,
) -> list[dict[str, Any]]:
    """Qualify class-static fields hidden by a primitive same-name field.

    Procyon can emit h.ae inside class h while h (or a superclass) also
    declares a primitive field named h. javac then resolves h as a value
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
            and str(field.get("descriptor", ""))
            in _PRIMITIVE_FIELD_DESCRIPTORS
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
                        "procyon_hierarchy_primitive_shadowed_class_owner"
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
            for path in sorted(\n                source_root.rglob("*.java"),\n                key=lambda path: path.relative_to(source_root).as_posix(),\n            ):
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
    except zipfile.BadZipFile as exc:
        raise SourceNormalizationError(
            f"readable JAR is invalid: {readable_jar}"
        ) from exc

    for path in sorted(\n        source_root.rglob("*.java"),\n        key=lambda path: path.relative_to(source_root).as_posix(),\n    ):
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
