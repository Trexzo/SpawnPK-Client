"""R434: real OS process tests for bounded R422 holder startup; fabricated only.

No recovered private class, client, history, or Java process is used here.
The production R422 holder interaction is retained; these tests exercise
the newly shared read helper against ordinary child Python processes.
"""
from __future__ import annotations

import inspect
from pathlib import Path
import subprocess
import sys
import time
import unittest
from types import SimpleNamespace

from tools.r422 import run_private_store_acceptance as runner


def start_child(source: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-u", "-c", source],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1,
    )


def reap_child(child: subprocess.Popen) -> None:
    if child.poll() is None:
        child.kill()
    child.wait(timeout=5)
    for stream in (child.stdin, child.stdout, child.stderr):
        if stream is not None:
            stream.close()


class R434BoundedHolderStartup(unittest.TestCase):
    def test_01_real_child_announces_acquisition(self):
        child = start_child("import time; print('ACQUIRED',flush=True); time.sleep(10)")
        try:
            self.assertEqual(runner.read_holder_announcement(child, 4), "ACQUIRED")
        finally:
            reap_child(child)
        self.assertIsNotNone(child.poll())

    def test_02_silent_child_refuses_with_bounded_wait(self):
        child = start_child("import time; time.sleep(10)")
        begin = time.monotonic()
        try:
            with self.assertRaisesRegex(RuntimeError,
                                        "R422_OWNER_HOLDER_STARTUP_TIMEOUT"):
                runner.read_holder_announcement(child, 0.35)
        finally:
            reap_child(child)
        self.assertLess(time.monotonic() - begin, 4)
        self.assertIsNotNone(child.poll())

    def test_03_partial_line_does_not_bypass_deadline(self):
        child = start_child(
            "import sys,time; sys.stdout.write('ACQUIRED'); sys.stdout.flush(); "
            "time.sleep(10)")
        try:
            with self.assertRaisesRegex(RuntimeError,
                                        "R422_OWNER_HOLDER_STARTUP_TIMEOUT"):
                runner.read_holder_announcement(child, 0.35)
        finally:
            reap_child(child)
        self.assertIsNotNone(child.poll())

    def test_04_early_eof_fails_closed(self):
        child = start_child("pass")
        try:
            with self.assertRaisesRegex(RuntimeError,
                                        "R422_OWNER_HOLDER_EXITED_BEFORE_ANNOUNCEMENT"):
                runner.read_holder_announcement(child, 3)
        finally:
            reap_child(child)

    def test_05_refusal_is_not_misread_as_acquisition(self):
        child = start_child("print('REFUSED_OWNER',flush=True)")
        try:
            self.assertEqual(runner.read_holder_announcement(child, 3),
                             "REFUSED_OWNER")
        finally:
            reap_child(child)
        # The existing main-side label check must still reject anything
        # other than exact ACQUIRED and preserve the named receipt contract.
        main = inspect.getsource(runner.main)
        self.assertIn('line == "ACQUIRED"', main)
        self.assertIn('passed("actual_store_first_process_acquired"', main)

    def test_06_missing_stdout_is_refused(self):
        with self.assertRaisesRegex(RuntimeError,
                                    "R422_HOLDER_STDOUT_NOT_CAPTURED"):
            runner.read_holder_announcement(SimpleNamespace(stdout=None), 1)

    def test_07_nonpositive_deadline_is_refused(self):
        with self.assertRaisesRegex(RuntimeError,
                                    "R422_INVALID_HOLDER_STARTUP_DEADLINE"):
            runner.read_holder_announcement(SimpleNamespace(stdout=None), 0)

    def test_08_main_calls_bounded_helper_inside_kill_and_reap_finally(self):
        main = inspect.getsource(runner.main)
        self.assertIn("line = read_holder_announcement(holder)", main)
        self.assertNotIn("holder.stdout.readline()", main)
        self.assertIn("if holder.poll() is None:", main)
        self.assertIn("holder.kill()", main)
        self.assertIn("holder.wait(timeout=5)", main)
        self.assertIn("stream.close()", main)
        self.assertIn("holder.stdin.write", main)
        self.assertIn("holder.wait(timeout=10)", main)


if __name__ == "__main__":
    unittest.main()
