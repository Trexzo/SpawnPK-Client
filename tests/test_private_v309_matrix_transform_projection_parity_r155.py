"""R155: original linked matrix quaternion/transform projection JVM Code parity.

All hosted fixtures are synthetic. Private v309 original source and
reconstructed original methods remain solely in the isolated workspace.
"""
import json
import re
import unittest

from test_private_v309_matrix_euler_source_parity_r154 import (
    R154EulerSourceCodeTests,
)
from spk_recovery.private_v309_matrix_packet_loader_parity_r153 import (
    PrivateMatrixLoaderR153Error, verify_private_original_matrix_packet_loader,
)


class R155OriginalTransformProjectionSourceTests(R154EulerSourceCodeTests):
    TRANSFORM_FIELDS = (
        "public float p0,p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11; "
    )

    def original_jar(self):
        self.support_sources["ext/Rotation.java"] = (
            self.support_sources["ext/Rotation.java"].replace(
                "public class Rotation {",
                "public class Rotation { " + self.TRANSFORM_FIELDS))
        return super().original_jar()

    def stub_support(self):
        helpers = super().stub_support()
        helpers["ext/Rotation.java"] = helpers["ext/Rotation.java"].replace(
            "public class Rotation {",
            "public class Rotation { " + self.TRANSFORM_FIELDS)
        return helpers

    def matrix_java(self, *, extra, transform_call="this.apply(r);"):
        java = super().matrix_java(
            extra=extra, transform_call=transform_call)
        projected = (
            " void apply(ext.Rotation r) {\n"
        )
        source_indices = (
            "p7", "p1", "p2", None, "p0", "p4", "p5", None,
            "p6", "p3", "p8", None, "p9", "p10", "p11", "one"
        )
        for index, name in enumerate(source_indices):
            value = ("0f" if name is None else
                     "1f" if name == "one" else "r." + name)
            projected += f"  this.values[{index}] = {value};\n"
        projected += " }\n"
        updated, count = re.subn(
            r" void apply\(ext\.Rotation x\) \{\n"
            r"   this\.values\[0\] = (?:1f|999f);\n"
            r" \}\n",
            lambda _match: projected,
            java)
        self.assertEqual(1, count)
        return updated

    def setUp(self):
        super().setUp()
        self.projection_selection = self.root / "five-methods-selection.json"
        self.projection_selection.write_text(json.dumps([
            {"name": "<init>", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "read", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "c", "descriptor": "()[F"},
            {"name": "d", "descriptor": "()[F"},
            {"name": "apply", "descriptor": "(Lext/Rotation;)V"},
        ]), encoding="utf-8")

    def prove_projection(self, *, source=None, supports=None,
                         selected=None, allow=True):
        source = source or self.donor
        supports = supports or self.support
        selected = selected or self.projection_selection
        return verify_private_original_matrix_packet_loader(
            self.original, source, supports, selected,
            original_sha256=self.sha(self.original),
            matrix_source_sha256=self.sha(source),
            support_source_sha256=self.sha(supports),
            selection_sha256=self.sha(selected),
            original_owner=self.matrix_owner,
            allow_euler_method_bodies=True,
            allow_transform_projection_method=allow)

    def test_original_transform_fields_recompile_and_match_selected_methods(self):
        result = self.prove_projection()
        self.assertEqual(5, result["verified_selected_method_count"])
        self.assertEqual(2, result["euler_float_array_source_methods_checked"])
        self.assertEqual(1, result["transform_projection_method_checked"])
        self.assertGreater(result["matched_opcode_count"], 110)
        self.assertTrue(result["all_selected_core_method_code_equal"])
        self.assertFalse(result["support_transform_type_field_values_accepted"])
        self.assertFalse(result["support_class_bodies_original_equivalence_accepted"])
        self.assertFalse(result["complete_original_matrix_class_source_accepted"])

    def test_projection_is_not_implicitly_accepted_by_euler_opt_in(self):
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_projection(allow=False)

    def test_one_wrong_transform_field_ref_vetoes_entire_selection(self):
        altered = self.matrix_java(extra="donor").replace(
            "this.values[10] = r.p8;", "this.values[10] = r.p7;")
        donor = self.archive(
            "wrong-projector-source.zip",
            {self.matrix_owner + ".java": altered})
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_projection(source=donor)

    def test_wrong_support_declaration_is_not_original_source(self):
        helpers = self.stub_support()
        helpers["ext/Rotation.java"] = (
            helpers["ext/Rotation.java"].replace("p10,p11;", "p10;"))
        archive = self.archive("missing-field-source.zip", helpers)
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_projection(supports=archive)

    def test_selection_wrong_projection_signature_rejected(self):
        selection = self.root / "bad-projection-selection.json"
        selection.write_text(json.dumps([
            {"name": "<init>", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "read", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "c", "descriptor": "()[F"},
            {"name": "d", "descriptor": "()[F"},
            {"name": "apply", "descriptor": "(Lext/Rotation;Z)V"},
        ]), encoding="utf-8")
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove_projection(selected=selection)


if __name__ == "__main__":
    unittest.main()
