"""R87: real Java9 compilation, two independent method mutation vetoes."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile
from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.private_dual_method_java9_acceptance import (
    DualMethodAcceptanceError, accept_dual_method_java9,
)

@unittest.skipUnless(shutil.which("javac"),"javac required")
class DualMethodAcceptanceTests(unittest.TestCase):
    def source(self,root,a="load-ok",b="save-ok"):
        path=root/"p"/"Owner.java"
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(
            'package p; public final class Owner {'
            'private static void restore(){ System.out.println("'+a+'"); }'
            'private static void save(){ System.out.println("'+b+'"); }'
            '}',encoding="utf-8")
        return path
    def fixture(self,root):
        src=self.source(root/"original")
        classes=root/"classes"
        classes.mkdir()
        run=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-d",str(classes),str(src)],
            capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        jar=root/"original.jar"
        with ZipFile(jar,"w") as z:
            z.write(classes/"p"/"Owner.class","p/Owner.class")
        profile=profile_jar_class(jar,"p/Owner.class")
        count=tuple(len(next(m for m in profile["methods"]
                if m["name"]==n)["instructions"]) for n in ("restore","save"))
        aliases=root/"aliases.json"
        aliases.write_text(json.dumps({"schema_version":1,"aliases":[]}),encoding="utf-8")
        return jar,hashlib.sha256(jar.read_bytes()).hexdigest(),count,aliases
    def accept(self,jar,sha,counts,aliases,source,out):
        return accept_dual_method_java9(
            jar,"p/Owner.class","restore","()V","save","()V",
            source,"p/Owner.class","restore","()V","save","()V",
            aliases,aliases,out,original_sha256=sha,required_counts=counts)
    def test_true_compiler_identity_for_both_methods(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            jar,sha,counts,aliases=self.fixture(root)
            src=root/"candidate"
            self.source(src)
            output=root/"accepted"
            p=self.accept(jar,sha,counts,aliases,src,output)
            self.assertTrue(p["both_R66_R81_method_parity_gates_pass"])
            self.assertTrue((output/"candidate.private.jar").is_file())
            self.assertFalse(p["whole_client_runtime_equivalence_certified"])
    def test_saver_literal_mutation_blocks_output_even_when_loader_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            jar,sha,counts,aliases=self.fixture(root)
            src=root/"candidate"
            self.source(src,b="forged")
            output=root/"rejected"
            with self.assertRaisesRegex(DualMethodAcceptanceError,"SAVER_R66_R81"):
                self.accept(jar,sha,counts,aliases,src,output)
            self.assertFalse(output.exists())
    def test_loader_mutation_and_wrong_pin_block_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            jar,sha,counts,aliases=self.fixture(root)
            src=root/"candidate"
            self.source(src,a="forged")
            output=root/"rejected"
            with self.assertRaisesRegex(DualMethodAcceptanceError,"LOADER_R86"):
                self.accept(jar,sha,counts,aliases,src,output)
            self.assertFalse(output.exists())
            self.source(src)
            with self.assertRaisesRegex(DualMethodAcceptanceError,"LOADER_R86"):
                self.accept(jar,"0"*64,counts,aliases,src,output)
            self.assertFalse(output.exists())
    def test_v309_counts_required_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            jar,sha,counts,aliases=self.fixture(root)
            src=root/"candidate"
            self.source(src)
            with self.assertRaisesRegex(DualMethodAcceptanceError,
                                        "LOADER_ORIGINAL_697_INSTRUCTION"):
                self.accept(jar,sha,(697,364),aliases,src,root/"rejected")

if __name__=="__main__":
    unittest.main()
