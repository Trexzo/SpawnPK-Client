from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any


class SourceRewriteError(ValueError):
    pass


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


def _helper_source() -> Path:
    path = Path(__file__).resolve().parent / "java" / "SourceNameRewriter.java"
    if not path.is_file():
        raise SourceRewriteError(f"missing packaged source rewriter helper: {path}")
    return path


def _require_executable(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise SourceRewriteError(f"required executable not found on PATH: {name}")
    return found


def _b64(value: Any) -> str:
    text = "" if value is None else str(value)
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def _validate_plan(
    plan: dict[str, Any],
    *,
    input_tree_sha256: str,
) -> list[dict[str, Any]]:
    if plan.get("schema_version") != 1:
        raise SourceRewriteError("unsupported source rename plan schema")
    if plan.get("kind") != "source_rename_plan":
        raise SourceRewriteError("wrong source rename plan kind")
    expected = str(plan.get("source_tree_sha256", "")).lower()
    if expected != input_tree_sha256.lower():
        raise SourceRewriteError(
            f"source tree SHA-256 {input_tree_sha256} does not match plan {expected}"
        )
    renames = plan.get("renames")
    if not isinstance(renames, list) or not renames:
        raise SourceRewriteError("source rename plan contains no accepted renames")

    seen_symbols: set[str] = set()
    seen_locations: set[tuple[str, int]] = set()
    for i, row in enumerate(renames):
        if not isinstance(row, dict):
            raise SourceRewriteError(f"renames[{i}] must be an object")
        symbol_id = row.get("source_symbol_id")
        source_file = row.get("source_file")
        start = row.get("declaration_start")
        old = row.get("current_name")
        new = row.get("new_name")
        if not all(isinstance(value, str) and value for value in (symbol_id, source_file, old, new)):
            raise SourceRewriteError(
                f"renames[{i}] requires non-empty symbol/file/current/new strings"
            )
        if not isinstance(start, int) or isinstance(start, bool) or start < 0:
            raise SourceRewriteError(f"renames[{i}].declaration_start must be >= 0")
        if old == new:
            raise SourceRewriteError(f"{symbol_id}: no-op source rename")
        if symbol_id in seen_symbols:
            raise SourceRewriteError(f"duplicate source symbol in rename plan: {symbol_id}")
        seen_symbols.add(symbol_id)
        location = (source_file, start)
        if location in seen_locations:
            raise SourceRewriteError(
                f"duplicate source declaration location in rename plan: {location!r}"
            )
        seen_locations.add(location)
    return renames


def _write_mapping(rows: list[dict[str, Any]], out: Path) -> None:
    lines = []
    for row in sorted(
        rows,
        key=lambda item: (
            str(item["source_file"]),
            int(item["declaration_start"]),
            str(item["source_symbol_id"]),
        ),
    ):
        lines.append(
            "\t".join(
                [
                    _b64(row["source_file"]),
                    str(row["declaration_start"]),
                    _b64(row["current_name"]),
                    _b64(row["new_name"]),
                    _b64(row["source_symbol_id"]),
                ]
            )
        )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _compile_helper(
    classes_dir: Path,
    *,
    javac: str,
) -> None:
    classes_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            javac,
            "--add-modules",
            "jdk.compiler",
            "-d",
            str(classes_dir),
            str(_helper_source()),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise SourceRewriteError(
            "source rewriter helper compilation failed:\n"
            + proc.stdout
            + proc.stderr
        )


def _run_helper(
    source_root: Path,
    mapping: Path,
    classes_dir: Path,
    *,
    java: str,
    classpath: list[Path],
) -> dict[str, int]:
    cmd = [
        java,
        "--add-modules",
        "jdk.compiler",
        "-cp",
        str(classes_dir),
        "SourceNameRewriter",
        str(source_root),
        str(mapping),
    ]
    if classpath:
        cmd.append(os.pathsep.join(str(path) for path in classpath))

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise SourceRewriteError(
            "semantic source rewrite failed:\n"
            + proc.stdout
            + proc.stderr
        )

    values: dict[str, int] = {}
    passed = False
    for line in proc.stdout.splitlines():
        if line.strip() == "SPK_SOURCE_REWRITE_PASS":
            passed = True
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            if key in {"accepted_symbols", "files_changed", "replacements"}:
                try:
                    values[key] = int(value)
                except ValueError as exc:
                    raise SourceRewriteError(
                        f"invalid source rewriter counter: {line!r}"
                    ) from exc
    if not passed:
        raise SourceRewriteError(
            "source rewriter exited successfully without PASS marker"
        )
    for key in ("accepted_symbols", "files_changed", "replacements"):
        if key not in values:
            raise SourceRewriteError(
                f"source rewriter did not report {key}"
            )
    return values


def rewrite_source_workspace(
    plan: dict[str, Any],
    source_root: Path,
    *,
    out_dir: Path,
    classpath: list[Path] | None = None,
    java_command: str = "java",
    javac_command: str = "javac",
) -> dict[str, Any]:
    """Rewrite accepted source symbols in a copied source workspace.

    The input tree is never modified. The Java helper uses javac semantic
    element resolution so only the declaration and identifier uses belonging
    to the exact accepted variable element are changed.
    """
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise SourceRewriteError(f"source root does not exist: {source_root}")

    input_sha, input_count, input_bytes = _source_tree_digest(source_root)
    renames = _validate_plan(plan, input_tree_sha256=input_sha)

    resolved_classpath: list[Path] = []
    for value in classpath or []:
        path = value.resolve()
        if not path.exists():
            raise SourceRewriteError(f"classpath entry does not exist: {path}")
        resolved_classpath.append(path)

    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SourceRewriteError(
            "source rewrite output directory must be empty"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    rewritten_root = out_dir / "src"

    # Copy the complete source workspace so non-Java companion files survive.
    shutil.copytree(source_root, rewritten_root)

    java = _require_executable(java_command)
    javac = _require_executable(javac_command)

    try:
        with tempfile.TemporaryDirectory(prefix="spk-source-rewrite-") as td:
            temp = Path(td)
            classes = temp / "classes"
            mapping = temp / "source-renames.tsv"
            _write_mapping(renames, mapping)
            _compile_helper(classes, javac=javac)
            counters = _run_helper(
                rewritten_root,
                mapping,
                classes,
                java=java,
                classpath=resolved_classpath,
            )
    except Exception:
        # Do not leave a partially rewritten source tree that looks complete.
        shutil.rmtree(rewritten_root, ignore_errors=True)
        raise

    if counters["accepted_symbols"] != len(renames):
        shutil.rmtree(rewritten_root, ignore_errors=True)
        raise SourceRewriteError(
            "rewriter accepted-symbol count disagrees with rename plan: "
            f"{counters['accepted_symbols']} != {len(renames)}"
        )
    if counters["files_changed"] <= 0 or counters["replacements"] < len(renames):
        shutil.rmtree(rewritten_root, ignore_errors=True)
        raise SourceRewriteError(
            "rewriter did not report the expected declaration replacements"
        )

    output_sha, output_count, output_bytes = _source_tree_digest(rewritten_root)
    if output_count != input_count:
        shutil.rmtree(rewritten_root, ignore_errors=True)
        raise SourceRewriteError(
            f"Java file count changed during source rewrite: {output_count} != {input_count}"
        )
    if output_sha == input_sha:
        shutil.rmtree(rewritten_root, ignore_errors=True)
        raise SourceRewriteError("accepted source rename produced no source-tree change")

    material = {
        "plan_id": plan.get("plan_id"),
        "inventory_id": plan.get("inventory_id"),
        "input_source_tree_sha256": input_sha,
        "output_source_tree_sha256": output_sha,
        "renames": [
            (
                row["source_symbol_id"],
                row["current_name"],
                row["new_name"],
            )
            for row in sorted(
                renames,
                key=lambda item: str(item["source_symbol_id"]),
            )
        ],
    }
    rewrite_id = (
        "SRCREWRITE_"
        + hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )

    manifest = {
        "schema_version": 1,
        "kind": "source_rewrite_manifest",
        "rewrite_id": rewrite_id,
        "plan_id": plan.get("plan_id"),
        "inventory_id": plan.get("inventory_id"),
        "review_id": plan.get("review_id"),
        "workspace_id": plan.get("workspace_id"),
        "build_id": plan.get("build_id"),
        "input_source_tree_sha256": input_sha,
        "output_source_tree_sha256": output_sha,
        "java_file_count": output_count,
        "input_source_bytes": input_bytes,
        "output_source_bytes": output_bytes,
        "accepted_rename_count": len(renames),
        "files_changed": counters["files_changed"],
        "identifier_replacements": counters["replacements"],
        "classpath": [
            {
                "path": str(path),
                "sha256": (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                    if path.is_file()
                    else None
                ),
            }
            for path in resolved_classpath
        ],
        "source_directory": "src",
        "semantic_analysis_pass": True,
        "note": (
            "Names are explicitly accepted inferred replacements. "
            "They are not claimed to be lost original local/parameter names."
        ),
    }
    (out_dir / "source-rewrite-manifest.json").write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "source-rename-plan.json").write_text(
        json.dumps(
            plan,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest
