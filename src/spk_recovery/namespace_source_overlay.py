from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from .source_digest import source_tree_digest


class NamespaceSourceOverlayError(ValueError):
    pass


@dataclass(frozen=True)
class _Token:
    kind: str
    start: int
    end: int
    text: str


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _lex_java(text: str) -> list[_Token]:
    out: list[_Token] = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if ch.isspace():
            start = i
            i += 1
            while i < n and text[i].isspace():
                i += 1
            out.append(_Token("trivia", start, i, text[start:i]))
            continue

        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            start = i
            i += 2
            while i < n and text[i] not in "\r\n":
                i += 1
            out.append(_Token("trivia", start, i, text[start:i]))
            continue

        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            start = i
            i += 2
            end = text.find("*/", i)
            if end < 0:
                raise NamespaceSourceOverlayError(
                    "unterminated block comment"
                )
            i = end + 2
            out.append(_Token("trivia", start, i, text[start:i]))
            continue

        if ch in {'"', "'"}:
            quote = ch
            kind = "string" if quote == '"' else "char"
            start = i
            i += 1
            escaped = False
            while i < n:
                current = text[i]
                if escaped:
                    escaped = False
                    i += 1
                    continue
                if current == "\\":
                    escaped = True
                    i += 1
                    continue
                if current == quote:
                    i += 1
                    break
                i += 1
            else:
                raise NamespaceSourceOverlayError(
                    f"unterminated {kind} literal"
                )
            out.append(_Token(kind, start, i, text[start:i]))
            continue

        if ch.isalpha() or ch in {"_", "$"}:
            start = i
            i += 1
            while i < n and (
                text[i].isalnum()
                or text[i] in {"_", "$"}
            ):
                i += 1
            out.append(_Token("ident", start, i, text[start:i]))
            continue

        if ch == ".":
            out.append(_Token("dot", i, i + 1, ch))
            i += 1
            continue

        out.append(_Token("symbol", i, i + 1, ch))
        i += 1

    return out


def _significant(tokens: list[_Token]) -> list[int]:
    return [
        index
        for index, token in enumerate(tokens)
        if token.kind != "trivia"
    ]


def _dotted_parts(
    tokens: list[_Token],
    sig: list[int],
    pos: int,
) -> tuple[list[str], list[tuple[int, int]], int]:
    parts: list[str] = []
    spans: list[tuple[int, int]] = []
    cursor = pos

    if cursor >= len(sig):
        return parts, spans, cursor

    token = tokens[sig[cursor]]
    if token.kind != "ident":
        return parts, spans, cursor

    parts.append(token.text)
    spans.append((token.start, token.end))
    cursor += 1

    while cursor + 1 < len(sig):
        dot = tokens[sig[cursor]]
        ident = tokens[sig[cursor + 1]]
        if dot.kind != "dot" or ident.kind != "ident":
            break
        parts.append(ident.text)
        spans.append((ident.start, ident.end))
        cursor += 2

    return parts, spans, cursor


def _mapping_rows(
    private_alias_plan: dict[str, Any],
) -> list[tuple[tuple[str, ...], str]]:
    if (
        private_alias_plan.get("schema_version") != 1
        or private_alias_plan.get("kind") != "namespace_alias_plan"
        or private_alias_plan.get("identifiers_included") is not True
    ):
        raise NamespaceSourceOverlayError(
            "requires private identifier-bearing namespace alias plan"
        )

    mapping = private_alias_plan.get("mapping")
    if not isinstance(mapping, dict) or not mapping:
        raise NamespaceSourceOverlayError(
            "private alias plan contains no mapping"
        )

    rows: list[tuple[tuple[str, ...], str]] = []
    seen_aliases: set[str] = set()

    for old, alias in mapping.items():
        if not isinstance(old, str) or not isinstance(alias, str):
            raise NamespaceSourceOverlayError(
                "invalid alias mapping entry"
            )
        old_parts = tuple(old.replace("$", ".").split("/"))
        alias_dotted = alias.replace("/", ".").replace("$", ".")
        if not old_parts or any(not part for part in old_parts):
            raise NamespaceSourceOverlayError(
                "invalid original JVM identity"
            )
        if alias_dotted in seen_aliases:
            raise NamespaceSourceOverlayError(
                "alias mapping is not one-to-one"
            )
        seen_aliases.add(alias_dotted)
        rows.append((old_parts, alias_dotted))

    rows.sort(
        key=lambda row: (-len(row[0]), row[0])
    )
    return rows


def _match_mapping(
    parts: list[str],
    rows: list[tuple[tuple[str, ...], str]],
) -> tuple[int, str] | None:
    for old_parts, alias in rows:
        if (
            len(parts) >= len(old_parts)
            and tuple(parts[: len(old_parts)]) == old_parts
        ):
            return len(old_parts), alias
    return None


