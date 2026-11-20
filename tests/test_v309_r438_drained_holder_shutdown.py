"""R438: prove synthetic holder stdout/stderr are drained during shutdown.

Uses only fabricated child Python processes, no owner-private Java, client,
user history, credentials, or persistent deletion evidence.
"""
from __future__ import annotations

import ast
import inspect
import subprocess
import sys
import time
import unittest

from tools.r422 import run_private_store_acceptance as r422


def launch(body: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-u", "-c", body],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )


def kill_and_reap(child: subprocess.Popen) -> None:
    if child.poll() is None:
        child.kill()
        child.communicate(timeout=5)
    for stream in (child.stdin, child.stdout, child.stderr):
        if stream is not None:
            stream.close()
    child.wait(timeout=5)


class R438DrainedHolderShutdown(unittest.TestCase):
    def test_01_normal_holder_release_and_reap(self):
        child = launch(
            "import sys; print('ACQUIRED', flush=True); "
            "sys.stdin.readline(); print('RELEASED',flush=True)"
        )
        try:
            self.assertEqual(r422.read_holder_announcement(child, 3),
                             "ACQUIRED")
            output = r422.release_holder_and_collect(child, 5)
            self.assertTrue(r422.exact_stdout_protocol(output, "RELEASED"))
            self.assertEqual(child.returncode, 0)
            self.assertIsNone(child.stdin)
        finally:
            kill_and_reap(child)
        self.assertIsNotNone(child.poll())

    def test_02_drains_large_stderr_before_waiting(self):
        # Much larger than a normal OS pipe. Old wait-before-read logic
        # would time out while a holder blocked inside stderr.write().
        child = launch(
            "import sys; print('ACQUIRED', flush=True); "
            "sys.stdin.readline(); "
            "sys.stderr.write('X'*700000); sys.stderr.flush(); "
            "print('RELEASED',flush=True)"
        )
        try:
            self.assertEqual(r422.read_holder_announcement(child, 3),
                             "ACQUIRED")
            output = r422.release_holder_and_collect(child, 7)
            self.assertEqual(child.returncode, 0)
            self.assertEqual(output, "RELEASED\n")
        finally:
            kill_and_reap(child)

    def test_03_extra_stdout_does_not_authorize_release(self):
        child = launch(
            "import sys; print('ACQUIRED',flush=True); "
            "sys.stdin.readline(); "
            "print('NOT_RELEASED',flush=True)"
        )
        try:
            self.assertEqual(r422.read_holder_announcement(child, 3),
                             "ACQUIRED")
            out = r422.release_holder_and_collect(child, 5)
            self.assertEqual(child.returncode, 0)
            self.assertFalse(r422.exact_stdout_protocol(out, "RELEASED"))
        finally:
            kill_and_reap(child)

    def test_04_nonzero_exit_does_not_authorize_release(self):
        child = launch(
            "import sys; print('ACQUIRED',flush=True); "
            "sys.stdin.readline(); print('RELEASED',flush=True); "
            "sys.exit(31)"
        )
        try:
            self.assertEqual(r422.read_holder_announcement(child, 3),
                             "ACQUIRED")
            out = r422.release_holder_and_collect(child, 5)
            self.assertTrue(r422.exact_stdout_protocol(out, "RELEASED"))
            self.assertEqual(child.returncode, 31)
        finally:
            kill_and_reap(child)
        body = inspect.getsource(r422.main)
        self.assertIn('passed("owner_release_terminates_normally", holder.returncode == 0)', body)

    def test_05_shutdown_timeout_kills_and_reaps_child(self):
        child = launch(
            "import sys,time; print('ACQUIRED',flush=True); "
            "sys.stdin.readline(); time.sleep(30)"
        )
        start = time.monotonic()
        try:
            self.assertEqual(r422.read_holder_announcement(child, 3),
                             "ACQUIRED")
            with self.assertRaises(subprocess.TimeoutExpired):
                r422.release_holder_and_collect(child, 0.25)
        finally:
            kill_and_reap(child)
        self.assertIsNotNone(child.poll())
        self.assertLess(time.monotonic() - start, 6)

    def test_06_refuse_missing_stdin_and_invalid_deadlines(self):
        class Missing:
            stdin = None
        for value in (0, -1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError,
                                            "R422_INVALID_HOLDER_RELEASE_DEADLINE"):
                    r422.release_holder_and_collect(Missing(), value)
        with self.assertRaisesRegex(RuntimeError,
                                    "R422_HOLDER_STDIN_NOT_AVAILABLE"):
            r422.release_holder_and_collect(Missing(), 1)

    def test_07_preserve_order_of_holder_initial_and_completion_receipts(self):
        body = inspect.getsource(r422.main)
        first = body.index("line = read_holder_announcement(holder)")
        second = body.index("released_stdout = release_holder_and_collect(holder)")
        third = body.index('passed("owner_release_terminates_normally"')
        fourth = body.index('passed("owner_release_receipt"')
        self.assertLess(first, second)
        self.assertLess(second, third)
        self.assertLess(third, fourth)
        self.assertNotIn("holder.wait(timeout=10)", body)
        self.assertNotIn("holder.stdout.read()", body)
        self.assertIn("holder.kill()", body)
        self.assertIn("holder.communicate(timeout=5)", body)
        self.assertIn("stream.close()", body)

    def test_08_collector_drains_both_pipes_before_lease_acceptance(self):
        helper = inspect.getsource(r422.release_holder_and_collect)
        self.assertIn("holder.stdin.close()", helper)
        self.assertIn("holder.stdin = None", helper)
        self.assertIn("holder.communicate(timeout=timeout)", helper)
        self.assertNotIn("holder.wait(", helper)
        self.assertNotIn("holder.stdout.read()", helper)

    def test_09_all_17_r422_case_labels_stable(self):
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
