"""Fail-closed *compile-only* alias for a reviewed, standalone Java class.

This narrowly bridges an original class/package shadowing edge for the
independently rebuilt SOURCE island. It does not accept a semantic rename,
modify canonical Java source, or publish proprietary code. Whole-client
namespace legalization remains the existing R125/remapper responsibility.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .namespace_source_overlay import _lex_java


class StandaloneAliasError(ValueError):
    pass


_ENTRY = re.compile(r"rs/(?:[A-Za-z_$][A-Za-z_$0-9]*/)*[A-Za-z_$][A-Za-z_$0-9]*[.]class\Z")


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise StandaloneAliasError(reason)


def validate_compile_aliases(
    selected: set[str],
    aliases: dict[str, str],
    original_jar_entries: set[str],
) -> dict[str, str]:
    """Only same-package class aliases; preserve all project package names."""
    _require(type(aliases) is dict and len(aliases) <= 4,
             "COMPILE_ALIAS_MAPPING_INVALID")
    for old, new in aliases.items():
        _require(
            type(old) is str and type(new) is str
            and _ENTRY.fullmatch(old) is not None
            and _ENTRY.fullmatch(new) is not None,
            "COMPILE_ALIAS_CLASS_PATH_INVALID",
        )
        _require(old in selected and new != old,
                 "COMPILE_ALIAS_OLD_CLASS_NOT_SELECTED")
        _require(old.rpartition("/")[0] == new.rpartition("/")[0],
                 "COMPILE_ALIAS_MUST_PRESERVE_PACKAGE")
        _require(new not in original_jar_entries,
                 "COMPILE_ALIAS_TARGET_EXISTS_IN_ORIGINAL")
    remapped = {aliases.get(x, x) for x in selected}
    _require(len(remapped) == len(selected), "COMPILE_ALIAS_NOT_INJECTIVE")
    names = {x[:-6] for x in remapped}
    _require(len({n.casefold() for n in names}) == len(names),
             "COMPILE_ALIAS_CASE_INSENSITIVE_COLLISION")
    for name in names:
        parts = name.split("/")
        for i in range(1, len(parts)):
            _require("/".join(parts[:i]) not in names,
                     "COMPILE_ALIAS_CLASS_PACKAGE_COLLISION_REMAINS")
    return dict(sorted(aliases.items()))


def _significant_java(source: str):
    return [x for x in _lex_java(source) if x.kind != "trivia"]


def rename_owned_class_source(
    source: str, *, old_entry: str, alias_entry: str,
) -> str:
    """Rewrite only recognized class declaration/type/constructor tokens.

    Any unrecognized use of old simple name refuses, rather than guessing
    whether it is a field name, invocation, label, or reflection reference.
    """
    old = old_entry.rsplit("/", 1)[-1][:-6]
    new = alias_entry.rsplit("/", 1)[-1][:-6]
    sig = _significant_java(source)
    edits: list[tuple[int, int]] = []
    declarations = 0
    for i, tok in enumerate(sig):
        if tok.kind != "ident" or tok.text != old:
            continue
        previous = sig[i-1].text if i > 0 else ""
        following = sig[i+1] if i + 1 < len(sig) else None
        next_text = following.text if following else ""
        is_class = previous == "class"
        is_ctor = (
            next_text == "("
            and previous in ("public", "private", "protected", "{", "}", ";")
        )
        is_type = following is not None and following.kind == "ident"
        _require(is_class or is_ctor or is_type,
                 "COMPILE_ALIAS_AMBIGUOUS_JAVA_IDENTIFIER")
        if is_class:
            declarations += 1
        edits.append((tok.start, tok.end))
    _require(declarations == 1 and len(edits) >= 2,
             "COMPILE_ALIAS_CLASS_DECLARATION_OR_REFERENCES_MISSING")
    result = source
    for start, end in reversed(edits):
        result = result[:start] + new + result[end:]
    return result


def ensure_no_external_alias_refs(
    text: str, *, old_entry: str,
) -> None:
    """Conservative no-reference gate for other sources in the small island.

    The package declaration `package rs.t;` is NOT a class reference.
    Other uses of the old class simple identifier are unsupported here.
    """
    old_name = old_entry.rsplit("/", 1)[-1][:-6]
    sig = _significant_java(text)
    idx = 0
    if sig and sig[0].text == "package":
        while idx < len(sig) and sig[idx].text != ";":
            idx += 1
        idx += 1
    for tok in sig[idx:]:
        if tok.kind == "ident" and tok.text == old_name:
            raise StandaloneAliasError(
                "COMPILE_ALIAS_EXTERNAL_SOURCE_REFERENCE_REQUIRES_REVIEW"
            )
