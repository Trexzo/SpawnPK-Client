from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any
import zipfile

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
    files = sorted(root.rglob("*.java"))
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
            for path in sorted(source_root.rglob("*.java")):
                action = _normalize_synthetic_class(
                    source_root=source_root,
                    path=path,
                    readable_zip=z,
                )
                if action is not None:
                    actions.append(action)
    except zipfile.BadZipFile as exc:
        raise SourceNormalizationError(
            f"readable JAR is invalid: {readable_jar}"
        ) from exc

    for path in sorted(source_root.rglob("*.java")):
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
