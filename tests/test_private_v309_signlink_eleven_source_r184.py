"""R184 original-unrelated synthetic Java9 class and source regression tests."""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_signlink_eleven_source_r184 import (
    R184SignlinkElevenSourceError, verify_eleven_signlink_methods,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R184SyntheticElevenSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK required")
        cls.tmp=TemporaryDirectory(prefix="r184-unrelated-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.owner="synthetic/bridge/Z"
        base=(
            "package synthetic.bridge;\n"
            "public final class Z implements Runnable {\n"
            "  private final int limit;\n"
            "  private static String saved;\n"
            "  private static int priority;\n"
            "  private static Runnable delegate;\n"
            "  private static byte[] buffer;\n"
            "  private Z() { limit = 12; }\n"
            "  public static boolean a(String value) { return value == null; }\n"
            "  public static boolean b(String value) { return value != null; }\n"
            "  public static synchronized void d(String value) { saved = value; }\n"
            "  public static synchronized void a(Runnable next, int rank) {\n"
            "    priority = rank; delegate = next;\n"
            "  }\n"
            "  public static boolean i() { return priority > 10; }\n"
        )
        addition=(
            "  public static synchronized java.net.Socket a(int port)"
            " throws java.io.IOException {\n"
            "    priority = port;\n"
            "    if (port < 0) throw new java.io.IOException(\"negative\");\n"
            "    return null;\n"
            "  }\n"
            "  public static synchronized boolean a(byte[] bytes,int count){\n"
            "    if (count < 0) return false;\n"
            "    buffer = bytes;\n"
            "    saved = \"sample\" + count + \".bin\";\n"
            "    return true;\n"
            "  }\n"
            "  public static synchronized void b(byte[] bytes,int count){\n"
            "    buffer=bytes; priority=count;\n"
            "  }\n"
            "  public static synchronized boolean h(){ return saved!=null; }\n"
            "  public static void e(String message){\n"
            "    System.out.println(\"message=\" + message);\n"
            "  }\n"
        )
        ending="  public void run(){ priority += 1; }\n}\n"
        cls.previous=base+ending
        cls.complete=base+addition+ending
        cls.prior_zip=cls.pack("prior.zip",cls.previous)
        cls.complete_zip=cls.pack("extended.zip",cls.complete)
        src=cls.root/"src"/(cls.owner+".java")
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text(cls.complete,encoding="utf-8")
        out=cls.root/"out"
        empty=cls.root/"empty"
        out.mkdir();empty.mkdir()
        proc=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-implicit:none","-classpath",str(empty),
             "-sourcepath",str(empty),"-d",str(out),str(src)],
            capture_output=True,text=True,timeout=60,check=False)
        if proc.returncode:
            raise AssertionError("synthetic fixture compile failed: "+proc.stderr)
        cls.original_class=(out/(cls.owner+".class")).read_bytes()
        cls.original_class_sha=hashlib.sha256(
            cls.original_class).hexdigest()
        cls.jar=cls.root/"original-synthetic.jar"
        with ZipFile(cls.jar,"w",ZIP_DEFLATED) as archive:
            archive.writestr(cls.owner+".class",cls.original_class)
        profile=profile_class_field_accesses(cls.original_class)
        cls.total_methods=len(profile["methods"])
        cls.selected_ids={
            ("<init>","()V"),("a","(Ljava/lang/String;)Z"),
            ("b","(Ljava/lang/String;)Z"),
            ("d","(Ljava/lang/String;)V"),
            ("a","(Ljava/lang/Runnable;I)V"),
            ("i","()Z"),
            ("a","(I)Ljava/net/Socket;"),
            ("a","([BI)Z"),
            ("b","([BI)V"),
            ("h","()Z"),
            ("e","(Ljava/lang/String;)V"),
        }
        cls.total_instructions=sum(
            len(m["instructions"]) for m in profile["methods"]
            if (m["name"],m["descriptor"]) in cls.selected_ids)
        cls.prior_instructions=sum(
            len(m["instructions"]) for m in profile["methods"]
            if (m["name"],m["descriptor"]) in
                cls.selected_ids-{
                    ("a","(I)Ljava/net/Socket;"),
                    ("a","([BI)Z"),
                    ("b","([BI)V"),
                    ("h","()Z"),
                    ("e","(Ljava/lang/String;)V"),
                })

    @classmethod
    def pack(cls,name,body):
        path=cls.root/name
        with ZipFile(path,"w",ZIP_DEFLATED) as z:
            z.writestr("client/src/main/java/"+cls.owner+".java",body)
        return path

    def proof(self, source=None, **kwargs):
        source=source or self.complete_zip
        params={
            "original_sha256":sha(self.jar),
            "previous_six_sha256":sha(self.prior_zip),
            "eleven_source_sha256":sha(source),
            "original_class_sha256":self.original_class_sha,
            "original_owner":self.owner,
            "expected_original_methods":self.total_methods,
            "expected_previous_instructions":self.prior_instructions,
            "expected_instructions":self.total_instructions,
            "expected_new_instructions":
                self.total_instructions-self.prior_instructions,
        }
        params.update(kwargs)
        return verify_eleven_signlink_methods(
            self.jar,self.prior_zip,source,**params)

    def test_full_eleven_selected_method_code_matches(self):
        result=self.proof()
        self.assertEqual(11,result["selected_original_method_bodies_verified"])
        self.assertEqual(5,result["new_original_method_bodies_verified"])
        self.assertEqual(self.total_instructions,
                         result["selected_original_jvm_instructions_matched"])
        self.assertTrue(result["source_only_javac_no_original_binary_fallback"])
        self.assertFalse(result["original_full_class_method_attributes_verified"])
        self.assertFalse(result["original_entire_signlink_source_recovered"])
        self.assertFalse(result["private_partial_source_added_to_canonical_tree"])
        self.assertFalse(result["original_game_binary_executed"])

    def test_mutated_new_selected_method_rejected(self):
        bad=self.pack("mutated-new.zip",
                      self.complete.replace("priority=count;",
                                            "priority=count+1;"))
        with self.assertRaises(R184SignlinkElevenSourceError):
            self.proof(source=bad)

    def test_mutated_old_selected_method_rejected(self):
        bad=self.pack("mutated-old.zip",
                      self.complete.replace("priority > 10",
                                            "priority > 11"))
        with self.assertRaises(R184SignlinkElevenSourceError):
            self.proof(source=bad)

    def test_unselected_run_placeholder_not_certified(self):
        changed=self.pack("different-run.zip",
                          self.complete.replace(
                              "priority += 1","priority += 9"))
        report=self.proof(source=changed)
        self.assertFalse(report["original_entire_signlink_source_recovered"])

    def test_wrong_pins_and_counts_rejected(self):
        for kw in (
            {"original_sha256":"0"*64},
            {"previous_six_sha256":"0"*64},
            {"eleven_source_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"expected_original_methods":self.total_methods+1},
            {"expected_instructions":self.total_instructions+1},
            {"expected_new_instructions":
                 self.total_instructions-self.prior_instructions+1},
        ):
            with self.subTest(kw=kw):
                with self.assertRaises((R184SignlinkElevenSourceError,
                                        ValueError)):
                    self.proof(**kw)

    def test_different_source_java_owner_rejected(self):
        wrong=self.root/"wrongowner.zip"
        with ZipFile(wrong,"w",ZIP_DEFLATED) as out:
            out.writestr("client/src/main/java/synthetic/bridge/Y.java",
                         self.complete)
        with self.assertRaises((R184SignlinkElevenSourceError,ValueError)):
            self.proof(source=wrong)


if __name__=="__main__":
    unittest.main()
