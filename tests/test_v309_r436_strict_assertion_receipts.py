"""R436: reject spoofed assertion counts in the actual public R422/R425 runners.

All records are fabricated; no owner-private Java classes, source, history,
real persistence, installed game, or remote desktop are involved.
"""
from __future__ import annotations

import inspect
from pathlib import Path
import subprocess
import sys
import unittest

from tools.r422 import run_private_store_acceptance as r422
from tools.r425 import compile_and_accept_private_overlay as r425

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("R422", r422.parse_r422_selftest_assertions, 73,
     "R422_ACTUAL_PRIVATE_STORE_PASS", "R422_OPTIONAL_SYMLINK_UNAVAILABLE"),
    ("R425", r425.parse_r425_selftest_assertions, 39,
     "R425_ACTUAL_PATCHED_PRIVATE_STORE_PASS", "R425_OPTIONAL_SYMLINK_UNAVAILABLE"),
)


class R436StrictAssertions(unittest.TestCase):
    def test_01_exact_complete_records_accepted(self):
        for name, parser, minimum, success, warning in CASES:
            for eol in ("\n", "\r\n"):
                for prefix in ("", warning + eol):
                    with self.subTest(name=name, eol=repr(eol), prefix=bool(prefix)):
                        self.assertEqual(
                            parser(prefix + success + f" assertions={minimum}" + eol),
                            minimum)

    def test_02_reject_negated_or_embedded_success_phrases(self):
        for name, parser, minimum, success, warning in CASES:
            valid = success + f" assertions={minimum}\n"
            bad = (
                "NOT_" + valid,
                "PRE" + valid,
                "FAILED:" + valid,
                "OK " + valid,
                "[INFO] " + valid,
                "FAILURE\n" + valid,
                "not even run\n" + valid,
                valid + "ERROR\n",
                valid + valid,
                "ACQUIRED\n" + valid,
            )
            for output in bad:
                with self.subTest(name=name, output=repr(output)):
                    self.assertIsNone(parser(output))

    def test_03_reject_wrong_optional_warning_or_placement(self):
        for name, parser, minimum, success, warning in CASES:
            valid = success + f" assertions={minimum}\n"
            bad = (
                warning + "\n" + warning + "\n" + valid,
                valid + warning + "\n",
                "NOT_" + warning + "\n" + valid,
                warning + "\nWRONG\n" + valid,
                warning + "\n" + valid + "\n",
                warning + "\r\n" + valid,  # mixed line endings
                warning + "\n" + success + f" assertions={minimum}\r\n",
            )
            for output in bad:
                with self.subTest(name=name, output=repr(output)):
                    self.assertIsNone(parser(output))

    def test_04_wrong_harness_status_refused(self):
        for name, parser, minimum, success, warning in CASES:
            other = "R425_ACTUAL_PATCHED_PRIVATE_STORE_PASS" if name == "R422" \
                    else "R422_ACTUAL_PRIVATE_STORE_PASS"
            self.assertIsNone(parser(other + f" assertions={minimum}\n"))

    def test_05_refuse_malformed_counts_and_missing_terminator(self):
        for name, parser, minimum, success, warning in CASES:
            for suffix in (
                "", "\n\n", " \n", "\t\n", "\r", "\rX\n",
                "\x00\n", "x\n", "-1\n", "+100\n", "0\n",
                "00\n", "0" + str(minimum) + "\n",
                "١٠٠\n", "1_000\n", "1.0\n",
                "1" * 7 + "\n", "1" * 5000 + "\n",
            ):
                with self.subTest(name=name, suffix=repr(suffix[:40])):
                    self.assertIsNone(parser(success + " assertions=" + suffix))

    def test_06_refuse_non_string_and_wrong_case(self):
        for name, parser, minimum, success, warning in CASES:
            self.assertIsNone(parser(None))
            self.assertIsNone(parser((success + f" assertions={minimum}\n").encode()))
            self.assertIsNone(parser(success.lower() + f" assertions={minimum}\n"))

    def test_07_numeric_threshold_remains_authoritative(self):
        for name, parser, minimum, success, warning in CASES:
            below = minimum - 1
            self.assertEqual(parser(success + f" assertions={below}\n"), below)
            self.assertEqual(parser(success + f" assertions={minimum}\n"), minimum)
            self.assertEqual(parser(success + f" assertions={minimum+1}\n"), minimum + 1)
            self.assertIsNone(parser(success + " assertions=1000000\n"))

    def test_08_r422_main_uses_parsed_integer_and_checks_exit(self):
        body = inspect.getsource(r422.main)
        self.assertIn("parse_r422_selftest_assertions(selftest.stdout)", body)
        self.assertIn("selftest.returncode != 0 or assertions is None or assertions < 73", body)
        self.assertIn('"real_store_assertions": assertions', body)
        self.assertNotIn("re.search(", body)
        self.assertNotIn("int(m.group(1))", body)

    def test_09_r425_actual_class_uses_parsed_integer_and_checks_exit(self):
        body = inspect.getsource(r425.execute_actual_class_acceptance)
        self.assertIn("parse_r425_selftest_assertions(proc.stdout)", body)
        self.assertIn("proc.returncode == 0 and assertions is not None and assertions >= 39", body)
        self.assertIn('"real_class_assertions": assertions', body)
        self.assertNotIn("re.search(", body)
        self.assertNotIn("int(match.group(1))", body)

    def test_10_public_java_producers_emit_exact_expected_lines(self):
        for name, parser, minimum, success, warning in CASES:
            file = (ROOT / "tests/fixtures" / name.lower() /
                    ("R422ActualStoreAcceptance.java" if name == "R422"
                     else "R425ActualPrivateOverlayAcceptance.java"))
            source = file.read_text(encoding="utf-8")
            self.assertIn('System.out.println("' + warning + '")', source)
            self.assertIn('System.out.println("' + success + ' assertions="', source)

    def test_11_real_child_process_good_and_misleading_records(self):
        for name, parser, minimum, success, warning in CASES:
            for negative in (False, True):
                line = ("NOT_" if negative else "") + success + f" assertions={minimum}"
                proc = subprocess.run(
                    [sys.executable, "-c", "print(" + repr(line) + ",flush=True)"],
                    text=True, capture_output=True, timeout=5, check=False)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                if negative:
                    self.assertIsNone(parser(proc.stdout))
                else:
                    self.assertEqual(parser(proc.stdout), minimum)


if __name__ == "__main__":
    unittest.main()
