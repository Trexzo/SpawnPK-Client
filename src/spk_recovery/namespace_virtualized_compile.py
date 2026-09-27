from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .classfile_utf8_remap import (
    ClassfileRemapError,
    assert_no_literal_alias_mentions,
    assert_no_utf8_alias_references,
    remap_classfile_utf8,
    remap_jar,
)
from .namespace_alias_plan import (
    NamespaceAliasPlanError,
    reverse_alias_mapping,
)
from .namespace_source_overlay import (
    NamespaceSourceOverlayError,
    build_namespace_source_overlay,
)
from .javac_diagnostics import (
    classify_javac_diagnostics,
    write_javac_diagnostic_report,
)
from .source_digest import source_tree_digest


class NamespaceVirtualizedCompileError(ValueError):
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
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _arg(value: str) -> str:
    return '"' + value.replace("\\", "/").replace('"', '\\"') + '"'


def _class_tree(
    root: Path,
) -> tuple[str, list[Path], int]:
    files = sorted(
        root.rglob("*.class"),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    h = hashlib.sha256()
    total = 0

    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
        total += len(data)

    return h.hexdigest(), files, total


def _require_executable(command: str) -> str:
    candidate = Path(command)
    if candidate.is_absolute():
        if not candidate.is_file():
            raise NamespaceVirtualizedCompileError(
                "javac executable does not exist"
            )
        return str(candidate)

    found = shutil.which(command)
    if found is None:
        raise NamespaceVirtualizedCompileError(
            "javac executable not found on PATH"
        )
    return found


def _validate_plan(
    private_alias_plan: dict[str, Any],
) -> dict[str, str]:
    if (
        private_alias_plan.get("schema_version") != 1
        or private_alias_plan.get("kind") != "namespace_alias_plan"
        or private_alias_plan.get("identifiers_included") is not True
    ):
        raise NamespaceVirtualizedCompileError(
            "requires private identifier-bearing namespace alias plan"
        )

    mapping = private_alias_plan.get("mapping")
    if not isinstance(mapping, dict) or not mapping:
        raise NamespaceVirtualizedCompileError(
            "private alias plan contains no mapping"
        )

    normalized: dict[str, str] = {}
    for old, alias in mapping.items():
        if (
            not isinstance(old, str)
            or not old
            or not isinstance(alias, str)
            or not alias
        ):
            raise NamespaceVirtualizedCompileError(
                "invalid alias mapping entry"
            )
        normalized[old] = alias

    return normalized


def _remap_overlay_diagnostics(
    text: str,
    *,
    overlay_root: Path,
    source_root: Path,
) -> str:
    value = text.replace("\r\n", "\n").replace("\r", "\n")
    replacements = [
        (str(overlay_root), str(source_root)),
        (overlay_root.as_posix(), source_root.as_posix()),
    ]
    for old, new in sorted(
        replacements,
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        value = value.replace(old, new)
    return value


def _public_diagnostic_summary(
    report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "report_id": report["report_id"],
        "frontier_id": report["frontier_id"],
        "input_sha256": report["input_sha256"],
        "summary": report["summary"],
        "identifiers_included": False,
    }


def compile_with_namespace_virtualization(
    private_alias_plan: dict[str, Any],
    source_root: Path,
    dependency_jar: Path,
    out_dir: Path,
    *,
    javac_command: str = "javac",
    release: int = 9,
    extra_classpath: list[Path] | None = None,
    report_compile_failure: bool = False,
    private_diagnostic_report_out: Path | None = None,
) -> dict[str, Any]:
    mapping = _validate_plan(private_alias_plan)
    reverse = reverse_alias_mapping(private_alias_plan)

    source_root = source_root.resolve()
    dependency_jar = dependency_jar.resolve()
    out_dir = out_dir.resolve()

    if not source_root.is_dir():
        raise NamespaceVirtualizedCompileError(
            "source root does not exist"
        )
    if not dependency_jar.is_file():
        raise NamespaceVirtualizedCompileError(
            "dependency JAR does not exist"
        )
    if out_dir.exists() and any(out_dir.iterdir()):
        raise NamespaceVirtualizedCompileError(
            "compile output directory must be empty"
        )

    javac = _require_executable(javac_command)

    classpath: list[Path] = [dependency_jar]
    for path in extra_classpath or []:
        resolved = path.resolve()
        if not resolved.exists():
            raise NamespaceVirtualizedCompileError(
                "extra classpath entry does not exist"
            )
        classpath.append(resolved)

    canonical_before_sha, canonical_before_files, canonical_before_bytes = (
        source_tree_digest(source_root)
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    alias_jar = out_dir / "compile-alias-dependency.jar"
    overlay_dir = out_dir / "overlay"
    generated_dir = out_dir / "generated-alias"
    restored_dir = out_dir / "restored-classes"
    argfile = out_dir / "javac.args"

    try:
        alias_stats = remap_jar(
            dependency_jar,
            alias_jar,
            mapping,
        )
        overlay = build_namespace_source_overlay(
            private_alias_plan,
            source_root,
            overlay_dir,
        )

        overlay_root = Path(overlay["overlay_root"])
        sources = sorted(
            overlay_root.rglob("*.java"),
            key=lambda path: path.relative_to(
                overlay_root
            ).as_posix(),
        )
        if not sources:
            raise NamespaceVirtualizedCompileError(
                "overlay contains no Java sources"
            )

        generated_dir.mkdir(parents=True, exist_ok=True)
        compile_cp = [
            alias_jar,
            *classpath[1:],
        ]
        args = [
            "-proc:none",
            "-encoding",
            "UTF-8",
            "-Xlint:none",
            "--release",
            str(release),
            "-classpath",
            os.pathsep.join(str(path) for path in compile_cp),
            "-d",
            str(generated_dir),
            *[str(path) for path in sources],
        ]
        argfile.write_text(
            "\n".join(_arg(value) for value in args) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        proc = subprocess.run(
            [javac, "@" + str(argfile)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            if not report_compile_failure:
                raise NamespaceVirtualizedCompileError(
                    "namespace-virtualized javac failed:\n"
                    + proc.stdout
                    + proc.stderr
                )

            remapped_diagnostic = _remap_overlay_diagnostics(
                proc.stdout + proc.stderr,
                overlay_root=overlay_root,
                source_root=source_root,
            )
            public_diagnostic = classify_javac_diagnostics(
                remapped_diagnostic
            )
            if private_diagnostic_report_out is not None:
                private_diagnostic = classify_javac_diagnostics(
                    remapped_diagnostic,
                    include_identifiers=True,
                )
                if (
                    private_diagnostic["report_id"]
                    != public_diagnostic["report_id"]
                    or private_diagnostic["frontier_id"]
                    != public_diagnostic["frontier_id"]
                ):
                    raise NamespaceVirtualizedCompileError(
                        "private/public javac diagnostic authority drifted"
                    )
                write_javac_diagnostic_report(
                    private_diagnostic,
                    private_diagnostic_report_out,
                )

            canonical_after_sha, canonical_after_files, canonical_after_bytes = (
                source_tree_digest(source_root)
            )
            if (
                canonical_after_sha != canonical_before_sha
                or len(canonical_after_files)
                != len(canonical_before_files)
                or canonical_after_bytes != canonical_before_bytes
            ):
                raise NamespaceVirtualizedCompileError(
                    "canonical source changed during failed virtualized compile"
                )

            dependency_sha = _sha256_file(dependency_jar)
            alias_sha = _sha256_file(alias_jar)
            material = {
                "alias_plan_id": private_alias_plan.get("plan_id"),
                "canonical_source_tree_sha256": canonical_before_sha,
                "dependency_jar_sha256": dependency_sha,
                "alias_dependency_jar_sha256": alias_sha,
                "overlay_id": overlay["overlay_id"],
                "overlay_source_tree_sha256": overlay[
                    "output_source_tree_sha256"
                ],
                "release": release,
                "source_count": len(sources),
                "status": "compile_failed",
                "javac_frontier_id": public_diagnostic[
                    "frontier_id"
                ],
            }
            compile_id = (
                "NSCOMPILE_"
                + _stable_digest(material)[:20].upper()
            )
            report = {
                "schema_version": 1,
                "kind": "namespace_virtualized_compile",
                "compile_id": compile_id,
                "status": "compile_failed",
                "alias_plan_id": private_alias_plan.get("plan_id"),
                "canonical_source_tree_sha256": canonical_before_sha,
                "canonical_source_tree_sha256_after": (
                    canonical_after_sha
                ),
                "canonical_source_modified": False,
                "dependency_jar_sha256": dependency_sha,
                "compile_only_alias_dependency": {
                    "path": "compile-alias-dependency.jar",
                    "sha256": alias_sha,
                    "runtime_allowed": False,
                    "class_count": alias_stats["class_count"],
                    "changed_class_count": alias_stats[
                        "changed_class_count"
                    ],
                    "replacement_count": alias_stats[
                        "replacement_count"
                    ],
                },
                "overlay": {
                    "overlay_id": overlay["overlay_id"],
                    "input_source_tree_sha256": overlay[
                        "input_source_tree_sha256"
                    ],
                    "output_source_tree_sha256": overlay[
                        "output_source_tree_sha256"
                    ],
                    "changed_file_count": overlay[
                        "changed_file_count"
                    ],
                    "replacement_count": overlay[
                        "replacement_count"
                    ],
                },
                "compiler": {
                    "target_release": release,
                    "source_count": len(sources),
                    "javac_input_transport": "argfile",
                    "exit_code": proc.returncode,
                    "diagnostic_classification": (
                        _public_diagnostic_summary(
                            public_diagnostic
                        )
                    ),
                },
                "generated_alias_classes": {
                    "class_count": 0,
                    "tree_sha256": None,
                    "total_bytes": 0,
                },
                "restored_classes": {
                    "class_count": 0,
                    "tree_sha256": None,
                    "total_bytes": 0,
                    "restore_replacement_count": 0,
                    "alias_utf8_reference_count": 0,
                    "alias_literal_reference_count": 0,
                },
                "runtime_alias_dependency_allowed": False,
            }
            (out_dir / "namespace-virtualized-compile.json").write_text(
                json.dumps(
                    report,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            return report

        generated_sha, generated_files, generated_bytes = _class_tree(
            generated_dir
        )
        if not generated_files:
            raise NamespaceVirtualizedCompileError(
                "javac produced no classfiles"
            )

        aliases = sorted(mapping.values())
        generated_data = [
            path.read_bytes()
            for path in generated_files
        ]
        assert_no_literal_alias_mentions(
            generated_data,
            aliases,
        )

        restored_dir.mkdir(parents=True, exist_ok=True)
        replacement_count = 0

        for path in generated_files:
            rel = path.relative_to(generated_dir)
            rel_posix = rel.as_posix()
            if any(
                alias + ".class" in rel_posix
                or rel_posix.startswith(alias + "/")
                for alias in aliases
            ):
                raise NamespaceVirtualizedCompileError(
                    "generated project class path contains compile-only alias"
                )

            original = path.read_bytes()
            restored = remap_classfile_utf8(
                original,
                reverse,
            )
            replacement_count += restored.replacement_count

            target = restored_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(restored.data)

        restored_sha, restored_files, restored_bytes = _class_tree(
            restored_dir
        )
        restored_data = [
            path.read_bytes()
            for path in restored_files
        ]

        assert_no_literal_alias_mentions(
            restored_data,
            aliases,
        )
        assert_no_utf8_alias_references(
            restored_data,
            aliases,
        )

    except (
        ClassfileRemapError,
        NamespaceAliasPlanError,
        NamespaceSourceOverlayError,
    ) as exc:
        raise NamespaceVirtualizedCompileError(str(exc)) from exc

    canonical_after_sha, canonical_after_files, canonical_after_bytes = (
        source_tree_digest(source_root)
    )
    if (
        canonical_after_sha != canonical_before_sha
        or len(canonical_after_files) != len(canonical_before_files)
        or canonical_after_bytes != canonical_before_bytes
    ):
        raise NamespaceVirtualizedCompileError(
            "canonical source changed during virtualized compile"
        )

    dependency_sha = _sha256_file(dependency_jar)
    alias_sha = _sha256_file(alias_jar)

    material = {
        "alias_plan_id": private_alias_plan.get("plan_id"),
        "canonical_source_tree_sha256": canonical_before_sha,
        "dependency_jar_sha256": dependency_sha,
        "alias_dependency_jar_sha256": alias_sha,
        "overlay_id": overlay["overlay_id"],
        "overlay_source_tree_sha256": overlay[
            "output_source_tree_sha256"
        ],
        "release": release,
        "source_count": len(sources),
        "generated_class_count": len(generated_files),
        "generated_class_tree_sha256": generated_sha,
        "restored_class_count": len(restored_files),
        "restored_class_tree_sha256": restored_sha,
        "restore_replacement_count": replacement_count,
    }
    compile_id = (
        "NSCOMPILE_"
        + _stable_digest(material)[:20].upper()
    )

    report = {
        "schema_version": 1,
        "kind": "namespace_virtualized_compile",
        "compile_id": compile_id,
        "status": "complete",
        "alias_plan_id": private_alias_plan.get("plan_id"),
        "canonical_source_tree_sha256": canonical_before_sha,
        "canonical_source_tree_sha256_after": canonical_after_sha,
        "canonical_source_modified": False,
        "dependency_jar_sha256": dependency_sha,
        "compile_only_alias_dependency": {
            "path": "compile-alias-dependency.jar",
            "sha256": alias_sha,
            "runtime_allowed": False,
            "class_count": alias_stats["class_count"],
            "changed_class_count": alias_stats[
                "changed_class_count"
            ],
            "replacement_count": alias_stats[
                "replacement_count"
            ],
        },
        "overlay": {
            "overlay_id": overlay["overlay_id"],
            "input_source_tree_sha256": overlay[
                "input_source_tree_sha256"
            ],
            "output_source_tree_sha256": overlay[
                "output_source_tree_sha256"
            ],
            "changed_file_count": overlay[
                "changed_file_count"
            ],
            "replacement_count": overlay[
                "replacement_count"
            ],
        },
        "compiler": {
            "target_release": release,
            "source_count": len(sources),
            "javac_input_transport": "argfile",
            "exit_code": 0,
            "diagnostic_classification": None,
        },
        "generated_alias_classes": {
            "class_count": len(generated_files),
            "tree_sha256": generated_sha,
            "total_bytes": generated_bytes,
        },
        "restored_classes": {
            "class_count": len(restored_files),
            "tree_sha256": restored_sha,
            "total_bytes": restored_bytes,
            "restore_replacement_count": replacement_count,
            "alias_utf8_reference_count": 0,
            "alias_literal_reference_count": 0,
        },
        "runtime_alias_dependency_allowed": False,
    }

    (out_dir / "namespace-virtualized-compile.json").write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return report
