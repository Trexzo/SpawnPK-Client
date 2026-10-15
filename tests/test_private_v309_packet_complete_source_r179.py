"""R179: complete original-JVM Packet class source proof on synthetic inputs.

All source/JAR inputs are independently generated in CI and contain no
SpawnPK original binary or Java source.
"""
import unittest
from zipfile import ZipFile
from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_packet_complete_source_r179 import (
    OriginalPacketCompleteR179Error,
    verify_original_complete_packet_java,
)
from test_private_v309_packet_73_methods_r178 import (
    R178OriginalPacketWithRealParentsTests,
)


class R179PacketCompleteSourceTests(R178OriginalPacketWithRealParentsTests):
    def setUp(self):
        super().setUp()
        self.full_source=self.archive("complete-packet.zip",{
            "rs/x/e.java":self.packet_java(original=True)})
        self.all_fields=4
        p=profile_class_field_accesses(self.original_class_bytes())
        self.full_opcodes=sum(len(m["instructions"]) for m in p["methods"])
        self.full_methods=len(p["methods"])

    def prove_full(self,source=None,source_sha=None,
                   method_delta=0, opcode_delta=0):
        source=source or self.full_source
        return verify_original_complete_packet_java(
            self.original,source,self.parents,self.stub,
            original_sha256=self.sha(self.original),
            packet_source_sha256=source_sha or self.sha(source),
            parent_source_sha256=self.sha(self.parents),
            helpers_source_sha256=self.sha(self.stub),
            original_owner=self.OWNER,
            original_class_sha256=self.packet_class_sha,
            parent_class_shas=self.parent_class_shas,
            original_helper_owners=("rs/q/a",),
            expected_method_count=self.full_methods+method_delta,
            expected_opcode_count=self.full_opcodes+opcode_delta,
            expected_field_count=self.all_fields,
            expected_parent_method_count=4,
            expected_parent_opcode_count=self.parent_inst)

    def test_all_original_methods_clinit_and_fields_exact(self):
        result=self.prove_full()
        self.assertEqual(self.full_methods,
                         result["verified_original_jvm_methods_including_initializer"])
        self.assertEqual(self.full_opcodes,
                         result["matched_original_jvm_instructions"])
        self.assertTrue(result["complete_packet_original_field_abi_verified"])
        self.assertTrue(result["original_packet_superclass_source_verified"])
        self.assertFalse(result["source_only_helper_bodies_verified_original"])
        self.assertFalse(result["entire_original_v309_client_compiles"])

    def test_one_selected_method_body_mutation_rejected(self):
        changed=self.archive("mutated-complete-source.zip",{
            "rs/x/e.java":self.packet_java(original=True,mutated=True)})
        with self.assertRaises(ValueError):
            self.prove_full(source=changed)

    def test_original_initializer_changed_rejected(self):
        body=self.packet_java(original=True)
        self.assertIn("STATIC_VALUE=19",body)
        changed=self.archive("mutated-initializer.zip",{
            "rs/x/e.java":body.replace("STATIC_VALUE=19","STATIC_VALUE=20")})
        with self.assertRaises(ValueError):
            self.prove_full(source=changed)

    def test_wrong_original_shas_and_expected_full_counts_rejected(self):
        with self.assertRaises(OriginalPacketCompleteR179Error):
            self.prove_full(source_sha="0"*64)
        with self.assertRaises(OriginalPacketCompleteR179Error):
            self.prove_full(method_delta=1)
        with self.assertRaises(OriginalPacketCompleteR179Error):
            self.prove_full(opcode_delta=1)


if __name__=="__main__":
    unittest.main()
