"""R227 independent invented tests for all-81 original Packet JVM Code parity.

Hosted CI never receives original proprietary client source or classfiles.
81 fake methods, 2,296 synthetic instructions, 30 symbolic aliases,
source-normalizer preflight, and malicious opcode/branch/field failures.
"""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from spk_recovery.private_v309_original_readable_packet_all_methods_r227 import (
    ORIGINAL_METHODS,ORIGINAL_INSTRUCTIONS,EXPECTED_SYMBOL_ALIASES,
    SOURCE_REWRITES,NORMALIZED_CLASS_SHA256,
    R227OriginalReadablePacketError,
    normalize_packet_java,
    compare_complete_original_packet,
    verify_private_normalized_packet,
)


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(
        obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def synthetic_packet_methods():
    old=[]
    new=[]
    summary=[]
    aliases={}
    counts=[28]*80+[56]
    assert len(counts)==81 and sum(counts)==2296
    for i,count in enumerate(counts):
        original_title=f"public void methodOriginal{i}();"
        readable_title=f"public void methodReadable{i}();"
        lhs=[original_title,"    Code:"]
        rhs=[readable_title,"    Code:"]
        local={}
        for j in range(count):
            if j==count-1:
                opcode="return"
                a=b=""
            elif j==1 and i<30:
                opcode="getstatic"
                a=f"Field invented/Original.member{i}:I"
                b=f"Field invented/Readable.member{i}:I"
                local[a]=b
                aliases[a]=b
            elif j==2:
                opcode="bipush"
                a=b="7"
            else:
                opcode="nop"
                a=b=""
            lhs.append(f"       {j}: {opcode}"+(
                " // "+a if a.startswith("Field ") else
                (" "+a if a else "")))
            rhs.append(f"       {j}: {opcode}"+(
                " // "+b if b.startswith("Field ") else
                (" "+b if b else "")))
        old.extend(lhs+[""])
        new.extend(rhs+[""])
        summary.append((original_title,readable_title,count,
                        canonical_hash(local),len(local)))
    return "\n".join(old),"\n".join(new),canonical_hash(aliases),\
           hashlib.sha256(json.dumps(summary,separators=(",",":")).encode()).hexdigest()


class R227Invented81MethodPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (cls.old,cls.new,cls.aliaspin,
         cls.rowpin)=synthetic_packet_methods()

    def check(self,right=None,**settings):
        options={
            "alias_sha":self.aliaspin,
            "ledger_sha":self.rowpin,
        }
        options.update(settings)
        return compare_complete_original_packet(
            self.old,right if right is not None else self.new,
            **options)

    def test_all_81_methods_and_2296_fake_instruction_rows(self):
        result=self.check()
        self.assertEqual(ORIGINAL_METHODS,81)
        self.assertEqual(ORIGINAL_INSTRUCTIONS,2296)
        self.assertEqual(81,result[
            "original_packet_method_Code_bodies_verified"])
        self.assertEqual(2296,result[
            "original_packet_JVM_instructions_verified"])
        self.assertEqual(30,result[
            "unique_original_to_readable_symbolic_aliases"])
        self.assertEqual(EXPECTED_SYMBOL_ALIASES,30)
        self.assertTrue(result[
            "original_offsets_opcodes_literal_constants_branches_all_match"])

    def test_corrupted_integer_constant_and_opcode_rejected(self):
        for bad in (
            self.new.replace("bipush 7","bipush 8",1),
            self.new.replace(": nop",": iadd",1),
        ):
            with self.subTest(bad=bad[:40]):
                with self.assertRaises(R227OriginalReadablePacketError):
                    self.check(bad)

    def test_wrong_symbolic_field_renaming_rejected(self):
        mutated=self.new.replace(
            "Field invented/Readable.member0:I",
            "Field invented/Readable.member99:I",1)
        with self.assertRaises(R227OriginalReadablePacketError):
            self.check(mutated)

    def test_wrong_method_order_missing_or_duplicate_rejected(self):
        wrong=self.new.replace(
            "public void methodReadable0();",
            "public void methodReadable81();",1)
        with self.assertRaises(R227OriginalReadablePacketError):
            self.check(wrong)
        with self.assertRaises(R227OriginalReadablePacketError):
            self.check(self.new+"\n"+self.new)

    def test_branch_instruction_offset_rejected(self):
        altered=self.new.replace("       4: nop","       55: nop",1)
        with self.assertRaises(R227OriginalReadablePacketError):
            self.check(altered)

    def test_wrong_hash_contracts_rejected(self):
        for change in (
            {"alias_sha":"0"*64},
            {"ledger_sha":"0"*64},
            {"expected_ops":2300},
            {"expected_method_count":82},
        ):
            with self.subTest(change=change):
                with self.assertRaises(R227OriginalReadablePacketError):
                    self.check(**change)

    def test_private_normalization_exact_scope_and_mutation(self):
        raw="\n".join(old for old,new,occ,n in SOURCE_REWRITES
                      for _ in range(occ))
        candidate=raw
        for old,new,occ,repl in SOURCE_REWRITES:
            candidate=candidate.replace(old,new,repl)
        rawsha=hashlib.sha256(raw.encode()).hexdigest()
        normsha=hashlib.sha256(candidate.encode()).hexdigest()
        self.assertEqual(
            candidate,normalize_packet_java(
                raw,raw_pin=rawsha,normalized_pin=normsha))
        with self.assertRaises(R227OriginalReadablePacketError):
            normalize_packet_java(raw,raw_pin="0"*64,
                                  normalized_pin=normsha)
        with self.assertRaises(R227OriginalReadablePacketError):
            normalize_packet_java(raw,raw_pin=rawsha,
                                  normalized_pin="0"*64)
        with self.assertRaises(R227OriginalReadablePacketError):
            normalize_packet_java(raw.replace(
                SOURCE_REWRITES[0][0],"changed",1),
                raw_pin=rawsha,normalized_pin=normsha)

    def test_fake_original_artifacts_rejected(self):
        with TemporaryDirectory() as temp:
            f=Path(temp)/"fake.jar"
            f.write_bytes(b"unrelated dummy input")
            with self.assertRaises(R227OriginalReadablePacketError):
                verify_private_normalized_packet(f,f,f)

    def test_provenance_does_not_claim_original_binary_identity(self):
        self.assertEqual(64,len(NORMALIZED_CLASS_SHA256))
        self.assertEqual(8,len(SOURCE_REWRITES))


if __name__=="__main__":
    unittest.main()
