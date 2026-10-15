"""R186: synthetic unrelated Java9 21-method source and helper-ABI tests."""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_signlink_sixteen_source_r185 import SIXTEEN
from spk_recovery.private_v309_signlink_twentyone_source_r186 import (
    R186OriginalSignlinkTwentyOneSourceError,
    verify_21_original_signlink_methods,
    TWENTYONE, HELPER_OWNERS,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R186SyntheticTwentyOneMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK required")
        cls.tmp=TemporaryDirectory(prefix="r186-invented-java-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.owner="synthetic/bridge/Z"
        header=(
            "package synthetic.bridge;\n"
            "public final class Z implements Runnable {\n"
            "  private int count;\n"
            "  private static String saved;\n"
            "  private static int priority;\n"
            "  private static Runnable runnable;\n"
            "  private static byte[] bytes;\n"
            "  private static rs.w.c a;\n"
            "  private Z(){count=2;}\n"
            "  public static boolean a(String text){return text==null;}\n"
            "  public static boolean b(String text){return text!=null;}\n"
            "  public static synchronized void d(String text){saved=text;}\n"
            "  public static synchronized void a(Runnable task,int x){\n"
            "    runnable=task;priority=x;\n"
            "  }\n"
            "  public static boolean i(){return priority>10;}\n"
        )
        second=(
            "  public static synchronized java.net.Socket a(int n)"
            " throws java.io.IOException {\n"
            "    if(n<0)throw new java.io.IOException(\"bad port\");\n"
            "    priority=n;return null;\n"
            "  }\n"
            "  public static synchronized boolean a(byte[] data,int n){\n"
            "    bytes=data;return n>0;\n"
            "  }\n"
            "  public static synchronized void b(byte[] data,int n){\n"
            "    bytes=data;priority=n;\n"
            "  }\n"
            "  public static synchronized boolean h(){return saved!=null;}\n"
            "  public static void e(String msg){System.out.println(msg);}\n"
        )
        third=(
            "  public static java.io.DataInputStream c(String key)"
            " throws java.io.IOException {\n"
            "    if(key==null)return null;\n"
            "    throw new java.io.IOException(key);\n"
            "  }\n"
            "  public static void a(){priority=3;}\n"
            "  public static void a(java.net.InetAddress host){\n"
            "    saved=host.toString();\n"
            "  }\n"
            "  private static int f(String key){return key.length();}\n"
            "  public static String c(){return saved;}\n"
        )
        fourth=(
            "  public static String b(){return System.getProperty(\"user.home\");}\n"
            "  public static String f(){return \".\"+rs.f.a.B;}\n"
            "  public static boolean d(){return rs.k.j.a()==rs.k.j.a;}\n"
            "  public static String e(){\n"
            "    String v=rs.secure.c.a();\n"
            "    if(v==null)v=rs.secure.b.a();\n"
            "    if(v==null)v=rs.secure.a.a();\n"
            "    return v;\n"
            "  }\n"
            "  public static void a(double v){a.a(v);}\n"
        )
        footer="  public void run(){priority+=1;}\n}\n"
        cls.six=header+footer
        cls.eleven=header+second+footer
        cls.sixteen=header+second+third+footer
        cls.twentyone=header+second+third+fourth+footer
        cls.six_zip=cls.write_zip("six.zip",{cls.owner:cls.six})
        cls.eleven_zip=cls.write_zip(
            "eleven.zip",{cls.owner:cls.eleven})
        cls.sixteen_zip=cls.write_zip(
            "sixteen.zip",{cls.owner:cls.sixteen})
        cls.twentyone_zip=cls.write_zip(
            "twentyone.zip",{cls.owner:cls.twentyone})
        cls.helpers={
            "rs/f/a":"package rs.f; public class a { public static String B; }",
            "rs/k/j":"package rs.k; public class j {"
                     " public static j a; public static j a(){return a;} }",
            "rs/w/c":"package rs.w; public class c {"
                     " public boolean a(double x){return true;} }",
            "rs/secure/a":"package rs.secure; public class a {"
                          " public static String a(){return null;} }",
            "rs/secure/b":"package rs.secure; public class b {"
                          " public static String a(){return null;} }",
            "rs/secure/c":"package rs.secure; public class c {"
                          " public static String a(){return null;} }",
        }
        cls.helper_zip=cls.write_zip("helpers.zip",cls.helpers)
        source_root=cls.root/"src"
        paths=[]
        for name,body in [(cls.owner,cls.twentyone),*cls.helpers.items()]:
            dest=source_root/(name+".java")
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(body,encoding="utf-8")
            paths.append(str(dest))
        empty=cls.root/"empty";out=cls.root/"classes"
        empty.mkdir();out.mkdir()
        compilation=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-implicit:none","-classpath",str(empty),
             "-sourcepath",str(empty),"-d",str(out),*paths],
            capture_output=True,text=True,timeout=90,check=False)
        if compilation.returncode:
            raise AssertionError(
                "synthetic original JDK9 compilation failed: "+
                compilation.stderr)
        class_bytes=(out/(cls.owner+".class")).read_bytes()
        cls.class_sha=hashlib.sha256(class_bytes).hexdigest()
        cls.jar=cls.root/"synthetic-jdk9-original.jar"
        with ZipFile(cls.jar,"w",ZIP_DEFLATED) as archive:
            archive.writestr(cls.owner+".class",class_bytes)
        profile=profile_class_field_accesses(class_bytes)
        cls.original_method_count=len(profile["methods"])
        counts={(m["name"],m["descriptor"]):
                len(m["instructions"]) for m in profile["methods"]}
        cls.six_count=sum(counts[x] for x in SIXTEEN[:6])
        cls.eleven_count=sum(counts[x] for x in SIXTEEN[:11])
        cls.sixteen_count=sum(counts[x] for x in SIXTEEN)
        cls.twentyone_count=sum(counts[x] for x in TWENTYONE)

    @classmethod
    def write_zip(cls,filename,source_by_owner):
        path=cls.root/filename
        with ZipFile(path,"w",ZIP_DEFLATED) as archive:
            for owner,body in sorted(source_by_owner.items()):
                archive.writestr("client/src/main/java/"+
                                 owner+".java",body)
        return path

    def verify(self,candidate=None,helpers=None,**overrides):
        candidate=candidate or self.twentyone_zip
        helpers=helpers or self.helper_zip
        args={
            "original_sha256":sha(self.jar),
            "six_source_sha256":sha(self.six_zip),
            "eleven_source_sha256":sha(self.eleven_zip),
            "sixteen_source_sha256":sha(self.sixteen_zip),
            "source_21_sha256":sha(candidate),
            "compiler_helper_sha256":sha(helpers),
            "original_owner":self.owner,
            "original_class_sha256":self.class_sha,
            "expected_original_methods":self.original_method_count,
            "six_previous_instructions":self.six_count,
            "eleven_previous_instructions":self.eleven_count,
            "sixteen_previous_instructions":self.sixteen_count,
            "expected_total_instructions":self.twentyone_count,
            "expected_added_instructions":
                self.twentyone_count-self.sixteen_count,
        }
        args.update(overrides)
        return verify_21_original_signlink_methods(
            self.jar,self.six_zip,self.eleven_zip,
            self.sixteen_zip,candidate,helpers,**args)

    def test_21_selected_methods_with_chained_prior_rebuilds(self):
        result=self.verify()
        self.assertEqual(21,result["verified_selected_method_count"])
        self.assertEqual(5,result["new_methods_verified"])
        self.assertEqual(self.twentyone_count,
                         result["matched_original_jvm_instructions"])
        self.assertTrue(result["selected_core_code_matches_original"])
        self.assertFalse(result["compiler_only_helpers_original_source_verified"])
        self.assertFalse(result["full_original_signlink_class_reconstructed"])
        self.assertFalse(result["whole_original_v309_client_compiles"])
        self.assertFalse(result["original_networking_or_audio_code_executed"])

    def test_changed_new_method_fails(self):
        changed=self.write_zip(
            "changed-new.zip",{self.owner:self.twentyone.replace(
                'return System.getProperty("user.home");',
                'return System.getProperty("user.dir");')})
        with self.assertRaises(R186OriginalSignlinkTwentyOneSourceError):
            self.verify(candidate=changed)

    def test_changed_earlier_selected_method_fails(self):
        changed=self.write_zip(
            "changed-prior.zip",{self.owner:self.twentyone.replace(
                "priority>10","priority>11")})
        with self.assertRaises(R186OriginalSignlinkTwentyOneSourceError):
            self.verify(candidate=changed)

    def test_unselected_run_is_not_accepted(self):
        changed=self.write_zip(
            "changed-run.zip",{self.owner:self.twentyone.replace(
                "priority+=1","priority+=9")})
        result=self.verify(candidate=changed)
        self.assertFalse(result["full_original_signlink_class_reconstructed"])
        self.assertFalse(result["unverified_methods_or_source_placeholders_accepted"])

    def test_wrong_helper_or_original_sha_rejected(self):
        for params in (
            {"original_sha256":"0"*64},
            {"six_source_sha256":"0"*64},
            {"source_21_sha256":"0"*64},
            {"compiler_helper_sha256":"0"*64},
            {"original_class_sha256":"0"*64},
            {"expected_total_instructions":self.twentyone_count+1},
        ):
            with self.subTest(params=params):
                with self.assertRaises((R186OriginalSignlinkTwentyOneSourceError,
                                        ValueError)):
                    self.verify(**params)

    def test_absent_compiler_only_helper_rejected(self):
        helpers=dict(self.helpers)
        del helpers["rs/w/c"]
        bad=self.write_zip("missing-helper.zip",helpers)
        with self.assertRaises(R186OriginalSignlinkTwentyOneSourceError):
            self.verify(helpers=bad)

    def test_source_owner_wrong_rejected(self):
        bad=self.write_zip(
            "wrong-owner.zip",
            {"synthetic/bridge/Y":self.twentyone})
        with self.assertRaises(R186OriginalSignlinkTwentyOneSourceError):
            self.verify(candidate=bad)


if __name__=="__main__":
    unittest.main()
