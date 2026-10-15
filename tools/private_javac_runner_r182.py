"""Private, source-only javac runner for the R182 diagnostic frontier.

Never uses an original client binary, silently obtains dependencies, or launches
game code. Compiler arguments are provided as a JSON argv array, not a shell.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from source_manifest_r182 import inventory_source, inspect_dependencies, digest_bytes
from javac_frontier_r182 import parse_transcript

def verify_javac(executable: Path, expected_sha: str) -> str:
    if not executable.is_file() or not re.fullmatch(r"[a-fA-F0-9]{64}", expected_sha):
        raise ValueError("Pinned javac executable required")
    actual = digest_bytes(executable.read_bytes())
    if actual.lower() != expected_sha.lower():
        raise ValueError("javac SHA-256 mismatch")
    return actual

def safe_argv(options: list[str]) -> None:
    if not isinstance(options, list) or any(not isinstance(x, str) for x in options):
        raise ValueError("Options must be a JSON array of strings")
    # No response files, classpaths, module paths, processors or alternate source
    # roots: all dependencies must be supplied through the approved manifest.
    blocked = ("-cp", "-classpath", "--class-path", "-p", "--module-path",
               "-processorpath", "--processor-path", "-sourcepath",
               "--source-path", "-bootclasspath", "--upgrade-module-path",
               "-Xbootclasspath", "-endorseddirs", "-extdirs", "-processor",
               "-d", "-s", "-h", "-J", "--patch-module")
    for option in options:
        if option.startswith("@") or option in blocked or any(
            option.startswith(x + "=") or option.startswith(x + ":") for x in blocked
        ):
            raise ValueError("Unsafe javac option: " + option)
        if option not in ("-XDrawDiagnostics", "-proc:none", "-encoding", "UTF-8",
                          "--release", "9", "-Xmaxerrs", "1000000"):
            raise ValueError("Only the fixed Java 9 diagnostic options are allowed: " + option)

def run(source_root: Path, java: Path, java_sha: str, deps: list[Path],
        approved: dict, timeout: int = 180) -> dict:
    if not (1 <= timeout <= 1200):
        raise ValueError("Invalid timeout")
    inv = inventory_source(source_root)
    dependencies = inspect_dependencies(deps, approved)
    actual = verify_javac(java, java_sha)
    source_root = source_root.resolve()
    # Source set from the hashed inventory; no glob expansion by javac.
    sources = [str(source_root / entry["path"]) for entry in inv["files"]]
    command = [str(java), "-XDrawDiagnostics", "-proc:none", "-encoding", "UTF-8",
               "--release", "9", "-Xmaxerrs", "1000000"]
    safe_argv(command[1:])
    if deps:
        # The explicit -classpath is generated here, never accepted from users.
        command += ["-classpath", os.pathsep.join(str(p.resolve()) for p in deps)]
    else:
        # Remove inherited CLASSPATH influence, below.
        command += ["-classpath", ""]
    command += sources
    env = {key: value for key, value in os.environ.items()
           if key not in ("CLASSPATH", "JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS")}
    try:
        completed = subprocess.run(command, env=env, cwd=source_root,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding="utf-8", errors="replace",
                                   timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("javac timed out; no complete inventory") from exc
    output = completed.stdout + "\n" + completed.stderr
    rows, unparsed = parse_transcript(output.splitlines())
    reported = re.findall(r"(?m)^\s*(\d+) errors?\s*$", output)
    errors = sum(r["key"].startswith("compiler.err.") for r in rows)
    claimed = sum(map(int, reported)) if reported else None
    return {
        "schema": "spk.private-javac-run.r182.v1",
        "javac_executable_sha256": actual,
        "source_scope_sha256": inv["source_scope_sha256"],
        "dependency_manifest_sha256": dependencies["dependency_manifest_sha256"],
        "sources": inv["file_count"],
        "dependencies": len(dependencies["dependencies"]),
        "compiler_exit_code": completed.returncode,
        "parsed_error_count": errors,
        "reported_error_count": claimed,
        "complete_error_inventory": claimed is not None and claimed == errors and not unparsed,
        "unparsed_line_count": len(unparsed),
        "transcript_sha256": digest_bytes(output.encode("utf-8")),
        "compiler_output": output,
        "limitations": [
            "Only direct JAR dependencies inspected; no transitive/shaded class proof",
            "Executable bytes pinned but toolchain installation/runtime libraries not pinned",
            "Compiler's environment and Java module graph not independently authenticated",
            "Compilation result does not establish original-bytecode equivalence",
        ],
    }

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--javac", type=Path, required=True)
    p.add_argument("--javac-sha256", required=True)
    p.add_argument("--approved-deps-json", type=Path, required=True)
    p.add_argument("--deps", type=Path, nargs="*", default=[])
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=180)
    args = p.parse_args()
    approved = json.loads(args.approved_deps_json.read_text(encoding="utf-8"))
    result = run(args.source_root, args.javac, args.javac_sha256,
                 args.deps, approved, args.timeout)
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2, sort_keys=True)
        file.write("\n")

if __name__ == "__main__":
    main()
