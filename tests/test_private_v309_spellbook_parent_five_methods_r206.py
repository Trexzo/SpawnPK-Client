"""R206 synthetic Java9 source-only five-method parent bytecode proof.

All fixtures are invented; nothing is copied from SpawnPK. Two original
synthetic enum types and six separately marked compiler helper classes
compile from sources. Negative tests alter parent method Code, not the
original binary, and prove the verifier rejects mutations.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_spellbook_parent_five_methods_r206 import (
    R206OriginalSpellbookPartialError,
    verify_pinned_spellbook_parent_five_methods,
    SELECTED_METHODS,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R206UnrelatedFiveMethods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK required")
        cls.tmp=TemporaryDirectory(prefix="r206-invented-java-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.parent="invented/Main"
        cls.category="invented/Category"
        cls.mode="invented/Mode"
        cls.helpers=(
            "invented/Base","invented/Widget","invented/Settings",
            "invented/Styles","invented/Icon","invented/Client")
        cls.code=(
            "package invented;\n"
            "import java.util.List;\n"
            "import java.util.ArrayList;\n"
            "public class Main extends Base {\n"
            " private static boolean enabled;\n"
            " private static boolean toggle;\n"
            " private static int previous=-1;\n"
            " private static final List<Category> categories=new ArrayList<>();\n"
            " public static void h(){enabled=!enabled;j();i();Settings.persist();}\n"
            " public static void i(){\n"
            "  if(enabled){Widget.items[10].x=20;}\n"
            "  else{Widget.items[11].x=30;}\n"
            " }\n"
            " public static void j(){\n"
            "  for(Mode mode:Mode.values())a(mode);\n"
            " }\n"
            " public static void m(int id){\n"
            "  if(id==300){\n"
            "   if(Client.ids[0]!=305)previous=Client.ids[0];\n"
            "   k();Client.ids[0]=305;\n"
            "  }\n"
            "  if(id==301 && previous!=-1){j();Client.ids[0]=previous;}\n"
            "  if(id==302 || id==303 || id==304){\n"
            "   Category c=Category.A;\n"
            "   if(id==303)c=Category.B;\n"
            "   if(id==304)c=Category.C;\n"
            "   if(categories.contains(c))categories.remove(c);\n"
            "   else categories.add(c);\n"
            "   k();Settings.persist();\n"
            "  }\n"
            "  if(id==306){toggle=!toggle;k();Settings.persist();}\n"
            " }\n"
            " public static void k(){\n"
            "  Widget.items[20].icon=categories.contains(Category.A)"
            "?Styles.on:Styles.off;\n"
            "  Widget.items[21].icon=categories.contains(Category.B)"
            "?Styles.on:Styles.off;\n"
            "  Widget.items[22].icon=categories.contains(Category.C)"
            "?Styles.on:Styles.off;\n"
            "  Widget.items[23].icon=toggle?Styles.on:Styles.off;\n"
            " }\n"
            " public static void a(Mode ignored){}\n"
            "}\n"
        )
        cls.real={
            cls.category:"package invented; public enum Category {A,B,C;}\n",
            cls.mode:"package invented; public enum Mode {X,Y,Z;}\n",
        }
        cls.fake={
            "invented/Base":"package invented; public class Base {}\n",
            "invented/Widget":(
                "package invented; public class Widget {"
                "public static Widget[] items; public int x;"
                "public Icon icon;}\n"),
            "invented/Settings":(
                "package invented; public class Settings {"
                "public static void persist(){}}\n"),
            "invented/Styles":(
                "package invented; public class Styles {"
                "public static Icon on,off;}\n"),
            "invented/Icon":"package invented; public class Icon {}\n",
            "invented/Client":(
                "package invented; public class Client {"
                "public static int[] ids;}\n"),
        }
        all_sources={cls.parent:cls.code,**cls.real,**cls.fake}
        files=[]
        for owner,body in all_sources.items():
            dest=cls.root/"src"/(owner+".java")
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(body,encoding="utf-8")
            files.append(str(dest))
        out=cls.root/"classes"
        empty=cls.root/"empty"
        out.mkdir();empty.mkdir()
        p=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),*files],
            capture_output=True,text=True,timeout=90,check=False)
        if p.returncode:
            raise AssertionError(
                "synthetic unrelated Java9 source did not compile: "+
                p.stderr.decode(errors="replace"))
        original=(out/(cls.parent+".class")).read_bytes()
        cls.original_class_sha256=hashlib.sha256(original).hexdigest()
        cls.jar=cls.root/"synthetic-original.jar"
        with ZipFile(cls.jar,"w",ZIP_DEFLATED) as z:
            z.writestr(cls.parent+".class",original)
        profile=profile_class_field_accesses(original)
        cls.original_methods=len(profile["methods"])
        cls.counts={
            (m["name"],m["descriptor"]):len(m["instructions"])
            for m in profile["methods"]
            if (m["name"],m["descriptor"]) in SELECTED_METHODS}
        cls.parent_zip=cls.pack("parent.zip",{cls.parent:cls.code})
        cls.category_zip=cls.pack("category.zip",{
            cls.category:cls.real[cls.category]})
        cls.mode_zip=cls.pack("mode.zip",{
            cls.mode:cls.real[cls.mode]})
        cls.helpers_zip=cls.pack("fake-helpers.zip",cls.fake)

    @classmethod
    def pack(cls,name,sources):
        f=cls.root/name
        with ZipFile(f,"w",ZIP_DEFLATED) as z:
            for owner,body in sorted(sources.items()):
                z.writestr("client/src/main/java/"+owner+".java",body)
        return f

    def verify(self,source=None,helpers=None,**updates):
        source=source or self.parent_zip
        helpers=helpers or self.helpers_zip
        params={
            "original_jar_sha256":sha(self.jar),
            "original_owner":self.parent,
            "original_class_sha256":self.original_class_sha256,
            "original_method_count":self.original_methods,
            "parent_source_sha256":sha(source),
            "category_owner":self.category,
            "category_source_sha256":sha(self.category_zip),
            "mode_owner":self.mode,
            "mode_source_sha256":sha(self.mode_zip),
            "compiler_helpers_sha256":sha(helpers),
            "helper_owners":self.helpers,
            "selected_method_counts":self.counts,
        }
        params.update(updates)
        return verify_pinned_spellbook_parent_five_methods(
            self.jar,source,self.category_zip,self.mode_zip,
            helpers,**params)

    def test_all_five_selected_unrelated_method_codes(self):
        result=self.verify()
        self.assertEqual(5,result[
            "fully_matched_original_selected_method_bodies"])
        self.assertEqual(sum(self.counts.values()),
                         result["original_jvm_instructions_exactly_verified"])
        self.assertTrue(result[
            "original_method_abi_offsets_and_symbols_preserved"])
        self.assertFalse(result["original_parent_full_field_inventory_verified"])
        self.assertFalse(result["compiler_only_helper_sources_original"])
        self.assertFalse(result["whole_original_client_compiles"])

    def test_changed_button_id_rejected(self):
        candidate=self.pack("changed-button.zip",{
            self.parent:self.code.replace("id==303","id==307")})
        with self.assertRaises(R206OriginalSpellbookPartialError):
            self.verify(source=candidate)

    def test_changed_icon_state_rejected(self):
        candidate=self.pack("changed-icon.zip",{
            self.parent:self.code.replace(
                "?Styles.on:Styles.off","?Styles.off:Styles.on",1)})
        with self.assertRaises(R206OriginalSpellbookPartialError):
            self.verify(source=candidate)

    def test_changed_filter_category_rejected(self):
        candidate=self.pack("changed-category.zip",{
            self.parent:self.code.replace(
                "Category c=Category.A","Category c=Category.B")})
        with self.assertRaises(R206OriginalSpellbookPartialError):
            self.verify(source=candidate)

    def test_bad_input_digest_and_selected_count_rejected(self):
        for changed in (
            {"original_jar_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"parent_source_sha256":"0"*64},
            {"category_source_sha256":"0"*64},
            {"mode_source_sha256":"0"*64},
            {"compiler_helpers_sha256":"0"*64},
            {"selected_method_counts":{
                **self.counts,("k","()V"):self.counts[("k","()V")]+1}},
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(R206OriginalSpellbookPartialError):
                    self.verify(**changed)

    def test_missing_support_class_rejected(self):
        missing=self.pack(
            "missing-helper.zip",
            {owner:body for owner,body in self.fake.items()
             if owner!="invented/Styles"})
        with self.assertRaises(R206OriginalSpellbookPartialError):
            self.verify(helpers=missing)


if __name__=="__main__":
    unittest.main()
