"""R90 real Java9 compile: dual method + initializer + full field metadata."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile
from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.private_owner_initializer_triple_gate import (
    FullOwnerCandidateGateError,
    accept_original_v309_owner_methods_and_initializer,
)

@unittest.skipUnless(shutil.which("javac"),"javac required")
class PrivateOwnerTripleGateTests(unittest.TestCase):
    def source(self,root,*,init_value=7,load="load-ok",save="save-ok",
               field_access="public static"):
        file=root/"p"/"Owner.java"
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text(
            "package p; public final class Owner {"
            +field_access+" int value;"
            "static { value = "+str(init_value)+"; }"
            "public static void restore(){System.out.println(\""+load+"\");}"
            "private static void save(){System.out.println(\""+save+"\");}"
            "}",encoding="utf-8")
        return file
    def fixture(self,root):
        src=self.source(root/"orig")
        out=root/"classes"
        out.mkdir()
        run=subprocess.run(["javac","--release","9","-g:none","-proc:none",
                            "-d",str(out),str(src)],
                           capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        jar=root/"original.jar"
        with ZipFile(jar,"w") as z:z.write(out/"p"/"Owner.class","p/Owner.class")
        profile=profile_jar_class(jar,"p/Owner.class")
        counts=tuple(len(next(m for m in profile["methods"]
                          if m["name"]==x)["instructions"])
                     for x in ("restore","save"))
        dual=root/"dual-aliases.json"
        dual.write_text(json.dumps({"schema_version":1,"aliases":[]}),
                        encoding="utf-8")
        init=root/"init-aliases.json"
        row={"original":{"name":"value","descriptor":"I"},
             "candidate":{"name":"value","descriptor":"I"}}
        init.write_text(json.dumps({"schema_version":1,"aliases":[row]}),
                        encoding="utf-8")
        return jar,hashlib.sha256(jar.read_bytes()).hexdigest(),counts,dual,init
    def check(self,jar,sha,counts,dual,init,source,out,*,fields=1,init_writes=1):
        return accept_original_v309_owner_methods_and_initializer(
            jar,"p/Owner.class","restore","save",source,
            "p/Owner.class","restore","save",dual,dual,init,out,
            original_sha256=sha,required_method_counts=counts,
            expected_fields=fields,expected_initializer_writes=init_writes)
    def test_one_compilation_three_gates_and_class_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            jar,sha,counts,dual,init=self.fixture(root)
            src=root/"candidate";self.source(src)
            out=root/"accepted"
            report=self.check(jar,sha,counts,dual,init,src,out)
            self.assertTrue(report["both_R87_methods_passed"])
            self.assertTrue(report["R58_initializer_operand_semantics_passed"])
            self.assertTrue(report["R88_original_owner_field_metadata_passed"])
            self.assertEqual(report["original_field_declaration_differences"],0)
            self.assertTrue((out/"candidate.private.jar").is_file())
            self.assertFalse(report["whole_original_client_runtime_equivalence_certified"])
    def test_changed_initializer_rejected_after_both_methods(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            jar,sha,counts,dual,init=self.fixture(root)
            src=root/"candidate";self.source(src,init_value=8)
            out=root/"blocked"
            with self.assertRaisesRegex(FullOwnerCandidateGateError,"R58_"):
                self.check(jar,sha,counts,dual,init,src,out)
            self.assertFalse(out.exists())
    def test_changed_field_modifier_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            jar,sha,counts,dual,init=self.fixture(root)
            src=root/"candidate";self.source(src,field_access="private static")
            out=root/"blocked"
            with self.assertRaisesRegex(FullOwnerCandidateGateError,"R88_"):
                self.check(jar,sha,counts,dual,init,src,out)
            self.assertFalse(out.exists())
    def test_changed_saver_literal_and_expected_field_count_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            jar,sha,counts,dual,init=self.fixture(root)
            src=root/"candidate";self.source(src,save="changed")
            out=root/"blocked"
            with self.assertRaisesRegex(FullOwnerCandidateGateError,"R87_"):
                self.check(jar,sha,counts,dual,init,src,out)
            self.assertFalse(out.exists())
            self.source(src)
            with self.assertRaisesRegex(FullOwnerCandidateGateError,
                                        "R88_ORIGINAL_FIELD_METADATA_NOT_EXACT"):
                self.check(jar,sha,counts,dual,init,src,out,fields=126)
            self.assertFalse(out.exists())

if __name__=="__main__":
    unittest.main()
