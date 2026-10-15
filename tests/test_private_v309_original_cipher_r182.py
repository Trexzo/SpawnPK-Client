"""R182 synthetic source-only tests; NO original game source or binaries in CI."""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_original_cipher_r182 import (
    OriginalCipherR182Error, verify_original_cipher_source,
    overlay_verified_cipher_source,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R182SyntheticOriginalCipherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("Java JDK unavailable")
        cls.tmp=TemporaryDirectory(prefix="spk-r182-synthetic-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.owner="demo/x"
        cls.original_java=(
            "package demo;\n"
            "public final class x {\n"
            "  private int state = 3;\n"
            "  public x(int[] seed) { state += seed.length; }\n"
            "  public int next() { return ++state ^ (state << 2); }\n"
            "}\n"
        )
        source=cls.root/"src/demo/x.java"
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_text(cls.original_java,encoding="utf-8")
        compiled=cls.root/"built"
        empty=cls.root/"empty"
        compiled.mkdir();empty.mkdir()
        run=subprocess.run([
            "javac","--release","9","-g:none","-proc:none","-implicit:none",
            "-classpath",str(empty),"-sourcepath",str(empty),
            "-d",str(compiled),str(source)
        ],capture_output=True,text=True,timeout=60,check=False)
        if run.returncode:
            raise AssertionError("synthetic Java9 fixture compilation failed")
        class_bytes=(compiled/"demo/x.class").read_bytes()
        cls.original_class_sha=hashlib.sha256(class_bytes).hexdigest()
        cls.original_jar=cls.root/"synthetic-original.jar"
        with ZipFile(cls.original_jar,"w",ZIP_DEFLATED) as z:
            z.writestr("demo/x.class",class_bytes)
        cls.source_zip=cls.archive_static("original-source.zip",cls.original_java)
        profile=profile_class_field_accesses(class_bytes)
        cls.expected_methods=len(profile["methods"])
        cls.expected_instructions=sum(
            len(m["instructions"]) for m in profile["methods"])

    @classmethod
    def archive_static(cls,filename,source):
        dest=cls.root/filename
        with ZipFile(dest,"w",ZIP_DEFLATED) as z:
            z.writestr("client/src/main/java/demo/x.java",source)
        return dest

    def check(self,source=None,sha_override=None,**kwargs):
        source=source or self.source_zip
        args=dict(
            original_sha256=sha(self.original_jar),
            source_sha256=sha_override or sha(source),
            original_owner=self.owner,
            original_class_sha256=self.original_class_sha,
            expected_methods=self.expected_methods,
            expected_instructions=self.expected_instructions,
            expected_fields=1)
        args.update(kwargs)
        return verify_original_cipher_source(
            self.original_jar,source,**args)

    def test_all_source_methods_and_full_field_abi_match(self):
        result=self.check()
        self.assertEqual(self.expected_methods,
                         result["complete_original_methods_compiled"])
        self.assertEqual(self.expected_instructions,
                         result["matching_original_jvm_instructions"])
        self.assertTrue(result["source_only_no_original_or_external_binary_fallback"])
        self.assertTrue(result["original_field_abi_verified"])
        self.assertFalse(result["original_client_code_executed"])
        self.assertFalse(result["full_v309_client_compiles"])
        self.assertFalse(result["source_redistribution_authorized"])

    def test_one_original_instruction_mutation_rejected(self):
        changed=self.archive_static(
            "wrong-operation.zip",
            self.original_java.replace("state << 2","state << 3"))
        with self.assertRaises(OriginalCipherR182Error):
            self.check(source=changed)

    def test_sha_count_and_field_guard_rejected(self):
        for kw in (
            {"original_sha256":"0"*64},
            {"source_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"expected_methods":self.expected_methods+1},
            {"expected_instructions":self.expected_instructions+1},
            {"expected_fields":2},
            {"expected_major":52}):
            with self.subTest(kw=kw):
                with self.assertRaises(OriginalCipherR182Error):
                    self.check(**kw)

    def test_source_overlay_preserves_all_previous_bytes(self):
        baseline=self.root/"synthetic-canonical-baseline.zip"
        baseline_content=b"package demo; class Keep {}\n"
        with ZipFile(baseline,"w",ZIP_DEFLATED) as z:
            z.writestr("recovered-source/v309/src/demo/Keep.java",
                        baseline_content)
        output=self.root/"synthetic-recovered-output.zip"
        report=overlay_verified_cipher_source(
            baseline,self.source_zip,output,
            original_tree_sha256=sha(baseline),
            verified_source_sha256=sha(self.source_zip),
            expected_previous_java=1,original_owner=self.owner)
        self.assertEqual(2,report["new_private_recovered_java_files"])
        self.assertFalse(report[
            "original_cipher_source_fully_verified_by_overlay_alone"])
        with ZipFile(output) as z:
            self.assertEqual(2,len(z.namelist()))
            self.assertEqual(baseline_content,z.read(
                "recovered-source/v309/src/demo/Keep.java"))
            self.assertEqual(self.original_java.encode(),z.read(
                "recovered-source/v309/src/demo/x.java"))
        with self.assertRaises(OriginalCipherR182Error):
            overlay_verified_cipher_source(
                baseline,self.source_zip,output,
                original_tree_sha256=sha(baseline),
                verified_source_sha256=sha(self.source_zip),
                expected_previous_java=1,original_owner=self.owner)

    def test_source_archive_owner_and_overlay_pin_guards(self):
        bad=self.root/"bad-source-name.zip"
        with ZipFile(bad,"w") as z:
            z.writestr("client/src/main/java/demo/y.java",
                        self.original_java)
        with self.assertRaises(OriginalCipherR182Error):
            self.check(source=bad)
        base=self.root/"bad-canonical.zip"
        with ZipFile(base,"w") as z:
            z.writestr("recovered-source/v309/src/demo/Keep.java",b"keep")
        with self.assertRaises(OriginalCipherR182Error):
            overlay_verified_cipher_source(
                base,self.source_zip,self.root/"never-created.zip",
                original_tree_sha256="0"*64,
                verified_source_sha256=sha(self.source_zip),
                expected_previous_java=1,original_owner=self.owner)


if __name__=="__main__":
    unittest.main()
