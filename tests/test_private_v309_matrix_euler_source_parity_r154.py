"""R154: optional exact original math-only Euler source-method JVM Code gate.

All original/source fixtures are synthetic. The actual original-v309 Euler
source recovered privately is never published as GitHub test code.
"""
import hashlib
import json
from pathlib import Path
import unittest

from test_private_v309_matrix_packet_loader_parity_r153 import (
    R153OriginalMatrixLoaderSources,
)
from spk_recovery.private_v309_matrix_packet_loader_parity_r153 import (
    PrivateMatrixLoaderR153Error, verify_private_original_matrix_packet_loader,
)


class R154EulerSourceCodeTests(R153OriginalMatrixLoaderSources):
    def matrix_java(self, *, extra, transform_call="this.apply(r);"):
        normal = super().matrix_java(
            extra=extra, transform_call=transform_call)
        self.assertTrue(normal.endswith("}\n"))
        # Synthetic distinct math-only (float[3]) methods. Not the original
        # user's proprietary reconstructed v309 Euler algorithms.
        methods = (
            " float[] c() {\n"
            "   float[] angles = new float[3];\n"
            "   if (this.values[2] > 0.5f) {\n"
            "      angles[0] = (float)Math.atan2((double)this.values[1], "
            "(double)this.values[0]);\n"
            "   } else {\n"
            "      angles[1] = (float)Math.asin((double)this.values[2]);\n"
            "   }\n"
            "   return angles;\n"
            " }\n"
            " public float[] d() {\n"
            "   float angle = (float)Math.atan2("
            "(double)this.values[4], (double)this.values[5]);\n"
            "   return new float[] { angle, 0f, 0f };\n"
            " }\n"
        )
        return normal[:-2] + methods + "}\n"

    def setUp(self):
        super().setUp()
        self.euler_selection = self.root / "four-original-methods.json"
        self.euler_selection.write_text(json.dumps([
            {"name": "<init>", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "read", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "c", "descriptor": "()[F"},
            {"name": "d", "descriptor": "()[F"},
        ]), encoding="utf-8")

    def prove_euler(self, *, matrix=None, selection=None, enabled=True):
        donor = matrix or self.donor
        selection = selection or self.euler_selection
        return verify_private_original_matrix_packet_loader(
            self.original, donor, self.support, selection,
            original_sha256=self.sha(self.original),
            matrix_source_sha256=self.sha(donor),
            support_source_sha256=self.sha(self.support),
            selection_sha256=self.sha(selection),
            original_owner=self.matrix_owner,
            allow_euler_method_bodies=enabled)

    def test_both_math_float_array_source_methods_exact_original_code(self):
        report = self.prove_euler()
        self.assertEqual(4, report["verified_selected_method_count"])
        self.assertEqual(1, report["verified_constructor_count"])
        self.assertEqual(2, report["euler_float_array_source_methods_checked"])
        self.assertGreater(report["matched_opcode_count"], 60)
        self.assertTrue(report["all_selected_core_method_code_equal"])
        self.assertTrue(report["compiler_external_classpath_empty"])
        self.assertFalse(report["support_class_bodies_original_equivalence_accepted"])
        self.assertFalse(report["whole_v309_client_source_compilation_accepted"])
        self.assertFalse(report["complete_original_matrix_class_source_accepted"])

    def test_four_methods_without_euler_opt_in_fails_closed(self):
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_euler(enabled=False)

    def test_modified_euler_index_refuses_entire_selection(self):
        wrong = self.matrix_java(extra="donor").replace(
            "this.values[4], (double)this.values[5]",
            "this.values[3], (double)this.values[5]")
        altered = self.archive(
            "bad-euler-donor.zip", {self.matrix_owner + ".java": wrong})
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_euler(matrix=altered)

    def test_missing_second_math_reader_fails_closed(self):
        source = self.matrix_java(extra="donor")
        source = source.replace("public float[] d()", "public int d()")
        modified = self.archive(
            "wrong-euler-declaration.zip",
            {self.matrix_owner + ".java": source})
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_euler(matrix=modified)

    def test_only_exact_two_original_math_float_array_methods_are_eligible(self):
        selection = self.root / "selection-one-euler.json"
        selection.write_text(json.dumps([
            {"name": "<init>", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "read", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "c", "descriptor": "()[F"},
        ]), encoding="utf-8")
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_euler(selection=selection)


if __name__ == "__main__":
    unittest.main()
