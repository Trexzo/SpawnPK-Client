"""R91 nine-method source stitching, original R60-count and tamper vetoes."""
import unittest
from spk_recovery.private_nine_owner_method_assembly import (
    ShortOwnerAssemblyError, integrate_short_owner_methods,
)

def fixture():
    original={"class_access":0x0031,"fields":[{} for _ in range(126)],
              "methods":[{} for _ in range(10)]}
    old="package p;\npublic final class Owner {\n    public static void load() {}\n    private static void save() {}\n}\n"
    short=("// PRIVATE: strictly proved original JVM short method source forms.\n"
           "// Remaining methods must NOT be fabricated or defaulted.\n"
           "    public Owner() {}\n"
           "    public static boolean a() { return false; }\n"
           "    public static boolean b() { return false; }\n"
           "    public static boolean c() { return a(); }\n"
           "    public static void toggle(boolean flag) {}\n"
           "    public static void arrayWriter() {}\n")
    proof={"bounded_short_method_sources":6,
           "remaining_methods_unreconstructed":3,
           "original_total_jvm_methods":10,
           "exact_original_array_element_writes":10}
    return original,old,short,proof

class NineMethodAssemblyTests(unittest.TestCase):
    def test_preserves_original_owner_and_appends_six_short_method_forms(self):
        o,owner,short,proof=fixture()
        p=integrate_short_owner_methods(o,owner,short,proof)
        content=p["private_nine_of_ten_method_owner_candidate_source"]
        self.assertEqual(content.count("public static boolean "),3)
        self.assertEqual(content.count("public static void "),3)
        self.assertEqual(content.count("private static void "),1)
        self.assertIn("public Owner() {}",content)
        self.assertTrue(content.endswith("}\n"))
        self.assertEqual(p["original_owner_methods_still_unrecovered"],1)
        self.assertFalse(p["original_complete_owner_source_compiled"])
    def test_changed_r60_method_count_or_original_owner_veto(self):
        o,owner,short,proof=fixture()
        proof["bounded_short_method_sources"]=5
        with self.assertRaisesRegex(ShortOwnerAssemblyError,
                                    "SIX_SHORT_METHOD_SOURCE_PROOF"):
            integrate_short_owner_methods(o,owner,short,proof)
        o,owner,short,proof=fixture()
        o["methods"].pop()
        with self.assertRaisesRegex(ShortOwnerAssemblyError,
                                    "TEN_METHOD_OWNER"):
            integrate_short_owner_methods(o,owner,short,proof)
    def test_unproved_short_method_fragment_veto(self):
        o,owner,short,proof=fixture()
        with self.assertRaisesRegex(ShortOwnerAssemblyError,
                                    "FRAGMENT_SHAPE_DRIFT"):
            integrate_short_owner_methods(o,owner,short.replace(
                "PRIVATE: strictly proved","UNPROVEN:"),proof)

if __name__=="__main__":
    unittest.main()
