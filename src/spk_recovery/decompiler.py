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
    if engine not in {"cfr", "vineflower"}:
        raise DecompilerError(
            "engine must be one of: cfr, vineflower"
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

    if engine == "cfr":
        cmd = [
            java,
            "-jar",
            str(decompiler_jar),
            str(input_jar),
            "--outputdir",
            str(out_dir),
        ]
    else:
        cmd = [
            java,
            "-jar",
            str(decompiler_jar),
            str(input_jar),
            str(out_dir),
        ]

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise DecompilerError(
            f"{engine} decompiler failed with exit code "
            f"{proc.returncode}\nstdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )

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
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
