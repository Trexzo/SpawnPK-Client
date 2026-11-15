"""R425 Windows owner entrypoint safety: public-source checks only.

The PowerShell entrypoint is NEVER executed in GitHub CI, because it is
reserved for the owner's own isolated R421 TEMP acceptance workspace.
"""
from pathlib import Path
import unittest

REPO=Path(__file__).resolve().parents[1]
SCRIPT=REPO/"tools/r425/owner_only_run_r425.ps1"

class R425OwnerWrapperSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SCRIPT.read_text("utf-8")

    def test_01_explicit_opt_in_required(self):
        self.assertIn("[switch]$RunOwnerPrivateAcceptance",self.source)
        self.assertIn("if (-not $RunOwnerPrivateAcceptance)",self.source)

    def test_02_r421_isolated_tree_only(self):
        self.assertIn("R421-Private-NoFollow-Cache-Directory-Preflight",self.source)
        self.assertIn("SpawnPK-R386-Isolated-Acceptance",self.source)

    def test_03_source_and_compiled_class_inputs_are_separate(self):
        self.assertIn("'Source-Candidate-R421'",self.source)
        self.assertIn("'R421-Compiled-Classes'",self.source)

    def test_04_launches_only_python_runner(self):
        self.assertIn("& $PythonExe @arguments",self.source)
        self.assertNotIn("Start-Process",self.source)
        self.assertNotIn("java -jar",self.source)
        self.assertNotIn("client.jar",self.source)

    def test_05_never_deletes_files_or_deploys_archive(self):
        for token in ("Remove-Item","Copy-Item","Move-Item","Expand-Archive",
                      "Compress-Archive","Invoke-Expression"):
            self.assertNotIn(token,self.source)
        self.assertIn("R425_RELEASE_GATE_REMAINS_CLOSED",self.source)

    def test_06_verifies_receipt_after_runner_success(self):
        self.assertIn("$LASTEXITCODE",self.source)
        self.assertIn("R425-Final-Private-Acceptance-Receipt.json",self.source)
        self.assertIn("Test-Path -LiteralPath $receipt",self.source)

    def test_07_dependency_jars_are_explicitly_hash_checked(self):
        self.assertIn("R239_filtered.jar",self.source)
        self.assertIn("R218.jar",self.source)
        self.assertIn("Get-FileHash -LiteralPath $depA",self.source)
        self.assertIn("Get-FileHash -LiteralPath $depB",self.source)

    def test_08_output_is_unique_owner_temp_child(self):
        self.assertIn("[guid]::NewGuid()",self.source)
        self.assertIn("R424-Private-Candidate-R425-",self.source)
        self.assertIn("Join-Path $env:TEMP",self.source)

if __name__=="__main__":
    unittest.main()
