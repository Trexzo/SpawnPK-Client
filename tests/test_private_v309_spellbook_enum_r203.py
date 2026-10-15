"""R203 unrelated Java9 three-value enum regression, no SpawnPK Java in CI."""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from spk_recovery.private_v309_spellbook_enum_r203 import (
    R203OriginalSpellbookEnumError,
    verify_pinned_original_spellbook_filter_enum,
)
from spk_recovery.private_v309_signlink_nested_enum_r190 import (
    R190NestedDirectionEnumError,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R203UnrelatedSyntheticEnumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK required")
        cls.tmp=TemporaryDirectory(prefix="r203-synthetic-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.owner="invented/filter/Q"
        cls.baseline=(
            "package invented.filter;\n"
            "public enum Q {ALPHA, BETA, GAMMA;}\n"
        )
        cls.expanded=(
            "package invented.filter;\n"
            "public enum Q {\n"
            " ALPHA, BETA, GAMMA;\n"
            " public static final Q a=ALPHA;\n"
            " public static final Q b=BETA;\n"
            " public static final Q c=GAMMA;\n"
            "}\n"
        )
        old=cls.root/"original"
        p=old/"src"/(cls.owner+".java")
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(cls.baseline,encoding="utf-8")
        out=old/"classes"
        empty=old/"empty"
        out.mkdir();empty.mkdir()
        cmd=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),str(p)],
            capture_output=True,text=True,timeout=60,check=False)
        if cmd.returncode:
            raise AssertionError("Invented Java9 original fixture failed")
        binary=(out/(cls.owner+".class")).read_bytes()
        cls.original_class_sha=hashlib.sha256(binary).hexdigest()
        cls.jar=cls.root/"original-invented.jar"
        with ZipFile(cls.jar,"w",ZIP_DEFLATED) as z:
            z.writestr(cls.owner+".class",binary)
        cls.source_zip=cls.pack("correct-source.zip",cls.expanded)

    @classmethod
    def pack(cls,name,source):
        target=cls.root/name
        with ZipFile(target,"w",ZIP_DEFLATED) as z:
            z.writestr("client/src/main/java/"+cls.owner+".java",source)
        return target

    def verify(self,source=None,**kwargs):
        source=source or self.source_zip
        settings={
            "original_jar_sha256":sha(self.jar),
            "original_class_sha256":self.original_class_sha,
            "source_zip_sha256":sha(source),
            "original_owner":self.owner,
            "original_field_map":{
                "ALPHA":"ALPHA","BETA":"BETA",
                "GAMMA":"GAMMA","$VALUES":"$VALUES",
            },
            "original_values_helper_map":{"$values":"$values"},
        }
        settings.update(kwargs)
        return verify_pinned_original_spellbook_filter_enum(
            self.jar,source,**settings)

    def test_five_original_source_methods_with_aliases(self):
        report=self.verify()
        self.assertEqual(5,report[
            "original_method_bodies_semantically_matched"])
        self.assertEqual(50,report["original_jvm_instructions_matched"])
        self.assertEqual(6,report[
            "nonoriginal_alias_initializer_instructions"])
        self.assertFalse(report[
            "full_original_classfile_binary_identity_verified"])
        self.assertFalse(report[
            "original_game_or_enum_runtime_executed"])
        self.assertFalse(report["whole_original_v309_client_compiles"])

    def test_changed_alias_value_rejected(self):
        source=self.pack("wrong-alias.zip",
                         self.expanded.replace("a=ALPHA;","a=GAMMA;"))
        with self.assertRaises(
                (R203OriginalSpellbookEnumError,
                 R190NestedDirectionEnumError)):
            self.verify(source)

    def test_changed_enum_order_rejected(self):
        source=self.pack("wrong-order.zip",self.expanded.replace(
            "ALPHA, BETA, GAMMA;","BETA, ALPHA, GAMMA;"))
        with self.assertRaises(
                (R203OriginalSpellbookEnumError,
                 R190NestedDirectionEnumError)):
            self.verify(source)

    def test_missing_alias_rejected(self):
        source=self.pack("missing-c.zip",self.expanded.replace(
            " public static final Q c=GAMMA;\n",""))
        with self.assertRaises(
                (R203OriginalSpellbookEnumError,
                 R190NestedDirectionEnumError)):
            self.verify(source)

    def test_wrong_private_sha_owner_and_field_map_rejected(self):
        for bad in (
            {"original_jar_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"source_zip_sha256":"0"*64},
            {"original_owner":"invented/filter/Y"},
            {"original_field_map":{
                "ALPHA":"BETA","BETA":"ALPHA",
                "GAMMA":"GAMMA","$VALUES":"$VALUES"}},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(
                        (R203OriginalSpellbookEnumError,
                         R190NestedDirectionEnumError)):
                    self.verify(**bad)


if __name__=="__main__":
    unittest.main()
