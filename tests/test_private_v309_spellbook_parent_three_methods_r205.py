"""R205 invented Java9 partial-source fixtures; no original game Java in CI.

Three static methods h/i/j are compared as full original-resolved JVM Code
against a synthetic JVM class independently compiled from unrelated logic.
Other original-owner methods are deliberately not accepted by this verifier.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_spellbook_parent_three_methods_r205 import (
    R205OriginalSpellbookPartialError,
    verify_pinned_original_spellbook_parent_methods,
    SELECTED_METHODS,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R205SyntheticParentSelectedMethods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK required")
        cls.tmp=TemporaryDirectory(prefix="r205-unrelated-java-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.parent="invented/Main"
        cls.mode="invented/Mode"
        cls.helpers=("invented/Base","invented/Widget","invented/Settings")
        cls.main_source=(
            "package invented;\n"
            "public class Main extends Base {\n"
            " private static boolean enabled;\n"
            " public static void h(){\n"
            "  enabled=!enabled;\n"
            "  j();i();Settings.persist();\n"
            " }\n"
            " public static void i(){\n"
            "  if(enabled){Widget.items[10].x=20;}\n"
            "  else {Widget.items[11].x=30;}\n"
            " }\n"
            " public static void j(){\n"
            "  for(Mode m:Mode.values()){a(m);}\n"
            " }\n"
            " public static void a(Mode ignored){}\n"
            "}\n"
        )
        cls.aux={
            cls.mode:(
                "package invented;\n"
                "public enum Mode { ONE, TWO, THREE; }\n"
            ),
            "invented/Base":(
                "package invented; public class Base {}\n"
            ),
            "invented/Widget":(
                "package invented;\n"
                "public class Widget {public static Widget[] items;\n"
                " public int x;}\n"
            ),
            "invented/Settings":(
                "package invented;\n"
                "public class Settings {public static void persist(){}}\n"
            ),
        }
        sources={cls.parent:cls.main_source,**cls.aux}
        src=cls.root/"original"
        paths=[]
        for owner,code in sources.items():
            p=src/(owner+".java")
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(code,encoding="utf-8")
            paths.append(str(p))
        out=cls.root/"classes"
        empty=cls.root/"empty"
        out.mkdir();empty.mkdir()
        c=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),*paths],
            capture_output=True,text=True,timeout=90,check=False)
        if c.returncode:
            raise AssertionError("Synthetic staged Java9 fixture compilation failed")
        raw=(out/(cls.parent+".class")).read_bytes()
        cls.original_class_sha256=hashlib.sha256(raw).hexdigest()
        cls.jar=cls.root/"invented-original.jar"
        with ZipFile(cls.jar,"w",ZIP_DEFLATED) as z:
            z.writestr(cls.parent+".class",raw)
        prof=profile_class_field_accesses(raw)
        cls.method_count=len(prof["methods"])
        cls.selected_total=sum(
            len(m["instructions"]) for m in prof["methods"]
            if (m["name"],m["descriptor"]) in SELECTED_METHODS)
        cls.partial_zip=cls.write_zip(
            "invented-main.zip",{cls.parent:cls.main_source})
        cls.mode_zip=cls.write_zip(
            "invented-mode.zip",{cls.mode:cls.aux[cls.mode]})
        cls.helper_zip=cls.write_zip(
            "invented-helper-declarations.zip",
            {owner:cls.aux[owner] for owner in cls.helpers})

    @classmethod
    def write_zip(cls,name,sources):
        p=cls.root/name
        with ZipFile(p,"w",ZIP_DEFLATED) as z:
            for owner,source in sorted(sources.items()):
                z.writestr("client/src/main/java/"+owner+".java",source)
        return p

    def verify(self,candidate=None,helpers=None,**changes):
        candidate=candidate or self.partial_zip
        helpers=helpers or self.helper_zip
        args={
            "original_sha256":sha(self.jar),
            "original_owner":self.parent,
            "original_class_sha256":self.original_class_sha256,
            "partial_source_sha256":sha(candidate),
            "mode_owner":self.mode,
            "mode_source_sha256":sha(self.mode_zip),
            "compiler_helpers_sha256":sha(helpers),
            "helper_owners":self.helpers,
            "original_method_count":self.method_count,
            "expected_instructions":self.selected_total,
        }
        args.update(changes)
        return verify_pinned_original_spellbook_parent_methods(
            self.jar,candidate,self.mode_zip,helpers,**args)

    def test_three_original_selected_methods_match_while_class_partial(self):
        result=self.verify()
        self.assertEqual(3,result["original_selected_method_count_verified"])
        self.assertEqual(self.selected_total,
                         result["original_selected_instructions_verified"])
        self.assertTrue(result[
            "original_method_code_offsets_and_symbolic_refs_match"])
        self.assertFalse(result["original_full_parent_method_set_rebuilt"])
        self.assertFalse(result["placeholder_original_parent_methods_accepted"])
        self.assertFalse(result["compiler_only_support_java_original"])
        self.assertFalse(result["entire_v309_client_compiles"])

    def test_changed_toggle_method_rejected(self):
        bad=self.write_zip("bad-toggle.zip",{
            self.parent:self.main_source.replace(
                "enabled=!enabled;","enabled=true;")})
        with self.assertRaises(R205OriginalSpellbookPartialError):
            self.verify(candidate=bad)

    def test_changed_widget_reference_rejected(self):
        bad=self.write_zip("bad-widget-index.zip",{
            self.parent:self.main_source.replace(
                "Widget.items[10]","Widget.items[12]")})
        with self.assertRaises(R205OriginalSpellbookPartialError):
            self.verify(candidate=bad)

    def test_changed_enum_dispatch_rejected(self):
        bad=self.write_zip("bad-dispatch.zip",{
            self.parent:self.main_source.replace("a(m);","i();")})
        with self.assertRaises(R205OriginalSpellbookPartialError):
            self.verify(candidate=bad)

    def test_wrong_original_source_and_helper_sha_pins_rejected(self):
        for opts in (
            {"original_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"partial_source_sha256":"0"*64},
            {"mode_source_sha256":"0"*64},
            {"compiler_helpers_sha256":"0"*64},
            {"original_method_count":self.method_count+1},
            {"expected_instructions":self.selected_total+1},
        ):
            with self.subTest(opts=opts):
                with self.assertRaises(R205OriginalSpellbookPartialError):
                    self.verify(**opts)

    def test_extra_or_missing_compiler_support_owner_rejected(self):
        missing=self.write_zip(
            "missing-helper.zip",
            {"invented/Base":self.aux["invented/Base"],
             "invented/Widget":self.aux["invented/Widget"]})
        with self.assertRaises(R205OriginalSpellbookPartialError):
            self.verify(helpers=missing)


if __name__=="__main__":
    unittest.main()
