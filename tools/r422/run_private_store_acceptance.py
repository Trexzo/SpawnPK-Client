#!/usr/bin/env python3
"""R422 opt-in acceptance of *actual* owner-private compiled LootHistoryStore.

Only supports the owner-provided exact private classpath and explicitly
fabricated, new TEMP roots. Does not launch the SpawnPK client, read real
history, delete artifacts, package a JAR or publish private bytecode.
Run only after review and only against a SHA-pinned private candidate.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from queue import Empty, Queue
from threading import Thread


CLASS_REL = Path("rs/plugins/loottracker/LootHistoryStore.class")
MAIN = "rs.plugins.loottracker.R422ActualStoreAcceptance"


def require(ok: bool, code: str) -> None:
    if not ok:
        raise RuntimeError(code)


def sha_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def run(command: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True,
                          timeout=timeout, check=False)


def exact_stdout_protocol(output: str, *expected: str) -> bool:
    """Accept only complete, ordered stdout records from a child JVM.

    Java uses LF/CRLF platform newline conventions. We accept either while
    rejecting substring matches, prefixes, suffixes, extra lines, embedded
    carriage returns, and missing final line terminators. All negative and
    ambiguous output must fail closed; stderr remains diagnostic only.
    """
    if type(output) is not str or not expected:
        return False
    if any(type(token) is not str or not token or "\n" in token
           or "\r" in token for token in expected):
        return False
    return output in ("".join(t + "\n" for t in expected),
                      "".join(t + "\r\n" for t in expected))


def exact_invalid_root_refusal(process: subprocess.CompletedProcess) -> bool:
    """Evidence of the public Java harness's explicit invalid-root exit.

    Do not infer a negative-test pass from arbitrary stderr/stacktrace text.
    Exit 64 and the one complete refusal record must both be present.
    """
    return (
        process.returncode == 64
        and exact_stdout_protocol(
            process.stdout, "R422_REFUSE_NON_SYNTHETIC_TEMP_ROOT")
    )


def parse_r422_selftest_assertions(output: str) -> int | None:
    """Parse the entire R422 Java self-test stdout, never a substring.

    The public Java harness can legitimately emit exactly one optional
    symlink-unavailable warning before its final assertion receipt. All
    other stdout, missing final newlines and malformed counts fail closed.
    Python text subprocesses normalize platform line endings, but direct
    callers can supply either complete LF or CRLF records.
    """
    if type(output) is not str:
        return None
    for eol in ("\n", "\r\n"):
        match = re.fullmatch(
            r"(?:R422_OPTIONAL_SYMLINK_UNAVAILABLE" + re.escape(eol) + r")?"
            r"R422_ACTUAL_PRIVATE_STORE_PASS assertions=([1-9][0-9]{0,5})"
            + re.escape(eol),
            output,
        )
        if match is not None:
            return int(match.group(1))
    return None


def read_holder_announcement(holder: subprocess.Popen, timeout: float = 10.0) -> str:
    """Wait at most timeout seconds for a held owner to announce its state.

    A daemon reader thread is necessary because pipe.readline() has no
    portable timeout (select on Windows anonymous pipes is not supported).
    The caller MUST retain its existing try/finally that kills/reaps the
    holder and closes its pipes on timeout or any other refusal.
    """
    require(timeout > 0, "R422_INVALID_HOLDER_STARTUP_DEADLINE")
    require(holder.stdout is not None, "R422_HOLDER_STDOUT_NOT_CAPTURED")
    events = Queue(maxsize=1)

    def read_line() -> None:
        try:
            events.put(("line", holder.stdout.readline(64)))
        except (OSError, ValueError):
            events.put(("error", ""))

    Thread(target=read_line, daemon=True,
           name="R422-holder-announcement-reader").start()
    try:
        kind, line = events.get(timeout=timeout)
    except Empty:
        raise RuntimeError("R422_OWNER_HOLDER_STARTUP_TIMEOUT") from None
    require(kind == "line", "R422_OWNER_HOLDER_STDOUT_READ_FAILED")
    require(bool(line), "R422_OWNER_HOLDER_EXITED_BEFORE_ANNOUNCEMENT")
    # No strip(): " ACQUIRED", "ACQUIRED " or an unterminated line must
    # never count as acquiring the JVM ownership lease.
    require(
        exact_stdout_protocol(line, "ACQUIRED")
        or exact_stdout_protocol(line, "REFUSED_OWNER")
        or exact_stdout_protocol(line, "REFUSED_PREPARE"),
        "R422_HOLDER_MALFORMED_ANNOUNCEMENT",
    )
    return line[:-2] if line.endswith("\r\n") else line[:-1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--javac", type=Path, required=True)
    parser.add_argument("--private-classes", type=Path, required=True)
    parser.add_argument("--dependency-a", type=Path, required=True)
    parser.add_argument("--dependency-b", type=Path, required=True)
    parser.add_argument("--public-java-source", type=Path, required=True)
    parser.add_argument("--expected-store-class-sha256", required=True)
    args = parser.parse_args(argv)

    require(re.fullmatch(r"[0-9a-f]{64}",
                        args.expected_store_class_sha256) is not None,
            "INVALID_EXPECTED_SHA")
    require(args.java.is_file() and args.javac.is_file(), "JDK_UNAVAILABLE")
    for path in (args.private_classes, args.dependency_a, args.dependency_b,
                 args.public_java_source):
        require(path.exists() and not path.is_symlink(), "MISSING_OR_SYMLINK_INPUT")
    require(args.private_classes.is_dir(), "PRIVATE_COMPILED_CLASSES_NOT_DIRECTORY")
    pinned_class = args.private_classes / CLASS_REL
    require(pinned_class.is_file() and not pinned_class.is_symlink(),
            "PRIVATE_STORE_CLASS_MISSING")
    require(sha_file(pinned_class) == args.expected_store_class_sha256,
            "PRIVATE_STORE_CLASS_SHA_PIN_MISMATCH")

    temp_parent = Path(tempfile.gettempdir()).resolve()
    require(temp_parent.is_dir() and not temp_parent.is_symlink(),
            "UNSAFE_SYSTEM_TEMP_PARENT")
    # Preserves every synthetic artifact for owner inspection. Does not delete.
    workspace = Path(tempfile.mkdtemp(
        prefix="R422-Synthetic-ActualStore-", dir=str(temp_parent)))
    classes = workspace / "harness-classes"
    classes.mkdir()
    cp = os.pathsep.join(map(str, (args.private_classes, args.dependency_a,
                                   args.dependency_b)))
    compiled = run([str(args.javac), "--release", "11", "-proc:none",
                    "-cp", cp, "-d", str(classes),
                    str(args.public_java_source)], timeout=60)
    require(compiled.returncode == 0,
            "HARNESS_COMPILE_FAILED:" + compiled.stderr[-1200:])

    full_cp = os.pathsep.join((str(classes), cp))
    def command(mode: str, root: Path) -> list[str]:
        return [str(args.java), "-Xmx512m",
                # Java and Python can have different default TEMP roots on
                # Windows GitHub runners. Use the already validated Python
                # TEMP parent for both instead of weakening Java's path gate.
                "-Djava.io.tmpdir=" + str(temp_parent),
                "-Duser.home=" + str(workspace),
                "-cp", full_cp, MAIN, mode, str(root)]

    cases = []
    def passed(label, condition):
        require(condition, "R422_CASE_FAILED_"+label)
        cases.append(label)

    selftest = run(command("selftest", workspace), timeout=50)
    assertions = parse_r422_selftest_assertions(selftest.stdout)
    if selftest.returncode != 0 or assertions is None or assertions < 73:
        raise RuntimeError(
            "R422_SELFTEST_DIAGNOSTIC:"
            + "exit=" + str(selftest.returncode)
            + ";stdout=" + selftest.stdout[-900:].replace("\n", " ")
            + ";stderr=" + selftest.stderr[-1600:].replace("\n", " ")
        )
    passed("actual_private_store_73_assertions", True)

    lock_root = Path(tempfile.mkdtemp(prefix="R422-Synthetic-Lock-",dir=str(temp_parent)))
    holder = subprocess.Popen(command("hold", lock_root),
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, bufsize=1)
    try:
        line = read_holder_announcement(holder)
        passed("actual_store_first_process_acquired", line == "ACQUIRED")
        contender = run(command("try", lock_root))
        passed("actual_store_second_process_refused",
               contender.returncode == 0 and
               exact_stdout_protocol(contender.stdout, "REFUSED_OWNER"))
        passed("actual_store_contender_did_not_create_history",
               not (lock_root / "loot-history.json").exists())
        holder.stdin.write("\n")
        holder.stdin.flush()
        holder.wait(timeout=10)
        passed("owner_release_terminates_normally", holder.returncode == 0)
        released_stdout = holder.stdout.read()
        passed("owner_release_receipt", exact_stdout_protocol(released_stdout, "RELEASED"))
    finally:
        if holder.poll() is None:
            holder.kill()
            holder.wait(timeout=5)
        for stream in (holder.stdin, holder.stdout, holder.stderr):
            if stream:
                stream.close()

    reacquired = run(command("try", lock_root))
    passed("actual_store_reacquire_after_shutdown",
           reacquired.returncode == 0 and exact_stdout_protocol(reacquired.stdout,
                                     "ACQUIRED", "RELEASED"))
    passed("real_os_lock_path_persists_after_release",
           (lock_root / "loot-history.writer.lock").is_file())

    crash_root = Path(tempfile.mkdtemp(prefix="R422-Synthetic-Crash-",dir=str(temp_parent)))
    crash = run(command("crash", crash_root))
    passed("actual_store_crash_exit", crash.returncode == 77 and
           exact_stdout_protocol(crash.stdout, "ACQUIRED"))
    passed("crash_keeps_inert_lock_file",
           (crash_root / "loot-history.writer.lock").is_file())
    after_crash = run(command("try", crash_root))
    passed("actual_store_reacquire_after_jvm_halt",
           after_crash.returncode == 0 and exact_stdout_protocol(after_crash.stdout,
                                              "ACQUIRED", "RELEASED"))

    new_leaf = workspace / "R422-Synthetic-NewLeaf"
    passed("new_leaf_absent_before", not new_leaf.exists())
    new_leaf_try = run(command("try", new_leaf))
    passed("actual_store_first_run_creates_leaf_and_acquires",
           new_leaf_try.returncode == 0 and exact_stdout_protocol(new_leaf_try.stdout,
                                           "ACQUIRED", "RELEASED")
           and new_leaf.is_dir())
    passed("first_run_does_not_create_history", not (new_leaf/"loot-history.json").exists())

    marker = lock_root / "loot-history.delete.ack"
    marker.write_bytes(b"fabricated-ack-do-not-modify")
    marker_before = marker.read_bytes()
    marker_probe = run(command("try", lock_root))
    passed("lease_try_does_not_repair_unresolved_marker",
           marker_probe.returncode == 0 and exact_stdout_protocol(marker_probe.stdout,
                                         "ACQUIRED", "RELEASED")
           and marker.read_bytes() == marker_before)
    passed("pinned_real_class_unchanged_by_acceptance",
           sha_file(pinned_class) == args.expected_store_class_sha256)

    outside = run(command("try", temp_parent))
    passed("non_synthetic_temp_root_is_rejected",
           exact_invalid_root_refusal(outside))

    print(json.dumps({
        "status": "R422_OWNER_PRIVATE_ACTUAL_STORE_PROCESS_ACCEPTANCE_PASS",
        "checks": len(cases),
        "real_store_assertions": assertions,
        "class_sha256_verified": args.expected_store_class_sha256,
        "synthetic_workspace": str(workspace),
        "synthetic_lock_root": str(lock_root),
        "synthetic_crash_root": str(crash_root),
        "cases": cases,
        "original_game_started": False,
        "production_history_opened": False,
        "private_release_authorized": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
        print(json.dumps({"status": "R422_OWNER_PRIVATE_ACCEPTANCE_REFUSED",
                          "reason": str(exc)[:1800]}))
        raise SystemExit(2)
