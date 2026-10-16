"""R211 source-order parser tests with invented placeholder widget declarations.

No game source/JAR in CI. These tests establish that the proposed full
14-field/14-method crosswalk does not silently accept changed source
declaration order, types or required callsite fingerprints. Real method
JVM Code equivalence remains explicitly unaccepted.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED
import unittest

from spk_recovery.private_v309_spellbook_complete_crosswalk_r211 import (
    R211SpellbookCompleteCrosswalkError,
    FIELD_PAIR_ORDER,
    METHOD_PAIR_ORDER,
    DONOR_ANCHORS,
    inspect_readable_members,
    verify_pinned_original_spellbook_complete_crosswalk,
)


class R211SyntheticSpellbookSourceShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fields=[]
        for index,(_,name) in enumerate(FIELD_PAIR_ORDER):
            if index in (0,1):
                typename="int[]"
            elif index in (2,13):
                typename="int"
            elif index in (3,4):
                typename="boolean"
            elif index==5:
                typename="List<Class176>"
            else:
                typename="Sprite"
            qualifier="public" if index in (2,3,4,5) else "private"
            qualifier+=" static final" if index==5 else " static"
            initializer={
                "field3645":" = 0","field3646":" = true",
                "field3647":" = true",
                "field3648":" = new ArrayList()",
                "field3656":" = -1",
            }.get(name,"")
            fields.append(
                f"  {qualifier} {typename} {name}{initializer};\n")
        members=[]
        for (_,descriptor),(name,args) in METHOD_PAIR_ORDER:
            if name=="<clinit>":
                continue
            signature=(
                f"  public Class179({args} v) {{\n"
                if name=="Class179" else
                f"  public {'void' if name!='other' else 'int'} "
                f"{name}({args+' v' if args else ''}) {{\n"
            )
            # These unique, unrelated explanatory comments are only for
            # exercising the SOURCE structure gate, not compiling Java.
            tokens="\n".join("    // "+x for x in DONOR_ANCHORS.get(name,()))
            members.append(signature+tokens+"\n  }\n")
        cls.java=(
            "package invented;\n"
            "public class Class179 extends Widget {\n"
            +"".join(fields)+"\n"+"".join(members)+"}\n"
        )

    def test_full_fourteen_field_and_fourteen_method_candidate_inventory(self):
        result=inspect_readable_members(self.java)
        self.assertEqual(14,result["readable_member_field_count"])
        self.assertEqual(14,result[
            "readable_member_method_count_including_initializer"])
        self.assertEqual(14,result["original_to_deobf_method_candidate_count"])
        self.assertEqual(9,result[
            "critical_method_source_fingerprint_checks"])
        self.assertFalse(result["code_semantic_equivalence_proved"])

    def test_reordered_fields_and_duplicate_member_names_rejected(self):
        old="private static int[] field3643;\n  private static int[] field3644;"
        changed="private static int[] field3644;\n  private static int[] field3643;"
        self.assertIn(old,self.java)
        with self.assertRaises(R211SpellbookCompleteCrosswalkError):
            inspect_readable_members(self.java.replace(old,changed))
        with self.assertRaises(R211SpellbookCompleteCrosswalkError):
            inspect_readable_members(self.java.replace(
                "public void method1966()","public void method3153()"))

    def test_missing_field_and_invalid_method_parameters_rejected(self):
        with self.assertRaises(R211SpellbookCompleteCrosswalkError):
            inspect_readable_members(self.java.replace(
                "private static Sprite field3654;\n",""))
        with self.assertRaises(R211SpellbookCompleteCrosswalkError):
            inspect_readable_members(self.java.replace(
                "method2689(Class178 v)","method2689(int v)"))

    def test_missing_static_initializer_and_callsite_rejected(self):
        with self.assertRaises(R211SpellbookCompleteCrosswalkError):
            inspect_readable_members(
                self.java.replace("field3656 = -1;","field3656 = 0;"))
        with self.assertRaises(R211SpellbookCompleteCrosswalkError):
            inspect_readable_members(
                self.java.replace("Configuration.saveSettings();",
                                  "DifferentStore.saveSettings();"))

    def test_forged_original_jar_is_rejected(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            jar=root/"fake.jar"
            tree=root/"fake-source.zip"
            with ZipFile(jar,"w",ZIP_DEFLATED) as z:
                z.writestr("rs/n/c/ap.class",b"not original JVM")
            with ZipFile(tree,"w",ZIP_DEFLATED) as z:
                z.writestr(
                    "recovered-source/v309/src/"
                    "rs/interfaces/widgets/Class179.java",self.java)
            with self.assertRaisesRegex(
                R211SpellbookCompleteCrosswalkError,
                "R211_PINNED_ORIGINAL_BINARY_OR_DECOMPILED_SOURCE_ZIP_DRIFT"):
                verify_pinned_original_spellbook_complete_crosswalk(
                    jar,tree)


if __name__=="__main__":
    unittest.main()
