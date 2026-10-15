"""R185: synthetic original-unrelated Java9 sixteen-method proof."""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_signlink_sixteen_source_r185 import (
    R185PartialOriginalSignlinkError,
    verify_sixteen_original_signlink_java,
    SELECTED_ELEVEN, SIXTEEN,
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R185SyntheticSixteenMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("Java compiler required")
        cls.temp=TemporaryDirectory(prefix="r185-synthetic-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        cls.owner="synthetic/bridge/Z"
        base=(
            "package synthetic.bridge;\n"
            "public final class Z implements Runnable {\n"
            "  private final int limit;\n"
            "  private static String saved;\n"
            "  private static int priority;\n"
            "  private static Runnable delegate;\n"
            "  private static byte[] buffer;\n"
            "  private Z() { limit=12; }\n"
            "  public static boolean a(String value){return value==null;}\n"
            "  public static boolean b(String value){return value!=null;}\n"
            "  public static synchronized void d(String value){saved=value;}\n"
            "  public static synchronized void a(Runnable task,int rank){\n"
            "    priority=rank;delegate=task;\n"
            "  }\n"
            "  public static boolean i(){return priority>10;}\n"
        )
        five=(
            "  public static synchronized java.net.Socket a(int port)"
            " throws java.io.IOException {\n"
            "    priority=port;\n"
            "    if(port<0)throw new java.io.IOException(\"invalid\");\n"
            "    return null;\n"
            "  }\n"
            "  public static synchronized boolean a(byte[] data,int length){\n"
            "    buffer=data;return length>0;\n"
            "  }\n"
            "  public static synchronized void b(byte[] data,int length){\n"
            "    buffer=data;priority=length;\n"
            "  }\n"
            "  public static synchronized boolean h(){return saved!=null;}\n"
            "  public static void e(String msg){System.out.println(msg);}\n"
        )
        newest=(
            "  public static synchronized java.io.DataInputStream c(String key)"
            " throws java.io.IOException {\n"
            "    if(key==null)return null;\n"
            "    throw new java.io.IOException(key);\n"
            "  }\n"
            "  public static void a(){priority=3;}\n"
            "  public static void a(java.net.InetAddress host){\n"
            "    saved=host.toString();\n"
            "  }\n"
            "  private static int f(String value){return value.length();}\n"
            "  public static String c(){return saved;}\n"
        )
        ending="  public void run(){priority+=1;}\n}\n"
        cls.six=base+ending
        cls.eleven=base+five+ending
        cls.sixteen=base+five+newest+ending
        cls.six_zip=cls.make_source_zip("six.zip",cls.six)
        cls.eleven_zip=cls.make_source_zip("eleven.zip",cls.eleven)
        cls.sixteen_zip=cls.make_source_zip("sixteen.zip",cls.sixteen)
        src=cls.root/"src"/(cls.owner+".java")
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text(cls.sixteen,encoding="utf-8")
        empty=cls.root/"empty";out=cls.root/"classes"
        empty.mkdir();out.mkdir()
        proc=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-implicit:none","-classpath",str(empty),
             "-sourcepath",str(empty),"-d",str(out),str(src)],
            capture_output=True,text=True,check=False,timeout=90)
        if proc.returncode:
            raise AssertionError("Synthetic Java fixture compile failed: "+proc.stderr)
        original=(out/(cls.owner+".class")).read_bytes()
        cls.class_sha=hashlib.sha256(original).hexdigest()
        cls.jar=cls.root/"synthetic-original.jar"
        with ZipFile(cls.jar,"w",ZIP_DEFLATED) as archive:
            archive.writestr(cls.owner+".class",original)
        profile=profile_class_field_accesses(original)
        cls.method_count=len(profile["methods"])
        cls.opcounts={
            (m["name"],m["descriptor"]):len(m["instructions"])
            for m in profile["methods"]}
        cls.all_count=sum(cls.opcounts[x] for x in SIXTEEN)
        cls.eleven_count=sum(cls.opcounts[x] for x in SELECTED_ELEVEN)
        cls.six_count=sum(cls.opcounts[x]
                          for x in SELECTED_ELEVEN[:6])

    @classmethod
    def make_source_zip(cls,name,body):
        path=cls.root/name
        with ZipFile(path,"w",ZIP_DEFLATED) as z:
            z.writestr("client/src/main/java/"+cls.owner+".java",body)
        return path

    def audit(self,source=None,**override):
        source=source or self.sixteen_zip
        params={
            "original_sha256":digest(self.jar),
            "six_source_sha256":digest(self.six_zip),
            "eleven_source_sha256":digest(self.eleven_zip),
            "sixteen_source_sha256":digest(source),
            "original_owner":self.owner,
            "original_class_sha256":self.class_sha,
            "original_total_methods":self.method_count,
            "previous_six_instructions":self.six_count,
            "previous_eleven_instructions":self.eleven_count,
            "expected_total_instructions":self.all_count,
            "expected_new_instructions":self.all_count-self.eleven_count,
        }
        params.update(override)
        return verify_sixteen_original_signlink_java(
            self.jar,self.six_zip,self.eleven_zip,source,**params)

    def test_complete_sixteen_selected_source_code(self):
        report=self.audit()
        self.assertEqual(16,report["selected_original_methods_verified"])
        self.assertEqual(5,report["new_selected_original_methods_verified"])
        self.assertEqual(self.all_count,
                         report["matched_original_jvm_instructions"])
        self.assertTrue(report["selected_method_core_code_matches"])
        self.assertFalse(report["full_original_signlink_class_recovered"])
        self.assertFalse(report["partial_source_added_to_canonical_tree"])
        self.assertFalse(report["original_game_binary_executed"])
        self.assertFalse(report["unselected_run_compiler_placeholder_verified"])

    def test_new_method_mutation_is_rejected(self):
        changed=self.make_source_zip(
            "altered-c.zip",self.sixteen.replace(
                "return value.length();","return value.length()+1;"))
        with self.assertRaises(R185PartialOriginalSignlinkError):
            self.audit(source=changed)

    def test_mutated_prior_method_is_rejected(self):
        changed=self.make_source_zip(
            "altered-i.zip",self.sixteen.replace(
                "priority>10","priority>11"))
        with self.assertRaises(R185PartialOriginalSignlinkError):
            self.audit(source=changed)

    def test_unselected_run_is_not_accepted(self):
        changed=self.make_source_zip(
            "altered-run.zip",self.sixteen.replace(
                "priority+=1","priority+=9"))
        report=self.audit(source=changed)
        self.assertFalse(report["unselected_run_compiler_placeholder_verified"])
        self.assertFalse(report["full_original_signlink_class_recovered"])

    def test_bad_private_pins_and_total_counts_fail(self):
        for kw in (
            {"original_sha256":"0"*64},
            {"six_source_sha256":"0"*64},
            {"eleven_source_sha256":"0"*64},
            {"sixteen_source_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"original_total_methods":self.method_count+1},
            {"expected_total_instructions":self.all_count+1},
        ):
            with self.subTest(kw=kw):
                with self.assertRaises((R185PartialOriginalSignlinkError,
                                        ValueError)):
                    self.audit(**kw)


if __name__=="__main__":
    unittest.main()
