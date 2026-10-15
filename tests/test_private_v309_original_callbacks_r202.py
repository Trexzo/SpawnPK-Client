"""R202 synthetic unrelated Java9 callback classes and negative verification.

No SpawnPK source or client JAR is used by hosted CI. Tests compile a
separately authored original-unrelated callback scheduler and ensure exact
class/member/JVM Code comparisons reject changes instead of trusting SHA
pins alone. No classes are executed.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_original_callbacks_r202 import (
    R202OriginalCallbackError,
    verify_original_callback_java,
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R202UnrelatedSyntheticCallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK javac required")
        cls.tmp=TemporaryDirectory(prefix="r202-invented-callbacks-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.source={
            "invented/cb/b": (
                "package invented.cb;\n"
                "public interface b {void invoke();}\n"
            ),
            "invented/cb/e": (
                "package invented.cb;\n"
                "public interface e {boolean loop();}\n"
            ),
            "invented/cb/c": (
                "package invented.cb;\n"
                "import java.util.ArrayList;\n"
                "import java.util.List;\n"
                "import java.util.concurrent.ConcurrentHashMap;\n"
                "import java.util.concurrent.CopyOnWriteArrayList;\n"
                "public final class c {\n"
                "  private static final CopyOnWriteArrayList<b> a ="
                " new CopyOnWriteArrayList<>();\n"
                "  private static final ConcurrentHashMap<String,b> b ="
                " new ConcurrentHashMap<>();\n"
                "  private static final ConcurrentHashMap<String,e> c ="
                " new ConcurrentHashMap<>();\n"
                "  public c(){}\n"
                "  public static void a(b action){a.add(action);}\n"
                "  public static void a(String key,b action){b.put(key,action);}\n"
                "  public static void a(String key,e test){c.put(key,test);}\n"
                "  public static boolean a(String key){return c.containsKey(key);}\n"
                "  public static void a(){\n"
                "    if(!a.isEmpty()){\n"
                "      for(b action:a)action.invoke();\n"
                "      a.clear();\n"
                "    }\n"
                "    if(!c.isEmpty()){\n"
                "      List<String> toRemove=new ArrayList<>();\n"
                "      for(String key:c.keySet()){\n"
                "        e test=c.get(key);\n"
                "        if(!test.loop())toRemove.add(key);\n"
                "      }\n"
                "      for(String key:toRemove)c.remove(key);\n"
                "    }\n"
                "    if(!b.isEmpty()){\n"
                "      for(b action:b.values())action.invoke();\n"
                "      b.clear();\n"
                "    }\n"
                "  }\n"
                "}\n"
            ),
        }
        cls.source_zip=cls.zip_sources("invented-sources.zip",cls.source)
        srcroot=cls.root/"src"
        paths=[]
        for owner,code in cls.source.items():
            path=srcroot/(owner+".java")
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(code,encoding="utf-8")
            paths.append(str(path))
        dest=cls.root/"classes"
        empty=cls.root/"empty"
        dest.mkdir();empty.mkdir()
        compiled=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(dest),*paths],
            capture_output=True,text=True,timeout=90,check=False)
        if compiled.returncode:
            raise AssertionError("Synthetic Java9 source compilation failed: "+
                                 compiled.stderr)
        cls.original=cls.root/"invented-original.jar"
        cls.class_hashes={}
        with ZipFile(cls.original,"w",ZIP_DEFLATED) as jar:
            for owner in cls.source:
                blob=(dest/(owner+".class")).read_bytes()
                jar.writestr(owner+".class",blob)
                cls.class_hashes[owner]=hashlib.sha256(blob).hexdigest()
        profile=profile_class_field_accesses(
            (dest/"invented/cb/c.class").read_bytes())
        cls.total=sum(len(m["instructions"]) for m in profile["methods"])
        cls.fields={"invented/cb/b":0,"invented/cb/e":0,
                    "invented/cb/c":3}
        cls.methods={"invented/cb/b":1,"invented/cb/e":1,
                     "invented/cb/c":7}

    @classmethod
    def zip_sources(cls,name,sources):
        path=cls.root/name
        with ZipFile(path,"w",ZIP_DEFLATED) as z:
            for owner,content in sorted(sources.items()):
                z.writestr("client/src/main/java/"+owner+".java",content)
        return path

    def verify(self,source=None,**changes):
        source=source or self.source_zip
        params={
            "original_sha256":digest(self.original),
            "source_sha256":digest(source),
            "original_class_hashes":self.class_hashes,
            "expected_fields":self.fields,
            "expected_methods":self.methods,
            "expected_scheduler_instructions":self.total,
        }
        params.update(changes)
        return verify_original_callback_java(
            self.original,source,**params)

    def test_three_original_unrelated_owner_code_and_abi(self):
        report=self.verify()
        self.assertEqual(3,report["reconstructed_original_java_source_owners"])
        self.assertEqual(9,report["original_method_declarations_verified"])
        self.assertEqual(self.total,
                         report["original_jvm_method_instructions_matched"])
        self.assertTrue(report[
            "all_original_callback_field_and_method_abi_matched"])
        self.assertTrue(report["source_only_javac_release9"])
        self.assertFalse(report["original_callback_scheduler_executed"])
        self.assertFalse(report["entire_original_client_compiled"])

    def test_scheduler_mutation_rejected(self):
        changed=dict(self.source)
        changed["invented/cb/c"]=changed["invented/cb/c"].replace(
            "c.containsKey(key)","b.containsKey(key)")
        candidate=self.zip_sources("changed-contains.zip",changed)
        with self.assertRaises(R202OriginalCallbackError):
            self.verify(source=candidate)

    def test_changed_interface_method_rejected(self):
        changed=dict(self.source)
        changed["invented/cb/e"]=changed["invented/cb/e"].replace(
            "boolean loop()","boolean ready()")
        changed["invented/cb/c"]=changed["invented/cb/c"].replace(
            "test.loop()","test.ready()")
        candidate=self.zip_sources("changed-interface.zip",changed)
        with self.assertRaises(R202OriginalCallbackError):
            self.verify(source=candidate)

    def test_class_digests_and_expected_inventory_pinned(self):
        for change in (
            {"original_sha256":"0"*64},
            {"source_sha256":"0"*64},
            {"original_class_hashes":{
                **self.class_hashes,"invented/cb/c":"0"*64}},
            {"expected_fields":{**self.fields,"invented/cb/c":4}},
            {"expected_methods":{**self.methods,"invented/cb/c":8}},
            {"expected_scheduler_instructions":self.total+1},
        ):
            with self.subTest(change=change):
                with self.assertRaises(R202OriginalCallbackError):
                    self.verify(**change)

    def test_missing_or_extra_original_source_owner_rejected(self):
        for source_set in (
            {k:v for k,v in self.source.items()
             if k!="invented/cb/b"},
            {**self.source,"invented/cb/d":
             "package invented.cb; public interface d {}"},
        ):
            candidate=self.zip_sources(
                "owner-count-"+str(len(source_set))+".zip",source_set)
            with self.assertRaises(R202OriginalCallbackError):
                self.verify(source=candidate)


if __name__=="__main__":
    unittest.main()
