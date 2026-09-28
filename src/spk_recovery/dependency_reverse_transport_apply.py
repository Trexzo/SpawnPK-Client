from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .dependency_reference_surface import scan_project_reference_surface


class DependencyReverseTransportApplyError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_plan(path: Path) -> dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyReverseTransportApplyError(
            f"invalid reverse transport plan: {path}"
        ) from exc

    if (
        plan.get("schema_version") != 1
        or plan.get("kind")
        != "dependency_reverse_compile_transport_plan"
        or plan.get("identifiers_included") is not True
    ):
        raise DependencyReverseTransportApplyError(
            "requires private identifier-bearing DEPREVERSE plan"
        )

    summary = plan.get("summary")
    if not isinstance(summary, dict):
        raise DependencyReverseTransportApplyError(
            "DEPREVERSE plan lacks summary"
        )
    if (
        summary.get("ready_for_bytecode_restore") is not True
        or int(summary.get("blocker_count", -1)) != 0
        or plan.get("blockers") not in ([], None)
    ):
        raise DependencyReverseTransportApplyError(
            "DEPREVERSE plan is not ready for bytecode restore"
        )
    return plan


def _require(command: str) -> str:
    candidate = Path(command)
    if candidate.is_absolute():
        if not candidate.is_file():
            raise DependencyReverseTransportApplyError(
                f"required executable missing: {candidate}"
            )
        return str(candidate)
    found = shutil.which(command)
    if found is None:
        raise DependencyReverseTransportApplyError(
            f"required executable not found on PATH: {command}"
        )
    return found


def _helper_source() -> Path:
    path = (
        Path(__file__).resolve().parent
        / "java"
        / "SpkJarRemapper.java"
    )
    if not path.is_file():
        raise DependencyReverseTransportApplyError(
            f"missing packaged JAR remapper: {path}"
        )
    return path


_ASM_EXPORTS = (
    "java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED",
    "java.base/jdk.internal.org.objectweb.asm.commons=ALL-UNNAMED",
)


def _compile_helper(classes: Path, *, javac: str) -> None:
    classes.mkdir(parents=True, exist_ok=True)
    args = [javac]
    for export in _ASM_EXPORTS:
        args.extend(["--add-exports", export])
    args.extend(["-d", str(classes), str(_helper_source())])
    proc = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise DependencyReverseTransportApplyError(
            "SpkJarRemapper compilation failed:\n"
            + proc.stdout
            + proc.stderr
        )


def _map_descriptor(
    descriptor: str,
    class_mapping: dict[str, str],
) -> str:
    value = descriptor
    for old, new in sorted(
        class_mapping.items(),
        key=lambda item: (-len(item[0]), item[0]),
    ):
        value = value.replace(
            "L" + old + ";",
            "L" + new + ";",
        )
    return value


