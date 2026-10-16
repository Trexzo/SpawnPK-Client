"""R210 synthetic deobfuscated base-widget JVM parity regression suite.

Invented toy.WidgetBase and readable UI Widget classes deliberately contain
11 JVM instructions / six method declarations. No original proprietary
Java code, JAR or runtime is present in hosted CI.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from spk_recovery.private_v309_readable_widget_source_parity_r210 import (
    R210OriginalReadableWidgetError,
    audit_readable_widget_classfiles,
)

class R210SyntheticReadableWidgetParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("javac required")
        cls.tmp=TemporaryDirectory(prefix="r210-toy-readable-widget-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.old_owner="fixture/old/Base"
        cls.readable_owner="fixture/ui/Widget"
        cls.owners={
            "fixture/old/Base":"fixture/ui/Widget",
            "fixture/old/Parent":"fixture/ui/WidgetComponent",
            "fixture/old/Font":"fixture/ui/Typeface",
        }
        cls.fields={
            ("a","[Lfixture/old/Font;"):
                ("fonts","[Lfixture/ui/Typeface;"),
            ("b","Z"):("visible","Z"),
        }
        cls.methods={
            ("<init>","([Lfixture/old/Font;)V"):
                ("<init>","([Lfixture/ui/Typeface;)V"),
            ("a","()V"):("register","()V"),
            ("a","(ILjava/lang/String;)V"):
                ("onMenuAction","(ILjava/lang/String;)V"),
            ("a","(I)V"):("onOptionClick","(I)V"),
            ("b","()V"):("close","()V"),
            ("c","()Z"):("isEnabled","()Z"),
        }
        cls.old_source=(
            "package fixture.old;\n"
            "public abstract class Base extends Parent {\n"
            " protected Font[] a;\n"
            " protected boolean b;\n"
            " public Base(Font[] typefaces){this.a=typefaces;}\n"
            " public abstract void a();\n"
            " public void a(int i,String str){}\n"
            " public void a(int i){}\n"
            " public void b(){}\n"
            " public boolean c(){return true;}\n"
            "}\n"
        )
        cls.new_source=(
            "package fixture.ui;\n"
            "public abstract class Widget extends WidgetComponent {\n"
            " protected Typeface[] fonts;\n"
            " protected boolean visible;\n"
            " public Widget(Typeface[] typefaces){this.fonts=typefaces;}\n"
            " public abstract void register();\n"
            " public void onMenuAction(int i,String str){}\n"
            " public void onOptionClick(int i){}\n"
            " public void close(){}\n"
            " public boolean isEnabled(){return true;}\n"
            "}\n"
        )
        cls.original=cls.compile_java(
            "original",cls.old_owner,cls.old_source,
            {
                "fixture/old/Parent":
                    "package fixture.old; public abstract class Parent {}",
                "fixture/old/Font":
                    "package fixture.old; public class Font {}",
            })
        cls.readable=cls.compile_java(
            "readable",cls.readable_owner,cls.new_source,
            {
                "fixture/ui/WidgetComponent":
                    "package fixture.ui; "
                    "public abstract class WidgetComponent {}",
                "fixture/ui/Typeface":
                    "package fixture.ui; public class Typeface {}",
            })

    @classmethod
    def compile_java(cls,label,owner,source,helpers):
        root=cls.root/label
        empty=root/"empty"
        out=root/"classes"
        empty.mkdir(parents=True,exist_ok=True)
        out.mkdir()
        java={owner:source,**helpers}
        paths=[]
        for classname,text in java.items():
            dest=root/"src"/(classname+".java")
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(text,encoding="utf-8")
            paths.append(str(dest))
        p=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),*paths],
            capture_output=True,text=True,timeout=60,check=False)
        if p.returncode:
            raise AssertionError("Invented Java9 compilation failed: "+p.stderr)
        emitted={x.relative_to(out).as_posix()
                 for x in out.rglob("*.class")}
        if emitted!={x+".class" for x in java}:
            raise AssertionError("Unexpected synthetic output inventory")
        return (out/(owner+".class")).read_bytes()

    def audit(self,candidate=None,**changes):
        kwargs={
            "owner_map":self.owners,
            "field_map":self.fields,
            "method_map":self.methods,
            "original_owner":self.old_owner,
            "readable_owner":self.readable_owner,
            "expected_original_sha256":
                hashlib.sha256(self.original).hexdigest(),
        }
        kwargs.update(changes)
        return audit_readable_widget_classfiles(
            self.original,candidate or self.readable,**kwargs)

    def rebuilt(self,label,text,helpers=None):
        return self.compile_java(label,self.readable_owner,text,
            helpers or {
                "fixture/ui/WidgetComponent":
                    "package fixture.ui;"
                    " public abstract class WidgetComponent {}",
                "fixture/ui/Typeface":
                    "package fixture.ui; public class Typeface {}",
            })

    def test_six_method_original_to_readable_code_mapping(self):
        result=self.audit()
        self.assertEqual(6,result["original_complete_methods_mapped"])
        self.assertEqual(5,result["original_concrete_methods_jvm_code_matched"])
        self.assertEqual(11,result["matched_original_decoded_jvm_instructions"])
        self.assertTrue(result[
            "existing_decompiled_widget_source_semantics_match_original"])
        self.assertTrue(result[
            "original_and_readable_superclass_edges_mapped"])
        self.assertFalse(result["original_game_code_executed"])
        self.assertFalse(result["full_original_client_compiled"])

    def test_changed_enabled_predicate_is_rejected(self):
        mutant=self.rebuilt(
            "false-enabled",self.new_source.replace(
                "return true;","return false;"))
        with self.assertRaises(R210OriginalReadableWidgetError):
            self.audit(mutant)

    def test_changed_field_access_flags_rejected(self):
        mutant=self.rebuilt(
            "private-field",self.new_source.replace(
                "protected Typeface[] fonts","private Typeface[] fonts"))
        with self.assertRaises(R210OriginalReadableWidgetError):
            self.audit(mutant)

    def test_modified_constructor_field_assignment_rejected(self):
        mutant=self.rebuilt(
            "missing-field-store",self.new_source.replace(
                "this.fonts=typefaces;","this.visible=true;"))
        with self.assertRaises(R210OriginalReadableWidgetError):
            self.audit(mutant)

    def test_changed_method_name_rejected(self):
        mutant=self.rebuilt(
            "renamed-method",self.new_source.replace(
                "void close()","void shutdown()"))
        with self.assertRaises(R210OriginalReadableWidgetError):
            self.audit(mutant)

    def test_missing_abstract_method_rejected(self):
        mutant=self.rebuilt(
            "changed-contract",self.new_source.replace(
                "public abstract void register();",
                "public abstract boolean register();"))
        with self.assertRaises(R210OriginalReadableWidgetError):
            self.audit(mutant)

    def test_superclass_edge_mutation_rejected(self):
        mutant=self.rebuilt(
            "wrong-super",self.new_source.replace(
                "extends WidgetComponent","extends WrongBase"),
            {
                "fixture/ui/WrongBase":
                    "package fixture.ui; public abstract class WrongBase {}",
                "fixture/ui/Typeface":
                    "package fixture.ui; public class Typeface {}",
            })
        with self.assertRaises(R210OriginalReadableWidgetError):
            self.audit(mutant)

    def test_wrong_member_map_and_wrong_original_sha_rejected(self):
        for overrides in (
            {"expected_original_sha256":"0"*64},
            {"field_map":{**self.fields,
                          ("b","Z"):("fonts","Z")}},
            {"method_map":{**self.methods,
                           ("c","()Z"):("close","()Z")}},
            {"owner_map":{**self.owners,
                          self.old_owner:"fixture/ui/Other"}},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(R210OriginalReadableWidgetError):
                    self.audit(**overrides)


if __name__=="__main__":
    unittest.main()
