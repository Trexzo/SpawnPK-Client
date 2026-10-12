"""R91: the private original JAR does not bundle Java runtime classes."""
import unittest

from spk_recovery.small_owner_method_source import (
    SimpleOwnerMethodSourceError, _private_external_field_owners,
)


class ExternalShortOwnerDependencyTests(unittest.TestCase):
    def test_java_standard_library_static_reads_are_not_bundled_dependencies(self):
        original = {
            "internal_name": "p/Owner",
            "methods": [
                {"name": "<clinit>", "instructions": [
                    {"opcode": "0xb2", "owner": "missing/OnlyInitializer"}
                ]},
                {"name": "save", "instructions": [
                    {"opcode": "0xb2", "owner": "java/nio/file/StandardCopyOption"},
                    {"opcode": "0xb2", "owner": "java/lang/System"},
                    {"opcode": "0xb2", "owner": "p/Owner"},
                    {"opcode": "0xb3", "owner": "client/Required"},
                ]},
                {"name": "short", "instructions": [
                    {"opcode": "0xb2", "owner": "client/Required"},
                ]},
            ],
        }
        self.assertEqual(_private_external_field_owners(original),
                         {"client/Required"})

    def test_unresolved_field_owner_fails_closed(self):
        original = {
            "internal_name": "p/Owner",
            "methods": [{"name": "m", "instructions": [
                {"opcode": "0xb2", "owner": None}]}],
        }
        with self.assertRaisesRegex(
                SimpleOwnerMethodSourceError,
                "ORIGINAL_EXTERNAL_STATIC_FIELD_OWNER_UNRESOLVED"):
            _private_external_field_owners(original)

    def test_third_party_client_owner_remains_required(self):
        original = {
            "internal_name": "p/Owner",
            "methods": [{"name": "m", "instructions": [
                {"opcode": "0xb2", "owner": "other/PrivateClass"},
                {"opcode": "0xb3", "owner": "javax/swing/UIManager"},
            ]}],
        }
        self.assertEqual(_private_external_field_owners(original),
                         {"other/PrivateClass"})


if __name__ == "__main__":
    unittest.main()
