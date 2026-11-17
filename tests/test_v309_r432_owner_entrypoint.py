"""R432 public-only static safety test for opt-in owner PowerShell chain.

PowerShell itself is NOT executed on hosted GitHub: the owner's recovered
private source and local JDK paths are not available in CI.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/r425/owner_only_run_r425.ps1"

class R432OwnerEntrypointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text("utf-8")

    def test_01_requires_explicit_owner_opt_in(self):
        self.assertIn("[switch]$RunOwnerPrivateAcceptance", self.script)
        self.assertIn("if (-not $RunOwnerPrivateAcceptance)", self.script)

    def test_02_still_uses_only_isolated_r421_temp_workspace(self):
        self.assertIn("SpawnPK-R386-Isolated-Acceptance", self.script)
        self.assertIn("R421-Private-NoFollow-Cache-Directory-Preflight",
                      self.script)

    def test_03_both_gates_run_serially_in_same_invocation(self):
        self.assertIn("& $PythonExe @arguments", self.script)
        self.assertIn("& $PythonExe @secondArgs", self.script)
        self.assertLess(self.script.index("& $PythonExe @arguments"),
                        self.script.index("& $PythonExe @secondArgs"))

    def test_04_second_gate_receipt_mandatory_and_fail_closed(self):
        self.assertIn("R432_CROSS_PROCESS_GATE_REFUSED", self.script)
        self.assertIn("R432-Final-Private-CrossProcess-Receipt.json",
                      self.script)
        self.assertIn("R432_REFUSED: final cross-process receipt missing.",
                      self.script)

    def test_05_no_jar_installation_client_launch_or_delete(self):
        for command in ("Remove-Item","Move-Item","Copy-Item",
                        "Expand-Archive","Compress-Archive",
                        "Start-Process","java -jar","client.jar",
                        "Invoke-Expression"):
            self.assertNotIn(command, self.script)
        self.assertIn("R432_RELEASE_GATE_REMAINS_CLOSED", self.script)

    def test_06_no_bypassing_sha_class_or_dependency_hashes(self):
        for option in ("--candidate-temp-root", "--prior-source-root",
                       "--prior-classes-root", "--dependency-a-sha256",
                       "--dependency-b-sha256", "--javac", "--java"):
            self.assertIn(option, self.script)


if __name__ == "__main__":
    unittest.main()
