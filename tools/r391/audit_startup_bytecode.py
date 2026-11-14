"""R391: read-only, SHA-pinned original-v309 vs reconstructed startup bytecode audit.

Invokes JDK javap only. Never invokes a client main method, initializes a class,
connects to a game server, opens application settings, or changes user caches.
Reports only aggregate behavior flags/counts, not raw proprietary disassembly.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_DISASSEMBLY_CHARS = 8_000_000
HEX = re.compile(r"[0-9a-f]{64}\Z")
TARGETS = {
    "rs.gui.Launcher": ("main(java.lang.String[])", "b()"),
    "rs.Client": ("init()", "main(java.lang.String[])"),
}
CALL = re.compile(r"^\s*\d+:\s+invoke(?:virtual|special|static|interface|dynamic)\b")
BRANCH = re.compile(r"^\s*\d+:\s+if(?:eq|ne|lt|le|gt|ge|null|nonnull|_icmp\w*|_acmp\w*)\b")
METHOD = re.compile(r"^  (?:public|protected|private|static).+\([^)]*\);$")


class Refused(ValueError):
    pass


def hash_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def pin_archive(path: Path, expected: str) -> None:
    if not HEX.fullmatch(expected):
        raise Refused("INVALID_SHA256_PIN")
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise Refused("INVALID_OR_UNSAFE_ARCHIVE")
    if hash_file(path) != expected:
        raise Refused("ARCHIVE_SHA256_DRIFT")


def disassemble(javap: Path, jar: Path, classname: str) -> str:
    if javap.is_symlink() or not javap.is_file() or javap.name.lower() not in ("javap.exe", "javap"):
        raise Refused("INVALID_JAVAP_EXECUTABLE")
    if classname not in TARGETS:
        raise Refused("UNSUPPORTED_CLASS")
    env = dict(os.environ)
    env.pop("JAVA_TOOL_OPTIONS", None)
    env.pop("JDK_JAVA_OPTIONS", None)
    try:
        completed = subprocess.run(
            [str(javap), "-private", "-c", "-s", "-classpath", str(jar), classname],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=45, check=False, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        raise Refused("JAVAP_EXECUTION_FAILED") from err
    if completed.returncode or len(completed.stdout) > MAX_DISASSEMBLY_CHARS:
        raise Refused("JAVAP_NO_VALID_DISASSEMBLY")
    return completed.stdout.decode("utf-8", "replace")


def method_body(disassembly: str, signature: str) -> list[str]:
    lines = disassembly.splitlines()
    headers = [index for index, row in enumerate(lines) if METHOD.match(row)]
    matches = [index for index in headers if signature in lines[index]]
    if len(matches) != 1:
        raise Refused("MISSING_OR_AMBIGUOUS_METHOD")
    start = matches[0]
    end = next((index for index in headers if index > start), len(lines))
    body = lines[start:end]
    if not any(row.strip() == "Code:" for row in body):
        raise Refused("METHOD_WITHOUT_CODE")
    return body


def features(body: list[str]) -> dict:
    calls = [line for line in body if CALL.search(line)]
    branches = [line for line in body if BRANCH.search(line)]
    def matches(marker: str) -> int:
        return sum(marker in row for row in calls)
    return {
        "invocations": len(calls),
        "conditional_branches": len(branches),
        "log_deletes": matches("java/io/File.delete:"),
        "stdout_redirects": matches("java/lang/System.setOut:"),
        "stderr_redirects": matches("java/lang/System.setErr:"),
        "localhost_resolutions": matches("java/net/InetAddress.getLocalHost:"),
        "client_init_calls": matches("rs/Client.init:"),
        "client_start_calls": matches("rs/Client.start:"),
        "init_then_start": (
            next((i for i, row in enumerate(calls) if "rs/Client.init:" in row), -1) >= 0
            and next((i for i, row in enumerate(calls) if "rs/Client.start:" in row), -1)
            > next((i for i, row in enumerate(calls) if "rs/Client.init:" in row), -1)
        ),
        "configuration_log_gate": any(
            "rs/Configuration.field1252:Z" in row and "getstatic" in row for row in body
        ),
    }


def audit_text(original: dict[str, str], candidate: dict[str, str]) -> dict:
    findings = {}
    for classname, signatures in TARGETS.items():
        if classname not in original or classname not in candidate:
            raise Refused("MISSING_DISASSEMBLY")
        for signature in signatures:
            key = classname.rsplit(".", 1)[-1] + "." + signature
            findings[key] = {
                "original": features(method_body(original[classname], signature)),
                "candidate": features(method_body(candidate[classname], signature)),
            }
    omain = findings["Launcher.main(java.lang.String[])"]["original"]
    cmain = findings["Launcher.main(java.lang.String[])"]["candidate"]
    ob = findings["Launcher.b()"]["original"]
    cb = findings["Launcher.b()"]["candidate"]
    oinit = findings["Client.init()"]["original"]
    cinit = findings["Client.init()"]["candidate"]
    return {
        "status": "R391_READ_ONLY_STARTUP_AUDIT",
        "methods": findings,
        "comparison": {
            "original_log_redirection_present": bool(
                omain["stdout_redirects"] and omain["stderr_redirects"]
            ),
            "reconstructed_log_redirection_present": bool(
                cmain["stdout_redirects"] and cmain["stderr_redirects"]
            ),
            "reconstructed_adds_log_configuration_guard": (
                cmain["configuration_log_gate"] and not omain["configuration_log_gate"]
            ),
            "original_launcher_b_init_then_start": ob["init_then_start"],
            "candidate_launcher_b_init_then_start": cb["init_then_start"],
            "both_client_init_resolve_localhost": bool(
                oinit["localhost_resolutions"] and cinit["localhost_resolutions"]
            ),
            "launcher_main_call_count_changed": (
                omain["invocations"] != cmain["invocations"]
            ),
        },
        "client_code_executed": False,
        "behavioral_equivalence_proven": False,
        "runtime_launch_approved": False,
        "private_source_release_approved": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--javap", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.original.resolve(strict=False) == args.candidate.resolve(strict=False):
            raise Refused("SAME_ARCHIVE")
        pin_archive(args.original, args.original_sha256)
        pin_archive(args.candidate, args.candidate_sha256)
        if args.out and (args.out.exists() or args.out.is_symlink()):
            raise Refused("REFUSE_EXISTING_OUTPUT")
        before = {k: disassemble(args.javap, args.original, k) for k in TARGETS}
        after = {k: disassemble(args.javap, args.candidate, k) for k in TARGETS}
        report = audit_text(before, after)
        report["original_sha256"] = args.original_sha256
        report["candidate_sha256"] = args.candidate_sha256
        rendered = json.dumps(report, sort_keys=True, indent=2) + "\n"
        if args.out:
            with args.out.open("x", encoding="utf-8") as stream:
                stream.write(rendered)
        else:
            print(rendered)
    except (Refused, OSError) as err:
        reason = str(err) if isinstance(err, Refused) else "FILESYSTEM_FAILURE"
        print(json.dumps({"status": "R391_REFUSED", "reason": reason}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
