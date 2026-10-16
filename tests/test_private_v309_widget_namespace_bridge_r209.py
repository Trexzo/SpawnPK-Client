"""R209 synthetic Java9 collision bridge tests: NO original game binaries.

Checks the preexisting R125 Java/Windows namespace plan, confirms Java9
rejects a class/package collision, then compiles the legal type alias
together with a child while independently verifying the emitted JVM
child -> base superclass owner. Private original JAR replay is separate.
"""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from spk_recovery.private_client_namespace_legalizer_r125 import (
    plan_client_namespaces,
)
from spk_recovery.private_v309_widget_namespace_bridge_r209 import (
    R209NamespaceBridgeError,
    inspect_widget_legalizer,
    verify_private_v309_widget_namespace,
    compile_synthetic_widget_alias_pair,
)


class R209SyntheticWidgetNamespaceTests(unittest.TestCase):
    def test_java9_fails_original_names_but_builds_legal_pair(self):
        result=compile_synthetic_widget_alias_pair()
        self.assertTrue(result[
            "original_name_synthetic_javac_failed"])
        self.assertTrue(result[
            "legalized_name_synthetic_javac_passed"])
        self.assertTrue(result[
            "legalized_compiled_child_extends_alias"])
        self.assertEqual(53,result["independently_compiled_java_major"])
        self.assertFalse(result["original_v309_binary_byte_identity_proven"])
        self.assertFalse(result["original_proprietary_source_compiled"])
        self.assertFalse(result["original_game_code_executed"])

    def test_mapping_is_deterministic_and_child_package_is_preserved(self):
        original={"toy/widget/Base","toy/widget/Base/Child"}
        first=inspect_widget_legalizer(
            original,expected_base="toy/widget/Base",
            expected_child="toy/widget/Base/Child")
        second=inspect_widget_legalizer(
            set(reversed(sorted(original))),
            expected_base="toy/widget/Base",
            expected_child="toy/widget/Base/Child")
        self.assertEqual(first,second)
        self.assertEqual("toy/widget/Base/Child",
                         first["legal_java_child_owner"])
        self.assertEqual(
            "toy/widget/Base__Type_"+
            hashlib.sha256(b"toy/widget/Base").hexdigest()[:12],
            first["legal_java_base_owner"])
        self.assertNotEqual(first["original_base_owner"],
                            first["legal_java_base_owner"])
        self.assertFalse(first["source_java_rewritten"])
        self.assertFalse(first["renamed_classfile_bytecode_parity_proven"])

    def test_shadow_collisions_across_multiple_class_package_depths(self):
        original={
            "toy", "toy/widget", "toy/widget/Base",
            "toy/widget/Base/Child",
            "toy/widget/Base/Child$Inner",
        }
        proof=inspect_widget_legalizer(
            original,expected_base="toy/widget/Base",
            expected_child="toy/widget/Base/Child")
        self.assertEqual("toy/widget/Base/Child",
                         proof["legal_java_child_owner"])
        self.assertTrue(proof["class_package_shadow_resolved"])
        self.assertTrue(proof["java_and_casefold_safe"])
        self.assertFalse(proof["full_original_client_compiles"])

    def test_missing_class_or_child_package_is_rejected(self):
        for incomplete in (
            {"toy/widget/Base"},
            {"toy/widget/Base/Child"},
            {"toy/widget/Base","toy/widget/Other"},
        ):
            with self.subTest(names=incomplete):
                with self.assertRaises(R209NamespaceBridgeError):
                    inspect_widget_legalizer(
                        incomplete,expected_base="toy/widget/Base",
                        expected_child="toy/widget/Base/Child")

    def test_wrong_or_reused_name_mapping_is_rejected(self):
        owners={"toy/widget/Base","toy/widget/Base/Child"}
        def dishonest_planner(_classes,include_identifiers):
            return {
                "identifiers_included":include_identifiers,
                "remaps":[],
                "no_type_package_shadow_after_mapping":False,
                "mapped_paths_unique_after_casefold":True,
                "mapped_package_directories_unique_after_casefold":True,
                "private_mapping_sha256":"0"*64,
            }
        with self.assertRaises(R209NamespaceBridgeError):
            inspect_widget_legalizer(
                owners,planner=dishonest_planner,
                expected_base="toy/widget/Base",
                expected_child="toy/widget/Base/Child")

    def test_original_binary_is_never_accepted_without_full_sha(self):
        with TemporaryDirectory() as tmp:
            original=Path(tmp)/"unrelated.jar"
            with ZipFile(original,"w",ZIP_DEFLATED) as archive:
                archive.writestr(
                    "rs/n/c.class",b"\xca\xfe\xba\xbe")
                archive.writestr(
                    "rs/n/c/ap.class",b"\xca\xfe\xba\xbe")
            with self.assertRaises(ValueError):
                verify_private_v309_widget_namespace(original)

    def test_invalid_java_fixture_names_are_rejected(self):
        for name,child in (
            ("toy/widget/Base","toy/widget/Other"),
            ("toy/widget/class","toy/widget/class/Child"),
            ("toy/Base","toy/Base/Child"),
        ):
            with self.subTest(name=name):
                with self.assertRaises(R209NamespaceBridgeError):
                    compile_synthetic_widget_alias_pair(
                        original_base=name,original_child=child)


if __name__=="__main__":
    unittest.main()
