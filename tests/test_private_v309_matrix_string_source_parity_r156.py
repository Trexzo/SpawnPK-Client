"""R156 synthetic matrix toString Java source-vs-original JVM instruction proof.

No proprietary original or privately restored source is present in CI.
"""
import json
import unittest

from test_private_v309_matrix_transform_projection_parity_r155 import (
    R155OriginalTransformProjectionSourceTests,
)
from spk_recovery.private_v309_matrix_packet_loader_parity_r153 import (
    PrivateMatrixLoaderR153Error, verify_private_original_matrix_packet_loader,
)


class R156OriginalMatrixStringSourceTests(R155OriginalTransformProjectionSourceTests):
    def matrix_java(self, *, extra, transform_call="this.apply(r);"):
        source = super().matrix_java(
            extra=extra, transform_call=transform_call)
        self.assertTrue(source.endswith("}\n"))
        # Entirely synthetic row formatting and Math expression; NOT the
        # user's reconstructed original matrix toString implementation.
        extra_method = (
            " public String toString() {\n"
            "   StringBuilder result = new StringBuilder();\n"
            "   this.d();\n"
            "   this.c();\n"
            "   for (int row=0; row<4; row++) {\n"
            "     for (int column=0; column<4; column++) {\n"
            '       if (column>0) result.append(",");\n'
            "       float value=this.values[column+4*row];\n"
            "       if (Math.sqrt((double)(value*value)) < 0.00001d) {\n"
            "          value=0f;\n"
            "       }\n"
            "       result.append(value);\n"
            "     }\n"
            '     result.append(";");\n'
            "   }\n"
            "   return result.toString();\n"
            " }\n"
        )
        return source[:-2] + extra_method + "}\n"

    def setUp(self):
        super().setUp()
        self.string_selection = self.root / "six-exact-original-methods.json"
        self.string_selection.write_text(json.dumps([
            {"name": "<init>", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "read", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "c", "descriptor": "()[F"},
            {"name": "d", "descriptor": "()[F"},
            {"name": "apply", "descriptor": "(Lext/Rotation;)V"},
            {"name": "toString", "descriptor": "()Ljava/lang/String;"},
        ]), encoding="utf-8")

    def prove_string(self, *, source=None, selection=None, enabled=True,
                     euler=True):
        source = source or self.donor
        selection = selection or self.string_selection
        return verify_private_original_matrix_packet_loader(
            self.original, source, self.support, selection,
            original_sha256=self.sha(self.original),
            matrix_source_sha256=self.sha(source),
            support_source_sha256=self.sha(self.support),
            selection_sha256=self.sha(selection),
            original_owner=self.matrix_owner,
            allow_euler_method_bodies=euler,
            allow_transform_projection_method=True,
            allow_matrix_string_method=enabled)

    def test_original_stringbuilder_and_math_calls_recompiled_from_java(self):
        report = self.prove_string()
        self.assertEqual(6, report["verified_selected_method_count"])
        self.assertEqual(2, report["euler_float_array_source_methods_checked"])
        self.assertEqual(1, report["transform_projection_method_checked"])
        self.assertEqual(1, report["matrix_string_method_checked"])
        self.assertTrue(report["all_selected_core_method_code_equal"])
        self.assertTrue(report["compiler_external_classpath_empty"])
        self.assertFalse(report["support_class_bodies_original_equivalence_accepted"])
        self.assertFalse(report["complete_original_matrix_class_source_accepted"])

    def test_text_method_must_be_explicitly_enabled(self):
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_string(enabled=False)

    def test_text_method_requires_accepted_euler_selection(self):
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_string(euler=False)

    def test_changed_separator_detected_in_original_code(self):
        altered = self.matrix_java(extra="donor").replace(
            'result.append(",");', 'result.append("x");')
        donor = self.archive(
            "incorrect-string-renderer.zip",
            {self.matrix_owner + ".java": altered})
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_string(source=donor)

    def test_changed_math_threshold_detected(self):
        altered = self.matrix_java(extra="donor").replace(
            "0.00001d", "0.00002d")
        donor = self.archive(
            "incorrect-threshold.zip",
            {self.matrix_owner + ".java": altered})
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_string(source=donor)

    def test_only_full_string_method_descriptor_supported(self):
        selection = self.root / "wrong-toString-descriptor.json"
        selection.write_text(json.dumps([
            {"name": "<init>", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "read", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "c", "descriptor": "()[F"},
            {"name": "d", "descriptor": "()[F"},
            {"name": "apply", "descriptor": "(Lext/Rotation;)V"},
            {"name": "toString", "descriptor": "()V"},
        ]), encoding="utf-8")
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_string(selection=selection)


if __name__ == "__main__":
    unittest.main()
