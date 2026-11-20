"""R437: strict, bounded first JVM lease announcement and invalid-root refusal.

All processes and file trees in this test are synthetic; the Java negative
test uses a fabricated Store facade and the unchanged public R422 harness.
No real private source/classes, live game, or history files are touched.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace

from tools.r422 import run_private_store_acceptance as r422

ROOT = Path(__file__).resolve().parents[1]
JAVA_HARNESS = ROOT / "tests/fixtures/r422/R422ActualStoreAcceptance.java"

SYNTHETIC_STORE = r"""
package rs.plugins.loottracker;
import java.util.List;
final class LootTrackerRecord { }
final class LootHistoryStore {
    static final String FILE_NAME = "loot-history.json";
    enum R411StageState { CLEAR, UNSAFE, ORPHAN }
    LootHistoryStore(String location) { }
    List<LootTrackerRecord> loadForMerge() { return null; }
    boolean saveWithReceipt(List<LootTrackerRecord> records) { return false; }
    boolean clearWithReceipt() { return false; }
    boolean r421PrepareHistoryDirectoryForLease() { return false; }
    boolean r419ActivateOwner() { return false; }
    R411StageState r411StageState() { return R411StageState.CLEAR; }
    void r419CloseOwner() { }
    boolean r419WithOwner(Runnable action) { return false; }
    void deleteStale() { }
}
"""


def start_python(source: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-u", "-c", source],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1,
    )


def reap(child: subprocess.Popen) -> None:
    if child.poll() is None:
        child.kill()
    child.wait(timeout=5)
    for stream in (child.stdin, child.stdout, child.stderr):
        if stream is not None:
            stream.close()


def announcement(source: str, deadline: float = 3.5) -> str:
    child = start_python(source)
    try:
        return r422.read_holder_announcement(child, deadline)
    finally:
        reap(child)


class R437ExactHolderAndNegativeRoot(unittest.TestCase):
    def test_01_owner_acquired_exact_complete_line(self):
        self.assertEqual(announcement("print('ACQUIRED',flush=True)"), "ACQUIRED")

    def test_02_defined_refusals_remain_distinct_from_owner_success(self):
        for token in ("REFUSED_OWNER", "REFUSED_PREPARE"):
            with self.subTest(token=token):
                self.assertEqual(announcement("print(" + repr(token) + ")"), token)
                self.assertNotEqual(token, "ACQUIRED")

    def test_03_refuse_whitespace_padded_ownership(self):
        for token in (" ACQUIRED", "ACQUIRED ", "\tACQUIRED",
                      "ACQUIRED\t", "  ACQUIRED  "):
            with self.subTest(token=repr(token)):
                with self.assertRaisesRegex(RuntimeError,
                                            "R422_HOLDER_MALFORMED_ANNOUNCEMENT"):
                    announcement("print(" + repr(token) + ",flush=True)")

    def test_04_refuse_negated_prefixed_or_renamed_success(self):
        for token in ("NOT_ACQUIRED", "PRE_ACQUIRED", "ACQUIRED=false",
                      "ACQUIRED_PENDING", "acquired", "OWNER_ACQUIRED"):
            with self.subTest(token=token):
                with self.assertRaisesRegex(RuntimeError,
                                            "R422_HOLDER_MALFORMED_ANNOUNCEMENT"):
                    announcement("print(" + repr(token) + ",flush=True)")

    def test_05_missing_final_terminator_does_not_count(self):
        for token in ("ACQUIRED", "REFUSED_OWNER"):
            with self.subTest(token=token):
                with self.assertRaisesRegex(RuntimeError,
                                            "R422_HOLDER_MALFORMED_ANNOUNCEMENT"):
                    announcement(
                        "import sys; sys.stdout.write(" + repr(token) +
                        "); sys.stdout.flush()"
                    )

    def test_06_overlong_line_is_refused_without_unbounded_read(self):
        child = start_python(
            "import sys,time; sys.stdout.write('ACQUIRED'+'X'*200000); "
            "sys.stdout.flush(); time.sleep(7)"
        )
        started = time.monotonic()
        try:
            with self.assertRaisesRegex(RuntimeError,
                                        "R422_HOLDER_MALFORMED_ANNOUNCEMENT"):
                r422.read_holder_announcement(child, 3)
        finally:
            reap(child)
        self.assertLess(time.monotonic() - started, 5)

    def test_07_empty_early_exit_remains_explicitly_refused(self):
        with self.assertRaisesRegex(RuntimeError,
                                    "R422_OWNER_HOLDER_EXITED_BEFORE_ANNOUNCEMENT"):
            announcement("pass")

    def test_08_silent_child_still_has_bounded_timeout(self):
        child = start_python("import time; time.sleep(8)")
        started = time.monotonic()
        try:
            with self.assertRaisesRegex(RuntimeError,
                                        "R422_OWNER_HOLDER_STARTUP_TIMEOUT"):
                r422.read_holder_announcement(child, 0.25)
        finally:
            reap(child)
        self.assertLess(time.monotonic() - started, 4)

    def test_09_invalid_root_requires_exact_exit_and_stdout(self):
        valid = "R422_REFUSE_NON_SYNTHETIC_TEMP_ROOT\n"
        accepted = SimpleNamespace(returncode=64, stdout=valid)
        self.assertTrue(r422.exact_invalid_root_refusal(accepted))
        for code, stdout in (
            (0, valid), (1, valid), (77, valid), (63, valid),
            (64, "NOT_" + valid), (64, "FAILURE\n" + valid),
            (64, valid + "ACQUIRED\n"), (64, valid.rstrip("\n")),
            (64, "R422_REFUSE_NON_SYNTHETIC_TEMP_ROOT \n"),
            (64, "R422_REFUSE_NON_SYNTHETIC_TEMP_ROOT=false\n"),
            (64, ""),
        ):
            with self.subTest(code=code, stdout=repr(stdout)):
                self.assertFalse(r422.exact_invalid_root_refusal(
                    SimpleNamespace(returncode=code, stdout=stdout)
                ))

    def test_10_real_public_java_harness_negative_root_protocol(self):
        javac = shutil.which("javac")
        java = shutil.which("java")
        if javac is None or java is None:
            self.skipTest("JDK unavailable outside CI")
        self.assertTrue(JAVA_HARNESS.is_file())
        with tempfile.TemporaryDirectory(prefix="R437-Synthetic-Compile-") as tmp:
            work = Path(tmp)
            facade = work / "R437SyntheticPrivateStore.java"
            facade.write_text(SYNTHETIC_STORE, encoding="utf-8")
            classes = work / "classes"
            classes.mkdir()
            build = subprocess.run(
                [javac, "--release", "11", "-proc:none", "-d", str(classes),
                 str(facade), str(JAVA_HARNESS)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            root = Path(tempfile.gettempdir())
            prefix = [java, "-Djava.io.tmpdir=" + str(root),
                      "-cp", str(classes),
                      "rs.plugins.loottracker.R422ActualStoreAcceptance"]
            # Invalid TEMP parent is not a synthetic leaf. The exact Java
            # harness rejects it before touching the fabricated Store.
            denied = subprocess.run(
                prefix + ["try", str(root)],
                capture_output=True, text=True, timeout=15,
            )
            self.assertTrue(
                r422.exact_invalid_root_refusal(denied),
                (denied.returncode, denied.stdout, denied.stderr)
            )
            # Valid named synthetic root enters the mode and our invented
            # Store refuses prepare; it must NOT issue the invalid-root code.
            with tempfile.TemporaryDirectory(
                    prefix="R422-Synthetic-R437-", dir=str(root)) as permitted:
                allowed = subprocess.run(
                    prefix + ["try", permitted],
                    capture_output=True, text=True, timeout=15,
                )
                self.assertEqual(allowed.returncode, 0, allowed.stderr)
                self.assertTrue(r422.exact_stdout_protocol(
                    allowed.stdout, "REFUSED_PREPARE"))
                self.assertFalse(r422.exact_invalid_root_refusal(allowed))

    def test_11_main_binds_explicit_root_protocol_and_reaps_holder(self):
        body = inspect.getsource(r422.main)
        helper = inspect.getsource(r422.read_holder_announcement)
        self.assertIn("read_holder_announcement(holder)", body)
        self.assertIn('line == "ACQUIRED"', body)
        self.assertIn("exact_invalid_root_refusal(outside)", body)
        self.assertNotIn("outside.stderr", body)
        self.assertIn("reap_synthetic_holder(holder)", body)
        self.assertIn("release_holder_and_collect(holder)", body)
        cleanup = inspect.getsource(r422.reap_synthetic_holder)
        self.assertIn("holder.kill()", cleanup)
        self.assertIn("holder.communicate(timeout=timeout)", cleanup)
        self.assertIn("holder.stdout.readline(64)", helper)
        self.assertNotIn("line.strip()", helper)

    def test_12_java_negative_refusal_has_unique_exact_exit(self):
        source = JAVA_HARNESS.read_text(encoding="utf-8")
        self.assertIn('System.out.println("R422_REFUSE_NON_SYNTHETIC_TEMP_ROOT")',
                      source)
        self.assertIn("System.exit(64)", source)
        self.assertIn('invalidRoot.getMessage()', source)

    def test_13_required_r432_case_labels_unchanged(self):
        from tools.r432.chain_private_process_acceptance import REQUIRED_R422_CHECKS
        tree = ast.parse(inspect.getsource(r422.main))
        labels = [
            n.args[0].value for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "passed"
            and n.args and isinstance(n.args[0], ast.Constant)
        ]
        self.assertEqual(len(labels), 17)
        self.assertEqual(set(labels), REQUIRED_R422_CHECKS)


if __name__ == "__main__":
    unittest.main()