def _mapping_rows(
    plan: dict[str, Any],
) -> tuple[
    list[str],
    dict[str, str],
    dict[tuple[str, str, str, str], str],
    dict[str, int],
]:
    class_mapping: dict[str, str] = {}
    for row in plan.get("class_reverse", []):
        official = row.get("official_owner")
        bundled = row.get("bundled_owner")
        if not isinstance(official, str) or not official:
            raise DependencyReverseTransportApplyError(
                "reverse class row lacks official_owner"
            )
        if not isinstance(bundled, str) or not bundled:
            raise DependencyReverseTransportApplyError(
                "reverse class row lacks bundled_owner"
            )
        prior = class_mapping.get(official)
        if prior is not None and prior != bundled:
            raise DependencyReverseTransportApplyError(
                "conflicting reverse class source"
            )
        class_mapping[official] = bundled

    member_mapping: dict[
        tuple[str, str, str, str],
        str,
    ] = {}
    reference_kind_counts: dict[str, int] = {}

    for row in plan.get("member_reverse", []):
        reference_kind = row.get("reference_kind")
        transport_kind = row.get("transport_kind")
        if reference_kind not in {
            "field",
            "method",
            "interface_method",
        }:
            raise DependencyReverseTransportApplyError(
                "reverse member row has unsupported reference_kind"
            )
        expected_transport = (
            "field"
            if reference_kind == "field"
            else "method"
        )
        if transport_kind != expected_transport:
            raise DependencyReverseTransportApplyError(
                "reverse member transport_kind disagrees"
            )

        values = (
            row.get("official_owner"),
            row.get("official_name"),
            row.get("official_descriptor"),
            row.get("bundled_owner"),
            row.get("bundled_name"),
            row.get("bundled_descriptor"),
        )
        if not all(isinstance(value, str) and value for value in values):
            raise DependencyReverseTransportApplyError(
                "reverse member row lacks exact identities"
            )
        (
            official_owner,
            official_name,
            official_descriptor,
            bundled_owner,
            bundled_name,
            bundled_descriptor,
        ) = values

        mapped_owner = class_mapping.get(
            official_owner,
            official_owner,
        )
        if mapped_owner != bundled_owner:
            raise DependencyReverseTransportApplyError(
                "member owner is not explained by class reverse transport"
            )

        mapped_descriptor = _map_descriptor(
            official_descriptor,
            class_mapping,
        )
        if mapped_descriptor != bundled_descriptor:
            raise DependencyReverseTransportApplyError(
                "member descriptor is not explained by class reverse transport"
            )

        key = (
            str(transport_kind),
            official_owner,
            official_name,
            official_descriptor,
        )
        prior = member_mapping.get(key)
        if prior is not None and prior != bundled_name:
            raise DependencyReverseTransportApplyError(
                "conflicting reverse member source"
            )
        member_mapping[key] = bundled_name
        reference_kind_counts[str(reference_kind)] = (
            reference_kind_counts.get(str(reference_kind), 0)
            + 1
        )

    lines = [
        "\t".join(("C", old, new))
        for old, new in sorted(class_mapping.items())
    ]
    for key, new_name in sorted(member_mapping.items()):
        transport_kind, owner, name, descriptor = key
        row_kind = "F" if transport_kind == "field" else "M"
        lines.append(
            "\t".join(
                (
                    row_kind,
                    owner,
                    name,
                    descriptor,
                    new_name,
                )
            )
        )

    if not lines:
        raise DependencyReverseTransportApplyError(
            "DEPREVERSE plan contains no executable mappings"
        )

    counts = {
        "class_mapping_count": len(class_mapping),
        "field_mapping_count": sum(
            key[0] == "field"
            for key in member_mapping
        ),
        "method_mapping_count": sum(
            key[0] == "method"
            for key in member_mapping
        ),
        "member_mapping_count": len(member_mapping),
        "reference_kind_row_count": sum(
            reference_kind_counts.values()
        ),
    }
    return lines, class_mapping, member_mapping, counts


def _run_remapper(
    mapping_lines: list[str],
    input_jar: Path,
    output_jar: Path,
    *,
    java: str,
    javac: str,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="spk-depreverse-"
    ) as td:
        root = Path(td)
        classes = root / "classes"
        mapping = root / "mapping.tsv"
        mapping.write_text(
            "\n".join(mapping_lines) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        _compile_helper(classes, javac=javac)

        args = [java]
        for export in _ASM_EXPORTS:
            args.extend(["--add-exports", export])
        args.extend(
            [
                "-cp",
                str(classes),
                "SpkJarRemapper",
                str(mapping),
                str(input_jar),
                str(output_jar),
            ]
        )
        proc = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if (
            proc.returncode != 0
            or "SPK_JAR_REMAP_PASS" not in proc.stdout
        ):
            raise DependencyReverseTransportApplyError(
                "SpkJarRemapper failed:\n"
                + proc.stdout
                + proc.stderr
            )


def _class_entries(path: Path) -> list[str]:
    import zipfile
    try:
        with zipfile.ZipFile(path) as archive:
            return sorted(
                name
                for name in archive.namelist()
                if name.endswith(".class")
                and not name.endswith("/")
            )
    except zipfile.BadZipFile as exc:
        raise DependencyReverseTransportApplyError(
            f"invalid project JAR: {path}"
        ) from exc


def _expected_surface(
    surface: dict[str, Any],
    class_mapping: dict[str, str],
    member_mapping: dict[tuple[str, str, str, str], str],
) -> dict[str, Any]:
    class_sources: dict[str, set[str]] = {}
    for row in surface.get("class_references", []):
        target = class_mapping.get(
            str(row["target"]),
            str(row["target"]),
        )
        class_sources.setdefault(target, set()).update(
            str(value)
            for value in row.get("source_classes", [])
        )

    member_counts: dict[
        tuple[str, str, str, str],
        int,
    ] = {}
    member_sources: dict[
        tuple[str, str, str, str],
        set[str],
    ] = {}
    for row in surface.get("member_references", []):
        kind = str(row["kind"])
        transport_kind = (
            "field" if kind == "field" else "method"
        )
        owner = str(row["owner"])
        name = str(row["name"])
        descriptor = str(row["descriptor"])
        mapped_name = member_mapping.get(
            (
                transport_kind,
                owner,
                name,
                descriptor,
            ),
            name,
        )
        mapped_owner = class_mapping.get(owner, owner)
        mapped_descriptor = _map_descriptor(
            descriptor,
            class_mapping,
        )
        key = (
            kind,
            mapped_owner,
            mapped_name,
            mapped_descriptor,
        )
        member_counts[key] = (
            member_counts.get(key, 0)
            + int(row.get("reference_count", 0))
        )
        member_sources.setdefault(key, set()).update(
            str(value)
            for value in row.get("source_classes", [])
        )

    return {
        "project_class_count": int(
            surface.get("project_class_count", 0)
        ),
        "class_references": [
            {
                "target": target,
                "source_class_count": len(sources),
                "source_classes": sorted(sources),
            }
            for target, sources in sorted(class_sources.items())
        ],
        "member_references": [
            {
                "kind": key[0],
                "owner": key[1],
                "name": key[2],
                "descriptor": key[3],
                "reference_count": member_counts[key],
                "source_class_count": len(member_sources[key]),
                "source_classes": sorted(member_sources[key]),
            }
            for key in sorted(member_counts)
        ],
    }


def _surface_core(surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_class_count": int(
            surface.get("project_class_count", 0)
        ),
        "class_references": surface.get(
            "class_references",
            [],
        ),
        "member_references": surface.get(
            "member_references",
            [],
        ),
    }


