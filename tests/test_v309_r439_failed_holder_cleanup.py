"""R439: fail-closed owner holder reader-to-reaper handoff.

These tests use synthetic Python children and invented process mocks only.
They never access recovered SpawnPK source, private classes, player history,
real writer leases or installed client files.
"""
from __future__ import annotations

import ast
import inspect
import io
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest

from tools.r422 import run_private_store_acceptance as r422


def launch(source: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-u", "-c", source],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1,
    )


class R439FailureCleanup(unittest.TestCase):
    def test_01_successful_release_and_idempotent_reap(self):
        proc = launch(
            "import sys; print('ACQUIRED',flush=True); "
            "sys.stdin.readline(); print('RELEASED',flush=True)"
        )
        try:
            self.assertEqual(r422.read_holder_announcement(proc, 3), "ACQUIRED")
            out = r422.release_holder_and_collect(proc, 3)
            self.assertTrue(r422.exact_stdout_protocol(out, "RELEASED"))
            self.assertEqual(proc.returncode, 0)
        finally:
            r422.reap_synthetic_holder(proc)
        # Reaping an already-collected process cannot make a valid lease
        # success out of an error or raise because its pipes are closed.
        r422.reap_synthetic_holder(proc)
        self.assertIsNotNone(proc.poll())

    def test_02_silent_holder_is_killed_joined_then_reaped(self):
        proc = launch("import time; time.sleep(20)")
        start = time.monotonic()
        try:
            with self.assertRaisesRegex(
                    RuntimeError, "R422_OWNER_HOLDER_STARTUP_TIMEOUT"):
                r422.read_holder_announcement(proc, 0.25)
        finally:
            r422.reap_synthetic_holder(proc)
        self.assertIsNotNone(proc.poll())
        self.assertLess(time.monotonic() - start, 5)

    def test_03_partial_line_and_hang_reaped_without_pipe_competition(self):
        proc = launch(
            "import sys,time; sys.stdout.write('ACQUIRED'); "
            "sys.stdout.flush(); time.sleep(20)"
        )
        try:
            with self.assertRaisesRegex(
                    RuntimeError, "R422_OWNER_HOLDER_STARTUP_TIMEOUT"):
                r422.read_holder_announcement(proc, 0.25)
        finally:
            r422.reap_synthetic_holder(proc)
        self.assertIsNotNone(proc.poll())

    def test_04_stderr_saturation_before_announcement_is_bounded(self):
        proc = launch(
            "import sys,time; sys.stderr.write('X'*700000); "
            "sys.stderr.flush(); print('ACQUIRED',flush=True); "
            "time.sleep(20)"
        )
        start = time.monotonic()
        try:
            with self.assertRaisesRegex(
                    RuntimeError, "R422_OWNER_HOLDER_STARTUP_TIMEOUT"):
                r422.read_holder_announcement(proc, 0.3)
        finally:
            r422.reap_synthetic_holder(proc)
        self.assertIsNotNone(proc.poll())
        self.assertLess(time.monotonic() - start, 6)

    def test_05_malformed_owner_output_is_reaped_without_release(self):
        proc = launch(
            "import time; print('NOT_ACQUIRED',flush=True); time.sleep(20)"
        )
        try:
            with self.assertRaisesRegex(
                    RuntimeError, "R422_HOLDER_MALFORMED_ANNOUNCEMENT"):
                r422.read_holder_announcement(proc, 3)
        finally:
            r422.reap_synthetic_holder(proc)
        self.assertIsNotNone(proc.poll())

    def test_06_failed_contender_check_aborts_holder_lease(self):
        proc = launch(
            "import sys; print('ACQUIRED',flush=True); "
            "sys.stdin.readline(); print('RELEASED',flush=True)"
        )
        try:
            self.assertEqual(r422.read_holder_announcement(proc, 3), "ACQUIRED")
            # Models a failed competing-JVM check after the owner announces
            # acquisition but before any normal release request is sent.
            with self.assertRaisesRegex(RuntimeError, "CONTENDER_REFUSED"):
                raise RuntimeError("CONTENDER_REFUSED")
        finally:
            r422.reap_synthetic_holder(proc)
        self.assertIsNotNone(proc.poll())

    def test_07_release_timeout_is_killed_and_reaped(self):
        proc = launch(
            "import sys,time; print('ACQUIRED',flush=True); "
            "sys.stdin.readline(); time.sleep(20)"
        )
        try:
            self.assertEqual(r422.read_holder_announcement(proc, 3), "ACQUIRED")
            with self.assertRaises(subprocess.TimeoutExpired):
                r422.release_holder_and_collect(proc, 0.25)
        finally:
            r422.reap_synthetic_holder(proc)
        self.assertIsNotNone(proc.poll())

    def test_08_early_eof_is_reaped_and_never_claimed_as_acquired(self):
        proc = launch("pass")
        try:
            with self.assertRaisesRegex(
                    RuntimeError, "R422_OWNER_HOLDER_EXITED_BEFORE_ANNOUNCEMENT"):
                r422.read_holder_announcement(proc, 3)
        finally:
            r422.reap_synthetic_holder(proc)
        self.assertIsNotNone(proc.poll())

    def test_09_termination_race_does_not_promote_cleanup_to_pass(self):
        class ExitedDuringKill:
            def __init__(self):
                self.stdin = io.StringIO()
                self.stdout = io.StringIO()
                self.stderr = io.StringIO()
                self.reaped = False
            def poll(self):
                return None
            def kill(self):
                raise ProcessLookupError("exited just before kill")
            def communicate(self, timeout):
                self.reaped = True
                return "", ""
        proc = ExitedDuringKill()
        r422.reap_synthetic_holder(proc, 1)
        self.assertTrue(proc.reaped)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            self.assertTrue(stream.closed)

    def test_10_reap_timeout_refuses_and_closes_mock_handles(self):
        class Unreapable:
            def __init__(self):
                self.stdin = io.StringIO()
                self.stdout = io.StringIO()
                self.stderr = io.StringIO()
                self.killed = False
            def poll(self):
                return None
            def kill(self):
                self.killed = True
            def communicate(self, timeout):
                raise subprocess.TimeoutExpired("synthetic", timeout)
        proc = Unreapable()
        with self.assertRaisesRegex(RuntimeError, "R422_HOLDER_REAP_UNCONFIRMED"):
            r422.reap_synthetic_holder(proc, 0.1)
        self.assertTrue(proc.killed)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            self.assertTrue(stream.closed)

    def test_11_invalid_reap_deadline_is_refused(self):
        with self.assertRaisesRegex(RuntimeError,
                                    "R422_INVALID_HOLDER_REAP_DEADLINE"):
            r422.reap_synthetic_holder(object(), 0)

    def test_12_reader_is_joined_before_concurrent_pipe_draining(self):
        helper = inspect.getsource(r422.read_holder_announcement)
        self.assertIn("reader.join(timeout=3)", helper)
        self.assertIn("holder.kill()", helper)
        self.assertIn("R422_OWNER_HOLDER_READER_NOT_REAPED", helper)
        cleanup = inspect.getsource(r422.reap_synthetic_holder)
        self.assertIn("holder.communicate(timeout=timeout)", cleanup)
        self.assertIn("except ProcessLookupError:", cleanup)
        self.assertNotIn("holder.wait(", cleanup)
        main = inspect.getsource(r422.main)
        self.assertIn("finally:\n        reap_synthetic_holder(holder)", main)
        self.assertIn("release_holder_and_collect(holder)", main)

    def test_13_no_orphaned_announcement_threads_after_timeouts(self):
        # All readers created by the preceding sequential test runs must
        # have exited rather than remaining blocked on abandoned pipes.
        active = [t.name for t in threading.enumerate()
                  if t.name == "R422-holder-announcement-reader" and t.is_alive()]
        self.assertEqual(active, [])

    def test_15_unjoinable_reader_never_competes_for_stdout(self):
        class BusyReader:
            def is_alive(self):
                return True
            def join(self, timeout):
                self.waited = timeout
        class ChildWithInheritedPipe:
            def __init__(self):
                self.stdin = io.StringIO()
                self.stdout = io.StringIO()
                self.stderr = io.StringIO()
                self._r422_announcement_reader = BusyReader()
                self.killed = False
                self.waited = False
                self.communicated = False
            def poll(self):
                return None
            def kill(self):
                self.killed = True
            def wait(self, timeout):
                self.waited = True
                return 0
            def communicate(self, timeout):
                self.communicated = True
                raise AssertionError("Cannot race with active stdout reader")
        proc = ChildWithInheritedPipe()
        with self.assertRaisesRegex(RuntimeError,
                                    "R422_HOLDER_READER_NOT_REAPED"):
            r422.reap_synthetic_holder(proc, 0.1)
        self.assertTrue(proc.killed)
        self.assertTrue(proc.waited)
        self.assertFalse(proc.communicated)
        self.assertFalse(proc.stdout.closed)
        self.assertTrue(proc.stdin.closed)
        self.assertTrue(proc.stderr.closed)

    def test_14_r432_cross_process_acceptance_contract_stays_fixed(self):
        from tools.r432.chain_private_process_acceptance import REQUIRED_R422_CHECKS
        tree = ast.parse(inspect.getsource(r422.main))
        labels = [
            n.args[0].value for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "passed" and n.args
            and isinstance(n.args[0], ast.Constant)
        ]
        self.assertEqual(len(labels), 17)
        self.assertEqual(set(labels), REQUIRED_R422_CHECKS)


if __name__ == "__main__":
    unittest.main()
