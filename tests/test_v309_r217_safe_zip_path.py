"""JDK-only, no original game source or proprietary binary in public CI."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "tools" / "java" / "r217"

class ZipGuardTests(unittest.TestCase):
    def test_compile_and_execute_public_java_path_guard(self):
        with tempfile.TemporaryDirectory(prefix="r217-") as dest:
            out = Path(dest)
            subprocess.run(
                ["javac", "--release", "11", "-d", str(out),
                 str(JAVA / "SafeZipPath.java"),
                 str(JAVA / "SafeZipPathSelfTest.java")],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True)
            actual = subprocess.run(
                ["java", "-cp", str(out), "SafeZipPathSelfTest"],
                check=True, capture_output=True, text=True)
            self.assertIn("PASS: R217", actual.stdout)

if __name__ == "__main__":
    unittest.main()
