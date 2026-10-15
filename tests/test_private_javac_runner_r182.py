"""Synthetic-only regression coverage for private javac runner policy."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from private_javac_runner_r182 import safe_argv, verify_javac, run

class PrivateJavacRunnerTests(unittest.TestCase):
    def test_disallowed_user_options(self):
        for option in ("@args", "-cp", "--class-path=evil.jar", "-processor",
                       "-J-Xmx1g", "-d", "--patch-module=x"):
            with self.subTest(option=option):
                with self.assertRaises(ValueError):
                    safe_argv([option])

    def test_pinned_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            java = Path(temp) / "synthetic-javac"
            java.write_bytes(b"not an executable")
            digest = hashlib.sha256(java.read_bytes()).hexdigest()
            self.assertEqual(digest, verify_javac(java, digest))
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify_javac(java, "0" * 64)

    def test_timeout_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base / "A.java").write_text("class A {}", encoding="utf-8")
            javac = base / "fake-javac"
            javac.write_bytes(b"synthetic")
            digest = hashlib.sha256(javac.read_bytes()).hexdigest()
            with patch("private_javac_runner_r182.subprocess.run",
                       side_effect=__import__("subprocess").TimeoutExpired("fake", 1)):
                with self.assertRaisesRegex(ValueError, "timed out"):
                    run(base, javac, digest, [], {}, timeout=1)


    def test_success_and_unexplained_exit(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base / "A.java").write_text("class A {}", encoding="utf-8")
            javac = base / "fake-javac"
            javac.write_bytes(b"synthetic")
            digest = hashlib.sha256(javac.read_bytes()).hexdigest()
            def successful(argv, **kwargs):
                self.assertIn("-proc:none", argv)
                self.assertIn("-sourcepath", argv)
                self.assertIn("-classpath", argv)
                self.assertIn("-d", argv)
                self.assertEqual(1, sum(x.endswith("A.java") for x in argv))
                self.assertNotIn("CLASSPATH", kwargs["env"])
                return subprocess.CompletedProcess(argv, 0, "", "")
            with patch("private_javac_runner_r182.subprocess.run", side_effect=successful):
                result = run(base, javac, digest, [], {})
            self.assertTrue(result["complete_error_inventory"])
            self.assertEqual(0, result["parsed_error_count"])
            self.assertIsNone(result["reported_error_count"])
            with patch("private_javac_runner_r182.subprocess.run",
                       return_value=subprocess.CompletedProcess([], 1, "", "fatal: compiler crashed")):
                failed = run(base, javac, digest, [], {})
            self.assertFalse(failed["complete_error_inventory"])
            self.assertEqual(1, failed["compiler_exit_code"])

if __name__ == "__main__":
    unittest.main()
