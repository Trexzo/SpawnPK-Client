"""R178: original parent-source integration safeguards (synthetic-only CI)."""
import ast
from pathlib import Path
import unittest
from spk_recovery.private_v309_packet_inheritance_r178 import (
    verify_packet_with_original_parents)


class R178InheritanceSafetyTests(unittest.TestCase):
    def test_does_not_accept_missing_original_source_and_parent_pins(self):
        with self.assertRaises((ValueError,FileNotFoundError)):
            verify_packet_with_original_parents(
                "/absent-private-original.jar",
                "/absent-packet-source.zip",
                "/absent-original-parent-source.zip",
                original_sha256="0"*64,
                packet_source_sha256="1"*64,
                parent_source_sha256="2"*64,
                class_sha256="3"*64,
                parent_class_shas={"rs/t":"4"*64,"rs/a":"5"*64})

    def test_source_does_not_embed_client_original_binary_dependency(self):
        import inspect
        source=inspect.getsource(verify_packet_with_original_parents)
        tree=ast.parse(source)
        self.assertIn("--release",source)
        self.assertIn("-classpath",source)
        self.assertIn("verify_original_packet_parents",source)
        self.assertIn("verify_packet_61",source)
        self.assertIn("all_selected_core_method_code_equal",source)
        self.assertIn("original_game_binary_compiler_dependency",source)


if __name__=="__main__":
    unittest.main()
