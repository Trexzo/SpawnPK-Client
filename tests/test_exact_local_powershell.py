from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(
    os.name == "nt" and shutil.which("powershell.exe"),
    "Windows PowerShell required",
)
class ExactLocalPowerShellTests(unittest.TestCase):
    def test_source_m1_output_root_is_case_sensitive_before_children(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo / "scripts" / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        ).read_text(encoding="utf-8")
        prepare = script.index(
            "Enable-CaseSensitiveWorkspace -Path $OutDir"
        )
        children = script.index(
            '$BootstrapReadableDir = Join-Path $OutDir "bootstrap-readable"'
        )
        self.assertLess(prepare, children)
        self.assertNotIn(
            "Enable-CaseSensitiveWorkspace -Path $CollisionWorkspace",
            script,
        )

    def test_source_m1_exact_local_runner_parses(self):
        repo = Path(__file__).resolve().parents[1]
        script = repo / "scripts" / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        literal = str(script).replace("'", "''")
        command = (
            "$tokens=$null; $errors=$null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            f"'{literal}', [ref]$tokens, [ref]$errors) | Out-Null; "
            "if ($errors.Count -ne 0) { "
            "$errors | ForEach-Object { Write-Error $_.Message }; exit 1 "
            "}; exit 0"
        )
        proc = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            proc.stdout + proc.stderr,
        )


    def test_external_oracle_frontier_is_opt_in_and_precedes_blocked_exit(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo / "scripts" / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "[string]$ExternalOracleReport",
            script,
        )
        self.assertIn(
            '$BootstrapClassRemapPlan = Join-Path $BootstrapReadableDir "class-remap-plan.json"',
            script,
        )
        condition = script.index(
            'if (-not [string]::IsNullOrWhiteSpace($ExternalOracleReport))'
        )
        diagnostic = script.index(
            '$PrivateDiagnostic = Join-Path $ReleaseDir "javac-diagnostic-private.json"'
        )
        invoke = script.index(
            'Invoke-PyChecked "INTERSECT EXTERNAL ORACLE WITH JAVAC FRONTIER"'
        )
        blocked_exit = script.index(
            "    exit 3\n}",
            invoke,
        )
        self.assertLess(diagnostic, condition)
        self.assertLess(condition, invoke)
        self.assertLess(invoke, blocked_exit)
        self.assertIn(
            '"spk_recovery.external_oracle_frontier_cli"',
            script,
        )
        self.assertIn(
            '"--collision-plan"',
            script,
        )
        self.assertIn(
            '$BootstrapClassRemapPlan',
            script,
        )


    def test_new_source_normalization_counters_are_projected_and_printed(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo / "scripts" / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        ).read_text(encoding="utf-8")

        expected = {
            "invokedynamic_parameter_capture_alias_method_count":
                "/normalization_summary/invokedynamic_parameter_capture_alias_method_count",
            "invokedynamic_lambda_outer_capture_collision_action_count":
                "/normalization_summary/invokedynamic_lambda_outer_capture_collision_action_count",
            "invokedynamic_lambda_outer_capture_collision_reference_count":
                "/normalization_summary/invokedynamic_lambda_outer_capture_collision_reference_count",
            "invokedynamic_parameter_capture_alias_reference_count":
                "/normalization_summary/invokedynamic_parameter_capture_alias_reference_count",
            "hidden_layout_constructor_argument_action_count":
                "/normalization_summary/hidden_layout_constructor_argument_action_count",
            "hidden_layout_constructor_argument_reference_count":
                "/normalization_summary/hidden_layout_constructor_argument_reference_count",
            "impossible_collectors_tolist_cast_action_count":
                "/normalization_summary/impossible_collectors_tolist_cast_action_count",
            "impossible_collectors_tolist_cast_reference_count":
                "/normalization_summary/impossible_collectors_tolist_cast_reference_count",
            "erased_generic_constructor_argument_cast_action_count":
                "/normalization_summary/erased_generic_constructor_argument_cast_action_count",
            "erased_generic_constructor_argument_cast_reference_count":
                "/normalization_summary/erased_generic_constructor_argument_cast_reference_count",
            "invokedynamic_image_loader_local_action_count":
                "/normalization_summary/invokedynamic_image_loader_local_action_count",
            "invokedynamic_image_loader_local_reference_count":
                "/normalization_summary/invokedynamic_image_loader_local_reference_count",
            "imported_outer_nested_static_field_action_count":
                "/normalization_summary/shadowed_imported_outer_nested_static_field_action_count",
            "imported_outer_nested_static_field_reference_count":
                "/normalization_summary/shadowed_imported_outer_nested_static_field_reference_count",
        }
        for name, pointer in expected.items():
            self.assertIn(
                f'{name} = "{pointer}"',
                script,
            )

        self.assertIn(
            'INVOKEDYNAMIC_LAMBDA_OUTER_CAPTURE_COLLISION_REFERENCES='
            '$($Recovered.invokedynamic_lambda_outer_capture_collision_reference_count)',
            script,
        )
        self.assertIn(
            'INVOKEDYNAMIC_PARAMETER_CAPTURE_ALIAS_REFERENCES='
            '$($Recovered.invokedynamic_parameter_capture_alias_reference_count)',
            script,
        )
        self.assertIn(
            'HIDDEN_LAYOUT_CONSTRUCTOR_ARGUMENT_REFERENCES='
            '$($Recovered.hidden_layout_constructor_argument_reference_count)',
            script,
        )
        self.assertIn(
            'IMPOSSIBLE_COLLECTORS_TOLIST_CAST_REFERENCES='
            '$($Recovered.impossible_collectors_tolist_cast_reference_count)',
            script,
        )
        self.assertIn(
            'ERASED_GENERIC_CONSTRUCTOR_ARGUMENT_CAST_REFERENCES='
            '$($Recovered.erased_generic_constructor_argument_cast_reference_count)',
            script,
        )
        self.assertIn(
            'INVOKEDYNAMIC_IMAGE_LOADER_LOCAL_REFERENCES='
            '$($Recovered.invokedynamic_image_loader_local_reference_count)',
            script,
        )
        self.assertIn(
            'IMPORTED_OUTER_NESTED_STATIC_FIELD_REFERENCES='
            '$($Recovered.imported_outer_nested_static_field_reference_count)',
            script,
        )



    def test_private_frontier_focus_file_count_is_configurable(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo / "scripts" / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "[ValidateRange(1, 20)]\n    [int]$FocusFiles = 8",
            script,
        )
        self.assertIn(
            "--focus-files $FocusFiles",
            script,
        )
        self.assertNotIn(
            "--focus-files 3",
            script,
        )

if __name__ == "__main__":
    unittest.main()
