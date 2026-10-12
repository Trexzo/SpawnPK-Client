"""R92 Java 9 compiler lambda method: exact private method-reference JVM shape."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile
from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.private_lambda_method_source import (
    OriginalLambdaSourceError,recover_private_four_op_lambda,
)

@unittest.skipUnless(shutil.which("javac"),"javac required")
class OriginalLambdaSourceTests(unittest.TestCase):
    def fixture(self,root):
        files={
            "p/Owner.java":(
                'package p; public final class Owner {'
                'public static void register(){p.Register.add("save",Owner::save);}'
                'private static void save(){}'
                '}'),
            "p/Callback.java":(
                'package p; @FunctionalInterface public interface Callback {'
                'void call(); }'),
            "p/Register.java":(
                'package p; public final class Register {'
                'public static void add(String key,Callback callback){} }'),
        }
        src=root/"src";out=root/"classes"
        for path,code in files.items():
            dst=src/path;dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_text(code,encoding="utf-8")
        out.mkdir()
        process=subprocess.run(["javac","--release","9","-g:none","-proc:none",
                                "-d",str(out)]+[str(src/x) for x in files],
                               capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stdout+process.stderr)
        jar=root/"client.jar"
        with ZipFile(jar,"w") as z:
            for f in out.rglob("*.class"):
                z.write(f,f.relative_to(out).as_posix())
        return {name:profile_jar_class(jar,name) for name in (
            "p/Owner.class","p/Callback.class","p/Register.class")}
    def test_exact_original_four_jvm_ops_java9_method_reference(self):
        with tempfile.TemporaryDirectory() as td:
            profiles=self.fixture(Path(td))
            p=recover_private_four_op_lambda(
                profiles["p/Owner.class"],profiles["p/Register.class"],
                profiles["p/Callback.class"],"register",expected_target_ops=1)
            source=p["private_four_op_lambda_java_source"]
            self.assertIn('p.Register.add("save", p.Owner::save)',source)
            self.assertEqual(p["original_exact_instructions"],4)
            self.assertTrue(p["original_Java9_LambdaMetafactory_bootstrap_exact"])
            self.assertFalse(p["whole_original_client_runtime_equivalence_certified"])
    def test_tampered_string_and_bootstrap_target_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            import copy
            profiles=self.fixture(Path(td))
            owner=profiles["p/Owner.class"]
            bad=copy.deepcopy(owner)
            method=next(m for m in bad["methods"] if m["name"]=="register")
            method["instructions"][0]["constant_pool_tag"]=3
            with self.assertRaisesRegex(OriginalLambdaSourceError,"STRING_NOT_EXACT"):
                recover_private_four_op_lambda(
                    bad,profiles["p/Register.class"],profiles["p/Callback.class"],
                    "register",expected_target_ops=1)
            bad=copy.deepcopy(owner)
            bad["bootstrap_methods"][0]["arguments"][1]["method_handle"]["name"]="other"
            with self.assertRaisesRegex(OriginalLambdaSourceError,
                                        "TARGET_NOT_PRIVATE_SAVE"):
                recover_private_four_op_lambda(
                    bad,profiles["p/Register.class"],profiles["p/Callback.class"],
                    "register",expected_target_ops=1)

if __name__=="__main__":
    unittest.main()
