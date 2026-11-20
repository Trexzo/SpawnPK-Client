"""R435: fail-closed exact R422 JVM protocol acceptance.

Public fabricated output only. Never imports private classes or history.
"""
from __future__ import annotations

import inspect
from pathlib import Path
import subprocess
import sys
import unittest

from tools.r422 import run_private_store_acceptance as r422


class R435ExactProcessProtocol(unittest.TestCase):
    def test_01_accepts_only_complete_expected_success_lines(self):
        check = r422.exact_stdout_protocol
        self.assertTrue(check("ACQUIRED\n", "ACQUIRED"))
        self.assertTrue(check("RELEASED\n", "RELEASED"))
        self.assertTrue(check("ACQUIRED\nRELEASED\n", "ACQUIRED", "RELEASED"))
        self.assertTrue(check("ACQUIRED\r\nRELEASED\r\n", "ACQUIRED", "RELEASED"))
        self.assertTrue(check("REFUSED_OWNER\n", "REFUSED_OWNER"))

    def test_02_refuses_negation_substring_collisions(self):
        check = r422.exact_stdout_protocol
        for output in ("NOT_RELEASED\n", "UNRELEASED\n",
                       "RELEASED=false\n", "RELEASED_PENDING\n",
                       "OWNER_NOT_RELEASED\n", "RELEASED_WARN\n"):
            with self.subTest(output=output):
                self.assertFalse(check(output, "RELEASED"))
        for output in ("NOT_ACQUIRED\n", "PRE_ACQUIRED\n", 
                       "ACQUIRED=false\n", "ACQUIRED_BUT_STALE\n"):
            with self.subTest(output=output):
                self.assertFalse(check(output, "ACQUIRED"))

    def test_03_rejects_misordered_duplicate_and_extra_success_lines(self):
        check = r422.exact_stdout_protocol
        for output in (
            "RELEASED\nACQUIRED\n",
            "ACQUIRED\nACQUIRED\nRELEASED\n",
            "ACQUIRED\nNOT_RELEASED\n",
            "NOT_ACQUIRED\nRELEASED\n",
            "ACQUIRED\nRELEASED\nDIAGNOSTIC\n",
            "DIAGNOSTIC\nACQUIRED\nRELEASED\n",
            "ACQUIRED\nRELEASED\nRELEASED\n",
        ):
            with self.subTest(output=output):
                self.assertFalse(check(output, "ACQUIRED", "RELEASED"))

    def test_04_missing_or_partial_record_fails_closed(self):
        check = r422.exact_stdout_protocol
        for output in ("", "RELEASED", "RELEAS", "RELEASED\n\n",
                       " RELEASED\n", "RELEASED \n", "\nRELEASED\n",
                       "RELEASED\r", "RELEASED\rX\n", "RELEASED\0\n"):
            with self.subTest(output=repr(output)):
                self.assertFalse(check(output, "RELEASED"))
        for output in ("ACQUIRED\n", "ACQUIRED\nRELEASED"):
            self.assertFalse(check(output, "ACQUIRED", "RELEASED"))

    def test_05_refuses_broken_or_dangerous_expected_contract(self):
        check = r422.exact_stdout_protocol
        self.assertFalse(check(None, "RELEASED"))
        self.assertFalse(check(b"RELEASED\n", "RELEASED"))
        self.assertFalse(check("RELEASED\n"))
        self.assertFalse(check("RELEASED\n", ""))
        self.assertFalse(check("RELEASED\n", "RELEASED\n"))
        self.assertFalse(check("RELEASED\n", "RELEASED\r"))
        self.assertFalse(check("RELEASED\n", 12))

    def test_06_actual_r422_owner_receipts_use_exact_checks(self):
        source = inspect.getsource(r422.main)
        for label in (
            "actual_store_second_process_refused",
            "owner_release_receipt",
            "actual_store_reacquire_after_shutdown",
            "actual_store_crash_exit",
            "actual_store_reacquire_after_jvm_halt",
            "actual_store_first_run_creates_leaf_and_acquires",
            "lease_try_does_not_repair_unresolved_marker",
        ):
            with self.subTest(label=label):
                offset = source.index('passed("' + label + '"')
                end = source.find('passed("', offset + 8)
                block = source[offset: end if end >= 0 else len(source)]
                self.assertIn("exact_stdout_protocol(", block)
        self.assertNotIn('"RELEASED" in', source)
        self.assertNotIn('"ACQUIRED" in', source)
        self.assertIn('line == "ACQUIRED"', source)

    def test_07_no_change_to_named_r432_receipt_labels(self):
        from tools.r432.chain_private_process_acceptance import REQUIRED_R422_CHECKS
        import ast
        tree = ast.parse(inspect.getsource(r422.main))
        labels = [
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "passed"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ]
        self.assertEqual(len(labels), 17)
        self.assertEqual(set(labels), REQUIRED_R422_CHECKS)

    def test_08_real_child_os_native_lines_are_accepted(self):
        child = subprocess.run(
            [sys.executable, "-c",
             "print('ACQUIRED', flush=True); print('RELEASED', flush=True)"],
            capture_output=True, text=True, timeout=5, check=False)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertTrue(r422.exact_stdout_protocol(
            child.stdout, "ACQUIRED", "RELEASED"))

    def test_09_real_child_negated_status_is_rejected(self):
        child = subprocess.run(
            [sys.executable, "-c",
             "print('NOT_ACQUIRED', flush=True); print('NOT_RELEASED', flush=True)"],
            capture_output=True, text=True, timeout=5, check=False)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertFalse(r422.exact_stdout_protocol(
            child.stdout, "ACQUIRED", "RELEASED"))

    def test_10_real_child_exit_does_not_rescue_ambiguous_status(self):
        child = subprocess.run(
            [sys.executable, "-c",
             "print('ACQUIRED', flush=True); print('NOT_RELEASED', flush=True)"],
            capture_output=True, text=True, timeout=5, check=False)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertFalse(r422.exact_stdout_protocol(
            child.stdout, "ACQUIRED", "RELEASED"))

    def test_11_public_java_harness_emits_defined_owner_tokens(self):
        source = (Path(__file__).resolve().parents[1] /
                  "tests/fixtures/r422/R422ActualStoreAcceptance.java").read_text(
                      encoding="utf-8")
        for token in ("ACQUIRED", "RELEASED", "REFUSED_OWNER"):
            self.assertIn('System.out.println("' + token + '")', source)
        self.assertIn('Runtime.getRuntime().halt(77)', source)
        self.assertIn('System.in.read()', source)


if __name__ == "__main__":
    unittest.main()
