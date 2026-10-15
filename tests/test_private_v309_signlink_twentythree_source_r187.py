"""R187 synthetic unrelated Java9 6→11→16→21→23 method proof.

Inherit the R186 invented fixture and append two invented source bodies.
Their Java bytecode is compared against that separately compiled synthetic
"original", never against a game classfile in hosted CI.
"""
import hashlib
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

from test_private_v309_signlink_twentyone_source_r186 import (
    R186SyntheticTwentyOneMethodTests, sha,
)
from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_signlink_twentythree_source_r187 import (
    R187OriginalSignlinkTwentyThreeError,
    verify_23_original_signlink_java,
    NEW_TWO,
)


class R187SyntheticTwentyThreeMethods(R186SyntheticTwentyOneMethodTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Add a synthetic cache path method and static initializer while
        # retaining all 21 previously selected source method implementations.
        old='  public void run(){priority+=1;}\n}\n'
        assert old in cls.twentyone
        cls.twentythree=cls.twentyone.replace(
            old,
            '  public static String g(){\n'
            '    String[] names={"alpha","beta","gamma"};\n'
            '    for(String name:names){\n'
            '      if(name.length()>1)return name;\n'
            '    }\n'
            '    return null;\n'
            '  }\n'
            '  static { saved="synthetic"; priority=12; }\n'
            +old,
        )
        cls.twentythree_zip=cls.write_zip(
            "twentythree.zip",{cls.owner:cls.twentythree})
        source=cls.root/"src"/(cls.owner+".java")
        source.write_text(cls.twentythree,encoding="utf-8")
        empty=cls.root/"empty"
        out=cls.root/"classes"
        paths=[str(source)]
        for owner in sorted(cls.helpers):
            paths.append(str(cls.root/"src"/(owner+".java")))
        build=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-implicit:none","-classpath",str(empty),
             "-sourcepath",str(empty),"-d",str(out),*paths],
            capture_output=True,text=True,timeout=90,check=False)
        if build.returncode:
            raise AssertionError(
                "R187 unrelated source fixture compilation failed: "+
                build.stderr)
        binary=(out/(cls.owner+".class")).read_bytes()
        cls.class_sha=hashlib.sha256(binary).hexdigest()
        with ZipFile(cls.jar,"w",ZIP_DEFLATED) as archive:
            archive.writestr(cls.owner+".class",binary)
        p=profile_class_field_accesses(binary)
        cls.original_method_count=len(p["methods"])
        instructions={(m["name"],m["descriptor"]):len(m["instructions"])
                      for m in p["methods"]}
        cls.twentythree_count=(
            cls.twentyone_count+
            sum(instructions[id] for id in NEW_TWO))

    def verify23(self,candidate=None,**overrides):
        candidate=candidate or self.twentythree_zip
        args={
            "original_sha256":sha(self.jar),
            "source_6_sha256":sha(self.six_zip),
            "source_11_sha256":sha(self.eleven_zip),
            "source_16_sha256":sha(self.sixteen_zip),
            "source_21_sha256":sha(self.twentyone_zip),
            "source_23_sha256":sha(candidate),
            "compiler_helpers_sha256":sha(self.helper_zip),
            "original_owner":self.owner,
            "original_class_sha256":self.class_sha,
            "expected_original_method_count":self.original_method_count,
            "expected_six_instructions":self.six_count,
            "expected_eleven_instructions":self.eleven_count,
            "expected_sixteen_instructions":self.sixteen_count,
            "expected_twentyone_instructions":self.twentyone_count,
            "expected_all_instructions":self.twentythree_count,
            "expected_new_instructions":
                self.twentythree_count-self.twentyone_count,
        }
        args.update(overrides)
        return verify_23_original_signlink_java(
            self.jar,self.six_zip,self.eleven_zip,self.sixteen_zip,
            self.twentyone_zip,candidate,self.helper_zip,**args)

    def test_23_selected_original_unrelated_code_and_initializer(self):
        report=self.verify23()
        self.assertEqual(23,report["verified_original_method_count"])
        self.assertEqual(self.twentythree_count,
                         report["matched_original_jvm_instructions"])
        self.assertTrue(report[
            "class_initializer_complete_original_code_verified"])
        self.assertTrue(report["original_run_method_unverified"])
        self.assertFalse(report["full_original_signlink_source_verified"])
        self.assertFalse(report["entire_original_client_compiled"])
        self.assertFalse(report["compiler_only_helper_java_is_original"])

    def test_changed_cache_path_method_rejected(self):
        candidate=self.write_zip(
            "wrong-g.zip",{self.owner:self.twentythree.replace(
                '"alpha","beta","gamma"',
                '"alpha","delta","gamma"')})
        with self.assertRaises(R187OriginalSignlinkTwentyThreeError):
            self.verify23(candidate)

    def test_changed_static_initializer_rejected(self):
        candidate=self.write_zip(
            "wrong-clinit.zip",{self.owner:self.twentythree.replace(
                'priority=12;', 'priority=13;')})
        with self.assertRaises(R187OriginalSignlinkTwentyThreeError):
            self.verify23(candidate)

    def test_unselected_run_stays_outside_acceptance(self):
        candidate=self.write_zip(
            "changed-run.zip",{self.owner:self.twentythree.replace(
                'priority+=1','priority+=3')})
        report=self.verify23(candidate)
        self.assertTrue(report["original_run_method_unverified"])
        self.assertFalse(report["full_original_signlink_source_verified"])

    def test_all_seven_private_sha_pins_guarded(self):
        for changes in (
            {"original_sha256":"0"*64},
            {"source_6_sha256":"0"*64},
            {"source_11_sha256":"0"*64},
            {"source_16_sha256":"0"*64},
            {"source_21_sha256":"0"*64},
            {"source_23_sha256":"0"*64},
            {"compiler_helpers_sha256":"0"*64},
            {"expected_all_instructions":self.twentythree_count+1},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises((R187OriginalSignlinkTwentyThreeError,
                                        ValueError)):
                    self.verify23(**changes)