def rewrite_java_source(
    text: str,
    private_alias_plan: dict[str, Any],
) -> tuple[str, dict[str, int]]:
    tokens = _lex_java(text)
    sig = _significant(tokens)
    rows = _mapping_rows(private_alias_plan)

    replacements: list[tuple[int, int, str, str]] = []
    rewritten_imports = 0
    rewritten_qualified = 0
    skipped_package_declarations = 0

    pos = 0
    while pos < len(sig):
        token = tokens[sig[pos]]

        if token.kind == "ident" and token.text == "package":
            skipped_package_declarations += 1
            pos += 1
            while pos < len(sig):
                current = tokens[sig[pos]]
                pos += 1
                if current.kind == "symbol" and current.text == ";":
                    break
            continue

        is_import = (
            token.kind == "ident"
            and token.text == "import"
        )
        start_pos = pos
        static_import = False
        if is_import:
            start_pos += 1
            if (
                start_pos < len(sig)
                and tokens[sig[start_pos]].kind == "ident"
                and tokens[sig[start_pos]].text == "static"
            ):
                static_import = True
                start_pos += 1

        scan_pos = start_pos if is_import else pos
        parts, spans, end_pos = _dotted_parts(
            tokens,
            sig,
            scan_pos,
        )
        if not parts:
            pos += 1
            continue

        matched = _match_mapping(parts, rows)
        if matched is None:
            pos += 1
            continue

        part_count, alias = matched
        if part_count > len(spans):
            raise NamespaceSourceOverlayError(
                "internal dotted-name span mismatch"
            )

        start = spans[0][0]
        end = spans[part_count - 1][1]
        kind = "import" if is_import else "qualified"
        replacements.append((start, end, alias, kind))

        if is_import:
            rewritten_imports += 1
        else:
            rewritten_qualified += 1

        pos = max(end_pos, pos + 1)

        if static_import:
            # Static member suffix remains untouched.
            continue

    # Refuse overlapping edits rather than guessing.
    replacements.sort(key=lambda row: (row[0], row[1]))
    for previous, current in zip(replacements, replacements[1:]):
        if current[0] < previous[1]:
            raise NamespaceSourceOverlayError(
                "overlapping source alias rewrites"
            )

    out = text
    for start, end, replacement, _kind in reversed(replacements):
        out = out[:start] + replacement + out[end:]

    return out, {
        "replacement_count": len(replacements),
        "rewritten_import_count": rewritten_imports,
        "rewritten_qualified_count": rewritten_qualified,
        "skipped_package_declaration_count": (
            skipped_package_declarations
        ),
    }


def build_namespace_source_overlay(
    private_alias_plan: dict[str, Any],
    source_root: Path,
    out_dir: Path,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    out_dir = out_dir.resolve()

    if not source_root.is_dir():
        raise NamespaceSourceOverlayError(
            "source root does not exist"
        )
    if out_dir.exists() and any(out_dir.iterdir()):
        raise NamespaceSourceOverlayError(
            "overlay output directory must be empty"
        )

    input_sha, input_files, input_bytes = source_tree_digest(
        source_root
    )
    input_count = len(input_files)

    out_dir.mkdir(parents=True, exist_ok=True)
    overlay_root = out_dir / "src"
    shutil.copytree(source_root, overlay_root)

    changed_files = 0
    replacement_count = 0
    rewritten_import_count = 0
    rewritten_qualified_count = 0
    skipped_package_declaration_count = 0

    try:
        for path in sorted(
            overlay_root.rglob("*.java"),
            key=lambda value: value.relative_to(
                overlay_root
            ).as_posix(),
        ):
            original = path.read_text(
                encoding="utf-8",
                errors="strict",
            )
            rewritten, counters = rewrite_java_source(
                original,
                private_alias_plan,
            )
            if rewritten != original:
                path.write_text(
                    rewritten,
                    encoding="utf-8",
                    newline="",
                )
                changed_files += 1

            replacement_count += counters["replacement_count"]
            rewritten_import_count += counters[
                "rewritten_import_count"
            ]
            rewritten_qualified_count += counters[
                "rewritten_qualified_count"
            ]
            skipped_package_declaration_count += counters[
                "skipped_package_declaration_count"
            ]
    except Exception:
        shutil.rmtree(overlay_root, ignore_errors=True)
        raise

    output_sha, output_files, output_bytes = source_tree_digest(
        overlay_root
    )
    output_count = len(output_files)
    (
        canonical_after_sha,
        canonical_after_files,
        canonical_after_bytes,
    ) = source_tree_digest(source_root)
    canonical_after_count = len(canonical_after_files)

    if (
        canonical_after_sha != input_sha
        or canonical_after_count != input_count
        or canonical_after_bytes != input_bytes
    ):
        raise NamespaceSourceOverlayError(
            "canonical source tree changed during overlay generation"
        )

    if output_count != input_count:
        raise NamespaceSourceOverlayError(
            "Java file count changed in overlay"
        )
    if replacement_count == 0:
        raise NamespaceSourceOverlayError(
            "namespace alias overlay produced no rewrites"
        )
    if output_sha == input_sha:
        raise NamespaceSourceOverlayError(
            "namespace alias overlay did not change source tree"
        )

    material = {
        "alias_plan_id": private_alias_plan.get("plan_id"),
        "input_source_tree_sha256": input_sha,
        "output_source_tree_sha256": output_sha,
        "java_file_count": output_count,
        "changed_file_count": changed_files,
        "replacement_count": replacement_count,
        "rewritten_import_count": rewritten_import_count,
        "rewritten_qualified_count": rewritten_qualified_count,
    }
    overlay_id = (
        "NSOVERLAY_"
        + _stable_digest(material)[:20].upper()
    )

    return {
        "schema_version": 1,
        "kind": "namespace_source_overlay",
        "overlay_id": overlay_id,
        "alias_plan_id": private_alias_plan.get("plan_id"),
        "input_source_tree_sha256": input_sha,
        "output_source_tree_sha256": output_sha,
        "input_java_file_count": input_count,
        "output_java_file_count": output_count,
        "input_source_bytes": input_bytes,
        "output_source_bytes": output_bytes,
        "changed_file_count": changed_files,
        "replacement_count": replacement_count,
        "rewritten_import_count": rewritten_import_count,
        "rewritten_qualified_count": rewritten_qualified_count,
        "skipped_package_declaration_count": (
            skipped_package_declaration_count
        ),
        "overlay_root": str(overlay_root),
        "canonical_source_modified": False,
        "canonical_source_tree_sha256_after": (
            canonical_after_sha
        ),
    }
