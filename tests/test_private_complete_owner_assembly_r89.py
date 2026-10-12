"""R89: R59 shell plus R80/R85 method bodies, zero Java/source guessing."""
import unittest
from spk_recovery.private_complete_owner_assembly import (
    OriginalOwnerAssemblyError, stitch_original_owner_source,
)

def fixture():
    p={"class_access":0x0031,
       "fields":[{"name":"field"+str(i),"descriptor":"I","access":9}
                 for i in range(126)],
       "methods":[
           {"name":"load","descriptor":"()V","access":9,
            "instructions":[{} for _ in range(697)]},
           {"name":"save","descriptor":"()V","access":10,
            "instructions":[{} for _ in range(364)]}]}
    shell=("// PRIVATE original JVM declaration and initializer source shell.\n"
           "// Original methods / nested enums / exact runtime unverified.\n"
           "package p;\npublic final class Owner {\n"
           "    static { System.out.println(1); }\n}\n")
    return p,shell

class OriginalOwnerAssemblyTests(unittest.TestCase):
    def test_preserves_exact_r59_shell_and_adds_two_verified_method_wrappers(self):
        profile,shell=fixture()
        p=stitch_original_owner_source(
            profile,shell,"try { int x=1; } catch (Exception ignored) {}",
            "try { int y=1; } catch (Exception ignored) {}",
            "load","save")
        src=p["private_complete_owner_java_candidate"]
        self.assertTrue(src.startswith(shell[:shell.rfind("}")]))
        self.assertEqual(src.count("public static void load()"),1)
        self.assertEqual(src.count("private static void save()"),1)
        self.assertTrue(src.endswith("}\n"))
        self.assertFalse(p["both_methods_R87_replay_passed"])
    def test_changed_method_access_or_unproven_shell_rejected(self):
        profile,shell=fixture()
        profile["methods"][1]["access"]=9
        with self.assertRaisesRegex(OriginalOwnerAssemblyError,"PUBLIC_PRIVATE_STATIC"):
            stitch_original_owner_source(profile,shell,"try {}","try {}","load","save")
        profile,shell=fixture()
        with self.assertRaisesRegex(OriginalOwnerAssemblyError,"R59_OWNER_SHELL_STRUCTURE"):
            stitch_original_owner_source(profile,shell.replace(
                "PRIVATE original JVM declaration","UNKNOWN"),"try {}","try {}","load","save")
    def test_missing_jvm_instructions_and_duplicate_method_rejected(self):
        profile,shell=fixture()
        profile["methods"][0]["instructions"].pop()
        with self.assertRaisesRegex(OriginalOwnerAssemblyError,"EXPECTED_ORIGINAL_697_AND_364"):
            stitch_original_owner_source(profile,shell,"try {}","try {}","load","save")
        profile,shell=fixture()
        with self.assertRaisesRegex(OriginalOwnerAssemblyError,"LOADER_SAVER_NOT_UNIQUE"):
            stitch_original_owner_source(profile,shell,"try {}","try {}","load","load")

if __name__=="__main__":
    unittest.main()
