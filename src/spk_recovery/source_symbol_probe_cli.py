from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any
import zipfile

from .bytecode_profile import BytecodeProfileError, profile_class_field_accesses
from .source_normalization import (
    _METHOD_DECL_RE,
    _descriptor_parameter_count,
    _field_visible_from,
    _java_code_mask,
    _matching_brace_end,
    _primitive_same_name_value_shadow_spans,
    _read_readable_hierarchy,
    _same_name_value_shadow_spans,
    _source_parameter_count,
    _source_parameters_match_descriptor,
)


class SourceSymbolProbeError(ValueError):
    pass


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _member_rows(method: dict[str, Any], symbols: set[str]):
    fields = Counter()
    calls = Counter()
    for row in method.get("field_accesses", []):
        name = str(row.get("name", ""))
        if name in symbols:
            fields[(str(row.get("operation", "")), str(row.get("owner", "")), name, str(row.get("descriptor", "")))] += 1
    for row in method.get("method_invocations", []):
        name = str(row.get("name", ""))
        if name in symbols:
            calls[(str(row.get("operation", "")), str(row.get("owner", "")), name, str(row.get("descriptor", "")))] += 1

    def rows(counter):
        return [
            {"operation": op, "owner": owner, "name": name, "descriptor": desc, "count": count}
            for (op, owner, name, desc), count in sorted(counter.items())
        ]
    return rows(fields), rows(calls)


def probe_source_symbols(*, source_root: Path, readable_jar: Path, source_path: str, symbols: list[str]) -> dict[str, Any]:
    source_root = source_root.resolve()
    source = (source_root / Path(source_path)).resolve()
    if source_root not in source.parents:
        raise SourceSymbolProbeError("source path escapes source root")
    if not source.is_file():
        raise SourceSymbolProbeError(f"source file is missing: {source}")

    clean_symbols = []
    for symbol in symbols:
        if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", symbol):
            raise SourceSymbolProbeError(f"symbol is not a Java identifier: {symbol!r}")
        if symbol not in clean_symbols:
            clean_symbols.append(symbol)
    if not clean_symbols:
        raise SourceSymbolProbeError("at least one symbol is required")

    rel = source.relative_to(source_root).as_posix()
    class_entry = Path(rel).with_suffix(".class").as_posix()
    text = source.read_text(encoding="utf-8")
    whole_code = _java_code_mask(text)
    symbol_set = set(clean_symbols)

    with zipfile.ZipFile(readable_jar, "r") as readable_zip:
        try:
            class_bytes = readable_zip.read(class_entry)
        except KeyError as exc:
            raise SourceSymbolProbeError(f"exact readable class is missing: {class_entry}") from exc
        try:
            profile = profile_class_field_accesses(class_bytes)
        except BytecodeProfileError as exc:
            raise SourceSymbolProbeError(f"exact readable class profile failed: {exc}") from exc

        current_owner = str(profile.get("internal_name", ""))
        if current_owner != class_entry[:-6]:
            raise SourceSymbolProbeError(f"source/class identity mismatch: {class_entry[:-6]} != {current_owner}")
        current_package = current_owner.rpartition("/")[0]

        declarations = {symbol: [] for symbol in clean_symbols}
        for declaring_owner, parsed in _read_readable_hierarchy(readable_zip=readable_zip, internal_name=current_owner):
            for field in parsed.fields:
                name = str(field.get("name", ""))
                if name not in symbol_set:
                    continue
                access = int(field.get("access", 0))
                declarations[name].append({
                    "declaring_owner": declaring_owner,
                    "descriptor": str(field.get("descriptor", "")),
                    "access": access,
                    "static": bool(access & 0x0008),
                    "visible": _field_visible_from(
                        declaring_owner=declaring_owner,
                        current_owner=current_owner,
                        access=access,
                    ),
                })

        methods = []
        covered_spans = []
        for method_match in _METHOD_DECL_RE.finditer(text):
            brace_start = text.find("{", method_match.start(), method_match.end())
            if brace_start < 0:
                continue
            body_end = _matching_brace_end(text, brace_start)
            method_code = _java_code_mask(text[method_match.start():body_end])
            occurrences = {}
            for symbol in clean_symbols:
                token = re.compile(r"(?<![A-Za-z0-9_$])" + re.escape(symbol) + r"(?![A-Za-z0-9_$])")
                hits = list(token.finditer(method_code))
                if not hits:
                    continue
                ref_param, ref_locals = _same_name_value_shadow_spans(
                    method_match=method_match,
                    method_code=method_code,
                    simple_name=symbol,
                )
                prim_param, prim_locals = _primitive_same_name_value_shadow_spans(
                    method_match=method_match,
                    method_code=method_code,
                    simple_name=symbol,
                )
                occurrences[symbol] = {
                    "count": len(hits),
                    "invocation_count": sum(1 for hit in hits if re.match(r"\s*\(", method_code[hit.end():])),
                    "qualified_count": sum(1 for hit in hits if re.search(r"\.\s*$", method_code[:hit.start()])),
                    "lines": sorted({_line_number(text, method_match.start() + hit.start()) for hit in hits}),
                    "reference_parameter_shadow": ref_param,
                    "reference_local_shadow_scope_count": len(ref_locals),
                    "primitive_parameter_shadow": prim_param,
                    "primitive_local_shadow_scope_count": len(prim_locals),
                }
            if not occurrences:
                continue

            covered_spans.append((method_match.start(), body_end))
            source_static = bool(re.search(r"\bstatic\b", whole_code[method_match.start():brace_start]))
            source_arity = _source_parameter_count(method_match.group("params"))
            exact_candidates = []
            for method in profile.get("methods", []):
                if method.get("name") != method_match.group("name"):
                    continue
                descriptor = str(method.get("descriptor", ""))
                if _descriptor_parameter_count(descriptor) != source_arity:
                    continue
                method_static = bool(int(method.get("access", 0)) & 0x0008)
                if method_static != source_static:
                    continue
                parameter_match = _source_parameters_match_descriptor(
                    method_match.group("params"),
                    descriptor,
                    current_package=current_package,
                )
                if parameter_match is False:
                    continue
                fields, calls = _member_rows(method, symbol_set)
                exact_candidates.append({
                    "descriptor": descriptor,
                    "access": int(method.get("access", 0)),
                    "static": method_static,
                    "parameter_match": parameter_match,
                    "field_accesses": fields,
                    "method_invocations": calls,
                })

            methods.append({
                "source_method": method_match.group("name"),
                "source_params": method_match.group("params"),
                "source_static": source_static,
                "source_line_start": _line_number(text, method_match.start()),
                "source_line_end": _line_number(text, body_end),
                "source_occurrences": occurrences,
                "exact_candidates": exact_candidates,
            })

        unmatched = []
        for symbol in clean_symbols:
            token = re.compile(r"(?<![A-Za-z0-9_$])" + re.escape(symbol) + r"(?![A-Za-z0-9_$])")
            for hit in token.finditer(whole_code):
                if any(start <= hit.start() < end for start, end in covered_spans):
                    continue
                unmatched.append({"symbol": symbol, "line": _line_number(text, hit.start())})

    return {
        "source_path": rel,
        "class_entry": class_entry,
        "current_owner": current_owner,
        "symbols": clean_symbols,
        "hierarchy_field_declarations": declarations,
        "methods": methods,
        "unmatched_source_occurrences": sorted(unmatched, key=lambda row: (row["line"], row["symbol"])),
    }


