"""R183 tests use invented Java9 source, never original SpawnPK classes."""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_signlink_six_source_r183 import (
    R183OriginalSignlinkPartialSourceError,
    verify_six_original_signlink_methods,
    SELECTED_METHODS,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R183SyntheticSixMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("Java compiler unavailable")
        cls.tmp=TemporaryDirectory(prefix="r183-synthetic-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.owner="synthetic/bridge/Z"
        cls.source_text=(
            "package synthetic.bridge;\n"
            "public final class Z implements Runnable {\n"
            "  private final int limit;\n"
            "  private static String saved;\n"
            "  private static int priority;\n"
            "  private static Runnable delegate;\n"
            "  private Z() { limit = 12; }\n"
            "  public static boolean a(String value) { return value == null; }\n"
            "  public static boolean b(String value) { return value != null; }\n"
            "  public static synchronized void d(String value) { saved = value; }\n"
            "  public static synchronized void a(Runnable next, int rank) {\n"
            "    priority = rank; delegate = next;\n"
            "  }\n"
            "  public static boolean i() { return priority > 10; }\n"
            "  public void run() { priority += 1; }\n"
            "}\n"
        )
        src=cls.root/"src"/(cls.owner+".java")
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text(cls.source_text,encoding="utf-8")
        build=cls.root/"build"
        empty=cls.root/"empty"
        build.mkdir()
        empty.mkdir()
        proc=subprocess.run([
            "javac","--release","9","-g:none","-proc:none","-implicit:none",
            "-classpath",str(empty),"-sourcepath",str(empty),
            "-d",str(build),str(src)
        ],capture_output=True,text=True,timeout=60,check=False)
        if proc.returncode:
            raise AssertionError("synthetic original fixture failed: "+proc.stderr)
        cls.original_class=(build/(cls.owner+".class")).read_bytes()
        cls.original_class_sha=hashlib.sha256(
            cls.original_class).hexdigest()
        cls.original_jar=cls.root/"synthetic-original.jar"
        with ZipFile(cls.original_jar,"w",ZIP_DEFLATED) as jar:
            jar.writestr(cls.owner+".class",cls.original_class)
        cls.full_profile=profile_class_field_accesses(
            cls.original_class)
        cls.total_methods=len(cls.full_profile["methods"])
        cls.selected_count=sum(
            len(m["instructions"]) for m in cls.full_profile["methods"]
            if (m["name"],m["descriptor"]) in SELECTED_METHODS)
        cls.verified_source=cls.source_zip("source.zip",cls.source_text)

    @classmethod
    def source_zip(cls,filename,text):
        path=cls.root/filename
        with ZipFile(path,"w",ZIP_DEFLATED) as out:
            out.writestr("client/src/main/java/"+cls.owner+".java",
                         text)
        return path

    def verify(self, source=None, **changes):
        source=source or self.verified_source
        options={
            "original_sha256":sha(self.original_jar),
            "partial_source_sha256":sha(source),
            "original_owner":self.owner,
            "original_class_sha256":self.original_class_sha,
            "expected_original_methods":self.total_methods,
            "expected_selected_instructions":self.selected_count,
        }
        options.update(changes)
        return verify_six_original_signlink_methods(
            self.original_jar,source,**options)

    def test_six_selected_methods_match_without_full_class_claim(self):
        result=self.verify()
        self.assertEqual(6,result["selected_original_methods_verified"])
        self.assertEqual(self.selected_count,
                         result["matched_original_jvm_instructions"])
        self.assertTrue(result[
            "source_only_compilation_no_original_binary_fallback"])
        self.assertFalse(result[
            "full_original_signlink_java_source_recovered"])
        self.assertFalse(result[
            "original_partial_source_installed_canonically"])
        self.assertFalse(result["original_runtime_networking_executed"])

    def test_change_one_selected_method_rejected(self):
        mutated=self.source_zip(
            "mutated-selected.zip",
            self.source_text.replace("priority > 10","priority > 12"))
        with self.assertRaises(R183OriginalSignlinkPartialSourceError):
            self.verify(source=mutated)

    def test_unselected_placeholder_is_not_verified(self):
        rewritten=self.source_zip(
            "unselected-different.zip",
            self.source_text.replace(
                "public void run() { priority += 1; }",
                "public void run() { priority += 3; }"))
        outcome=self.verify(source=rewritten)
        self.assertFalse(outcome[
            "full_original_signlink_java_source_recovered"])
        self.assertGreater(
            outcome["remaining_original_method_implementations_not_verified"],0)

    def test_wrong_shas_counts_and_selected_set_rejected(self):
        for changes in (
            {"original_sha256":"0"*64},
            {"partial_source_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"expected_original_methods":self.total_methods+1},
            {"expected_selected_instructions":self.selected_count+1},
            {"selected_methods":SELECTED_METHODS[:-1]},
            {"expected_major":52},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(R183OriginalSignlinkPartialSourceError):
                    self.verify(**changes)

    def test_missing_original_name_java_rejected(self):
        missing=self.root/"wrong-path.zip"
        with ZipFile(missing,"w",ZIP_DEFLATED) as out:
            out.writestr("client/src/main/java/synthetic/bridge/W.java",
                         self.source_text)
        with self.assertRaises(R183OriginalSignlinkPartialSourceError):
            self.verify(source=missing)


if __name__=="__main__":
    unittest.main()
