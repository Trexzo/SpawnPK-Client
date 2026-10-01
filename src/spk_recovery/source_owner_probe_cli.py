from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any
import zipfile

from .bytecode_profile import BytecodeProfileError, profile_class_field_accesses
from .classfile import ClassFormatError, parse_class
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


class SourceOwnerProbeError(ValueError):
    pass


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _field_access_rows(
    method: dict[str, Any],
    *,
    source_fields: set[str],
    owner_simple: str,
) -> list[dict[str, Any]]:
    counter: Counter[tuple[str, str, str, str]] = Counter()
    for access in method.get("field_accesses", []):
        operation = str(access.get("operation", ""))
        if operation not in {"getstatic", "putstatic", "getfield", "putfield"}:
            continue
        owner = str(access.get("owner", ""))
        name = str(access.get("name", ""))
        descriptor = str(access.get("descriptor", ""))
        if name not in source_fields and owner.rsplit("/", 1)[-1] != owner_simple:
            continue
        counter[(operation, owner, name, descriptor)] += 1
    return [
        {
            "operation": operation,
            "owner": owner,
            "name": name,
            "descriptor": descriptor,
            "count": count,
        }
        for (operation, owner, name, descriptor), count in sorted(
            counter.items()
        )
    ]


def probe_source_owner(
    *,
    source_root: Path,
    readable_jar: Path,
    source_path: str,
    owner_simple: str,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    source = (source_root / Path(source_path)).resolve()
    if source_root not in source.parents:
        raise SourceOwnerProbeError("source path escapes source root")
    if not source.is_file():
        raise SourceOwnerProbeError(f"source file is missing: {source}")
    if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", owner_simple):
        raise SourceOwnerProbeError("owner-simple is not a Java identifier")

    rel = source.relative_to(source_root).as_posix()
    class_entry = Path(rel).with_suffix(".class").as_posix()
    text = source.read_text(encoding="utf-8")
    whole_code = _java_code_mask(text)

    with zipfile.ZipFile(readable_jar, "r") as readable_zip:
        try:
            class_bytes = readable_zip.read(class_entry)
        except KeyError as exc:
            raise SourceOwnerProbeError(
                f"exact readable class is missing: {class_entry}"
            ) from exc
        try:
            profile = profile_class_field_accesses(class_bytes)
        except BytecodeProfileError as exc:
            raise SourceOwnerProbeError(
                f"exact readable class profile failed: {exc}"
            ) from exc

        current_owner = str(profile.get("internal_name", ""))
        if current_owner != class_entry[:-6]:
            raise SourceOwnerProbeError(
                "source/class identity mismatch: "
                f"{class_entry[:-6]} != {current_owner}"
            )
        current_package = current_owner.rpartition("/")[0]
        same_package_owner = (
            current_package + "/" + owner_simple
            if current_package
            else owner_simple
        )

        same_package_class_exists = False
        same_package_static_fields: list[dict[str, Any]] = []
        try:
            sibling = parse_class(
                readable_zip.read(same_package_owner + ".class")
            )
        except (KeyError, ClassFormatError):
            sibling = None
        if sibling is not None and sibling.name == same_package_owner:
            same_package_class_exists = True
            for field in sibling.fields:
                access = int(field.get("access", 0))
                if not (access & 0x0008):
                    continue
                same_package_static_fields.append(
                    {
                        "name": str(field.get("name", "")),
                        "descriptor": str(field.get("descriptor", "")),
                        "access": access,
                        "visible": _field_visible_from(
                            declaring_owner=same_package_owner,
                            current_owner=current_owner,
                            access=access,
                        ),
                    }
                )

        hierarchy_bindings: list[dict[str, Any]] = []
        hierarchy = _read_readable_hierarchy(
            readable_zip=readable_zip,
            internal_name=current_owner,
        )
        for declaring_owner, parsed in hierarchy:
            for field in parsed.fields:
                if str(field.get("name", "")) != owner_simple:
                    continue
                access = int(field.get("access", 0))
                hierarchy_bindings.append(
                    {
                        "declaring_owner": declaring_owner,
                        "descriptor": str(field.get("descriptor", "")),
                        "access": access,
                        "static": bool(access & 0x0008),
                        "visible": _field_visible_from(
                            declaring_owner=declaring_owner,
                            current_owner=current_owner,
                            access=access,
                        ),
                    }
                )

        method_rows: list[dict[str, Any]] = []
        covered_spans: list[tuple[int, int]] = []
        owner_field_token = re.compile(
            r"(?<![A-Za-z0-9_$.])"
            + re.escape(owner_simple)
            + r"\.(?P<field>[A-Za-z_$][A-Za-z0-9_$]*)"
            + r"\b(?!\s*\()"
        )

        for method_match in _METHOD_DECL_RE.finditer(text):
            brace_start = text.find(
                "{", method_match.start(), method_match.end()
            )
            if brace_start < 0:
                continue
            body_end = _matching_brace_end(text, brace_start)
            method_text = text[method_match.start():body_end]
            method_code = _java_code_mask(method_text)
            hits = list(owner_field_token.finditer(method_code))
            if not hits:
                continue

            covered_spans.append((method_match.start(), body_end))
            source_field_counts = Counter(
                hit.group("field") for hit in hits
            )
            source_static = bool(
                re.search(
                    r"\bstatic\b",
                    whole_code[method_match.start():brace_start],
                )
            )
            reference_parameter, reference_local_spans = (
                _same_name_value_shadow_spans(
                    method_match=method_match,
                    method_code=method_code,
                    simple_name=owner_simple,
                )
            )
            primitive_parameter, primitive_local_spans = (
                _primitive_same_name_value_shadow_spans(
                    method_match=method_match,
                    method_code=method_code,
                    simple_name=owner_simple,
                )
            )

            source_arity = _source_parameter_count(
                method_match.group("params")
            )
            exact_candidates: list[dict[str, Any]] = []
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
                accesses = _field_access_rows(
                    method,
                    source_fields=set(source_field_counts),
                    owner_simple=owner_simple,
                )
                same_package_counts: Counter[str] = Counter()
                alternate_static_counts: Counter[tuple[str, str]] = Counter()
                for row in accesses:
                    if row["operation"] not in {"getstatic", "putstatic"}:
                        continue
                    if row["name"] not in source_field_counts:
                        continue
                    if row["owner"] == same_package_owner:
                        same_package_counts[row["name"]] += int(row["count"])
                    else:
                        alternate_static_counts[
                            (str(row["owner"]), str(row["name"]))
                        ] += int(row["count"])
                exact_candidates.append(
                    {
                        "descriptor": descriptor,
                        "access": int(method.get("access", 0)),
                        "static": method_static,
                        "parameter_match": parameter_match,
                        "field_accesses": accesses,
                        "same_package_field_counts": dict(
                            sorted(same_package_counts.items())
                        ),
                        "same_package_complete_match": all(
                            same_package_counts.get(name, 0) == count
                            for name, count in source_field_counts.items()
                        ),
                        "alternate_static_field_counts": [
                            {
                                "owner": owner,
                                "name": name,
                                "count": count,
                            }
                            for (owner, name), count in sorted(
                                alternate_static_counts.items()
                            )
                        ],
                    }
                )

            method_rows.append(
                {
                    "source_method": method_match.group("name"),
                    "source_params": method_match.group("params"),
                    "source_static": source_static,
                    "source_line_start": _line_number(
                        text, method_match.start()
                    ),
                    "source_line_end": _line_number(text, body_end),
                    "source_field_counts": dict(
                        sorted(source_field_counts.items())
                    ),
                    "reference_parameter_shadow": reference_parameter,
                    "reference_local_shadow_scope_count": len(
                        reference_local_spans
                    ),
                    "primitive_parameter_shadow": primitive_parameter,
                    "primitive_local_shadow_scope_count": len(
                        primitive_local_spans
                    ),
                    "exact_candidates": exact_candidates,
                }
            )

        unmatched_hits: list[dict[str, Any]] = []
        for hit in owner_field_token.finditer(whole_code):
            absolute = hit.start()
            if any(start <= absolute < end for start, end in covered_spans):
                continue
            unmatched_hits.append(
                {
                    "line": _line_number(text, absolute),
                    "field": hit.group("field"),
                    "text": hit.group(0),
                }
            )

    return {
        "source_path": rel,
        "class_entry": class_entry,
        "current_owner": current_owner,
        "owner_simple": owner_simple,
        "same_package_owner": same_package_owner,
        "same_package_class_exists": same_package_class_exists,
        "same_package_static_fields": same_package_static_fields,
        "hierarchy_bindings": hierarchy_bindings,
        "methods": method_rows,
        "unmatched_source_occurrences": unmatched_hits,
    }


def _print_human(report: dict[str, Any]) -> None:
    print("SPK_SOURCE_OWNER_CORRELATION_PASS")
    print(f"source_path={report['source_path']}")
    print(f"current_owner={report['current_owner']}")
    print(f"owner_simple={report['owner_simple']}")
    print(f"same_package_owner={report['same_package_owner']}")
    print(
        "same_package_class_exists="
        + str(report["same_package_class_exists"])
    )
    print(
        "hierarchy_binding_count="
        + str(len(report["hierarchy_bindings"]))
    )
    for row in report["hierarchy_bindings"]:
        print(
            "HIERARCHY "
            f"owner={row['declaring_owner']} "
            f"descriptor={row['descriptor']} "
            f"static={row['static']} visible={row['visible']}"
        )
    static_fields = [
        row["name"]
        for row in report["same_package_static_fields"]
        if row["visible"]
    ]
    print(
        "same_package_visible_static_fields="
        + ",".join(static_fields)
    )
    for method in report["methods"]:
        fields = ",".join(
            f"{name}:{count}"
            for name, count in method["source_field_counts"].items()
        )
        print(
            "METHOD "
            f"line={method['source_line_start']} "
            f"name={method['source_method']} "
            f"static={method['source_static']} "
            f"fields={fields} "
            f"ref_param={method['reference_parameter_shadow']} "
            f"ref_locals={method['reference_local_shadow_scope_count']} "
            f"prim_param={method['primitive_parameter_shadow']} "
            f"prim_locals={method['primitive_local_shadow_scope_count']}"
        )
        if not method["exact_candidates"]:
            print("  EXACT <none>")
        for candidate in method["exact_candidates"]:
            print(
                "  EXACT "
                f"descriptor={candidate['descriptor']} "
                "same_package_complete_match="
                f"{candidate['same_package_complete_match']}"
            )
            for access in candidate["field_accesses"]:
                print(
                    "    FIELD "
                    f"{access['operation']} "
                    f"{access['owner']}.{access['name']} "
                    f"{access['descriptor']} x{access['count']}"
                )
    for hit in report["unmatched_source_occurrences"]:
        print(
            "UNMATCHED_SOURCE "
            f"line={hit['line']} field={hit['field']} text={hit['text']}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Correlate a suspicious simple Java field owner against exact "
            "readable-JAR field-access bytecode without modifying sources."
        )
    )
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--readable-jar", required=True, type=Path)
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--owner-simple", required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = probe_source_owner(
        source_root=args.source_root,
        readable_jar=args.readable_jar,
        source_path=args.source_path,
        owner_simple=args.owner_simple,
    )
    _print_human(report)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"json_out={args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
