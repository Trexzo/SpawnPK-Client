"""R196 invented Java9 MIDI-shaped fixture; no audio devices or game code run."""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_original_midi_source_r196 import (
    verify_pinned_original_v309_midi_java,
)
from spk_recovery.private_v309_macos_serial_source_r193 import (
    R193OriginalMacOSSerialSourceError,
)
from spk_recovery.private_v309_four_owner_javac_frontier_r192 import (
    build_private_four_owner_overlay,
    compare_pinned_private_four_owner_javac,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R196SyntheticMidiOwnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK required")
        cls.tmp=TemporaryDirectory(prefix="r196-invented-midi-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.owner="invented/M"
        cls.body=(
            "package invented;\n"
            "public class M {\n"
            " String a;\n"
            " String b;\n"
            " Object c;\n"
            " Object d;\n"
            " Object e;\n"
            " double f=0.0d;\n"
            " public M(){}\n"
            " public String a(){return a;}\n"
            " public String b(){return b;}\n"
            " public void a(String t){a=t;}\n"
            " public void b(String t){b=t;}\n"
            " public boolean a(double v){return a(v,true);}\n"
            " public boolean a(double v,boolean saved){\n"
            "  if(saved)f=v;\n"
            "  int counter=0;\n"
            "  while(counter<3){counter++;}\n"
            "  return true;\n"
            " }\n"
            " private boolean a(javax.sound.midi.Receiver r,double v){\n"
            "  try{\n"
            "   javax.sound.midi.ShortMessage m=new javax.sound.midi.ShortMessage();\n"
            "   m.setMessage(176,0,7,(int)(v*127d));\n"
            "   r.send(m,-1);\n"
            "   return true;\n"
            "  }catch(Exception err){return false;}\n"
            " }\n"
            " public void c(){}\n"
            " public void d(){String z=a()+b();d=z;}\n"
            " private void a(javax.sound.midi.MetaMessage m){\n"
            "  if(m.getType()==3)a(f,false);\n"
            " }\n"
            "}\n"
        )
        src=cls.root/"source/invented/M.java"
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text(cls.body,encoding="utf-8")
        classes=cls.root/"classes"
        empty=cls.root/"empty"
        classes.mkdir();empty.mkdir()
        result=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(classes),str(src)],
            capture_output=True,text=True,timeout=60,check=False)
        if result.returncode:
            raise AssertionError("invented MIDI-like Java9 compilation failed")
        blob=(classes/(cls.owner+".class")).read_bytes()
        cls.class_sha=hashlib.sha256(blob).hexdigest()
        cls.jar=cls.root/"invented-jar.zip"
        with ZipFile(cls.jar,"w",ZIP_DEFLATED) as z:
            z.writestr(cls.owner+".class",blob)
        cls.source_zip=cls.pack("invented-java.zip",cls.body)
        profile=profile_class_field_accesses(blob)
        cls.instructions=sum(
            len(method["instructions"]) for method in profile["methods"])

    @classmethod
    def pack(cls,name,body):
        path=cls.root/name
        with ZipFile(path,"w",ZIP_DEFLATED) as z:
            z.writestr("client/src/main/java/"+cls.owner+".java",body)
        return path

    def verify(self,source=None,**options):
        source=source or self.source_zip
        kwargs={
            "original_sha256":sha(self.jar),
            "original_source_sha256":sha(source),
            "original_owner":self.owner,
            "original_class_sha256":self.class_sha,
            "expected_methods":11,
            "expected_instructions":self.instructions,
            "expected_fields":6,
        }
        kwargs.update(options)
        return verify_pinned_original_v309_midi_java(
            self.jar,source,**kwargs)

    def test_all_eleven_original_unrelated_jvm_methods_match(self):
        result=self.verify()
        self.assertEqual(11,result["full_original_method_count_compiled"])
        self.assertEqual(self.instructions,
                         result["full_original_jvm_instructions_matched"])
        self.assertTrue(result[
            "source_compiled_without_any_fake_class_helpers"])
        self.assertFalse(result["original_audio_device_or_game_code_executed"])
        self.assertFalse(result["whole_v309_client_compiles"])

    def test_changed_midi_branch_operation_rejected(self):
        bad=self.pack(
            "changed-meta-branch.zip",
            self.body.replace("m.getType()==3","m.getType()==4"))
        with self.assertRaises(R193OriginalMacOSSerialSourceError):
            self.verify(source=bad)

    def test_changed_channel_loop_rejected(self):
        bad=self.pack(
            "changed-control-loop.zip",
            self.body.replace("counter<3","counter<4"))
        with self.assertRaises(R193OriginalMacOSSerialSourceError):
            self.verify(source=bad)

    def test_bad_digest_or_method_and_field_inventory_rejected(self):
        for opt in (
            {"original_sha256":"0"*64},
            {"original_source_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"original_owner":"invented/Wrong"},
            {"expected_methods":12},
            {"expected_fields":5},
            {"expected_instructions":self.instructions+1},
        ):
            with self.subTest(opt=opt):
                with self.assertRaises(R193OriginalMacOSSerialSourceError):
                    self.verify(**opt)

    def test_previous_original_source_bytes_preserved_in_overlay(self):
        baseline=self.root/"baseline.zip"
        with ZipFile(baseline,"w",ZIP_DEFLATED) as z:
            z.writestr("recovered-source/v309/src/invented/Base.java",
                        "package invented; public class Base {}")
        overlay=self.root/"overlay.zip"
        result=build_private_four_owner_overlay(
            baseline,[self.source_zip],overlay,
            baseline_sha256=sha(baseline),
            source_identities=((self.owner+".java",sha(self.source_zip)),),
            expected_baseline_java=1)
        self.assertEqual(2,result["candidate_java_source_file_count"])
        with ZipFile(overlay) as z:
            self.assertEqual(
                b"package invented; public class Base {}",
                z.read("recovered-source/v309/src/invented/Base.java"))
        report=compare_pinned_private_four_owner_javac(
            baseline,overlay,
            original_sha256=sha(baseline),
            candidate_sha256=sha(overlay),
            expected_original_count=1,expected_added_count=1)
        self.assertEqual(0,report["compilation_error_delta"])
        self.assertFalse(report["original_jar_on_compiler_classpath"])


if __name__=="__main__":
    unittest.main()
