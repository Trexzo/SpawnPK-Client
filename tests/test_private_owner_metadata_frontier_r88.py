"""R88: exact declaration set-difference accounting without runtime claims."""
import copy
import unittest
from spk_recovery.private_owner_metadata_frontier import (
    OriginalOwnerFrontierError, private_owner_frontier,
)

def profile(fields, methods):
    return {
        "internal_name":"p/Owner","classfile_major":53,
        "super_name":"java/lang/Object","class_access":0x0021,
        "signature":None,"interfaces":[],
        "fields":[{"name":name,"descriptor":desc,"access":access,
                   "signature":None,"constant_value":None}
                  for name,desc,access in fields],
        "methods":[{"name":name,"descriptor":desc,"access":access,
                    "signature":None} for name,desc,access in methods],
    }

class PrivateOwnerFrontierTests(unittest.TestCase):
    def test_missing_fields_methods_nested_class_are_precisely_accounted(self):
        orig=profile([("a","I",0x0009),("b","Z",0x0009),("c","I",0x0009)],
                     [("<init>","()V",1),("<clinit>","()V",8),
                      ("load","()V",9),("save","()V",10)])
        cand=profile([("a","I",0x0009),("b","Z",0x0001)],
                     [("<init>","()V",1),("load","()V",9)])
        report=private_owner_frontier(
            orig,cand,{"p/Owner$A.class","p/Owner$B.class"},
            {"p/Owner$A.class"})
        self.assertEqual(report["original_fields"],3)
        self.assertEqual(report["candidate_fields"],2)
        self.assertEqual(report["missing_original_fields"],1)
        self.assertEqual(report["shared_field_declaration_mismatches"],1)
        self.assertEqual(report["original_methods"],4)
        self.assertEqual(report["candidate_methods"],2)
        self.assertEqual(report["missing_original_methods"],2)
        self.assertTrue(report["original_owner_clinit_present"])
        self.assertFalse(report["candidate_owner_clinit_present"])
        self.assertEqual(report["missing_original_nested_classes"],1)
        self.assertFalse(report["complete_owner_method_implementation_parity_proven"])
        private=report["private_missing_and_drift_identities"]
        self.assertEqual(private["missing_original_fields"],[("c","I")])
        self.assertEqual(private["missing_original_methods"],
                         [("<clinit>","()V"),("save","()V")])
    def test_extra_candidate_and_duplicate_declarations_measured_or_rejected(self):
        orig=profile([("a","I",0x0009)],[("load","()V",9)])
        cand=profile([("a","I",0x0009),("x","Z",0x0009)],
                     [("load","()V",9),("invented","()V",9)])
        a=private_owner_frontier(orig,cand,set(),set())
        self.assertEqual(a["extra_candidate_fields"],1)
        self.assertEqual(a["extra_candidate_methods"],1)
        bad=copy.deepcopy(cand)
        bad["fields"].append(dict(bad["fields"][0]))
        with self.assertRaisesRegex(OriginalOwnerFrontierError,
                                    "DUPLICATE_CANDIDATE_FIELD_DECLARATION"):
            private_owner_frontier(orig,bad,set(),set())
    def test_wrong_class_identity_fails_closed(self):
        orig=profile([],[])
        candidate=profile([],[])
        candidate["internal_name"]="p/Other"
        with self.assertRaisesRegex(OriginalOwnerFrontierError,
                                    "ORIGINAL_CANDIDATE_OWNER_NAME_DIFFERENT"):
            private_owner_frontier(orig,candidate,set(),set())

if __name__ == "__main__":
    unittest.main()
