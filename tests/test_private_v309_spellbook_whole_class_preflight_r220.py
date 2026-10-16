"""R220 regression gate: verify *all* 14/14 original method evidence contracts.

No original-derived source or JAR is present or executed in public CI.
This test does not claim whole-class source-only compilation.
"""
import unittest
from spk_recovery.private_v309_spellbook_whole_class_preflight_r220 import (
    EXPECTED,ROWS,NONVERBATIM,MODULES,
    R220IntegrationEvidenceError,verify_manifest,
)

class R220EvidenceClosureTests(unittest.TestCase):
    def test_all_original_methods_once_and_4314_instructions(self):
        a=verify_manifest()
        self.assertEqual(14,a["original_JVM_methods_inventoried"])
        self.assertEqual(4314,a["original_JVM_instructions_inventoried"])
        self.assertEqual(8,len(a["individual_proof_modules_checked"]))
        self.assertFalse(a["single_whole_class_Javac_compiled"])
        self.assertFalse(a["source_only_original_client_compiled"])
        self.assertEqual(2,a["compiler_normalized_method_count"])

    def test_duplication_and_omission_rejected(self):
        for rows in (ROWS[:-1],ROWS+(ROWS[-1],),
                     ROWS[:-1]+(ROWS[0],)):
            with self.subTest(count=len(rows)):
                with self.assertRaises(R220IntegrationEvidenceError):
                    verify_manifest(rows=rows,load_modules=False)

    def test_changed_original_instruction_count_rejected(self):
        rows=list(ROWS)
        key,method,count=rows[0]
        rows[0]=(key,method,count+1)
        with self.assertRaises(R220IntegrationEvidenceError):
            verify_manifest(rows=tuple(rows),load_modules=False)

    def test_wrong_method_pair_or_extra_batch_rejected(self):
        rows=list(ROWS)
        batch,method,count=rows[1]
        rows[1]=("r219",method,count)
        with self.assertRaises(R220IntegrationEvidenceError):
            verify_manifest(rows=tuple(rows),load_modules=False)
        with self.assertRaises(R220IntegrationEvidenceError):
            verify_manifest(modules={**MODULES,"r999":"fake"},load_modules=False)

    def test_unspecified_compiler_rewrites_rejected(self):
        for aliases in ({}, {"n()V":"unknown"}, {
            **NONVERBATIM,"l()V":"unapproved"}):
            with self.assertRaises(R220IntegrationEvidenceError):
                verify_manifest(nonverbatim=aliases,load_modules=False)

if __name__=="__main__":
    unittest.main()
