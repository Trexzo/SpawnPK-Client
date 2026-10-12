"""R95: real Java 9 nested enum compilation, four-class gate and flatten veto."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile
from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.private_four_nested_enum_acceptance import (
    FourNestedEnumAcceptanceError, nested_entries,
    symbolic_innerclasses_table, check_four_nested_enums,
    replay_private_four_enum_gate,
)

@unittest.skipUnless(shutil.which("javac"),"javac required")
class FourNestedEnumTests(unittest.TestCase):
    def fixture(self,root):
        src=root/"source"/"p"/"Owner.java";src.parent.mkdir(parents=True)
        src.write_text(
            "package p; public final class Owner {"
            "public enum One {A,B} public enum Two {C,D}"
            "public enum Three {E,F} public enum Four {G,H}"
            "}",encoding="utf-8")
        classes=root/"classes";classes.mkdir()
        cmd=["javac","--release","9","-g:none","-proc:none",
             "-d",str(classes),str(src)]
        p=subprocess.run(cmd,capture_output=True,text=True)
        if p.returncode:raise AssertionError(p.stdout+p.stderr)
        jar=root/"original.jar"
        with ZipFile(jar,"w") as z:
            for path in classes.rglob("*.class"):
                z.write(path,path.relative_to(classes).as_posix())
        return jar,hashlib.sha256(jar.read_bytes()).hexdigest()
    def test_one_original_jar_all_four_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);jar,sha=self.fixture(root)
            out=root/"accepted"
            report=replay_private_four_enum_gate(
                jar,jar,"p/Owner.class",out,
                original_sha256=sha,candidate_sha256=sha)
            self.assertEqual(report["original_nested_enum_classes_verified"],4)
            self.assertTrue(report["symbolic_InnerClasses_tables_identical_all_four"])
            self.assertFalse(report["whole_client_runtime_equivalence_certified"])
            self.assertTrue((out/"all-four-nested-enums.aggregate.json").is_file())
    def test_missing_nested_candidate_fails_no_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);jar,sha=self.fixture(root)
            trimmed=root/"trimmed.jar"
            with ZipFile(jar) as a, ZipFile(trimmed,"w") as b:
                for name in a.namelist():
                    if name.endswith("Owner$Four.class"):continue
                    b.writestr(name,a.read(name))
            out=root/"blocked"
            with self.assertRaisesRegex(FourNestedEnumAcceptanceError,
                                        "EXPECTED_FOUR_ORIGINAL_NESTED_ENUM"):
                replay_private_four_enum_gate(
                    jar,trimmed,"p/Owner.class",out,
                    original_sha256=sha,
                    candidate_sha256=hashlib.sha256(trimmed.read_bytes()).hexdigest())
            self.assertFalse(out.exists())
    def test_flattened_original_innerclass_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);jar,sha=self.fixture(root)
            with ZipFile(jar) as z:
                entries=nested_entries(z.namelist(),"p/Owner.class")
                profiles={key:profile_jar_class(jar,key) for key in entries}
                attrs={key:symbolic_innerclasses_table(z.read(key)) for key in entries}
                owner_attrs=symbolic_innerclasses_table(z.read("p/Owner.class"))
            wrong=dict(attrs)
            wrong[entries[0]]=()
            with self.assertRaisesRegex(FourNestedEnumAcceptanceError,
                                        "ORIGINAL_INNERCLASSES_METADATA_DIFFER"):
                check_four_nested_enums(profiles,profiles,attrs,wrong,sha,owner_attrs,owner_attrs)
    def test_original_owner_innerclasses_omission_rejected_even_if_four_inner_classfiles_match(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);jar,sha=self.fixture(root)
            with ZipFile(jar) as z:
                entries=nested_entries(z.namelist(),"p/Owner.class")
                profiles={key:profile_jar_class(jar,key) for key in entries}
                attrs={key:symbolic_innerclasses_table(z.read(key)) for key in entries}
                original_owner_table=symbolic_innerclasses_table(z.read("p/Owner.class"))
            self.assertTrue(original_owner_table)
            with self.assertRaisesRegex(FourNestedEnumAcceptanceError,
                                        "ORIGINAL_OWNER_INNERCLASSES_METADATA_DIFFER"):
                check_four_nested_enums(profiles,profiles,attrs,attrs,sha,
                                        original_owner_table,())
            with self.assertRaisesRegex(FourNestedEnumAcceptanceError,
                                        "ORIGINAL_OWNER_INNERCLASSES_MISSING_NESTED_IDENTITIES"):
                check_four_nested_enums(profiles,profiles,attrs,attrs,sha,
                                        (("java/lang/invoke/MethodHandles$Lookup",
                                          "java/lang/invoke/MethodHandles","Lookup",0),),
                                        (("java/lang/invoke/MethodHandles$Lookup",
                                          "java/lang/invoke/MethodHandles","Lookup",0),))

    def test_tampered_enum_method_veto(self):
        with tempfile.TemporaryDirectory() as td:
            import copy
            root=Path(td);jar,sha=self.fixture(root)
            with ZipFile(jar) as z:
                entries=nested_entries(z.namelist(),"p/Owner.class")
                profiles={key:profile_jar_class(jar,key) for key in entries}
                attrs={key:symbolic_innerclasses_table(z.read(key)) for key in entries}
                owner_attrs=symbolic_innerclasses_table(z.read("p/Owner.class"))
            bad=copy.deepcopy(profiles)
            entry=entries[0]
            target=next(m for m in bad[entry]["methods"]
                        if m["name"]=="values")
            target["instructions"][0]["opcode"]="0x00"
            with self.assertRaisesRegex(FourNestedEnumAcceptanceError,
                                        "R49_ONE_OR_MORE"):
                check_four_nested_enums(profiles,bad,attrs,attrs,sha,owner_attrs,owner_attrs)

if __name__=="__main__":
    unittest.main()
