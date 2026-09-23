from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any


class DecompilerError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_decompiler(
    input_jar: Path,
    decompiler_jar: Path,
    *,
    expected_decompiler_sha256: str,
    engine: str,
    out_dir: Path,
    clean_out: bool = False,
    java_command: str = "java",
    input_class_files: list[Path] | None = None,
    max_command_chars: int = 12000,
) -> dict[str, Any]:
    input_jar = input_jar.resolve()
    decompiler_jar = decompiler_jar.resolve()
    out_dir = out_dir.resolve()

    if not input_jar.is_file():
        raise DecompilerError(f"input JAR does not exist: {input_jar}")
    if not decompiler_jar.is_file():
        raise DecompilerError(
            f"decompiler JAR does not exist: {decompiler_jar}"
        )

    actual_decompiler_sha = sha256_file(decompiler_jar)
    if (
        actual_decompiler_sha.lower()
        != expected_decompiler_sha256.lower()
    ):
        raise DecompilerError(
            "decompiler SHA-256 mismatch: "
            f"{actual_decompiler_sha} != {expected_decompiler_sha256}"
        )

    engine = engine.lower()
    if engine not in {"cfr", "vineflower", "procyon"}:
        raise DecompilerError(
            "engine must be one of: cfr, vineflower, procyon"
        )

    class_files: list[Path] | None = None
    if input_class_files is not None:
        if engine != "procyon":
            raise DecompilerError(
                "selective class-file input is currently supported only by Procyon"
            )
        if not isinstance(max_command_chars, int) or max_command_chars < 1024:
            raise DecompilerError("max_command_chars must be an integer >= 1024")
        if not isinstance(max_batch_classes, int) or max_batch_classes < 1:
            raise DecompilerError("max_batch_classes must be an integer >= 1")
        class_files = sorted(
            {Path(path).resolve() for path in input_class_files},
            key=lambda path: path.as_posix(),
        )
        if not class_files:
            raise DecompilerError("selective class-file input must not be empty")
        missing = [path for path in class_files if not path.is_file()]
        if missing:
            raise DecompilerError(
                "selective class-file input contains missing files: "
                + repr([str(path) for path in missing[:10]])
            )

    if out_dir.exists():
        if clean_out:
            shutil.rmtree(out_dir)
        elif any(out_dir.iterdir()):
            raise DecompilerError(
                "output directory is not empty; use clean_out explicitly"
            )
    out_dir.mkdir(parents=True, exist_ok=True)

    java = shutil.which(java_command)
    if java is None:
        raise DecompilerError(
            f"required executable not found on PATH: {java_command}"
        )

    commands: list[list[str]]
    input_mode = "whole_archive"
    if engine == "cfr":
        commands = [[
            java,
            "-jar",
            str(decompiler_jar),
            str(input_jar),
            "--outputdir",
            str(out_dir),
        ]]
    elif engine == "vineflower":
        commands = [[
            java,
            "-jar",
            str(decompiler_jar),
            str(input_jar),
            str(out_dir),
        ]]
    elif class_files is None:
        commands = [[
            java,
            "-jar",
            str(decompiler_jar),
            "-jar",
            str(input_jar),
            "-o",
            str(out_dir),
        ]]
    else:
        input_mode = "class_files"
        base = [java, "-jar", str(decompiler_jar), "-o", str(out_dir)]
        commands = []
        current = list(base)
        current_chars = sum(len(value) + 1 for value in current)
        for class_file in class_files:
            value = str(class_file)
            extra = len(value) + 1
            current_class_count = len(current) - len(base)
            if len(current) > len(base) and (
                current_class_count >= max_batch_classes
                or current_chars + extra > max_command_chars
            ):
                commands.append(current)
                current = list(base)
                current_chars = sum(len(item) + 1 for item in current)
            if current_chars + extra > max_command_chars:
                raise DecompilerError(
                    "one selective class-file path exceeds max_command_chars"
                )
            current.append(value)
            current_chars += extra
        if len(current) > len(base):
            commands.append(current)

    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    for batch_index, cmd in enumerate(commands, start=1):
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout_parts.append(proc.stdout)
        stderr_parts.append(proc.stderr)
        if proc.returncode != 0:
            raise DecompilerError(
                f"{engine} decompiler batch {batch_index}/{len(commands)} "
                f"failed with exit code {proc.returncode}\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )

    combined_stdout = "".join(stdout_parts)
    combined_stderr = "".join(stderr_parts)

    java_files = sorted(out_dir.rglob("*.java"))
    if not java_files:
        raise DecompilerError(
            f"{engine} completed but produced no .java files"
        )

    return {
        "schema_version": 1,
        "kind": "decompiler_result",
        "engine": engine,
        "input_sha256": sha256_file(input_jar),
        "decompiler_sha256": actual_decompiler_sha,
        "java_file_count": len(java_files),
        "output_directory": str(out_dir),
        "input_mode": input_mode,
        "selected_class_file_count": (
            len(class_files) if class_files is not None else None
        ),
        "batch_count": len(commands),
        "stdout": combined_stdout,
        "stderr": combined_stderr,
    }


def write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
