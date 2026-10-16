"""R221 synthetic complete 14-method JVM comparator acceptance regression.

Constructs 4314 unrelated invented JVM instruction rows, including 178
ldc -> ldc_w width changes. No original client source/class/JAR is in CI;
private acceptance uses separate pinned exact-source and class files.
"""
import hashlib
import json
import unittest

from spk_recovery.private_v309_unified_spellbook_class_r221 import (
    METHODS,
    R221SingleClassParityError,
    parse_method,
    verify_unified_disassembly,
    verify_private_unified_class,
)


class R221Invented14MethodCode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        empty_sha=hashlib.sha256(b"{}").hexdigest()
        methods=[]
        old=[]
        new=[]
        for i,(heading,reheaded,count,widened,_) in enumerate(METHODS):
            assert count>=widened+1
            offsets=[]
            new_offsets=[]
            cursor=0
            other=0
            for j in range(count):
                if j<count-1 and j<widened:
                    opcode="ldc"
                    new_opcode="ldc_w"
                    width=2
                    new_width=3
                    operand="int 3"
                elif j<count-1:
                    opcode="nop"
                    new_opcode="nop"
                    width=1
                    new_width=1
                    operand=""
                else:
                    opcode="return"
                    new_opcode="return"
                    width=1
                    new_width=1
                    operand=""
                offsets.append(f"       {cursor}: {opcode} "+operand)
                new_offsets.append(f"       {other}: {new_opcode} "+operand)
                cursor+=width
                other+=new_width
            old.extend((heading,"    Code:",*offsets,""))
            new.extend((reheaded,"    Code:",*new_offsets,""))
            methods.append((heading,reheaded,count,widened,empty_sha))
        cls.original="\n".join(old)
        cls.rebuilt="\n".join(new)
        cls.pinned=tuple(methods)

    def test_all_synthetic_methods_and_178_legal_widenings(self):
        result=verify_unified_disassembly(
            self.original,self.rebuilt,expected=self.pinned)
        self.assertEqual(14,result["verified_original_JVM_methods"])
        self.assertEqual(4314,result["verified_original_JVM_instructions"])
        self.assertEqual(
            178,result["allowlisted_ldc_to_ldc_w_encoding_changes"])
        self.assertFalse(result["whole_v309_client_compiled"])
        self.assertFalse(result["original_game_code_executed"])

    def test_changed_opcode_or_constant_rejected(self):
        for mutant in (
            self.rebuilt.replace("ldc_w int 3","iconst_1",1),
            self.rebuilt.replace("ldc_w int 3","ldc_w int 4",1),
            self.rebuilt.replace("nop ","pop ",1),
        ):
            with self.subTest(sample=mutant[:25]):
                with self.assertRaises(R221SingleClassParityError):
                    verify_unified_disassembly(
                        self.original,mutant,expected=self.pinned)

    def test_extra_or_missing_method_row_rejected(self):
        with self.assertRaises(R221SingleClassParityError):
            verify_unified_disassembly(
                self.original,self.rebuilt,
                expected=self.pinned[:-1]+(self.pinned[0],))

    def test_alias_digests_fail_closed(self):
        rows=list(self.pinned)
        a,b,n,w,d=rows[0]
        rows[0]=(a,b,n,w,"0"*64)
        with self.assertRaises(R221SingleClassParityError):
            verify_unified_disassembly(
                self.original,self.rebuilt,expected=tuple(rows))

    def test_pinned_original_binary_source_class_sha_required(self):
        with self.assertRaises(R221SingleClassParityError):
            verify_private_unified_class(
                "/nonexistent-original-client.jar",
                "/nonexistent-source.java",
                "/nonexistent-candidate.class")

    def test_parser_rejects_unidentified_methods(self):
        with self.assertRaises(R221SingleClassParityError):
            parse_method(self.original,"public void fake();")


if __name__=="__main__":
    unittest.main()