def _print_human(report: dict[str, Any]) -> None:
    print("SPK_SOURCE_SYMBOL_CORRELATION_PASS")
    print(f"source_path={report['source_path']}")
    print(f"current_owner={report['current_owner']}")
    print("symbols=" + ",".join(report["symbols"]))
    for symbol in report["symbols"]:
        rows = report["hierarchy_field_declarations"][symbol]
        print(f"SYMBOL {symbol} hierarchy_field_count={len(rows)}")
        for row in rows:
            print(
                "  DECL "
                f"owner={row['declaring_owner']} descriptor={row['descriptor']} "
                f"static={row['static']} visible={row['visible']}"
            )
    for method in report["methods"]:
        print(f"METHOD line={method['source_line_start']} name={method['source_method']} static={method['source_static']}")
        for symbol, occ in method["source_occurrences"].items():
            print(
                f"  SOURCE symbol={symbol} count={occ['count']} calls={occ['invocation_count']} "
                f"qualified={occ['qualified_count']} lines=" + ",".join(str(x) for x in occ["lines"])
            )
        if not method["exact_candidates"]:
            print("  EXACT <none>")
        for candidate in method["exact_candidates"]:
            print(f"  EXACT descriptor={candidate['descriptor']} parameter_match={candidate['parameter_match']}")
            for row in candidate["field_accesses"]:
                print(f"    FIELD {row['operation']} {row['owner']}.{row['name']} {row['descriptor']} x{row['count']}")
            for row in candidate["method_invocations"]:
                print(f"    CALL {row['operation']} {row['owner'] or '<dynamic>'}.{row['name']} {row['descriptor']} x{row['count']}")
    for row in report["unmatched_source_occurrences"]:
        print(f"UNMATCHED_SOURCE line={row['line']} symbol={row['symbol']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only exact source-symbol correlation probe.")
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--readable-jar", required=True, type=Path)
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--symbol", action="append", required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    report = probe_source_symbols(
        source_root=args.source_root,
        readable_jar=args.readable_jar,
        source_path=args.source_path,
        symbols=args.symbol,
    )
    _print_human(report)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"json_out={args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
