"""R192 synthetic source-only Java9 baseline/overlay/delta tests."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import shutil
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from spk_recovery.private_v309_four_owner_javac_frontier_r192 import (
    R192PrivateSourceFrontierError,
    build_private_four_owner_overlay,
    compare_pinned_private_four_owner_javac,
)


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


class R192SyntheticFourOwnerCompilerFrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK required")
        cls.tmp=TemporaryDirectory(prefix="r192-original-unrelated-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.baseline=cls.root/"baseline.zip"
        with ZipFile(cls.baseline,"w",ZIP_DEFLATED) as z:
            z.writestr(
                "recovered-source/v309/src/example/A.java",
                "package example; public final class A {"
                " public static int x(){return 3;} }\n")
        cls.new_java=cls.root/"new-source.zip"
        with ZipFile(cls.new_java,"w",ZIP_DEFLATED) as z:
            z.writestr(
                "client/src/main/java/example/B.java",
                "package example; public final class B {"
                " public static int y(){return MissingOwner.x();} }\n")
        cls.identities=(("example/B.java",sha(cls.new_java)),)

    def overlay(self,name="overlay.zip",**options):
        output=self.root/name
        args={
            "baseline_sha256":sha(self.baseline),
            "source_identities":self.identities,
            "expected_baseline_java":1,
        }
        args.update(options)
        report=build_private_four_owner_overlay(
            self.baseline,[self.new_java],output,**args)
        return output,report

    def test_original_java_preserved_and_added_source_precisely(self):
        candidate,summary=self.overlay("preservation.zip")
        self.assertEqual(1,summary[
            "baseline_java_files_exactly_preserved"])
        self.assertEqual(1,summary[
            "added_independently_evidenced_java_files"])
        self.assertEqual(2,summary["candidate_java_source_file_count"])
        self.assertFalse(summary["invented_compiler_helpers_added"])
        with ZipFile(self.baseline) as z:
            original=z.read("recovered-source/v309/src/example/A.java")
        with ZipFile(candidate) as z:
            self.assertEqual(2,len(z.namelist()))
            self.assertEqual(original,z.read(
                "recovered-source/v309/src/example/A.java"))
            self.assertIn(
                b"MissingOwner",z.read(
                    "recovered-source/v309/src/example/B.java"))
        with self.assertRaises(R192PrivateSourceFrontierError):
            self.overlay("preservation.zip")

    def test_measured_javac_frontier_is_source_only_and_reproducible(self):
        output,_=self.overlay("javac-fixture.zip")
        report=compare_pinned_private_four_owner_javac(
            self.baseline,output,
            original_sha256=sha(self.baseline),
            candidate_sha256=sha(output),
            expected_original_count=1,expected_added_count=1)
        self.assertEqual(0,report["baseline"]["total_compiler_errors"])
        self.assertGreater(report["candidate"]["total_compiler_errors"],0)
        self.assertEqual(report["candidate"]["total_compiler_errors"],
                         report["compilation_error_delta"])
        self.assertTrue(report["previous_source_files_byte_identical"])
        self.assertFalse(report["original_jar_on_compiler_classpath"])
        self.assertFalse(report["full_original_v309_client_compiles"])

    def test_missing_private_source_digest_rejected(self):
        with self.assertRaises(R192PrivateSourceFrontierError):
            self.overlay("wrong-pin.zip",
                         source_identities=(("example/B.java","0"*64),))
        with self.assertRaises(R192PrivateSourceFrontierError):
            self.overlay("wrong-base.zip",baseline_sha256="0"*64)

    def test_source_archive_owner_mismatch_rejected(self):
        with self.assertRaises(R192PrivateSourceFrontierError):
            self.overlay("wrong-owner.zip",
                         source_identities=(("example/C.java",sha(self.new_java)),))

    def test_canonical_baseline_path_escape_rejected(self):
        unsafe=self.root/"unsafe.zip"
        with ZipFile(unsafe,"w",ZIP_DEFLATED) as z:
            z.writestr("recovered-source/v309/src/../Evil.java",
                        "package example; class Evil {}")
        with self.assertRaises(R192PrivateSourceFrontierError):
            build_private_four_owner_overlay(
                unsafe,[self.new_java],self.root/"no-unsafe.zip",
                baseline_sha256=sha(unsafe),
                source_identities=self.identities,
                expected_baseline_java=1)

    def test_tampered_overlay_preservation_rejected(self):
        candidate,_=self.overlay("untampered.zip")
        bad=self.root/"tampered.zip"
        with ZipFile(candidate) as z,ZipFile(bad,"w",ZIP_DEFLATED) as out:
            for name in z.namelist():
                body=z.read(name)
                if name.endswith("A.java"):
                    body=body.replace(b"return 3",b"return 4")
                out.writestr(name,body)
        with self.assertRaises(R192PrivateSourceFrontierError):
            compare_pinned_private_four_owner_javac(
                self.baseline,bad,
                original_sha256=sha(self.baseline),
                candidate_sha256=sha(bad),
                expected_original_count=1,expected_added_count=1)


if __name__=="__main__":
    unittest.main()
