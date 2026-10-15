"""R188 synthetic source-only run() JVM method verification.

The fixture is unrelated to SpawnPK. It exercises the entire chained
6→11→16→21→23→run source-only verifier, including all digest guards,
without publishing or executing original game source or binary classes.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import subprocess
import unittest

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_signlink_run_source_r188 import (
    R188OriginalSignlinkRunSourceError,
    verify_original_signlink_run_source,
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R188SyntheticRunSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reuse earlier *invented* fixture without inheriting its tests.
        from test_private_v309_signlink_twentythree_source_r187 import (
            R187SyntheticTwentyThreeMethods,
        )
        fixture=type("R188LocalFixture",
                     (R187SyntheticTwentyThreeMethods,),{})
        fixture.setUpClass()
        cls.addClassCleanup(fixture.doClassCleanups)
        cls.f=fixture
        cls.full_java=fixture.twentythree.replace(
            "priority+=1;", "priority+=5;")
        if cls.full_java==fixture.twentythree:
            raise AssertionError("R188 synthetic run source mutation absent")
        cls.run_source=fixture.write_zip(
            "synthetic-run-source-r188.zip",
            {fixture.owner:cls.full_java})
        cls.helpers=dict(fixture.helpers)
        cls.helpers["rs/v/a$a"]=(
            "package rs.v; public final class a$a {"
            "public static final a$a a=null;"
            "public static final a$a b=null;}")
        cls.run_helpers=fixture.write_zip(
            "synthetic-run-helpers-r188.zip",cls.helpers)
        path=fixture.root/"src"/(fixture.owner+".java")
        path.write_text(cls.full_java,encoding="utf-8")
        empt=fixture.root/"empty"
        out=fixture.root/"classes"
        sources=[str(path)]
        for owner in sorted(fixture.helpers):
            sources.append(str(fixture.root/"src"/(owner+".java")))
        compile_result=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-implicit:none","-classpath",str(empt),
             "-sourcepath",str(empt),"-d",str(out),*sources],
            capture_output=True,text=True,timeout=90,check=False)
        if compile_result.returncode:
            raise AssertionError("Synthetic run fixture did not compile: "+
                                 compile_result.stderr)
        compiled=(out/(fixture.owner+".class")).read_bytes()
        cls.class_sha=hashlib.sha256(compiled).hexdigest()
        with ZipFile(fixture.jar,"w",ZIP_DEFLATED) as archive:
            archive.writestr(fixture.owner+".class",compiled)
        p=profile_class_field_accesses(compiled)
        method=[m for m in p["methods"]
                if (m["name"],m["descriptor"])==("run","()V")]
        if len(method)!=1:
            raise AssertionError("Expected one unrelated original run")
        cls.run_count=len(method[0]["instructions"])

    def verify(self,candidate=None,helpers=None,**kwargs):
        f=self.f
        candidate=candidate or self.run_source
        helpers=helpers or self.run_helpers
        args={
            "original_sha256":digest(f.jar),
            "six_source_sha256":digest(f.six_zip),
            "eleven_source_sha256":digest(f.eleven_zip),
            "sixteen_source_sha256":digest(f.sixteen_zip),
            "twentyone_source_sha256":digest(f.twentyone_zip),
            "twentythree_source_sha256":digest(f.twentythree_zip),
            "six_helpers_sha256":digest(f.helper_zip),
            "run_source_sha256":digest(candidate),
            "run_helpers_sha256":digest(helpers),
            "original_owner":f.owner,
            "original_class_sha256":self.class_sha,
            "previous_six_instructions":f.six_count,
            "previous_eleven_instructions":f.eleven_count,
            "previous_sixteen_instructions":f.sixteen_count,
            "previous_twentyone_instructions":f.twentyone_count,
            "previous_twentythree_instructions":f.twentythree_count,
            "expected_run_instructions":self.run_count,
            "original_methods":f.original_method_count,
        }
        args.update(kwargs)
        return verify_original_signlink_run_source(
            f.jar,f.six_zip,f.eleven_zip,f.sixteen_zip,
            f.twentyone_zip,f.twentythree_zip,f.helper_zip,
            candidate,helpers,**args)

    def test_real_source_recompile_matches_synthetic_original_run(self):
        report=self.verify()
        self.assertTrue(report["independently_verified_original_run_method"])
        self.assertEqual(self.run_count,
                         report["run_matching_original_jvm_instructions"])
        self.assertEqual(23,
                         report["independently_verified_prior_original_methods"])
        self.assertTrue(report[
            "all_24_method_bodies_individually_recovered_in_separate_builds"])
        self.assertTrue(report["original_full_field_declaration_abi_equal"])
        self.assertFalse(report[
            "all_24_original_method_code_equal_in_one_recompiled_class"])
        self.assertFalse(report["original_nested_enum_java_source_recovered"])
        self.assertFalse(report["original_runtime_behavior_tested"])
        self.assertFalse(report["whole_original_v309_client_compiles"])

    def test_changed_run_bytecode_rejected(self):
        bad=self.f.write_zip(
            "mutated-run-r188.zip",
            {self.f.owner:self.full_java.replace(
                "priority+=5;","priority+=6;")})
        with self.assertRaises(R188OriginalSignlinkRunSourceError):
            self.verify(candidate=bad)

    def test_private_archive_digest_drift_rejected(self):
        for args in (
            {"original_sha256":"0"*64},
            {"six_source_sha256":"0"*64},
            {"twentythree_source_sha256":"0"*64},
            {"run_source_sha256":"0"*64},
            {"run_helpers_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"expected_run_instructions":self.run_count+1},
        ):
            with self.subTest(args=args):
                with self.assertRaises((
                        R188OriginalSignlinkRunSourceError,ValueError)):
                    self.verify(**args)

    def test_missing_or_extra_helper_rejected(self):
        for removed in ("rs/v/a$a","rs/w/c"):
            values=dict(self.helpers)
            del values[removed]
            src=self.f.write_zip("missing-"+removed.replace("/","_")+".zip",
                                 values)
            with self.subTest(removed=removed):
                with self.assertRaises(R188OriginalSignlinkRunSourceError):
                    self.verify(helpers=src)

    def test_unverified_full_source_not_claimed(self):
        report=self.verify()
        self.assertFalse(report["complete_original_classfile_identical"])
        self.assertFalse(report["original_client_code_executed"])
        self.assertFalse(report["canonical_source_tree_modified"])
        self.assertFalse(report["original_source_redistribution_authorized"])


if __name__=="__main__":
    unittest.main()
