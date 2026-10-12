"""R93 exact final method source aggregation without unproven runtime claims."""
import unittest
from spk_recovery.private_ten_method_owner_assembly import (
    OriginalTenMethodAssemblyError,integrate_exact_tenth_method,
)

class AllTenMethodAssemblyTests(unittest.TestCase):
    def fixture(self):
        profile={"class_access":0x0031,"fields":[{} for _ in range(126)],
                 "methods":[{} for _ in range(10)]}
        prior=("package p;\npublic final class Owner {\n"
               "public static boolean a(){return false;}\n"
               "public static boolean b(){return false;}\n"
               "public static boolean c(){return a();}\n"
               "private static void save(){}\n}\n")
        last='    public static void register(){p.Register.add("save",p.Owner::save);}\n'
        proof={"original_owner_methods_still_unrecovered":1,
               "original_total_method_declarations":10}
        return profile,prior,last,proof
    def test_all_ten_source_forms_after_exact_last_method(self):
        p,old,new,proof=self.fixture()
        obj=integrate_exact_tenth_method(p,old,new,proof)
        src=obj["private_ten_method_java_source_candidate"]
        self.assertIn('p.Register.add("save",p.Owner::save)',src)
        self.assertEqual(obj["original_unrecovered_owner_method_source_form_count"],0)
        self.assertFalse(obj["complete_original_owner_java9_compiled_and_accepted"])
        self.assertTrue(src.endswith("}\n"))
    def test_missing_method_or_wrong_original_inventory_rejected(self):
        p,old,new,proof=self.fixture()
        proof["original_owner_methods_still_unrecovered"]=2
        with self.assertRaisesRegex(OriginalTenMethodAssemblyError,
                                    "NINE_METHOD_SOURCE_INVENTORY"):
            integrate_exact_tenth_method(p,old,new,proof)
        p,old,new,proof=self.fixture()
        p["methods"].pop()
        with self.assertRaisesRegex(OriginalTenMethodAssemblyError,
                                    "TEN_METHOD_PROFILE_CHANGED"):
            integrate_exact_tenth_method(p,old,new,proof)
    def test_forged_lambda_or_nine_method_source_rejected(self):
        p,old,new,proof=self.fixture()
        with self.assertRaisesRegex(OriginalTenMethodAssemblyError,
                                    "FINAL_LAMBDA_SOURCE_NOT_RECOGNIZED"):
            integrate_exact_tenth_method(p,old,"public static void other(){}",proof)
        p,old,new,proof=self.fixture()
        with self.assertRaisesRegex(OriginalTenMethodAssemblyError,
                                    "NINE_METHOD_SOURCE_NOT_RECOGNIZED"):
            integrate_exact_tenth_method(p,old.replace("public final class","class"),
                                         new,proof)

if __name__=="__main__":
    unittest.main()