def apply_dependency_reverse_transport(
    private_plan_path: Path,
    input_project_jar: Path,
    output_project_jar: Path,
    *,
    project_prefixes: tuple[str, ...] = ("rs/", "tools/"),
    java_command: str = "java",
    javac_command: str = "javac",
) -> dict[str, Any]:
    private_plan_path = private_plan_path.resolve()
    input_project_jar = input_project_jar.resolve()
    output_project_jar = output_project_jar.resolve()

    if not input_project_jar.is_file():
        raise DependencyReverseTransportApplyError(
            "input project JAR does not exist"
        )
    if output_project_jar == input_project_jar:
        raise DependencyReverseTransportApplyError(
            "output project JAR must be disposable"
        )

    plan = _load_plan(private_plan_path)
    mapping_lines, class_mapping, member_mapping, counts = (
        _mapping_rows(plan)
    )
    java = _require(java_command)
    javac = _require(javac_command)

    pre_entries = _class_entries(input_project_jar)
    pre = scan_project_reference_surface(
        input_project_jar,
        project_prefixes=project_prefixes,
    )
    expected = _expected_surface(
        pre,
        class_mapping,
        member_mapping,
    )

    output_project_jar.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    if output_project_jar.exists():
        output_project_jar.unlink()

    _run_remapper(
        mapping_lines,
        input_project_jar,
        output_project_jar,
        java=java,
        javac=javac,
    )

    post_entries = _class_entries(output_project_jar)
    if post_entries != pre_entries:
        raise DependencyReverseTransportApplyError(
            "reverse transport changed project class entry identities"
        )

    post = scan_project_reference_surface(
        output_project_jar,
        project_prefixes=project_prefixes,
    )
    if _surface_core(post) != expected:
        raise DependencyReverseTransportApplyError(
            "restored dependency reference surface differs from "
            "the exact reverse-transport expectation"
        )

    semantic_sha = _stable_digest(expected)
    material = {
        "reverse_plan_id": plan["reverse_plan_id"],
        "input_project_jar_sha256": _sha256_file(
            input_project_jar
        ),
        "output_project_jar_sha256": _sha256_file(
            output_project_jar
        ),
        "pre_reference_surface_id": pre[
            "reference_surface_id"
        ],
        "post_reference_surface_id": post[
            "reference_surface_id"
        ],
        "restored_semantic_surface_sha256": semantic_sha,
        **counts,
    }
    return {
        "schema_version": 1,
        "kind": "dependency_reverse_transport_application",
        "application_id": (
            "DEPREVERSEAPPLY_"
            + _stable_digest(material)[:20].upper()
        ),
        "reverse_plan_id": plan["reverse_plan_id"],
        "input_project_jar_sha256": material[
            "input_project_jar_sha256"
        ],
        "output_project_jar_sha256": material[
            "output_project_jar_sha256"
        ],
        "pre_reference_surface_id": material[
            "pre_reference_surface_id"
        ],
        "post_reference_surface_id": material[
            "post_reference_surface_id"
        ],
        "restored_semantic_surface_sha256": semantic_sha,
        "summary": {
            **counts,
            "project_class_count": expected[
                "project_class_count"
            ],
            "class_reference_row_count": len(
                expected["class_references"]
            ),
            "member_reference_row_count": len(
                expected["member_references"]
            ),
            "project_class_identity_changed_count": 0,
            "reference_surface_match": True,
            "runtime_dependency_bytes_modified": False,
            "canonical_source_modified": False,
        },
    }


def write_dependency_reverse_transport_application(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
