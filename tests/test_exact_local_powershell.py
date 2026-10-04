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
            "two_string_swing_capture_alias_action_count":
                "/normalization_summary/two_string_swing_capture_alias_action_count",
            "two_string_swing_capture_alias_reference_count":
                "/normalization_summary/two_string_swing_capture_alias_reference_count",
            "compile_time_lombok_nonnull_action_count":
                "/normalization_summary/compile_time_lombok_nonnull_action_count",
            "compile_time_lombok_nonnull_reference_count":
                "/normalization_summary/compile_time_lombok_nonnull_reference_count",
            "linkedhashmap_field_key_reconstruction_method_count":
                "/normalization_summary/linkedhashmap_field_key_reconstruction_method_count",
            "linkedhashmap_field_key_reconstruction_reference_count":
                "/normalization_summary/linkedhashmap_field_key_reconstruction_reference_count",
            "intpredicate_parameter_capture_alias_action_count":
                "/normalization_summary/intpredicate_parameter_capture_alias_action_count",
            "intpredicate_parameter_capture_alias_reference_count":
                "/normalization_summary/intpredicate_parameter_capture_alias_reference_count",
            "invokedynamic_captured_class_local_alias_action_count":
                "/normalization_summary/invokedynamic_captured_class_local_alias_action_count",
            "invokedynamic_captured_class_local_alias_reference_count":
                "/normalization_summary/invokedynamic_captured_class_local_alias_reference_count",
            "collectors_to_list_wildcard_sink_cast_action_count":
                "/normalization_summary/collectors_to_list_wildcard_sink_cast_action_count",
            "collectors_to_list_wildcard_sink_cast_reference_count":
                "/normalization_summary/collectors_to_list_wildcard_sink_cast_reference_count",
            "enum_valueof_raw_class_cast_action_count":
                "/normalization_summary/enum_valueof_raw_class_cast_action_count",
            "enum_valueof_raw_class_cast_reference_count":
                "/normalization_summary/enum_valueof_raw_class_cast_reference_count",
            "shadowed_nested_static_method_action_count":
                "/normalization_summary/shadowed_nested_static_method_action_count",
            "shadowed_nested_static_method_reference_count":
                "/normalization_summary/shadowed_nested_static_method_reference_count",
            "reference_shadowed_self_static_field_method_count":
                "/normalization_summary/reference_shadowed_self_static_field_method_count",
            "reference_shadowed_self_static_field_reference_count":
                "/normalization_summary/reference_shadowed_self_static_field_reference_count",
            "methodhandle_invokeexact_result_cast_action_count":
                "/normalization_summary/methodhandle_invokeexact_result_cast_action_count",
            "methodhandle_invokeexact_result_cast_reference_count":
                "/normalization_summary/methodhandle_invokeexact_result_cast_reference_count",
            "missing_synthetic_constructor_accessor_action_count":
                "/normalization_summary/missing_synthetic_constructor_accessor_action_count",
            "missing_synthetic_constructor_accessor_method_count":
                "/normalization_summary/missing_synthetic_constructor_accessor_method_count",
            "missing_synthetic_bridge_forwarder_action_count":
                "/normalization_summary/missing_synthetic_bridge_forwarder_action_count",
            "missing_synthetic_bridge_forwarder_method_count":
                "/normalization_summary/missing_synthetic_bridge_forwarder_method_count",
            "object_boolean_condition_cast_action_count":
                "/normalization_summary/object_boolean_condition_cast_action_count",
            "object_boolean_condition_cast_reference_count":
                "/normalization_summary/object_boolean_condition_cast_reference_count",
            "erased_hashmap_get_array_return_cast_action_count":
                "/normalization_summary/erased_hashmap_get_array_return_cast_action_count",
            "erased_hashmap_get_array_return_cast_reference_count":
                "/normalization_summary/erased_hashmap_get_array_return_cast_reference_count",
            "erased_map_mixed_object_local_action_count":
                "/normalization_summary/erased_map_mixed_object_local_action_count",
            "erased_map_mixed_object_local_reference_count":
                "/normalization_summary/erased_map_mixed_object_local_reference_count",
            "erased_map_number_assignment_action_count":
                "/normalization_summary/erased_map_number_assignment_action_count",
            "erased_map_number_assignment_reference_count":
                "/normalization_summary/erased_map_number_assignment_reference_count",
            "erased_map_get_integer_ternary_cast_action_count":
                "/normalization_summary/erased_map_get_integer_ternary_cast_action_count",
            "erased_map_get_integer_ternary_cast_reference_count":
                "/normalization_summary/erased_map_get_integer_ternary_cast_reference_count",
            "erased_map_keyset_int_enhanced_for_action_count":
                "/normalization_summary/erased_map_keyset_int_enhanced_for_action_count",
            "erased_map_keyset_int_enhanced_for_reference_count":
                "/normalization_summary/erased_map_keyset_int_enhanced_for_reference_count",
            "erased_list_integer_enhanced_for_action_count":
                "/normalization_summary/erased_list_integer_enhanced_for_action_count",
            "erased_list_integer_enhanced_for_reference_count":
                "/normalization_summary/erased_list_integer_enhanced_for_reference_count",
            "erased_set_int_enhanced_for_action_count":
                "/normalization_summary/erased_set_int_enhanced_for_action_count",
            "erased_set_int_enhanced_for_reference_count":
                "/normalization_summary/erased_set_int_enhanced_for_reference_count",
            "erased_iterator_assignment_cast_action_count":
                "/normalization_summary/erased_iterator_assignment_cast_action_count",
            "erased_iterator_assignment_cast_reference_count":
                "/normalization_summary/erased_iterator_assignment_cast_reference_count",
            "cc_generic_value_object_cast_action_count":
                "/normalization_summary/cc_generic_value_object_cast_action_count",
            "cc_generic_value_object_cast_reference_count":
                "/normalization_summary/cc_generic_value_object_cast_reference_count",
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
            'TWO_STRING_SWING_CAPTURE_ALIAS_REFERENCES='
            '$($Recovered.two_string_swing_capture_alias_reference_count)',
            script,
        )
        self.assertIn(
            'COMPILE_TIME_LOMBOK_NONNULL_REFERENCES='
            '$($Recovered.compile_time_lombok_nonnull_reference_count)',
            script,
        )
        self.assertIn(
            'LINKEDHASHMAP_FIELD_KEY_RECONSTRUCTION_REFERENCES='
            '$($Recovered.linkedhashmap_field_key_reconstruction_reference_count)',
            script,
        )
        self.assertIn(
            'INTPREDICATE_PARAMETER_CAPTURE_ALIAS_REFERENCES='
            '$($Recovered.intpredicate_parameter_capture_alias_reference_count)',
            script,
        )
        self.assertIn(
            'INVOKEDYNAMIC_CAPTURED_CLASS_LOCAL_ALIAS_REFERENCES='
            '$($Recovered.invokedynamic_captured_class_local_alias_reference_count)',
            script,
        )
        self.assertIn(
            'COLLECTORS_TOLIST_WILDCARD_SINK_CAST_REFERENCES='
            '$($Recovered.collectors_to_list_wildcard_sink_cast_reference_count)',
            script,
        )
        self.assertIn(
            'ENUM_VALUEOF_RAW_CLASS_CAST_REFERENCES='
            '$($Recovered.enum_valueof_raw_class_cast_reference_count)',
            script,
        )
        self.assertIn(
            'NESTED_STATIC_METHOD_SHADOW_ACTIONS='
            '$($Recovered.shadowed_nested_static_method_action_count)',
            script,
        )
        self.assertIn(
            'NESTED_STATIC_METHOD_SHADOW_REFERENCES='
            '$($Recovered.shadowed_nested_static_method_reference_count)',
            script,
        )
        self.assertIn(
            'REFERENCE_SHADOWED_SELF_STATIC_FIELD_METHODS='
            '$($Recovered.reference_shadowed_self_static_field_method_count)',
            script,
        )
        self.assertIn(
            'REFERENCE_SHADOWED_SELF_STATIC_FIELD_REFERENCES='
            '$($Recovered.reference_shadowed_self_static_field_reference_count)',
            script,
        )
        self.assertIn(
            'METHODHANDLE_INVOKEEXACT_RESULT_CAST_ACTIONS='
            '$($Recovered.methodhandle_invokeexact_result_cast_action_count)',
            script,
        )
        self.assertIn(
            'METHODHANDLE_INVOKEEXACT_RESULT_CAST_REFERENCES='
            '$($Recovered.methodhandle_invokeexact_result_cast_reference_count)',
            script,
        )
        self.assertIn(
            'MISSING_SYNTHETIC_CONSTRUCTOR_ACCESSOR_ACTIONS='
            '$($Recovered.missing_synthetic_constructor_accessor_action_count)',
            script,
        )
        self.assertIn(
            'MISSING_SYNTHETIC_CONSTRUCTOR_ACCESSOR_METHODS='
            '$($Recovered.missing_synthetic_constructor_accessor_method_count)',
            script,
        )
        self.assertIn(
            'MISSING_SYNTHETIC_BRIDGE_FORWARDER_ACTIONS='
            '$($Recovered.missing_synthetic_bridge_forwarder_action_count)',
            script,
        )
        self.assertIn(
            'MISSING_SYNTHETIC_BRIDGE_FORWARDER_METHODS='
            '$($Recovered.missing_synthetic_bridge_forwarder_method_count)',
            script,
        )
        self.assertIn(
            'OBJECT_BOOLEAN_CONDITION_CAST_ACTIONS='
            '$($Recovered.object_boolean_condition_cast_action_count)',
            script,
        )
        self.assertIn(
            'OBJECT_BOOLEAN_CONDITION_CAST_REFERENCES='
            '$($Recovered.object_boolean_condition_cast_reference_count)',
            script,
        )
        self.assertIn(
            'ERASED_HASHMAP_GET_ARRAY_RETURN_CAST_ACTIONS='
            '$($Recovered.erased_hashmap_get_array_return_cast_action_count)',
            script,
        )
        self.assertIn(
            'ERASED_HASHMAP_GET_ARRAY_RETURN_CAST_REFERENCES='
            '$($Recovered.erased_hashmap_get_array_return_cast_reference_count)',
            script,
        )
        self.assertIn(
            'ERASED_MAP_MIXED_OBJECT_LOCAL_ACTIONS='
            '$($Recovered.erased_map_mixed_object_local_action_count)',
            script,
        )
        self.assertIn(
            'ERASED_MAP_MIXED_OBJECT_LOCAL_REFERENCES='
            '$($Recovered.erased_map_mixed_object_local_reference_count)',
            script,
        )
        self.assertIn(
            'ERASED_MAP_NUMBER_ASSIGNMENT_REFERENCES='
            '$($Recovered.erased_map_number_assignment_reference_count)',
            script,
        )
        self.assertIn(
            'ERASED_MAP_GET_INTEGER_TERNARY_CAST_ACTIONS='
            '$($Recovered.erased_map_get_integer_ternary_cast_action_count)',
            script,
        )
        self.assertIn(
            'ERASED_MAP_GET_INTEGER_TERNARY_CAST_REFERENCES='
            '$($Recovered.erased_map_get_integer_ternary_cast_reference_count)',
            script,
        )
        self.assertIn(
            'ERASED_MAP_KEYSET_INT_ENHANCED_FOR_ACTIONS='
            '$($Recovered.erased_map_keyset_int_enhanced_for_action_count)',
            script,
        )
        self.assertIn(
            'ERASED_MAP_KEYSET_INT_ENHANCED_FOR_REFERENCES='
            '$($Recovered.erased_map_keyset_int_enhanced_for_reference_count)',
            script,
        )
        self.assertIn(
            'ERASED_LIST_INTEGER_ENHANCED_FOR_ACTIONS='
            '$($Recovered.erased_list_integer_enhanced_for_action_count)',
            script,
        )
        self.assertIn(
            'ERASED_LIST_INTEGER_ENHANCED_FOR_REFERENCES='
            '$($Recovered.erased_list_integer_enhanced_for_reference_count)',
            script,
        )
        self.assertIn(
            'ERASED_SET_INT_ENHANCED_FOR_REFERENCES='
            '$($Recovered.erased_set_int_enhanced_for_reference_count)',
            script,
        )
        self.assertIn(
            'ERASED_ITERATOR_ASSIGNMENT_CAST_REFERENCES='
            '$($Recovered.erased_iterator_assignment_cast_reference_count)',
            script,
        )
        self.assertIn(
            'CC_GENERIC_VALUE_OBJECT_CAST_ACTIONS='
            '$($Recovered.cc_generic_value_object_cast_action_count)',
            script,
        )
        self.assertIn(
            'CC_GENERIC_VALUE_OBJECT_CAST_REFERENCES='
            '$($Recovered.cc_generic_value_object_cast_reference_count)',
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
