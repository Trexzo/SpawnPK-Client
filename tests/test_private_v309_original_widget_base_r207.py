"""R207 entirely invented Java9 abstract widget-base JVM source tests.

No original proprietary Java or game binary in hosted CI. Method bytecode,
abstract member ABI, superclass identity, protected field types and source
ZIP pins are independently verified. Compiled classes are never executed.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from spk_recovery.private_v309_original_widget_base_r207 import (
    R207OriginalWidgetBaseError,
    verify_original_widget_base_source,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R207UnrelatedAbstractWidgetBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK required")
        cls.tmp=TemporaryDirectory(prefix="r207-invented-base-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.owner="invented/Base"
        cls.helpers=("invented/Component","invented/Font")
        cls.source=(
            "package invented;\n"
            "public abstract class Base extends Component {\n"
            " protected Font[] a;\n"
            " protected boolean b;\n"
            " public Base(Font[] fonts){this.a=fonts;}\n"
            " public abstract void a();\n"
            " public void a(int option,String text){}\n"
            " public void a(int option){}\n"
            " public void b(){}\n"
            " public boolean c(){return true;}\n"
            "}\n"
        )
        cls.fake={
            "invented/Component":(
                "package invented; public class Component {}\n"),
            "invented/Font":(
                "package invented; public class Font {}\n"),
        }
        pathlist=[]
        for owner,body in ((cls.owner,cls.source),*cls.fake.items()):
            path=cls.root/"source"/(owner+".java")
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(body,encoding="utf-8")
            pathlist.append(str(path))
        out=cls.root/"classes"
        empty=cls.root/"empty"
        out.mkdir();empty.mkdir()
        p=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),*pathlist],
            capture_output=True,text=True,timeout=90,check=False)
        if p.returncode:
            raise AssertionError("synthetic original Java source build failed")
        raw=(out/(cls.owner+".class")).read_bytes()
        cls.class_sha=hashlib.sha256(raw).hexdigest()
        cls.jar=cls.root/"invented.jar"
        with ZipFile(cls.jar,"w",ZIP_DEFLATED) as archive:
            archive.writestr(cls.owner+".class",raw)
        cls.source_zip=cls.pack("original-named-source.zip",{
            cls.owner:cls.source})
        cls.helper_zip=cls.pack("fake-declarations.zip",cls.fake)

    @classmethod
    def pack(cls,name,items):
        path=cls.root/name
        with ZipFile(path,"w",ZIP_DEFLATED) as archive:
            for owner,java in sorted(items.items()):
                archive.writestr("client/src/main/java/"+owner+".java",
                                 java)
        return path

    def verify(self,source=None,helpers=None,**overrides):
        source=source or self.source_zip
        helpers=helpers or self.helper_zip
        kwargs={
            "original_jar_sha256":sha(self.jar),
            "original_owner":self.owner,
            "original_class_sha256":self.class_sha,
            "source_sha256":sha(source),
            "helper_source_sha256":sha(helpers),
            "helper_owners":self.helpers,
        }
        kwargs.update(overrides)
        return verify_original_widget_base_source(
            self.jar,source,helpers,**kwargs)

    def test_full_original_unrelated_abstract_class_parity(self):
        r=self.verify()
        self.assertTrue(r["full_original_member_abi_verified"])
        self.assertTrue(r["complete_original_six_method_inventory_verified"])
        self.assertEqual(5,r["original_concrete_method_code_verified"])
        self.assertEqual(11,r["all_original_jvm_instructions_compared"])
        self.assertTrue(r["original_superclass_binary_name_matches"])
        self.assertFalse(r["original_external_support_java_recovered"])
        self.assertFalse(r["original_game_code_executed"])
        self.assertFalse(r["full_original_client_compiles"])

    def test_mutated_return_boolean_rejected(self):
        bad=self.pack("changed-boolean.zip",{
            self.owner:self.source.replace(
                "return true;","return false;")})
        with self.assertRaises(R207OriginalWidgetBaseError):
            self.verify(source=bad)

    def test_removed_constructor_field_assignment_rejected(self):
        bad=self.pack("changed-constructor.zip",{
            self.owner:self.source.replace(
                "this.a=fonts;","this.b=true;")})
        with self.assertRaises(R207OriginalWidgetBaseError):
            self.verify(source=bad)

    def test_abstract_method_signature_changed_rejected(self):
        bad=self.pack("changed-abstract-method.zip",{
            self.owner:self.source.replace(
                "abstract void a();","abstract void a(int x);")})
        with self.assertRaises(R207OriginalWidgetBaseError):
            self.verify(source=bad)

    def test_nonoriginal_superclass_change_rejected(self):
        bad=self.pack("wrong-super.zip",{
            self.owner:self.source.replace(
                "extends Component","extends Font")})
        with self.assertRaises(R207OriginalWidgetBaseError):
            self.verify(source=bad)

    def test_private_source_and_binary_sha_guards(self):
        for k in (
            {"original_jar_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"source_sha256":"0"*64},
            {"helper_source_sha256":"0"*64},
            {"expected_methods":7},
            {"expected_fields":3},
            {"expected_instructions":12},
        ):
            with self.subTest(k=k):
                with self.assertRaises(R207OriginalWidgetBaseError):
                    self.verify(**k)

    def test_missing_or_extra_fake_compiler_helper_rejected(self):
        for fake in (
            {"invented/Component":self.fake["invented/Component"]},
            {**self.fake,"invented/Third":
             "package invented; public class Third {}"},
        ):
            name="helper"+str(len(fake))+".zip"
            candidate=self.pack(name,fake)
            with self.subTest(helper_count=len(fake)):
                with self.assertRaises(R207OriginalWidgetBaseError):
                    self.verify(helpers=candidate)


if __name__=="__main__":
    unittest.main()
