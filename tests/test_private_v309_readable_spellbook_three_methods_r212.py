"""R212 invented Java9 method Code parity + negative symbolic regression tests.

The tests compile unrelated toy source with 3 methods and an enum, never
SpawnPK source, and compare a deliberately renamed class's actual JVM
instructions, branch offsets, handlers and fields. This proves the public
comparison algorithm, not the real private JAR replay.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import unittest

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_readable_spellbook_three_methods_r212 import (
    R212ReadableSpellbookCodeError,
    audit_three_readable_method_code,
    extract_original_donor_method,
)


class R212UnrelatedThreeMethodSourceParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("javac required")
        cls.tmp=TemporaryDirectory(prefix="r212-invented-triple-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.original_body=(
            "package toy;\n"
            "import java.util.Arrays;\n"
            "public class Legacy {\n"
            "  static boolean active;\n"
            "  static int[] first,second;\n"
            "  public static void h(){active=!active;j();i();Util.save();}\n"
            "  public static void i(){\n"
            "    if(active){first[0]=5;second[1]=75;}\n"
            "    else{first=Arrays.copyOf(first,first.length);\n"
            "         second=Arrays.copyOf(second,second.length);}\n"
            "  }\n"
            "  public static void j(){for(Mode mode:Mode.values())a(mode);}\n"
            "  public static void a(Mode mode){}\n"
            "}\n"
        )
        cls.readable_body=(
            "package toy;\n"
            "import java.util.Arrays;\n"
            "public class Readable {\n"
            "  static boolean shown;\n"
            "  static int[] left,right;\n"
            "  public static void method1966(){shown=!shown;"
            "method236();method3153();Util.save();}\n"
            "  public static void method3153(){\n"
            "    if(shown){left[0]=5;right[1]=75;}\n"
            "    else{left=Arrays.copyOf(left,left.length);\n"
            "         right=Arrays.copyOf(right,right.length);}\n"
            "  }\n"
            "  public static void method236(){\n"
            "    for(Mode mode:Mode.values())method2689(mode);\n"
            "  }\n"
            "  public static void method2689(Mode mode){}\n"
            "}\n"
        )
        cls.original=cls.compile_java(
            "original","Legacy",cls.original_body)
        cls.rebuilt=cls.compile_java(
            "readable","Readable",cls.readable_body)
        old=profile_class_field_accesses(cls.original)
        cls.methods=[]
        for original,readable in (
            ("h","method1966"),("i","method3153"),("j","method236")):
            matched=[m for m in old["methods"]
                     if (m["name"],m["descriptor"])==(original,"()V")]
            if len(matched)!=1:
                raise AssertionError("Synthetic expected method missing")
            cls.methods.append((
                original,readable,len(matched[0]["instructions"]),None))
        cls.expected=sum(x[2] for x in cls.methods)
        cls.aliases={
            ("toy/Legacy","active","Z"):("toy/Readable","shown","Z"),
            ("toy/Legacy","first","[I"):("toy/Readable","left","[I"),
            ("toy/Legacy","second","[I"):("toy/Readable","right","[I"),
            ("toy/Legacy","i","()V"):
                ("toy/Readable","method3153","()V"),
            ("toy/Legacy","j","()V"):
                ("toy/Readable","method236","()V"),
            ("toy/Legacy","a","(Ltoy/Mode;)V"):
                ("toy/Readable","method2689","(Ltoy/Mode;)V"),
            ("toy/Util","save","()V"):("toy/Util","save","()V"),
            ("toy/Mode","values","()[Ltoy/Mode;"):
                ("toy/Mode","values","()[Ltoy/Mode;"),
            ("java/util/Arrays","copyOf","([II)[I"):
                ("java/util/Arrays","copyOf","([II)[I"),
        }

    @classmethod
    def compile_java(cls,label,name,code):
        root=cls.root/label
        java={
            "toy/"+name+".java":code,
            "toy/Util.java":(
                "package toy; public class Util {"
                "public static void save(){} }"),
            "toy/Mode.java":"package toy; public enum Mode {A,B,C;}",
        }
        paths=[]
        for rel,text in java.items():
            file=root/"src"/rel
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(text,encoding="utf-8")
            paths.append(str(file))
        out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        p=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),*paths],
            capture_output=True,text=True,timeout=60,check=False)
        if p.returncode:
            raise AssertionError(
                "Synthetic Java9 source failed: "+p.stderr)
        return (out/"toy"/(name+".class")).read_bytes()

    def check(self,compiled=None,**params):
        kwargs={
            "method_pairs":self.methods,
            "member_aliases":self.aliases,
            "expected_total":self.expected,
        }
        kwargs.update(params)
        return audit_three_readable_method_code(
            self.original,compiled or self.rebuilt,**kwargs)

    def test_full_invented_three_methods_match_jvm_code(self):
        proof=self.check()
        self.assertEqual(3,proof["selected_original_methods"])
        self.assertEqual(self.expected,proof[
            "matched_original_jvm_instructions"])
        self.assertTrue(proof[
            "all_original_method_code_under_named_aliases_equal"])
        self.assertFalse(proof[
            "unselected_spellbook_parent_methods_code_verified"])
        self.assertFalse(proof["original_client_game_code_executed"])

    def test_changed_branch_predicate_rejected(self):
        invalid=self.compile_java(
            "branch-mutation","Readable",
            self.readable_body.replace("if(shown)","if(!shown)"))
        with self.assertRaises(R212ReadableSpellbookCodeError):
            self.check(invalid)

    def test_wrong_original_member_alias_rejected(self):
        invalid={
            **self.aliases,
            ("toy/Legacy","active","Z"):
                ("toy/Readable","wrong","Z"),
        }
        with self.assertRaises(R212ReadableSpellbookCodeError):
            self.check(member_aliases=invalid)

    def test_changed_invocation_rejected(self):
        invalid=self.compile_java(
            "invocation-mutation","Readable",
            self.readable_body.replace(
                "method236();method3153()",
                "method3153();method236()"))
        with self.assertRaises(R212ReadableSpellbookCodeError):
            self.check(invalid)

    def test_changed_array_copy_expression_rejected(self):
        invalid=self.compile_java(
            "copy-mutation","Readable",
            self.readable_body.replace(
                "Arrays.copyOf(left,left.length)",
                "Arrays.copyOf(left,left.length+1)"))
        with self.assertRaises(R212ReadableSpellbookCodeError):
            self.check(invalid)

    def test_missing_method_and_wrong_total_rejected(self):
        with self.assertRaises(R212ReadableSpellbookCodeError):
            self.check(expected_total=self.expected+1)
        with self.assertRaises(R212ReadableSpellbookCodeError):
            self.check(method_pairs=[
                self.methods[0],self.methods[1],
                ("j","wrongMethod",self.methods[2][2],None)])

    def test_method_extract_requires_one_complete_source_body(self):
        sample=(
            "class A {\n"
            "public static void method1966(){if(true){return;}}\n"
            "}\n"
        )
        body=extract_original_donor_method(sample,"method1966")
        self.assertIn("if(true){return;}",body)
        with self.assertRaises(R212ReadableSpellbookCodeError):
            extract_original_donor_method(
                sample.replace("method1966","other"),"method1966")
        with self.assertRaises(R212ReadableSpellbookCodeError):
            extract_original_donor_method(
                sample.replace("return;}}\n}\n","return;}\n"),"method1966")


if __name__=="__main__":
    unittest.main()
